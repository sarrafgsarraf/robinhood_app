# %%
import robin_stocks.robinhood as r
import time
import pyotp
import os
from datetime import datetime, timedelta
import secret
import pandas as pd
pd.set_option('display.max_rows', None)
import yfinance as yf
from dateutil.rrule import rrule, WEEKLY
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import csv

def login(username, password, mfa_code):
  # Log in to Robinhood using credentials from credentials.py
  totp  = pyotp.TOTP(mfa_code).now()
  time_logged_in = 60*60*24*10

  r.authentication.login(username= username,
                          password= password,
                          expiresIn=time_logged_in,
                          scope='internal',
                          mfa_code=totp,
                          store_session=True)
  print("LOGGED INTO ROBINHOOD SUCCESSFULLY at", datetime.now())
  return True, datetime.now()


def logout():
    r.authentication.logout()
    print("LOGGED OUT OF ROBINHOOD SUCCESSFULLY at", datetime.now())
    return True, datetime.now()

#login(secret.robinhood_username,  secret.robinhood_password, secret.robinhood_mfa)
#logout()

# Function to send the email with an optional attachment
def send_email(subject, message, filename=None):
    # Set up the SMTP server
    s = smtplib.SMTP(host='smtp.gmail.com', port=587)
    s.starttls()
    
    # Login with your credentials
    MY_ADDRESS = secret.mail_username
    PASSWORD = secret.mail_password
    s.login(MY_ADDRESS, PASSWORD)

    # Create a message
    msg = MIMEMultipart()
    
    # Setup the parameters of the message
    msg['From'] = MY_ADDRESS
    msg['To'] = secret.customer_email
    msg['Subject'] = subject
    
    # Attach the body with the message instance
    msg.attach(MIMEText(message, 'plain'))
    
    # Check if the filename is provided and if the file exists
    if filename and os.path.isfile(filename):
        # Open the file as binary mode
        with open(filename, 'rb') as attachment:
            # Create a MIME part for the file
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)  # Encode to base64
            part.add_header('Content-Disposition', "attachment; filename= %s" % os.path.basename(filename))
            
            # Attach the MIME part
            msg.attach(part)
    
    # Send the email and close the connection
    s.send_message(msg)
    del msg  # Explicitly delete the message object
    s.quit()



#fucntion used in calculating days return
def get_prev_day_closing_price(symbol):
    """
    Returns the closing price of the stock from the previous trading day.
    """
    # Start with the previous day
    previous_day = datetime.now() - timedelta(days=1)
    
    # Get the historical prices for the past week
    historicals = r.stocks.get_stock_historicals(symbol, interval='day', span='week', bounds='regular')
    
    # If no data is returned, raise an exception
    if not historicals:
        raise Exception(f"No historical data found for {symbol} in the past week")

    # Adjust the date backwards until a valid trading day's data is found
    while True:
        previous_day_str = previous_day.strftime('%Y-%m-%d')
        for entry in historicals:
            if entry['begins_at'][:10] == previous_day_str:
                return float(entry['close_price'])
        # No data found for the specified day, move one day back
        previous_day -= timedelta(days=1)
        # If more than 7 days are checked, raise an exception
        if (datetime.now() - previous_day).days > 7:
            raise Exception(f"No historical data found for {symbol} on any of the previous 7 days")


#improved version to get stats. Does not set emails

def fetch_stats():
    holdings_stats = []
    tickers = []
    try:
        # Get portfolio info
        holdings = r.build_holdings()
        user_profile = r.build_user_profile()
        current_time = str(datetime.now())

        all_holdings_value = sum(float(value['equity']) for value in holdings.values())
        cash_balance = int(float(user_profile['cash']))
        portfolio_value = all_holdings_value + cash_balance

        total_return = 0.0
        total_today_return = 0.0
        for key, value in holdings.items():
            tickers.append(key)
            average_cost = float(value['average_buy_price'])
            current_price = float(value['price'])
            quantity = float(value['quantity'])
            equity = float(value['equity'])
            profit_loss = (current_price - average_cost) * quantity

            # Get the closing price from the previous day
            prev_day_closing_price = get_prev_day_closing_price(key)  # Replace this with the correct API call
            today_return = (current_price - prev_day_closing_price) * quantity

            total_return += profit_loss
            total_today_return += today_return
            holdings_stats.append({
                'Symbol': key,
                'Name': value['name'],
                'Equity $': equity,
                'Quantity': quantity,
                'Current Price $': current_price,
                'Allocation in %': (equity / portfolio_value) * 100,
                'Total Return $': profit_loss,
                'Todays Return $': today_return
            })
        return holdings_stats, portfolio_value, all_holdings_value, cash_balance, total_return, total_today_return, current_time

    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
#fetch_stats()

def print_and_export_stats(holdings_stats, portfolio_value, all_holdings_value, cash_balance, total_return, total_today_return, filename="portfolio_stats.csv"):
    current_time = str(datetime.now())
    # Open the CSV file for writing
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        
        # Print and Write the individual stock performance header
        stock_header = "Individual Stock Allocation and Profit/Loss as of " + current_time
        print("\n" + stock_header)
        writer.writerow([stock_header])
        
        # Convert holdings_stats to DataFrame, print and write to CSV
        holdings_stats_df = pd.DataFrame(holdings_stats)
        #display(holdings_stats_df)
        holdings_stats_df.to_csv(file, index=False)
        writer.writerow([])  # Add empty row for spacing in the CSV
        
        # Portfolio summary
        portfolio_summary = [
            ("Portfolio Value", "${:.2f}".format(portfolio_value)),
            ("All Holdings Value", "${:.2f}".format(all_holdings_value)),
            ("Cash Balance", "${}".format(cash_balance)),
            ("Warning", "The actual cash values might not be accurate because of unsettled orders. Verify using RobinHood online portal")
        ]
        
        # Total profit/loss
        profit_loss_symbol = "+" if total_return >= 0 else "-"
        total_profit_loss = "Total Profit/Loss", "{} ${:.2f} as of ".format(profit_loss_symbol, abs(total_return)) + current_time
        
        # Today's return
        today_return_symbol = "+" if total_today_return >= 0 else "-"
        todays_return = "Today's Return", "{} ${:.2f} as of ".format(today_return_symbol, abs(total_today_return)) + current_time
        
        # Print and write the summary and returns
        for line in portfolio_summary + [total_profit_loss, todays_return]:
            print(line[0] + ": " + line[1])
            writer.writerow(line)

#stats = fetch_stats()
#if stats is not None:
#    print_and_export_stats(*stats)
#    send_email("Portfolio Stats", "Please find the attached portfolio stats", "portfolio_stats.csv")


def get_all_open_orders():
    """
    This function fetches and prints all open orders.
    """
    try:
        # Get all open orders
        open_orders = []
        open_orders = r.orders.get_all_open_stock_orders()
        # Check if there are any open orders
        if not open_orders:
            print("No open orders.")
            return []

        order_data = []

        for order in open_orders:
            instrument_name = r.stocks.get_name_by_url(order['instrument'])

            order_data.append({
                'ID': order['id'],
                'Instrument': instrument_name,
                'Quantity': order['quantity'],
                'Type': order['type'],
                'Side': order['side'],
                'State': order['state'],
            })

        #df = pd.DataFrame(order_data)
        #display(df)
        return order_data

    except Exception as e:
        print(f"An error occurred: {e}")

#get_all_open_orders()


def execute_transactions(tickers_and_amounts, action):
    """
    This function takes in a list of ticker-amount pairs and an action (either 'buy' or 'sell') and executes the 
    transactions using the Robinhood API.
    """
    for ticker, amount in tickers_and_amounts:
        try:
            if action == 'buy':
                r.orders.order_buy_fractional_by_price(ticker, amount)
                print(f"Successfully BUY order placed for ${amount} of {ticker}")
            elif action == 'sell':
                r.orders.order_sell_fractional_by_price(ticker, amount)
                print(f"Successfully SELL order placed for ${amount} of {ticker}")
            else:
                print(f"Invalid action: {action}. Please specify either 'buy' or 'sell'")
        except Exception as e:
            print(f"An error occurred while trying to {action} {ticker}: {e}")


#execute_transactions([('VTWG', 10), ('AAPL', 10), ('CAT', 2) ,('MSFT', 20),('IYF', 10),('META', 5),('XSVM', 10),('XLE', 10),('AMZN', 5),('SCHB', 2),('LUMN', 2),('QQQ', 10),('SPY', 20),('NVDA', 10),('HON', 10),('TSLA', 30),('JNJ', 10)], 'buy')  # for buying
#execute_transactions([('AAPL', 1), ('TSLA', 1)], 'sell')  # for selling

def cancel_orders():
    """
    This function fetches all open orders and then cancels them.
    """
    try:
        # Get all open orders
        open_orders = get_all_open_orders()

        if not open_orders:  # If the open_orders list is empty
            print("No open orders to cancel.")
            return

        # Cancel each order
        for order in open_orders:
            order_id = order['ID']
            cancel_response = r.orders.cancel_stock_order(order_id)

            # Check if the cancellation was successful
            if 'detail' in cancel_response:
                print(f"Failed to cancel order {order_id}: {cancel_response['detail']}")
            else:
                print(f"Successfully canceled order {order_id}")

    except Exception as e:
        print(f"An error occurred: {e}")
    open_orders = get_all_open_orders()
    # Convert the list of dictionaries into a DataFrame
    df = pd.DataFrame(open_orders)
    # Display the DataFrame
    #display(df)

#cancel_orders()
