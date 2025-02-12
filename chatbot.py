import google.generativeai as genai
from config import Config
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# 配置 Gemini API
genai.configure(api_key=Config.GEMINI_API_KEY)

# 载入情感分析工具
analyzer = SentimentIntensityAnalyzer()

model = genai.GenerativeModel("gemini-1.5-flash")

def get_ai_response(user_message):
    """调用 Gemini API 生成 AI 回复，并执行情感分析"""
    
    # 情感分析
    sentiment_score = analyzer.polarity_scores(user_message)["compound"]
    if sentiment_score < -0.5:
        return "您的问题较为复杂，我们将为您转接人工客服..."

    """调用 Gemini 1.5 Flash API 生成 AI 回复"""
    response = model.generate_content(user_message)
    return response.text  # 获取 AI 生成的文本
