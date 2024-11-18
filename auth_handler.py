from telegram import Update
from telegram.ext import ContextTypes
from config import OWNER_ID
from database import add_authorized_user, remove_authorized_user, get_all_authorized_users

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a user to the authorized users list."""
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /add <user_id> <days>")
        return

    try:
        user_id = int(context.args[0])
        days = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid user ID or number of days.")
        return

    add_authorized_user(user_id, days)
    await update.message.reply_text(f"User {user_id} has been authorized for {days} days.")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a user from the authorized users list."""
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /remove <user_id>")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return

    remove_authorized_user(user_id)
    await update.message.reply_text(f"User {user_id} has been removed from the authorized users list.")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all authorized users."""
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    users = get_all_authorized_users()
    if not users:
        await update.message.reply_text("No authorized users found.")
        return

    user_list = "Authorized Users:\n\n"
    for user_id, expiration_date in users:
        user_list += f"User ID: {user_id}, Expires: {expiration_date}\n"

    await update.message.reply_text(user_list)