import asyncio

from pyrogram import filters, types

from bot import app, db, session_manager
from bot.helpers import buttons
from bot.helpers.decorators import error_handler


@app.on_callback_query(filters.regex("^menu_join$"))
@error_handler
async def join_menu(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    accounts = await db.get_accounts(user_id)

    await callback.message.edit_text(
        f" <b>Join Groups/Channels</b>\n\n"
        f"<b>Accounts:</b> {len(accounts)}\n\n"
        f"All your accounts will join the provided links.\n"
        f"• Max 10 links per request\n"
        f"• 5-10 second delay between each join\n"
        f"• Prevents FloodWait errors",
        reply_markup=buttons.join_options(),
    )


@app.on_callback_query(filters.regex("^join_single$"))
@error_handler
async def join_single(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    accounts = await db.get_accounts(user_id)

    if not accounts:
        return await callback.answer(
            " No accounts! Add accounts first.",
            show_alert=True,
        )

    from bot.plugins.account import login_states
    login_states[user_id] = {"step": "join_links"}
    await callback.message.edit_text(
        " <b>Join Group/Channel</b>\n\n"
        "Send the Telegram group or channel link.\n\n"
        "Examples:\n"
        "• <code>https://t.me/+abcdef123</code>\n"
        "• <code>https://t.me/channelname</code>\n"
        "• <code>@groupname</code>\n\n"
        "Type <code>cancel</code> to abort."
    )


@app.on_callback_query(filters.regex("^join_bulk$"))
@error_handler
async def join_bulk(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    accounts = await db.get_accounts(user_id)

    if not accounts:
        return await callback.answer(
            " No accounts! Add accounts first.",
            show_alert=True,
        )

    from bot.plugins.account import login_states
    login_states[user_id] = {"step": "join_links"}
    await callback.message.edit_text(
        " <b>Bulk Join</b>\n\n"
        "Send up to <b>10 links</b>, one per line.\n\n"
        "Example:\n"
        "<code>https://t.me/+link1\n"
        "https://t.me/+link2\n"
        "https://t.me/channel1</code>\n\n"
        "Type <code>cancel</code> to abort."
    )
