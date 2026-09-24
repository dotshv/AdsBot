import asyncio

from pyrogram import filters, types, errors

from bot import app, config, db
from bot.helpers import buttons
from bot.helpers.decorators import error_handler
from bot.helpers.filters import is_admin


@app.on_message(filters.command("admin") & filters.private & is_admin)
@error_handler
async def admin_cmd(client, message: types.Message):
    stats = await db.get_global_stats()
    await message.reply_text(
        f" <b>Admin Panel</b>\n\n"
        f"<b>Total Users:</b> {stats['total_users']}\n"
        f"<b>Total Accounts:</b> {stats['total_accounts']}\n"
        f"<b>Premium Users:</b> {stats['total_premium']}\n"
        f"<b>Total Messages:</b> {stats['total_messages']}",
        reply_markup=buttons.admin_panel(),
    )


@app.on_callback_query(filters.regex("^menu_admin$"))
@error_handler
async def admin_panel_cb(client, callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        return await callback.answer(" Admin only!", show_alert=True)

    stats = await db.get_global_stats()
    await callback.message.edit_text(
        f" <b>Admin Panel</b>\n\n"
        f"<b>Total Users:</b> {stats['total_users']}\n"
        f"<b>Total Accounts:</b> {stats['total_accounts']}\n"
        f"<b>Premium Users:</b> {stats['total_premium']}\n"
        f"<b>Total Messages:</b> {stats['total_messages']}",
        reply_markup=buttons.admin_panel(),
    )


@app.on_callback_query(filters.regex("^admin_stats$"))
@error_handler
async def admin_stats(client, callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        return await callback.answer(" Admin only!", show_alert=True)

    stats = await db.get_global_stats()
    await callback.message.edit_text(
        f" <b>Global Statistics</b>\n\n"
        f" <b>Total Users:</b> {stats['total_users']}\n"
        f" <b>Total Accounts:</b> {stats['total_accounts']}\n"
        f" <b>Premium Users:</b> {stats['total_premium']}\n"
        f" <b>Total Messages:</b> {stats['total_messages']}\n\n"
        f" <b>Bot:</b> @{app.username}\n"
        f" <b>Channel:</b> {config.CHANNEL}",
        reply_markup=buttons.back_to_menu(),
    )


@app.on_callback_query(filters.regex("^admin_broadcast$"))
@error_handler
async def admin_broadcast_start(client, callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        return await callback.answer(" Admin only!", show_alert=True)

    from bot.plugins.account import login_states
    login_states[callback.from_user.id] = {"step": "broadcast_msg"}
    await callback.message.edit_text(
        " <b>Broadcast</b>\n\n"
        "Send the message you want to broadcast to all users.\n"
        "Supports: Text, Photo, Video, Document, Animation.\n\n"
        "Or reply to a message with /broadcast to forward it.\n\n"
        "Type <code>cancel</code> to abort."
    )


@app.on_message(filters.command("broadcast") & filters.private & is_admin)
@error_handler
async def broadcast_cmd(client, message: types.Message):
    if not message.reply_to_message:
        from bot.plugins.account import login_states
        login_states[message.from_user.id] = {"step": "broadcast_msg"}
        return await message.reply_text(
            " Send the broadcast message.\nType <code>cancel</code> to abort."
        )
    await do_broadcast_media(client, message)


async def do_broadcast(client, message, text):
    users = await db.get_all_users()
    status_msg = await message.reply_text(
        f" Broadcasting to {len(users)} users..."
    )

    sent = 0
    failed = 0
    for user in users:
        try:
            await client.send_message(user["_id"], text)
            sent += 1
            await asyncio.sleep(0.05)
        except errors.FloodWait as fw:
            await asyncio.sleep(fw.value + 5)
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f" <b>Broadcast Complete</b>\n\n"
        f" <b>Sent:</b> {sent}\n"
        f" <b>Failed:</b> {failed}\n"
        f" <b>Total:</b> {len(users)}",
        reply_markup=buttons.back_to_menu(),
    )


async def do_broadcast_media(client, message):
    reply = message.reply_to_message
    users = await db.get_all_users()
    status_msg = await message.reply_text(
        f" Broadcasting to {len(users)} users..."
    )

    sent = 0
    failed = 0
    for user in users:
        try:
            await reply.copy(user["_id"])
            sent += 1
            await asyncio.sleep(0.05)
        except errors.FloodWait as fw:
            await asyncio.sleep(fw.value + 5)
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f" <b>Broadcast Complete</b>\n\n"
        f" <b>Sent:</b> {sent}\n"
        f" <b>Failed:</b> {failed}\n"
        f" <b>Total:</b> {len(users)}",
        reply_markup=buttons.back_to_menu(),
    )


@app.on_callback_query(filters.regex("^admin_suspend$"))
@error_handler
async def admin_suspend(client, callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        return await callback.answer(" Admin only!", show_alert=True)

    from bot.plugins.account import login_states
    login_states[callback.from_user.id] = {"step": "suspend_user"}
    await callback.message.edit_text(
        " <b>Suspend User</b>\n\n"
        "Send the user ID to suspend.\n\n"
        "Type <code>cancel</code> to abort."
    )


@app.on_message(filters.command("suspend") & filters.private & is_admin)
@error_handler
async def suspend_cmd(client, message: types.Message):
    if len(message.command) < 2:
        from bot.plugins.account import login_states
        login_states[message.from_user.id] = {"step": "suspend_user"}
        return await message.reply_text(
            "Send user ID to suspend.\nType <code>cancel</code> to abort."
        )

    try:
        target_id = int(message.command[1])
        reason = " ".join(message.command[2:]) or "No reason provided"
        await db.suspend_user(target_id, reason)
        await message.reply_text(
            f" User <code>{target_id}</code> suspended.\n"
            f"<b>Reason:</b> {reason}",
            reply_markup=buttons.back_to_menu(),
        )
        try:
            await client.send_message(
                target_id,
                f" <b>Account Suspended</b>\n\n"
                f"<b>Reason:</b> {reason}"
            )
        except Exception:
            pass
    except ValueError:
        await message.reply_text(" Invalid user ID.")


@app.on_callback_query(filters.regex("^admin_unsuspend$"))
@error_handler
async def admin_unsuspend(client, callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        return await callback.answer(" Admin only!", show_alert=True)

    from bot.plugins.account import login_states
    login_states[callback.from_user.id] = {"step": "unsuspend_user"}
    await callback.message.edit_text(
        " <b>Unsuspend User</b>\n\n"
        "Send the user ID to unsuspend.\n\n"
        "Type <code>cancel</code> to abort."
    )


@app.on_message(filters.command("unsuspend") & filters.private & is_admin)
@error_handler
async def unsuspend_cmd(client, message: types.Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /unsuspend <user_id>")

    try:
        target_id = int(message.command[1])
        await db.unsuspend_user(target_id)
        await message.reply_text(
            f" User <code>{target_id}</code> unsuspended.",
            reply_markup=buttons.back_to_menu(),
        )
        try:
            await client.send_message(
                target_id,
                " <b>Account Restored</b>\n\n"
                "Your suspension has been lifted."
            )
        except Exception:
            pass
    except ValueError:
        await message.reply_text(" Invalid user ID.")


@app.on_callback_query(filters.regex("^admin_userinfo$"))
@error_handler
async def admin_userinfo(client, callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        return await callback.answer(" Admin only!", show_alert=True)

    from bot.plugins.account import login_states
    login_states[callback.from_user.id] = {"step": "userinfo_id"}
    await callback.message.edit_text(
        " <b>User Info</b>\n\n"
        "Send the user ID to look up.\n\n"
        "Type <code>cancel</code> to abort."
    )


@app.on_message(filters.command("userinfo") & filters.private & is_admin)
@error_handler
async def userinfo_cmd(client, message: types.Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /userinfo <user_id>")

    try:
        target_id = int(message.command[1])
        user_data = await db.get_user(target_id)
        if not user_data:
            return await message.reply_text(" User not found.")

        acc_count = await db.get_account_count(target_id)
        stats = await db.get_stats(target_id)
        prem = " Yes" if user_data.get("premium") else " No"
        susp = " Yes" if user_data.get("suspended") else " No"

        await message.reply_text(
            f" <b>User Info</b>\n\n"
            f"<b>ID:</b> <code>{target_id}</code>\n"
            f"<b>Name:</b> {user_data.get('name', 'N/A')}\n"
            f"<b>Premium:</b> {prem}\n"
            f"<b>Suspended:</b> {susp}\n"
            f"<b>Accounts:</b> {acc_count}\n"
            f"<b>Messages:</b> {stats.get('total_messages', 0)}\n"
            f"<b>Joined:</b> {str(user_data.get('joined_at', 'N/A'))[:19]}",
            reply_markup=buttons.back_to_menu(),
        )
    except ValueError:
        await message.reply_text(" Invalid user ID.")


@app.on_message(filters.command("fix") & filters.private & is_admin)
@error_handler
async def fix_cmd(client, message: types.Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /fix <user_id>")

    try:
        target_id = int(message.command[1])
        await message.reply_text(f"Sending fix notification to {target_id}...")
        try:
            await client.send_message(
                target_id,
                " <b>Issue Resolved</b>\n\n"
                "We have fixed the issue you were facing. The bot codes have been updated and the bot has been restarted.\n\n"
                "Please try again now. Thank you for your patience!"
            )
            await message.reply_text(" Notification sent successfully.")
        except Exception as e:
            await message.reply_text(f" Failed to send message to user: {e}")
    except ValueError:
        await message.reply_text(" Invalid user ID.")


@app.on_message(filters.command("rmpremium") & filters.private & is_admin)
@error_handler
async def rmpremium_cmd(client, message: types.Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /rmpremium <user_id>")

    try:
        target_id = int(message.command[1])
        user_data = await db.get_user(target_id)
        
        if not user_data:
            return await message.reply_text("User not found.")
            
        await db.remove_premium(target_id)
        await message.reply_text(f"Premium removed for user <code>{target_id}</code>.")
        
        try:
            await client.send_message(
                target_id,
                "<b>Premium Expired</b>\n\nYour premium subscription has been removed by the admin."
            )
        except Exception:
            pass
    except ValueError:
        await message.reply_text("Invalid user ID.")


@app.on_message(filters.command("list") & filters.private & is_admin)
@error_handler
async def list_premium_cmd(client, message: types.Message):
    premium_users = await db.get_premium_users()
    if not premium_users:
        return await message.reply_text("No premium users found.")
    
    text = "<b>Premium Users List:</b>\n\n"
    for idx, u in enumerate(premium_users, 1):
        uid = u["_id"]
        name = u.get("name", "Unknown")
        expiry = str(u.get("premium_expiry", "Lifetime"))[:10]
        text += f"{idx}. <b>{name}</b> (<code>{uid}</code>) - {expiry}\n"
        
    # Split text if it's too long
    if len(text) > 4000:
        for x in range(0, len(text), 4000):
            await message.reply_text(text[x:x+4000])
    else:
        await message.reply_text(text)


@app.on_callback_query(filters.regex("^admin_list_premium$"))
@error_handler
async def cb_list_premium(client, callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        return await callback.answer(" Admin only!", show_alert=True)
    await list_premium_cmd(client, callback.message)


@app.on_callback_query(filters.regex("^admin_rm_premium$"))
@error_handler
async def cb_rm_premium(client, callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        return await callback.answer(" Admin only!", show_alert=True)
    await callback.message.reply_text(
        "Reply to this message with the User ID you want to remove premium from:\n"
        "(Or type /rmpremium <user_id> directly)",
        reply_markup=types.ForceReply(selective=True)
    )


@app.on_callback_query(filters.regex("^admin_fix_user$"))
@error_handler
async def cb_fix_user(client, callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        return await callback.answer(" Admin only!", show_alert=True)
    await callback.message.reply_text(
        "Reply to this message with the User ID you want to fix:\n"
        "(Or type /fix <user_id> directly)",
        reply_markup=types.ForceReply(selective=True)
    )


@app.on_message(filters.reply & filters.private & is_admin)
@error_handler
async def handle_admin_replies(client, message: types.Message):
    if not message.reply_to_message or not message.reply_to_message.text:
        return
    text = message.reply_to_message.text
    if "remove premium from" in text:
        message.command = ["rmpremium", message.text.strip()]
        await rmpremium_cmd(client, message)
    elif "fix" in text and "User ID" in text:
        message.command = ["fix", message.text.strip()]
        await fix_cmd(client, message)
    else:
        await message.reply_text(text)
