import logging
import threading
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from config import TOKEN, OWNER_ID
from database import init_db, is_user_authorized
from cc_checker import process_cc, mass_check_cc
from auth_handler import add_user, remove_user, list_users

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables to manage mass checking and user threads
mass_checking_status = {}
user_threads = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    if await is_user_authorized(user.id):
        keyboard = [
            [InlineKeyboardButton("Gates", callback_data="gates"),
             InlineKeyboardButton("Tools", callback_data="tools")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_html(
            f"Hi {user.mention_html()}! Welcome to the CC Checker Bot.",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("You are not authorized to use this bot. Please contact the owner.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "gates":
        await query.edit_message_text(
            text="Available gates:\n\n/chk - Check a single CC\n/mass - Start mass CC checking",
            parse_mode='HTML'
        )
    elif query.data == "tools":
        if str(user_id) == OWNER_ID:
            await query.edit_message_text(
                text="Tools:\n\n/id - Get your user ID\n/add <user_id> <days> - Add a user\n/remove <user_id> - Remove a user\n/all - List all authorized users",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                text="Tools:\n\n/id - Get your user ID",
                parse_mode='HTML'
            )
    elif query.data == "stop_checking":
        if user_id in mass_checking_status and mass_checking_status[user_id]:
            mass_checking_status[user_id] = False
            if user_id in user_threads:
                user_threads[user_id].join()  # Wait for the thread to exit
                del user_threads[user_id]
            await query.edit_message_text("Mass checking stopped.")
        else:
            await query.answer("No active mass checking to stop.", show_alert=True)
    elif query.data in ["charged", "cvv_live", "ccn_live", "insufficient_funds"]:
        user_data = context.user_data
        ccs = user_data.get(query.data, [])
        if ccs:
            message = "\n".join(f"<code>{cc}</code>" for cc in ccs)
        else:
            message = f"No {query.data.replace('_', ' ')} CCs found."
        await query.message.reply_html(message)

async def chk_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /chk command."""
    if not await is_user_authorized(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /chk <CC>")
        return

    cc = context.args[0]
    result = await process_cc(cc)
    await update.message.reply_html(result['message'])

async def mass_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /mass command."""
    if not await is_user_authorized(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    # Show dynamic buttons for mass checking
    keyboard = [
        [
            InlineKeyboardButton("Charge", callback_data="charged"),
            InlineKeyboardButton("CVV Live", callback_data="cvv_live"),
            InlineKeyboardButton("CCN Live", callback_data="ccn_live"),
        ],
        [InlineKeyboardButton("Insufficient Funds", callback_data="insufficient_funds")],
        [InlineKeyboardButton("Stop Checking", callback_data="stop_checking")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Mass checking buttons are now active. Use the buttons below to view results or stop the process.",
        reply_markup=reply_markup,
    )

    await update.message.reply_text("Please send a text file containing CC numbers to start mass checking.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming documents (CC list files)."""
    if not await is_user_authorized(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this feature.")
        return

    file = await context.bot.get_file(update.message.document.file_id)
    user_id = update.effective_user.id

    # Stop any existing thread for this user
    if user_id in user_threads:
        mass_checking_status[user_id] = False
        user_threads[user_id].join()

    # Start a new thread for this user
    mass_checking_status[user_id] = True
    thread = threading.Thread(target=mass_check_cc_thread, args=(update, context, file, mass_checking_status, user_id))
    user_threads[user_id] = thread
    thread.start()

    await update.message.reply_text("Mass checking started in a separate thread. You can continue using other commands.")

def mass_check_cc_thread(update, context, file, mass_checking_status, user_id):
    """Run the mass_check_cc function in a separate thread."""
    # Create a new event loop for the thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Run the mass_check_cc function in the new event loop
    loop.run_until_complete(mass_check_cc(update, context, file, mass_checking_status))

    # Clean up
    loop.close()
    if user_id in user_threads:
        del user_threads[user_id]

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send user ID when the command /id is issued."""
    user_id = update.effective_user.id
    await update.message.reply_text(f"Your user ID is: {user_id}")

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # Initialize the database
    init_db()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("chk", chk_command))
    application.add_handler(CommandHandler("mass", mass_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("add", add_user))
    application.add_handler(CommandHandler("remove", remove_user))
    application.add_handler(CommandHandler("all", list_users))

    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Document handler for mass CC checking
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
