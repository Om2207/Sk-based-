import logging
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

# Global variable to store mass checking status
mass_checking_status = {}

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

    if query.data == "gates":
        await query.edit_message_text(
            text="Available gates:\n\n/chk - Check a single CC\n/mass - Start mass CC checking",
            parse_mode='HTML'
        )
    elif query.data == "tools":
        if str(query.from_user.id) == OWNER_ID:
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
        user_id = query.from_user.id
        if user_id in mass_checking_status:
            mass_checking_status[user_id] = False
            await query.edit_message_text("Mass checking stopped.")

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

    await update.message.reply_text("Please send a text file containing CC numbers to start mass checking.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming documents (CC list files)."""
    if not await is_user_authorized(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this feature.")
        return

    file = await context.bot.get_file(update.message.document.file_id)
    user_id = update.effective_user.id
    mass_checking_status[user_id] = True
    await mass_check_cc(update, context, file, mass_checking_status)

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