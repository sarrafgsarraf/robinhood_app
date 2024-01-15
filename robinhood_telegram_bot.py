from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters, JobQueue
import logging
from typing import Dict
import robin_helper
import secret

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Define states
LOGIN = range(1)
keyboard = [["login", "cancel"]]
action_keyboard = [["Current_Stats"], ["Portfolio_Stats"], ["Trigger_Daily_Investment"], ["BUY", "SELL"], ["cancel", "logout"]]
markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
action_markup = ReplyKeyboardMarkup(action_keyboard, one_time_keyboard=True, resize_keyboard=True)

async def send_long_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, chunk_size: int = 4096):
    for x in range(0, len(text), chunk_size):
        chunk = text[x:x+chunk_size]
        await update.message.reply_text(chunk)

# Fallback function
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Operation cancelled. Send /start to start over.', reply_markup=ReplyKeyboardRemove())
    logger.info(f"User {update.effective_user.id} sent /cancel request.")
    context.user_data.clear()
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Clear any flags indicating an ongoing conversations
    context.user_data.clear()
    # Now, start a fresh conversation
    await update.message.reply_text('Welcome! Please choose an option:', reply_markup=markup)
    logger.info(f"User {update.effective_user.id} started the bot.")

async def start_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if we are already in the login process
    if context.user_data.get('login_stage'):
        await update.message.reply_text("You are in the login process or logged in already.\nPlease continue or send /cancel to start over.")
        return LOGIN
    else:
        context.user_data.clear()  # Clear any previous state
        context.user_data['login_stage'] = 'username'  # Set the login stage to username
        if update.effective_user.id == secret.t_effective_chat_id:
            saved_user_markup = ReplyKeyboardMarkup([[secret.t_effective_user_id]], one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("Please enter your Robinhood username without @:\nYou might see your username in keyboard if you are a frequest user!\nSend /cancel to cancel request.", reply_markup=saved_user_markup)
        else:
            await update.message.reply_text("Please enter your Robinhood username without @:\nSend /cancel to cancel request.", reply_markup=ReplyKeyboardRemove())
        return LOGIN

# Login process
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text.lower()

    if 'login_stage' not in user_data:  # No stage set, something went wrong, start over
        await start(update, context)
        return ConversationHandler.END

    if user_data['login_stage'] == 'username':
        if robin_helper.check_users(text):
            logger.info(f"User {update.effective_user.id} / {text}. Was found by helper")
            context.user_data['username'] = text
            user_data['login_stage'] = '2fa'  # Change stage to 2FA
            await update.message.reply_text("Please enter your 2FA code:")
        else:
            await update.message.reply_text("The user does not exist in our DB. Send /start to try again.")
            await update.message.reply_text("Welcome! Please choose an option:", reply_markup=markup)
            context.user_data.clear()
            return ConversationHandler.END
        
    elif user_data['login_stage'] == '2fa':
        context.user_data['two_factor_auth'] = text
        context.user_data['logged_in'], context.user_data['latest_login'] = robin_helper.login(context.user_data['username'], context.user_data['two_factor_auth'])
        if context.user_data['logged_in'] is not None:
            if context.user_data['logged_in']:
                await update.message.reply_text("You are were logged in at: "+str(context.user_data['latest_login'])+ "\nPlease send /logout to log out.")
                await update.message.reply_text("How can I help you?", reply_markup=action_markup)
                logger.info(f"User {update.effective_user.id} logged in successfully at {context.user_data['latest_login']}.")
                return ConversationHandler.END
            else:
                if 'tries' not in context.user_data: context.user_data['tries'] = 1
                else: context.user_data['tries'] += 1
                tries_remaining = 3 - context.user_data['tries']
                if tries_remaining > 0:
                    await update.message.reply_text(f"Invalid 2FA code. Please try again. Tries remaining: {tries_remaining}")
                    return LOGIN
                else:
                    await update.message.reply_text("Invalid 2FA code. You have exceeded the maximum number of tries.")
                    await update.message.reply_text("Welcome! Please choose an option:", reply_markup=markup)
                    context.user_data.clear()
                    return ConversationHandler.END
        else:
            await update.message.reply_text("Login failed, please try again in a few minutes.")
            context.user_data.clear()
            return ConversationHandler.END

'''async def current_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your request was sent. It may take about 30 seconds for the results to be displayed.") 
    stock_stats, portfolio_value, all_holdings_value, cash_balance, total_return, total_today_return, current_time = await robin_helper.get_current_stats(context.user_data['username'], context.user_data['logged_in'])
    if current_time is not None:
        logger.info(f"User {update.effective_user.id} got current stats successfully at {current_time}.")
        context.user_data['stock_stats'] = stock_stats
        context.user_data['portfolio_value'] = portfolio_value
        context.user_data['all_holdings_value'] = all_holdings_value
        context.user_data['cash_balance'] = cash_balance
        context.user_data['total_return'] = total_return
        context.user_data['total_today_return'] = total_today_return
        context.user_data['stats_time'] = current_time
        await update.message.reply_text(f"Your Portfolio Stats as of {context.user_data['stats_time']}:\nPortfolio Value: ${context.user_data['portfolio_value']}\nAll Holdings Value: ${context.user_data['all_holdings_value']}\nCash Balance: ${context.user_data['cash_balance']}\nTotal Return: ${context.user_data['total_return']}\nTotal Today Return: ${context.user_data['total_today_return']}")
        await send_long_message(update, context, f"Individual Stock Performance Part 1:\n{context.user_data['stock_stats']}")'''

async def current_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Send initial loading message
    loading_message = await update.message.reply_text("Processing your request... ⏳\nIt may take about 30 seconds for the results to be displayed.")

    # Fetch the current stats - simulate this with a delay if necessary
    stock_stats, portfolio_value, all_holdings_value, cash_balance, total_return, total_today_return, current_time = await robin_helper.get_current_stats(context.user_data['username'], context.user_data['logged_in'])

    # Once the stats are fetched, edit the loading message to indicate completion
    if current_time is not None:
        logger.info(f"User {update.effective_user.id} got current stats successfully at {current_time}.")
        context.user_data['stock_stats'] = stock_stats
        context.user_data['portfolio_value'] = portfolio_value
        context.user_data['all_holdings_value'] = all_holdings_value
        context.user_data['cash_balance'] = cash_balance
        context.user_data['total_return'] = total_return
        context.user_data['total_today_return'] = total_today_return
        context.user_data['stats_time'] = current_time

        # Edit the loading message with the results
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=loading_message.message_id,
            text=f"✅ Processing complete!\nYour Portfolio Stats as of {context.user_data['stats_time']}:\n"
                 f"Portfolio Value: ${context.user_data['portfolio_value']}\n"
                 f"All Holdings Value: ${context.user_data['all_holdings_value']}\n"
                 f"Cash Balance: ${context.user_data['cash_balance']}\n"
                 f"Total Return: ${context.user_data['total_return']}\n"
                 f"Total Today Return: ${context.user_data['total_today_return']}"
        )

        # Send the individual stock performance as a separate message
        await send_long_message(update, context, f"Individual Stock Performance:\n{context.user_data['stock_stats']}")
    else:
        # If stats are not available, indicate failure
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=loading_message.message_id,
            text="❌ Unable to fetch current stats. Please try again later."
        )

# Logout the user
async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the user is actually logged in by checking for login-related data
    if 'logged_in' in context.user_data and context.user_data['logged_in'] == True:
        # Clear existing data
        status, latest_logout = robin_helper.logout(context.user_data['username'])
        context.user_data.clear()
        context.user_data['logged_in'], context.user_data['latest_logout'] = status, latest_logout
        # Send logout message
        await update.message.reply_text('You have been logged out at ' +str(context.user_data['latest_logout'])+ '\nSend /start to log in again.', reply_markup=ReplyKeyboardRemove())
        logger.info(f"User {update.effective_user.id} logged out at {context.user_data['latest_logout']}.")
    else:
        # User is not logged in, inform them accordingly
        await update.message.reply_text('You are not currently logged in.\nSelect one of the options below to restart.', reply_markup=markup)
    # End the conversation in any case
    return ConversationHandler.END

async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Inform the user
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You have been logged out due to inactivity. Your last activity was more than 12 hours ago.", reply_markup=markup)
    # Call the logout function to clear user data and end the conversation
    return await logout(update, context)

def main() -> None:
    job_queue = JobQueue()
    
    # Create the Application with your bot's token
    application = Application.builder().token(secret.t_api_key).job_queue(job_queue).build()

    # Register the /start command handler
    start_handler = CommandHandler("start", start)
    #text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)

    # Set up the ConversationHandler for login
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('(?i)^login$'), start_login)],
        states={ LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, login)], ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout)] },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,   # This allows users to restart the flow with /start
        conversation_timeout=43200)  # 12 hours 

    # Register the /logout command handler
    logout_command_handler = CommandHandler("logout", logout)
    # Register a MessageHandler for "Logout" text keyword
    logout_message_handler = MessageHandler(filters.Regex('(?i)^logout$'), logout)

    # Register the /cancel command handler
    cancel_command_handler = CommandHandler("cancel", cancel)
    # Register a MessageHandler for "Cancel" text keyword
    cancel_message_handler = MessageHandler(filters.Regex('(?i)^cancel$'), cancel)

    # Register the /login command handler
    login_command_handler = CommandHandler("login", start_login)
    # Register a MessageHandler for "Login" text keyword
    login_message_handler = MessageHandler(filters.Regex('(?i)^login$'), start_login)

    # Register the /current stats command handler
    current_stats_command_handler = CommandHandler("current_stats", current_stats)
    # Register a MessageHandler for "Current Stats" text keyword
    current_stats_message_handler = MessageHandler(filters.Regex('(?i)^current_stats$'), current_stats)

    # Add all handlers to the application
    application.add_handler(start_handler)
    application.add_handler(conv_handler)
    application.add_handler(logout_command_handler)
    application.add_handler(logout_message_handler)
    application.add_handler(cancel_command_handler)
    application.add_handler(cancel_message_handler)
    application.add_handler(login_command_handler)
    application.add_handler(login_message_handler)
    application.add_handler(current_stats_command_handler)
    application.add_handler(current_stats_message_handler)




    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()
