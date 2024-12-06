import requests
import pandas as pd
import time
from binance.client import Client

# Telegram bot details
bot_token = "7661939787:AAGrZZDX46NEC0e4-_jTWFiAq1ItkmE9NDs"  # Replace with your bot token
chat_id = "6818110328"  # Replace with your chat ID

# Binance API details
api_key = "hWYjyzJlBGH1ZnLUmfZp0vNGsI9P7DOK3eYeTljeqS83FxHdKAo7td48b4YFVKTo"
api_secret = "Zl4GaOFliK1VD3F5ZeQFts9XQzy9Ruqv4mzwpwhiS6i3YxzDCi1OpKetGPIxMYh6"
client = Client(api_key, api_secret)

# Symbols and configuration
symbols = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT",
    "SOLUSDT", "LTCUSDT", "MATICUSDT", "ADAUSDT", "AVAXUSDT", 
    "DOTUSDT", "SHIBUSDT", "LINKUSDT", "BCHUSDT", "TRXUSDT", 
    "UNIUSDT", "FTMUSDT", "AAVEUSDT", "SUSHIUSDT", "GALAUSDT",
    "MKRUSDT", "LUNAUSDT", "FTTUSDT", "ENJUSDT", "ZRXUSDT",
    "XLMUSDT", "NEARUSDT", "ALGOUSDT", "RUNEUSDT", "VETUSDT",
    "XTZUSDT", "BANDUSDT", "DGBUSDT", "BNTUSDT", "STMXUSDT",
    "ATOMUSDT", "CHZUSDT", "CVCUSDT"
]


time_frame = "5m"  # Default time frame; adjustable
lookback = 500  # Look back for 500 candles

# Global variables for trade tracking
initial_balance = 100000  # Starting balance
current_balance = initial_balance
total_profit = 0.0
total_loss = 0.0
active_trades = {}
last_summary_time = time.time()

# Function to send a Telegram message
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    response = requests.post(url, json=payload)
    print(response.status_code, response.text)

# Function to set a new time frame
def set_time_frame(new_time_frame):
    global time_frame
    time_frame = new_time_frame
    print(f"Time frame updated to {time_frame}")

# Function to calculate the next candle close time
def get_next_candle_close_time():
    server_time = client.get_server_time()
    current_time = int(server_time['serverTime'] / 1000)  # Convert to seconds
    interval_seconds = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}  # Add more intervals if needed
    interval = interval_seconds[time_frame]
    next_close = (current_time // interval + 1) * interval
    return next_close

# Function to get historical candlestick data from Binance
def get_historical_data(symbol):
    candles = client.get_historical_klines(symbol, time_frame, f"{lookback} min ago UTC")
    data = []
    for candle in candles:
        data.append({
            "timestamp": pd.to_datetime(candle[0], unit="ms"),
            "open": float(candle[1]),
            "high": float(candle[2]),
            "low": float(candle[3]),
            "close": float(candle[4]),
            "volume": float(candle[5]),
        })
    return pd.DataFrame(data)

# Function to check for the 9/21 crossover
def check_crossover(df):
    df["ma9"] = df["close"].rolling(window=9).mean()
    df["ma21"] = df["close"].rolling(window=21).mean()
    if df["ma9"].iloc[-2] < df["ma21"].iloc[-2] and df["ma9"].iloc[-1] > df["ma21"].iloc[-1]:
        return "BUY"
    elif df["ma9"].iloc[-2] > df["ma21"].iloc[-2] and df["ma9"].iloc[-1] < df["ma21"].iloc[-1]:
        return "SELL"
    return None

# Function to calculate position size for a $100 trade
def calculate_position_size(symbol, entry_price):
    balance_per_trade = 100  # $100 per trade
    position_size = balance_per_trade / entry_price
    return position_size

# Function to monitor active trades for SL and TP
def monitor_trades():
    global active_trades, total_profit, total_loss, current_balance

    for symbol, trade in list(active_trades.items()):
        try:
            df = get_historical_data(symbol)
            current_price = df["close"].iloc[-1]
            
            if trade["side"] == "BUY":
                if current_price <= trade["sl"]:  # Stop Loss hit
                    loss = (trade["entry"] - trade["sl"]) * trade["position_size"]
                    total_loss += loss
                    current_balance -= loss
                    send_telegram_message(
                        f"{symbol}: Stop Loss hit at {current_price:.4f}. Loss: ${loss:.2f}. Current Balance: ${current_balance:.2f}"
                    )
                    del active_trades[symbol]
                elif current_price >= trade["tp"]:  # Take Profit hit
                    profit = (trade["tp"] - trade["entry"]) * trade["position_size"]
                    total_profit += profit
                    current_balance += profit
                    send_telegram_message(
                        f"{symbol}: Take Profit hit at {current_price:.4f}. Profit: ${profit:.2f}. Current Balance: ${current_balance:.2f}"
                    )
                    del active_trades[symbol]

            elif trade["side"] == "SELL":
                if current_price >= trade["sl"]:  # Stop Loss hit
                    loss = (trade["sl"] - trade["entry"]) * trade["position_size"]
                    total_loss += loss
                    current_balance -= loss
                    send_telegram_message(
                        f"{symbol}: Stop Loss hit at {current_price:.4f}. Loss: ${loss:.2f}. Current Balance: ${current_balance:.2f}"
                    )
                    del active_trades[symbol]
                elif current_price <= trade["tp"]:  # Take Profit hit
                    profit = (trade["entry"] - trade["tp"]) * trade["position_size"]
                    total_profit += profit
                    current_balance += profit
                    send_telegram_message(
                        f"{symbol}: Take Profit hit at {current_price:.4f}. Profit: ${profit:.2f}. Current Balance: ${current_balance:.2f}"
                    )
                    del active_trades[symbol]
        except Exception as e:
            print(f"Error monitoring {symbol}: {e}")

# Function to send hourly profit/loss summary
def send_hourly_summary():
    global total_profit, total_loss, current_balance, last_summary_time
    current_time = time.time()
    if current_time - last_summary_time >= 300:
        send_telegram_message(
            f"Hourly Summary:\nTotal Balance: ${current_balance:.2f}\nTotal Profit: ${total_profit:.2f}\nTotal Loss: ${total_loss:.2f}"
        )
        last_summary_time = current_time

# Main function to monitor the market
def monitor_market():
    send_telegram_message(f"Bot started with time frame {time_frame}")
    while True:
        try:
            next_candle_time = get_next_candle_close_time()
            sleep_time = next_candle_time - int(time.time())
            print(f"Waiting for the next candle to close in {sleep_time} seconds...")
            time.sleep(max(0, sleep_time))  # Wait for the candle to close
            
            for symbol in symbols:
                try:
                    df = get_historical_data(symbol)
                    signal = check_crossover(df)
                    
                    if signal and symbol not in active_trades:
                        entry_price = df["close"].iloc[-1]
                        position_size = calculate_position_size(symbol, entry_price)
                        
                        # Determine Stop Loss and Take Profit
                        if signal == "BUY":
                            sl = df["low"].iloc[-2]
                            risk = entry_price - sl
                            tp = entry_price + (4 * risk)
                        elif signal == "SELL":
                            sl = df["high"].iloc[-2]
                            risk = sl - entry_price
                            tp = entry_price - (4 * risk)
                        
                        entry_price = round(entry_price, 4)
                        position_size = round(position_size, 4)
                        sl = round(sl, 4)
                        tp = round(tp, 4)
                        
                        active_trades[symbol] = {
                            "side": signal,
                            "entry": entry_price,
                            "sl": sl,
                            "tp": tp,
                            "position_size": position_size,
                        }
                        
                        send_telegram_message(
                            f"{symbol}: {signal} Signal detected! Entry: {entry_price:.4f}, Position Size: {position_size:.4f}, SL: {sl:.4f}, TP: {tp:.4f}, RR Ratio: 4"
                        )
                
                except Exception as e:
                    print(f"Error with {symbol}: {e}")
            
            monitor_trades()
            send_hourly_summary()
        
        except Exception as e:
            print(f"Error in main loop: {e}")

# Start the bot
monitor_market()
