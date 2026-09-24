from pyrogram import filters, types

from bot import app, db, config
from bot.helpers import buttons
from bot.helpers.decorators import error_handler


@app.on_callback_query(filters.regex("^menu_stats$"))
@error_handler
async def stats_menu(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id

    stats = await db.get_stats(user_id)
    acc_count = await db.get_account_count(user_id)
    groups = await db.get_groups(user_id)
    is_prem = await db.is_premium(user_id)
    seen_groups = set()
    enabled_groups = set()
    for g in groups:
        seen_groups.add(g["group_id"])
        if g.get("enabled", True):
            enabled_groups.add(g["group_id"])

    await callback.message.edit_text(
        f" <b>Your Statistics</b>\n\n"
        f" <b>Accounts:</b> {acc_count}\n"
        f" <b>Total Groups:</b> {len(seen_groups)}\n"
        f" <b>Enabled Groups:</b> {len(enabled_groups)}\n"
        f" <b>Messages Sent:</b> {stats.get('total_messages', 0)}\n"
        f" <b>Plan:</b> {'Premium' if is_prem else 'Free'}\n\n"
        f" <b>Channel:</b> {config.CHANNEL}",
        reply_markup=buttons.back_to_menu(),
    )


@app.on_message(filters.command("stats") & filters.private)
@error_handler
async def stats_cmd(client, message: types.Message):
    user_id = message.from_user.id

    if user_id == config.ADMIN_ID:
        stats = await db.get_global_stats()
        await message.reply_text(
            f" <b>Global Statistics</b>\n\n"
            f" <b>Total Users:</b> {stats['total_users']}\n"
            f" <b>Total Accounts:</b> {stats['total_accounts']}\n"
            f" <b>Premium Users:</b> {stats['total_premium']}\n"
            f" <b>Total Messages:</b> {stats['total_messages']}",
            reply_markup=buttons.back_to_menu(),
        )
    else:
        user_stats = await db.get_stats(user_id)
        acc_count = await db.get_account_count(user_id)
        is_prem = await db.is_premium(user_id)
        await message.reply_text(
            f" <b>Your Statistics</b>\n\n"
            f" <b>Accounts:</b> {acc_count}\n"
            f" <b>Messages Sent:</b> {user_stats.get('total_messages', 0)}\n"
            f" <b>Plan:</b> {'Premium' if is_prem else 'Free'}",
            reply_markup=buttons.back_to_menu(),
        )
