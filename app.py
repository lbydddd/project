from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask_cors import CORS
import google.generativeai as genai
import os
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer





app = Flask(__name__)
CORS(app)  # Enable CORS
app.config['SECRET_KEY'] = 'your_secret_key'  


BASE_DIR = os.path.abspath(os.path.dirname(__file__))  
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'users.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db) 

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    survey_data = db.Column(db.Text, default="")  

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if not user:
            flash('❌ Account does not exist. Please register first.', 'danger')
            return redirect(url_for('login'))

        if not user.check_password(password):
            flash('❌ Incorrect password. Please try again.', 'danger')
            return redirect(url_for('login'))

        login_user(user)
        flash('✅ Login successful!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('❌ Username already exists. Please choose another one.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('❌ Passwords do not match. Please re-enter.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('✅ Registration successful! Redirecting to survey...', 'success')
        return redirect(url_for('register_success', user_id=new_user.id))

    return render_template('register.html')

@app.route('/register_success/<int:user_id>')
def register_success(user_id):
    return render_template('register_success.html', user_id=user_id)

@app.route('/survey/<int:user_id>', methods=['GET', 'POST'])
def survey(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('register'))

    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        profession = request.form.get('profession')
        investment_amount = request.form.get('investment_amount')
        investment_duration = request.form.get('investment_duration')
        risk_tolerance = request.form.get('risk_tolerance')

        survey_text = f"Name: {name}; Age: {age}; Profession: {profession}; " \
                      f"Investment Amount: {investment_amount}; Investment Duration: {investment_duration}; " \
                      f"Risk Tolerance: {risk_tolerance}"

        user.survey_data = survey_text
        db.session.commit()

        flash('Survey submitted successfully! Redirecting to login...', 'success')
        return redirect(url_for('login')) 

    return render_template('survey.html', user_id=user_id)

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username)

@app.route('/stock_analysis')
@login_required
def stock_analysis():
    return "Stock Analysis Page (Coming Soon)"

@app.route('/money_transfer')
@login_required
def money_transfer():
    return render_template("index.html")



@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))





# ------Chatbot Start---------

# Configure Gemini API
genai.configure(api_key=os.getenv("MAKERSUITE"))  # Ensure the API key is set in environment variables
model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize sentiment analysis tool
analyzer = SentimentIntensityAnalyzer()

# Keywords indicating a user request for human support
TRANSFER_KEYWORDS = ["human support", "human agent", "talk to an agent", "live agent", "customer service", "speak to a representative"]

# Define the conversation database model
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)

@app.route("/ai")
def chatbot():
    """Serve the frontend HTML page."""
    return render_template("chatbot.html")

@app.route("/chat", methods=["POST"])
def chat():
    """Handle user chat requests."""
    data = request.json
    user_message = data.get("message", "").lower()  # Convert to lowercase for keyword matching

    # Perform sentiment analysis
    sentiment_score = analyzer.polarity_scores(user_message)["compound"]

    # Generate AI response using Gemini API
    response = model.generate_content(user_message)
    ai_reply = response.text if response else "Sorry, I couldn't understand your message."


    # **Check if human support is needed**
    if sentiment_score < -0.5 or any(keyword in user_message for keyword in TRANSFER_KEYWORDS):
        ai_reply = "💬 It looks like you may need assistance from a human agent.<br>⏰ Our customer support is available from 9:00 AM to 6:00 PM.<br>You can contact us at (65)12345678"

    # Store the conversation in SQLite
    new_conversation = Conversation(user_message=user_message, bot_response=ai_reply)
    db.session.add(new_conversation)
    db.session.commit()

    return jsonify({"response": ai_reply})



# ------Chatbot End---------

if __name__ == '__main__':
    # Create database if it does not exist
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8000, debug=True)
