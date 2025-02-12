from transformers import pipeline
import yfinance as yf
import pandas as pd


def summarize_stock_trend(stock_symbol):
   try:
       stock = yf.Ticker(stock_symbol)
       hist = stock.history(period="1y")


       # Calculate price change and trend
       start_price = hist["Close"].iloc[0]
       end_price = hist["Close"].iloc[-1]
       change_percent = ((end_price - start_price) / start_price) * 100
       trend = "upward" if change_percent > 0 else "downward"


       # Highest and lowest prices
       max_price = hist["Close"].max()
       min_price = hist["Close"].min()
       max_date = hist["Close"].idxmax().date()
       min_date = hist["Close"].idxmin().date()


       # Average daily volatility
       daily_changes = hist["Close"].pct_change().dropna() * 100
       avg_daily_change = daily_changes.abs().mean()


       # Construct a short descriptive text focusing only on numerical trends
       trend_text = (
           f"{stock_symbol} stock trend summary: "
           f"Start price: ${start_price:.2f}, End price: ${end_price:.2f}, Change: {change_percent:.2f}% ({trend}). "
           f"Highest: ${max_price:.2f} on {max_date}, Lowest: ${min_price:.2f} on {min_date}. "
           f"Average daily fluctuation: {avg_daily_change:.2f}%."
       )


       # Use generative AI to refine the stock trend summary without adding external context
       summarizer = pipeline("text-generation", model="gpt2")
       summary = summarizer(trend_text, max_length=100, min_length=50, do_sample=False, pad_token_id=50256, eos_token_id=50256)
       return summary[0]["generated_text"].rsplit(".", 1)[0] + "."
   except Exception as e:
       return f"AI analysis failed: {str(e)}"
