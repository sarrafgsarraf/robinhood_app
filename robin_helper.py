import robinhood_main_app as robin 
import secret
import pyotp
from prettytable import PrettyTable

def check_users(username):  
    if username == "sarrafgsarraf": return True
    else: return False

def login(username, mfa):
    temp_code = pyotp.TOTP(secret.robinhood_mfa).now()
    if username == "sarrafgsarraf" and str(mfa) == str(temp_code):
        status, time = robin.login(secret.robinhood_username, secret.robinhood_password, secret.robinhood_mfa)
        print(status, time)
        if status == True: return status, time
        else: return False, None
    else: return False, None

def logout(username):
    if username == "sarrafgsarraf":
        status, time  = robin.logout()
        if status == True: return status, time

'''def get_current_stats(username, logged_in):
    if username == "sarrafgsarraf" and logged_in == True:
        holdings_stats, portfolio_value, all_holdings_value, cash_balance, total_return, total_today_return, current_time = robin.fetch_stats()

        # Create a PrettyTable object
        table = PrettyTable()

        # Define the column headers
        table.field_names = ["Name", "Current Price $", "Todays Return $"]
        table.align["Name"] = "l"
        table.align["Current Price $"] = "r"
        table.align["Todays Return $"] = "r"

        # Add rows to the table
        for item in holdings_stats:
            table.add_row([item['Name'], item['Current Price $'], round(item['Todays Return $'], 2)])

        # Convert the table to a string
        table_string = table.get_string()

        return table_string, round(portfolio_value, 2), round(all_holdings_value, 2), round(cash_balance, 2), round(total_return, 2), round(total_today_return, 2), current_time


async def get_current_stats(username, logged_in):
    if username == "sarrafgsarraf" and logged_in:
        holdings_stats, portfolio_value, all_holdings_value, cash_balance, total_return, total_today_return, current_time = robin.fetch_stats()

        # Determine the split index
        split_index = math.ceil(len(holdings_stats) / 2)

        # Split holdings_stats into two halves
        first_half_stats = holdings_stats[:split_index]
        second_half_stats = holdings_stats[split_index:]

        # Function to create table from stats
        def create_table(stats):
            table = PrettyTable()
            table.field_names = ["Name", "Current Price $", "Today's Return $"]
            table.align["Name"] = "l"
            table.align["Current Price $"] = "r"
            table.align["Today's Return $"] = "r"
            for item in stats: table.add_row([item['Symbol'], item['Current Price $'], round(item['Todays Return $'], 2)])
            return table.get_string()

        # Create tables for each half
        table_string_first_half = create_table(first_half_stats)
        table_string_second_half = create_table(second_half_stats)

        # Return both table strings along with the other statistics
        return (table_string_first_half, table_string_second_half, round(portfolio_value, 2), 
                round(all_holdings_value, 2), round(cash_balance, 2), 
                round(total_return, 2), round(total_today_return, 2), current_time)'''
    
async def get_current_stats(username, logged_in):
    if username == "sarrafgsarraf" and logged_in:
        # Fetch stats from your robin module
        holdings_stats, portfolio_value, all_holdings_value, cash_balance, total_return, total_today_return, current_time = robin.fetch_stats()

        # Create formatted messages for each holding
        formatted_holdings = [
            f"________________________________\n"
            f"{item['Name']}: {item['Symbol']}\n"
            f"Current Price: ${item['Current Price $']}\n"
            f"Today's Return: ${round(item['Todays Return $'], 3)}"
            for item in holdings_stats
        ]

        # Combine all formatted messages into one
        combined_holdings_message = "\n".join(formatted_holdings)

        # Return the combined message along with the other statistics
        return (combined_holdings_message, round(portfolio_value, 2), 
                round(all_holdings_value, 2), round(cash_balance, 2), 
                round(total_return, 2), round(total_today_return, 2), current_time)

