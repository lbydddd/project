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
from flask import  session
import sqlite3
import requests
import pandas as pd
import matplotlib.pyplot as plt
from a_stock_analysis import get_stock_info, predict_stock_trend
from generative_ai import summarize_stock_trend



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

@app.route('/sentiment_analysis')
@login_required
def sentiment_analysis():
   return render_template("b_index.html")


@app.route('/stock_analysis', methods=["GET", "POST"])
@login_required
def stock_analysis():
   return render_template("search.html")

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



# ------Sentiment Analysis Start---------


API_KEY = "YOUR_API_KEY"  # 确保 API Key 可用


def get_stock_news_sentiment(ticker, api_key, news_count=20):
   """ 获取股票新闻情感数据 """
   url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&limit={news_count}&apikey={api_key}"
   response = requests.get(url)
   data = response.json()
  
   if "feed" in data:
       news_list = data["feed"][:news_count]
       news_data = []
      
       for news in news_list:
           title = news.get("title", "N/A")
           url = news.get("url", "N/A")
           sentiment_score = float(news.get("overall_sentiment_score", 0))
           relevance_score = float(news.get("relevance_score", 0.5))


           ticker_sentiment_score = 0
           ticker_relevance_score = 0
           for sentiment in news.get("ticker_sentiment", []):
               if sentiment["ticker"] == ticker:
                   ticker_sentiment_score = float(sentiment.get("ticker_sentiment_score", 0))
                   ticker_relevance_score = float(sentiment.get("relevance_score", 0.5))
                   break


           final_sentiment_score = ticker_sentiment_score if ticker_relevance_score > 0 else sentiment_score


           news_data.append({
               "title": title,
               "url": url,
               "sentiment_score": final_sentiment_score,
               "relevance_score": ticker_relevance_score if ticker_relevance_score > 0 else relevance_score
           })
      
       return pd.DataFrame(news_data)
  
   return pd.DataFrame()


def generate_sentiment_plot(df, ticker):
   """ 生成情感分析图 """
   if df.empty:
       return None


   SENTIMENT_THRESHOLD = 0.1
   RELEVANCE_THRESHOLD = 0.5


   weighted_sentiment_score = (df["sentiment_score"] * df["relevance_score"]).sum() / df["relevance_score"].sum()


   plt.figure(figsize=(8, 6))
   colors = ['red' if (s > SENTIMENT_THRESHOLD and r > RELEVANCE_THRESHOLD) else 'blue'
             for s, r in zip(df["sentiment_score"], df["relevance_score"])]


   plt.scatter(df["relevance_score"], df["sentiment_score"], c=colors, alpha=0.7, edgecolors='k', label="News Data")
   plt.axhline(y=SENTIMENT_THRESHOLD, color='gray', linestyle='--', linewidth=1, label=f"Sentiment Threshold: {SENTIMENT_THRESHOLD}")
   plt.axvline(x=RELEVANCE_THRESHOLD, color='gray', linestyle='--', linewidth=1, label=f"Relevance Threshold: {RELEVANCE_THRESHOLD}")


   plt.xlabel("Relevance Score", fontsize=12)
   plt.ylabel("Sentiment Score", fontsize=12)
   plt.title(f"{ticker} Sentiment Analysis\n Weighted Sentiment Score: {weighted_sentiment_score:.3f}", fontsize=14)
   plt.legend()


   img_path = f"static/{ticker}_sentiment_plot.png"
   plt.savefig(img_path, format='png', bbox_inches='tight')
   plt.close()


   return img_path


@app.route("/get_news", methods=["POST"])
@login_required
def get_news():
   ticker = request.form.get("ticker", "").upper()


   if not ticker:
       return jsonify({"error": "Stock ticker is required"}), 400


   news_df = get_stock_news_sentiment(ticker, API_KEY)


   if news_df.empty:
       return jsonify({"error": "No news found"}), 404


   img_path = generate_sentiment_plot(news_df, ticker)
   news_json = news_df.to_dict(orient="records")
  
   return jsonify({"ticker": ticker, "news": news_json, "plot_url": img_path})


# ------Stock Analysis Start---------




@app.route("/stock_trend_analysis", methods=["GET", "POST"])
def stock_trend_analysis():
   stock_data = None
   prediction = None
   trend_summary = None
   future_trend_plot = None
  
   if request.method == "POST":
       stock_symbol = request.form.get("stock_symbol").upper()
       stock_data = get_stock_info(stock_symbol)
       prediction, future_trend_plot = predict_stock_trend(stock_symbol)
       trend_summary = summarize_stock_trend(stock_symbol)


   return render_template("search.html", stock_data=stock_data, prediction=prediction, trend_summary=trend_summary,
                          future_trend_plot=future_trend_plot)


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
    username = data.get("username")  # 假设前端会传递用户名

    # 连接数据库，查询用户信息
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # 查询用户的 survey_data
    cursor.execute("SELECT survey_data FROM user WHERE username = ?", (username,))
    user_data = cursor.fetchone()
    conn.close()

    # 解析用户基本信息
    if user_data and user_data[0]:
        user_info = f"User Profile: {user_data[0]}\n"
    else:
        user_info = "User Profile: No additional information available.\n"

    # 生成 AI prompt
    prompt = f"Consider the following user profile when answering:\n{user_info}\nUser's message: {user_message}"


    # 生成 AI 响应
    response = model.generate_content(prompt)
    ai_reply = response.text if response else "Sorry, I couldn't understand your message."

    # **检查是否需要人工客服**
    sentiment_score = analyzer.polarity_scores(user_message)["compound"]
    if sentiment_score < -0.5 or any(keyword in user_message for keyword in TRANSFER_KEYWORDS):
        ai_reply = "💬 It looks like you may need assistance from a human agent.<br>⏰ Our customer support is available from 9:00 AM to 6:00 PM.<br>You can contact us at (65)12345678"

    # 存储对话记录
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
