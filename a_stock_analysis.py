import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from statsmodels.tsa.arima.model import ARIMA


def get_stock_info(symbol):
   try:
       stock = yf.Ticker(symbol)
       hist = stock.history(period="1y")


       # Generate stock price trend chart (1 year)
       plt.figure(figsize=(8, 4))
       plt.plot(hist.index, hist["Close"], label="Stock Price", color="blue")
       plt.title(f"{symbol} Stock Price Trend (1 Year)")
       plt.xlabel("Date")
       plt.ylabel("Price")
       plt.legend()
       plt.grid(True)


       img = BytesIO()
       plt.savefig(img, format="png", bbox_inches='tight')
       img.seek(0)
       plot_url = base64.b64encode(img.getvalue()).decode()


       # Generate last month stock price trend chart
       hist_month = stock.history(period="1mo")
       plt.figure(figsize=(8, 4))
       plt.plot(hist_month.index, hist_month["Close"], label="Stock Price (1 Month)", color="green")
       plt.title(f"{symbol} Stock Price Trend (1 Month)")
       plt.xlabel("Date")
       plt.ylabel("Price")
       plt.legend()
       plt.grid(True)


       img_month = BytesIO()
       plt.savefig(img_month, format="png", bbox_inches='tight')
       img_month.seek(0)
       plot_url_month = base64.b64encode(img_month.getvalue()).decode()
      
       key_metrics = {
           "Market Cap": stock.info.get("marketCap", "N/A"),
           "P/B Ratio": stock.info.get("priceToBook", "N/A"),
           "P/E Ratio": stock.info.get("trailingPE", "N/A"),
           "EPS": stock.info.get("trailingEps", "N/A"),
       }


       stock_info = {
           "name": stock.info.get("longName", "Unknown"),
           "symbol": symbol,
           "plot_url": plot_url,
           "plot_url_month": plot_url_month,
           "key_metrics": key_metrics,
       }
       return stock_info
   except Exception as e:
       return {"error": f"Unable to retrieve data for {symbol}: {str(e)}"}


def predict_stock_trend(symbol):
   try:
       stock = yf.Ticker(symbol)
       hist = stock.history(period="6mo")["Close"]


       # Fit ARIMA model
       model = ARIMA(hist, order=(5, 1, 0))  # ARIMA(p=5, d=1, q=0)
       model_fit = model.fit()


       # Predict next 30 business days
       future_dates = pd.date_range(hist.index[-1], periods=30, freq="B")
       forecast = model_fit.forecast(steps=30)


       # Generate future stock price trend chart
       plt.figure(figsize=(8, 4))
       plt.plot(hist.index, hist, label="Historical Price", color="blue")
       plt.plot(future_dates, forecast, label="Predicted Price", color="red", linestyle='dashed')
       plt.title(f"{symbol} Future Stock Price Projection (ARIMA)")
       plt.xlabel("Date")
       plt.ylabel("Price")
       plt.legend()
       plt.grid(True)


       img = BytesIO()
       plt.savefig(img, format="png", bbox_inches='tight')
       img.seek(0)
       future_plot_url = base64.b64encode(img.getvalue()).decode()


       return f"Predicted future stock price ({future_dates[-1].date()}): ${forecast.iloc[-1]:.2f}", future_plot_url
   except Exception as e:
       return f"Prediction failed: {str(e)}", None
