import time
import yfinance as yf
import pandas as pd
import datetime
import pytz
from pandas.tseries.holiday import USFederalHolidayCalendar
import os
from tqdm.auto import tqdm

def download_data(filename, tickers):
    try:
        data = yf.download(tickers, period="1d")
        data = data.swaplevel(axis=1).sort_index(axis=1)  # Swap and sort column levels
        data = data.round(4)  # Round to 3 decimal places

        # Replace index with current date and time
        current_datetime = datetime.datetime.now(pytz.timezone('US/Eastern'))
        data.index = [current_datetime for _ in range(len(data.index))]

        # If file does not exist, write with header, otherwise skip the header
        if not os.path.isfile(filename): data.to_csv(filename)
        else: data.to_csv(filename, mode='a', header=False)

        #print("Downloaded data for ", tickers)
    except Exception as e:
        print("Could not download data: ", e)
        data = pd.DataFrame()


def is_market_open():
    # Current date and time in Eastern Time
    now = datetime.datetime.now(pytz.timezone('US/Eastern'))

    # Check if today is a holiday
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start='2023-01-01', end='2025-12-31').date  # List of federal holidays
    if now.date() in holidays: return False #Change this value to True for testing only

    # Check if it's a weekday
    if now.weekday() < 5:  
        # Check if the current time is within market hours
        if datetime.time(9, 30) <= now.time() <= datetime.time(16, 0):  return True
    return False #Change this value to True for testing only

def next_market_open_time():
    # Current date and time in Eastern Time
    now = datetime.datetime.now(pytz.timezone('US/Eastern'))
    
    if now.time() > datetime.time(16, 0) or now.date().weekday() >= 5:
        # If it's after market close or it's the weekend, set the next market open to the next weekday at 9:30
        next_day = now + datetime.timedelta(days=1)
        while next_day.weekday() >= 5:  # If it's the weekend, move to the next day
            next_day += datetime.timedelta(days=1)
        next_open = pytz.timezone('US/Eastern').localize(datetime.datetime(next_day.year, next_day.month, next_day.day, 9, 30))
    elif now.time() < datetime.time(9, 30):
        # If it's before market open, set the next market open to the current day at 9:30
        next_open = pytz.timezone('US/Eastern').localize(datetime.datetime(now.year, now.month, now.day, 9, 30))
    else:
        # If it's during market hours, set the next market open to the current day at 16:00
        next_open = pytz.timezone('US/Eastern').localize(datetime.datetime(now.year, now.month, now.day, 16, 0))
    
    return next_open
    
def main():
    tickers = ["NVDA", "MSFT", "HON", "TSLA", "AAPL", "SPY", "VTWG", "XSVM", "QQQ", "GOOGL", "AMZN", "META", "JNJ", "XLE", "IYF", "ASTR", "AMT", "CAT", "SCHB", "LUMN", "WFC", "SBSW", "WAL", "CTRA", "REK", "GEO", "NOV", "DVN", "PACW", "HBAN", "NYCB", "BABA", "JD", "SIG", "COF", "CI", "LILAK", "ZM", "COHR"]

    while True:
        if is_market_open():
            now = datetime.datetime.now()
            filename = "/home/gs/stock_app/historical_stock_prices/stock_prices_" + now.strftime("%Y_%m_%d") + ".csv"  # replace with your preferred filename
            download_data(filename, tickers)
            # Create a tqdm progress bar for the chunks
            for i in tqdm(range(20),  desc="Sleeping", unit="sec"): time.sleep(1)
            
            
        if not is_market_open():
            next_open = next_market_open_time()
            sleep_seconds = (next_open - datetime.datetime.now(pytz.timezone('US/Eastern'))).total_seconds()
            print("Market is closed.")
            print("Markets will open next on:", next_open)
            print(f"Sleeping for {sleep_seconds} seconds until the next market open.")
            for i in tqdm(range(int(sleep_seconds)),  desc="Sleeping", unit="sec"): time.sleep(1)

if __name__ == "__main__":
    main()
