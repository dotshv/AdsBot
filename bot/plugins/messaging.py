import asyncio

from pyrogram import filters, types
from pyrogram.errors import FloodWait

from bot import app, db, session_manager, config
from bot.helpers import buttons
from bot.helpers.decorators import error_handler
from bot.helpers.utils import format_time

active_messaging = {}


@app.on_callback_query(filters.regex("^menu_messaging$"))
@error_handler
async def messaging_menu(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_running = user_id in active_messaging

    msg = await db.get_user_setting(user_id, "global_message")
    msg_preview = msg[:100] + "..." if msg and len(msg) > 100 else msg or "Not set"

    accounts = await db.get_accounts(user_id)
    groups = await db.get_enabled_groups(user_id)

    await callback.message.edit_text(
        f"<b>Messaging Control</b>\n\n"
        f"<b>Status:</b> {'Running' if is_running else 'Stopped'}\n"
        f"<b>Accounts:</b> {len(accounts)}\n"
        f"<b>Enabled Groups:</b> {len(groups)}\n\n"
        f"<b>Message:</b>\n<i>{msg_preview}</i>",
        reply_markup=buttons.messaging_controls(is_running),
    )


@app.on_callback_query(filters.regex("^msg_set$"))
@error_handler
async def set_message(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    from bot.plugins.account import login_states
    login_states[user_id] = {"step": "set_global_message"}
    await callback.message.edit_text(
        "<b>Set Message</b>\n\n"
        "Send the message you want to broadcast to your groups.\n\n"
        "Type <code>cancel</code> to abort."
    )


@app.on_callback_query(filters.regex("^msg_timer$"))
@error_handler
async def set_global_timer(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    from bot.plugins.account import login_states
    login_states[user_id] = {"step": "set_global_timer"}
    await callback.message.edit_text(
        "<b>Set Default Timer</b>\n\n"
        "Send the interval in seconds that will apply to <b>ALL</b> your groups.\n"
        "Minimum: 1 second.\n\n"
        "Examples:\n"
        "- <code>5</code> = 5 seconds\n"
        "- <code>30s</code> = 30 seconds\n"
        "- <code>5m</code> = 5 minutes\n"
        "- <code>1h</code> = 1 hour\n\n"
        "Type <code>cancel</code> to abort."
    )


@app.on_callback_query(filters.regex("^msg_start$"))
@error_handler
async def start_messaging(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if user_id in active_messaging:
        return await callback.answer("Already running!", show_alert=True)

    msg = await db.get_user_setting(user_id, "global_message")
    if not msg:
        return await callback.answer(
            "Set a message first!",
            show_alert=True,
        )

    accounts = await db.get_accounts(user_id)
    if not accounts:
        return await callback.answer(
            "No accounts found. Add accounts first.",
            show_alert=True,
        )

    groups = await db.get_enabled_groups(user_id)
    if not groups:
        return await callback.answer(
            "No enabled groups. Enable groups first.",
            show_alert=True,
        )

    await callback.answer("Starting message sender...")

    # State MongoDB me save karo (restart pe resume ke liye)
    await db.save_task_state(user_id, "messaging", {"active": True})

    task = asyncio.create_task(
        messaging_loop(client, user_id, msg, accounts, groups)
    )
    active_messaging[user_id] = task

    await callback.message.edit_text(
        f"<b>Messaging Started</b>\n\n"
        f"<b>Accounts:</b> {len(accounts)}\n"
        f"<b>Groups:</b> {len(groups)}\n\n"
        f"Messages are being sent one-by-one with configured intervals.\n"
        f"Click Stop to end.",
        reply_markup=buttons.messaging_controls(True),
    )


@app.on_callback_query(filters.regex("^msg_stop$"))
@error_handler
async def stop_messaging(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if user_id in active_messaging:
        active_messaging[user_id].cancel()
        del active_messaging[user_id]
        await callback.answer("Stopped.", show_alert=True)
    else:
        await callback.answer("Not running.", show_alert=True)

    # State clear karo — manual stop tha, restart pe resume mat karo
    await db.clear_task_state(user_id, "messaging")

    await callback.message.edit_text(
        "<b>Messaging Stopped</b>\n\n"
        "All message sending has been stopped.",
        reply_markup=buttons.messaging_controls(False),
    )


async def messaging_loop(client, user_id, message_text, accounts, groups):
    total_sent = 0
    try:
        while True:
            if await db.has_free_trial_expired(user_id):
                active_messaging.pop(user_id, None)
                await db.clear_task_state(user_id, "messaging")
                from bot.helpers import buttons
                try:
                    await client.send_message(
                        user_id,
                        "<b>Trial Expired</b>\n\nAapka 24 ghante ka free trial poora ho chuka hai.\nAb bot use karne ke liye aapko Premium lena padega.",
                        reply_markup=buttons.buy_premium_button()
                    )
                except Exception:
                    pass
                return

            group_intervals = {}
            all_groups = await db.get_enabled_groups(user_id)
            for g in all_groups:
                group_intervals[g["group_id"]] = g.get("interval", 60)

            for group in all_groups:
                if user_id not in active_messaging:
                    return

                group_id = group["group_id"]
                phone = group["account_phone"]

                acc = await db.get_account_by_phone(user_id, phone)
                if not acc:
                    continue

                try:
                    success = await session_manager.send_message_to_group(
                        acc["session_string"], group_id, message_text
                    )
                    if success:
                        total_sent += 1
                        await db.update_stats(user_id, messages=1)
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 5)
                except Exception:
                    pass

                interval = group_intervals.get(group_id, 60)
                await asyncio.sleep(interval)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        from bot.helpers.utils import send_error_log
        await send_error_log(client, e, user_id, "messaging_loop")
    finally:
        active_messaging.pop(user_id, None)
