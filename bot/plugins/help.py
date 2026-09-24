from pyrogram import filters, types

from bot import app, config
from bot.helpers import buttons
from bot.helpers.decorators import error_handler


HELP_TEXTS = {
    "accounts": (
        " <b>Accounts Help</b>\n\n"
        "<b>How to add an account:</b>\n"
        "1. Click <b>My Accounts</b> → <b>Add Account</b>\n"
        "2. Send your phone number with country code\n"
        "3. Enter the login code from Telegram (with spaces: 1 2 3 4 5)\n"
        "4. If 2FA is enabled, enter your password\n"
        "5. Account will be added and groups loaded automatically\n\n"
        "<b>Free Plan:</b> Max 3 accounts\n"
        "<b>Premium:</b> Unlimited accounts\n\n"
        "<b>Auto-Cleanup:</b> Invalid sessions are removed automatically "
        "and you'll be notified."
    ),
    "groups": (
        " <b>Groups Help</b>\n\n"
        "<b>How to manage groups:</b>\n"
        "1. Click <b>Groups</b> to see all groups from your accounts\n"
        "2. Tap a group name to toggle Enable/Disable\n"
        "3. Tap  to set message interval per group\n"
        "4. Click <b>Refresh</b> to reload groups from accounts\n\n"
        "<b>Intervals:</b> Minimum 1 second, no maximum\n"
        "<b>Default:</b> All groups enabled, 60 second interval"
    ),
    "messaging": (
        " <b>Messaging Help</b>\n\n"
        "<b>How to send messages:</b>\n"
        "1. Click <b>Messaging</b>\n"
        "2. Set your message text\n"
        "3. Click <b>Start Sending</b>\n"
        "4. Messages are sent one-by-one to each enabled group\n"
        "5. Each group respects its own interval setting\n"
        "6. Click <b>Stop</b> to end\n\n"
        "<b>Note:</b> Messages are sent sequentially to avoid spam detection."
    ),
    "ai": (
        " <b>AI Chat Help</b> (Premium)\n\n"
        "<b>How AI Chat works:</b>\n"
        "1. Click <b>AI Chat</b>\n"
        "2. Select groups for AI chatting\n"
        "3. Click <b>Start</b>\n"
        "4. Your accounts will chat with each other naturally\n"
        "5. 1-2 second gaps between messages\n"
        "6. Click <b>Stop</b> to end\n\n"
        "<b>Requires:</b> Premium plan + at least 2 accounts\n"
        "<b>Non-selected groups:</b> Receive normal scheduled messages"
    ),
    "premium": (
        f" <b>Premium Help</b>\n\n"
        f"<b>Price:</b> ₹{config.PREMIUM_PRICE}\n\n"
        f"<b>Features:</b>\n"
        f"├ ️ Unlimited accounts\n"
        f"├  AI Chatting\n"
        f"├  Priority support\n"
        f"└  All future features\n\n"
        f"<b>Payment Methods:</b>\n"
        f"├  Telegram Stars (Instant)\n"
        f"├  UPI\n"
        f"└  USDT (BEP20)"
    ),
    "join": (
        " <b>Join Help</b>\n\n"
        "<b>How to join groups:</b>\n"
        "1. Click <b>Join Groups</b>\n"
        "2. Choose single or bulk join\n"
        "3. Send link(s) - max 10 per request\n"
        "4. All your accounts will join with 5-10 sec delays\n\n"
        "<b>Supported links:</b>\n"
        "• <code>https://t.me/+invite_hash</code>\n"
        "• <code>https://t.me/username</code>\n"
        "• <code>@username</code>"
    ),
}


@app.on_callback_query(filters.regex("^menu_help$"))
@error_handler
async def help_menu(client, callback: types.CallbackQuery):
    await callback.message.edit_text(
        " <b>Help Center</b>\n\n"
        "Select a topic to learn more:\n\n"
        f" <b>Channel:</b> {config.CHANNEL}",
        reply_markup=buttons.help_menu(),
    )


@app.on_message(filters.command("help") & filters.private)
@error_handler
async def help_cmd(client, message: types.Message):
    await message.reply_text(
        " <b>Help Center</b>\n\n"
        "Select a topic to learn more:\n\n"
        f" <b>Channel:</b> {config.CHANNEL}",
        reply_markup=buttons.help_menu(),
    )


@app.on_callback_query(filters.regex(r"^help_(\w+)$"))
@error_handler
async def help_section(client, callback: types.CallbackQuery):
    section = callback.matches[0].group(1)
    text = HELP_TEXTS.get(section, "Section not found.")
    await callback.message.edit_text(
        text,
        reply_markup=buttons.help_back(),
    )
