from pyrogram import filters, types

from bot import app, config, db, session_manager
from bot.helpers import buttons
from bot.helpers.decorators import error_handler, check_agreed, check_suspended

login_states = {}


@app.on_callback_query(filters.regex("^menu_accounts$"))
@error_handler
async def accounts_menu(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    if not user or not user.get("agreed"):
        return await callback.answer("Please accept terms first!", show_alert=True)
    if user.get("suspended"):
        return await callback.answer("Your account is suspended!", show_alert=True)

    accounts = await db.get_accounts(user_id)
    count = len(accounts)
    is_prem = await db.is_premium(user_id)
    limit = "Unlimited" if is_prem else str(config.FREE_ACCOUNT_LIMIT)

    text = (
        f" <b>My Accounts</b>\n\n"
        f"<b>Total:</b> {count}\n"
        f"<b>Limit:</b> {limit}\n"
        f"<b>Plan:</b> {' Premium' if is_prem else ' Free'}\n\n"
        f"Select an account or add a new one:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=buttons.account_list(accounts),
    )


@app.on_callback_query(filters.regex("^acc_add$"))
@error_handler
async def add_account_start(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    if not user or not user.get("agreed"):
        return await callback.answer("Please accept terms first!", show_alert=True)
    if user.get("suspended"):
        return await callback.answer("Your account is suspended!", show_alert=True)

    is_prem = await db.is_premium(user_id)
    count = await db.get_account_count(user_id)

    if not is_prem and count >= config.FREE_ACCOUNT_LIMIT:
        return await callback.answer(
            f" Free users can only add {config.FREE_ACCOUNT_LIMIT} accounts. Upgrade to Premium!",
            show_alert=True,
        )

    login_states[user_id] = {"step": "phone"}
    await callback.message.edit_text(
        " <b>Add New Account</b>\n\n"
        "Send your <b>phone number</b> with country code.\n\n"
        "Example: <code>+919876543210</code>\n\n"
        "Type <code>cancel</code> to abort.",
        reply_markup=buttons.back_to_menu(),
    )


@app.on_message(filters.text & filters.private & ~filters.command([
    "start", "help", "admin", "broadcast", "suspend", "unsuspend",
    "stats", "userinfo",
]))
@error_handler
async def handle_text_input(client, message: types.Message):
    user_id = message.from_user.id

    if user_id not in login_states:
        return

    state = login_states[user_id]
    text = message.text.strip()

    if text.lower() == "cancel":
        state = login_states.pop(user_id, None)
        if state and "client" in state:
            try:
                await state["client"].disconnect()
            except:
                pass
        return await message.reply_text(
            "Operation cancelled.",
            reply_markup=buttons.back_to_menu(),
        )

    if state["step"] == "phone":
        phone = text.replace(" ", "")
        if not phone.startswith("+"):
            phone = "+" + phone

        if not phone[1:].isdigit() or len(phone) < 10:
            return await message.reply_text(
                " Invalid phone number. Please send with country code.\n"
                "Example: <code>+919876543210</code>"
            )

        existing = await db.get_account_by_phone(user_id, phone)
        if existing:
            return await message.reply_text(
                " This account is already added!"
            )

        status_msg = await message.reply_text(" Sending login code...")

        try:
            client_obj, phone_code_hash = await session_manager.create_session(phone)
            login_states[user_id] = {
                "step": "code",
                "phone": phone,
                "client": client_obj,
                "phone_code_hash": phone_code_hash,
            }
            await status_msg.edit_text(
                " <b>Login Code Sent!</b>\n\n"
                "A login code has been sent to your Telegram account.\n"
                "Check your Telegram app for the login notification.\n\n"
                " <b>Important:</b> Enter the code with spaces between digits.\n"
                "Example: <code>1 2 3 4 5</code>\n\n"
                "Type <code>cancel</code> to abort."
            )
        except Exception as e:
            login_states.pop(user_id, None)
            error_str = str(e)
            await status_msg.edit_text(
                f" <b>Failed to send code</b>\n\n"
                f"<b>Error:</b> <code>{error_str[:200]}</code>\n\n"
                f"Please check the phone number and try again.",
                reply_markup=buttons.back_to_menu(),
            )
            from bot.helpers.utils import send_error_log
            await send_error_log(client, e, user_id, "send_login_code")

    elif state["step"] == "code":
        hint = session_manager.format_otp_hint(text)
        if hint:
            return await message.reply_text(hint)

        code = text.replace(" ", "")
        status_msg = await message.reply_text(" Verifying code...")

        try:
            state["code"] = code
            session_string, phone = await session_manager.complete_login(
                state["client"],
                state["phone"],
                state["phone_code_hash"],
                code,
            )

            await db.add_account(user_id, phone, session_string)
            await db.update_stats(user_id, accounts=1)
            login_states.pop(user_id, None)

            for channel in [config.FORCE_CHANNEL_1, config.FORCE_CHANNEL_2]:
                try:
                    await session_manager.join_channel(
                        session_string,
                        f"https://t.me/{channel.replace('@', '')}"
                    )
                except Exception:
                    pass

            groups = await session_manager.get_dialogs_groups(session_string)
            for grp in groups:
                await db.add_group(user_id, phone, grp["id"], grp["title"])

            await status_msg.edit_text(
                f" <b>Account Added Successfully!</b>\n\n"
                f" <b>Phone:</b> <code>{phone}</code>\n"
                f" <b>Groups Found:</b> {len(groups)}\n\n"
                f"All groups have been loaded automatically.",
                reply_markup=buttons.back_to_menu(),
            )
            from bot.helpers.utils import send_log_message
            await send_log_message(
                f"<b>New Account Added</b>\n\n"
                f"<b>User:</b> {message.from_user.mention} (<code>{user_id}</code>)\n"
                f"<b>Phone:</b> <code>{phone}</code>\n"
                f"<b>Groups:</b> {len(groups)}"
            )

        except ValueError as ve:
            if "2FA_REQUIRED" in str(ve):
                login_states[user_id]["step"] = "2fa"
                await status_msg.edit_text(
                    "<b>Two-Factor Authentication</b>\n\n"
                    "This account has 2FA enabled.\n"
                    "Please send your <b>2FA password</b>.\n\n"
                    "Type <code>cancel</code> to abort."
                )
                return
            login_states.pop(user_id, None)
            await status_msg.edit_text(
                f"<b>Login Failed</b>\n\n<code>{str(ve)[:200]}</code>",
                reply_markup=buttons.back_to_menu(),
            )
        except Exception as e:
            if "SESSION_PASSWORD_NEEDED" in str(e) or "SessionPasswordNeeded" in str(type(e)):
                login_states[user_id]["step"] = "2fa"
                await status_msg.edit_text(
                    "<b>Two-Factor Authentication</b>\n\n"
                    "This account has 2FA enabled.\n"
                    "Please send your <b>2FA password</b>.\n\n"
                    "Type <code>cancel</code> to abort."
                )
                return
            login_states.pop(user_id, None)
            await status_msg.edit_text(
                f"<b>Login Failed</b>\n\n<code>{str(e)[:200]}</code>",
                reply_markup=buttons.back_to_menu(),
            )
            from bot.helpers.utils import send_error_log
            await send_error_log(client, e, user_id, "verify_code")

    elif state["step"] == "2fa":
        status_msg = await message.reply_text("Verifying 2FA password...")

        try:
            session_string, phone = await session_manager.complete_login(
                state["client"],
                state["phone"],
                state["phone_code_hash"],
                state.get("code", ""),
                password=text,
            )

            await db.add_account(user_id, phone, session_string)
            await db.update_stats(user_id, accounts=1)
            login_states.pop(user_id, None)

            for channel in [config.FORCE_CHANNEL_1, config.FORCE_CHANNEL_2]:
                try:
                    await session_manager.join_channel(
                        session_string,
                        f"https://t.me/{channel.replace('@', '')}"
                    )
                except Exception:
                    pass

            groups = await session_manager.get_dialogs_groups(session_string)
            for grp in groups:
                await db.add_group(user_id, phone, grp["id"], grp["title"])

            await status_msg.edit_text(
                f"<b>Account Added Successfully!</b>\n\n"
                f"<b>Phone:</b> <code>{phone}</code>\n"
                f"<b>Groups Found:</b> {len(groups)}\n\n"
                f"All groups have been loaded automatically.",
                reply_markup=buttons.back_to_menu(),
            )
        except Exception as e:
            login_states.pop(user_id, None)
            await status_msg.edit_text(
                f"<b>2FA Failed</b>\n\n<code>{str(e)[:200]}</code>",
                reply_markup=buttons.back_to_menu(),
            )

    elif state["step"] == "set_message":
        group_id = state.get("group_id")
        await db.set_group_message(user_id, group_id, text)
        login_states.pop(user_id, None)
        await message.reply_text(
            f" <b>Message Set!</b>\n\n"
            f"<b>Message:</b>\n{text[:200]}",
            reply_markup=buttons.back_to_menu(),
        )

    elif state["step"] == "set_custom_time":
        group_id = state["group_id"]
        phone = state.get("phone")
        if text.lower() == "cancel":
            login_states.pop(user_id, None)
            return await message.reply_text("Cancelled.")
        try:
            val = text.replace("s", "").replace("m", "").replace("h", "")
            interval = int(val)
            if "m" in text: interval *= 60
            elif "h" in text: interval *= 3600

            await db.groups_col.update_one(
                {"user_id": user_id, "account_phone": phone, "group_id": group_id},
                {"$set": {"interval": interval}}
            )
            login_states.pop(user_id, None)
            await message.reply_text(f" Interval set to {interval} seconds.")
        except ValueError:
            await message.reply_text("Invalid format. Examples: 5, 30s, 5m, 1h")

    elif state["step"] == "join_links":
        from bot.helpers.utils import extract_links
        links = extract_links(text)
        if not links:
            return await message.reply_text(
                " No valid links found. Send Telegram group/channel links.\n"
                "Example: <code>https://t.me/+abcdef</code>"
            )
        if len(links) > 10:
            return await message.reply_text(
                " Maximum 10 links per request."
            )

        login_states.pop(user_id, None)
        accounts = await db.get_accounts(user_id)
        if not accounts:
            return await message.reply_text(
                " No accounts found. Add an account first.",
                reply_markup=buttons.back_to_menu(),
            )

        status_msg = await message.reply_text(
            f" Joining {len(links)} links with {len(accounts)} accounts..."
        )

        import asyncio
        results = []
        for link in links:
            link_results = {"link": link, "success": 0, "failed": 0}
            for acc in accounts:
                try:
                    success, info = await session_manager.join_channel(
                        acc["session_string"], link
                    )
                    if success:
                        link_results["success"] += 1
                    else:
                        link_results["failed"] += 1
                except Exception:
                    link_results["failed"] += 1
                await asyncio.sleep(7)
            results.append(link_results)
            await asyncio.sleep(3)

        report = " <b>Join Report</b>\n\n"
        for r in results:
            report += f" <code>{r['link'][:40]}</code>\n"
            report += f"    {r['success']} |  {r['failed']}\n\n"

        await status_msg.edit_text(
            report,
            reply_markup=buttons.back_to_menu(),
        )

    elif state["step"] == "broadcast_msg":
        login_states.pop(user_id, None)
        from bot.plugins.admin import do_broadcast
        await do_broadcast(client, message, text)

    elif state["step"] == "suspend_user":
        try:
            target_id = int(text)
            login_states[user_id] = {"step": "suspend_reason", "target_id": target_id}
            await message.reply_text(
                f" Now send the <b>reason</b> for suspending user <code>{target_id}</code>.\n\n"
                "Type <code>cancel</code> to abort."
            )
        except ValueError:
            login_states.pop(user_id, None)
            await message.reply_text(
                " Invalid user ID.",
                reply_markup=buttons.back_to_menu(),
            )

    elif state["step"] == "suspend_reason":
        target_id = state["target_id"]
        reason = text
        await db.suspend_user(target_id, reason)
        login_states.pop(user_id, None)
        await message.reply_text(
            f" User <code>{target_id}</code> has been suspended.\n"
            f"<b>Reason:</b> {reason}",
            reply_markup=buttons.back_to_menu(),
        )
        try:
            await client.send_message(
                target_id,
                f" <b>Account Suspended</b>\n\n"
                f"Your account has been suspended by admin.\n"
                f"<b>Reason:</b> {reason}"
            )
        except Exception:
            pass

    elif state["step"] == "unsuspend_user":
        try:
            target_id = int(text)
            await db.unsuspend_user(target_id)
            login_states.pop(user_id, None)
            await message.reply_text(
                f" User <code>{target_id}</code> has been unsuspended.",
                reply_markup=buttons.back_to_menu(),
            )
            try:
                await client.send_message(
                    target_id,
                    " <b>Account Restored</b>\n\n"
                    "Your account suspension has been lifted.\n"
                    "You can now use the bot again."
                )
            except Exception:
                pass
        except ValueError:
            login_states.pop(user_id, None)
            await message.reply_text(
                " Invalid user ID.",
                reply_markup=buttons.back_to_menu(),
            )

    elif state["step"] == "userinfo_id":
        try:
            target_id = int(text)
            login_states.pop(user_id, None)
            user_data = await db.get_user(target_id)
            if not user_data:
                return await message.reply_text(
                    " User not found.",
                    reply_markup=buttons.back_to_menu(),
                )
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
                f"<b>Messages Sent:</b> {stats.get('total_messages', 0)}\n"
                f"<b>Joined:</b> {str(user_data.get('joined_at', 'N/A'))[:19]}",
                reply_markup=buttons.back_to_menu(),
            )
        except ValueError:
            login_states.pop(user_id, None)
            await message.reply_text(
                " Invalid user ID.",
                reply_markup=buttons.back_to_menu(),
            )

    elif state["step"] == "reject_reason":
        payment_id = state["payment_id"]
        pay_user_id = state["pay_user_id"]
        reason = text
        from bson import ObjectId
        await db.reject_payment(ObjectId(payment_id), reason)
        login_states.pop(user_id, None)
        await message.reply_text(
            f" Payment rejected.\n<b>Reason:</b> {reason}",
            reply_markup=buttons.back_to_menu(),
        )
        try:
            await client.send_message(
                pay_user_id,
                f" <b>Payment Rejected</b>\n\n"
                f"Your payment has been rejected.\n"
                f"<b>Reason:</b> {reason}"
            )
        except Exception:
            pass

    elif state["step"] == "set_global_message":
        await db.set_user_setting(user_id, "global_message", text)
        login_states.pop(user_id, None)
        await message.reply_text(
            f" <b>Message Set!</b>\n\n"
            f"<b>Your message:</b>\n{text[:500]}",
            reply_markup=buttons.back_to_menu(),
        )

    elif state["step"] == "set_global_timer":
        if text.lower() == "cancel":
            login_states.pop(user_id, None)
            return await message.reply_text("Cancelled.", reply_markup=buttons.back_to_menu())
        try:
            val = text.replace("s", "").replace("m", "").replace("h", "")
            interval = int(val)
            if "m" in text: interval *= 60
            if "h" in text: interval *= 3600
            if interval < 1:
                return await message.reply_text("Interval must be at least 1 second.")
            
            await db.set_all_groups_interval(user_id, interval)
            login_states.pop(user_id, None)
            
            await message.reply_text(
                f" <b>Default Timer Set!</b>\n\n"
                f"All your groups will now send messages every <b>{interval}s</b>.",
                reply_markup=buttons.back_to_menu(),
            )
        except ValueError:
            await message.reply_text("Invalid time format. Try `5`, `30s`, `5m`, etc.")



@app.on_callback_query(filters.regex(r"^acc_remove_(.+)$"))
@error_handler
async def remove_account_prompt(client, callback: types.CallbackQuery):
    phone = callback.matches[0].group(1)
    await callback.message.edit_text(
        f" <b>Remove Account</b>\n\n"
        f"Are you sure you want to remove <code>{phone}</code>?\n"
        f"This will also remove all group settings for this account.",
        reply_markup=buttons.account_remove_confirm(phone),
    )


@app.on_callback_query(filters.regex(r"^acc_confirm_remove_(.+)$"))
@error_handler
async def confirm_remove_account(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    phone = callback.matches[0].group(1)

    acc = await db.get_account_by_phone(user_id, phone)
    if acc:
        try:
            await session_manager.disconnect_client(acc["session_string"])
        except Exception:
            pass

    await db.remove_account(user_id, phone)
    await db.remove_groups_by_phone(user_id, phone)

    await callback.answer(" Account removed!", show_alert=True)

    accounts = await db.get_accounts(user_id)
    is_prem = await db.is_premium(user_id)
    limit = "Unlimited" if is_prem else str(config.FREE_ACCOUNT_LIMIT)

    await callback.message.edit_text(
        f" <b>My Accounts</b>\n\n"
        f"<b>Total:</b> {len(accounts)}\n"
        f"<b>Limit:</b> {limit}\n"
        f"<b>Plan:</b> {' Premium' if is_prem else ' Free'}\n\n"
        f"Select an account or add a new one:",
        reply_markup=buttons.account_list(accounts),
    )


@app.on_callback_query(filters.regex(r"^acc_info_(.+)$"))
@error_handler
async def account_info(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    phone = callback.matches[0].group(1)

    acc = await db.get_account_by_phone(user_id, phone)
    if not acc:
        return await callback.answer("Account not found!", show_alert=True)

    added = str(acc.get("added_at", "N/A"))[:19]
    await callback.message.edit_text(
        f" <b>Account Details</b>\n\n"
        f"<b>Phone:</b> <code>{phone}</code>\n"
        f"<b>Added:</b> {added}\n"
        f"<b>Status:</b>  Active",
        reply_markup=buttons.account_remove_confirm(phone),
    )
