from pyrogram import filters, types

from bot import app, config, db
from bot.helpers import buttons
from bot.helpers.decorators import error_handler


TERMS_TEXT = (
    "<b>Terms of Service and Privacy Policy</b>\n\n"
    "<b>By using this bot, you agree to the following:</b>\n\n"
    "1. You are responsible for all activities performed through your accounts.\n"
    "2. We do not store your passwords. Only session strings are stored securely.\n"
    "3. Your data is stored in encrypted databases and never shared with third parties.\n"
    "4. We are not responsible for any account bans or restrictions from Telegram.\n"
    "5. Misuse of this bot for spam or illegal activities is strictly prohibited.\n"
    "6. We reserve the right to suspend your access at any time.\n"
    "7. Premium subscriptions are non-refundable.\n\n"
    "<b>Support:</b> @AdsGcHelper\n\n"
    "Do you agree to these terms?"
)

WELCOME_TEXT = (
    "<b>Welcome to Group Rank Helper Bot!</b>\n\n"
    "The ultimate Telegram advertising bot.\n\n"
    "<b>Add your accounts</b> and start sending messages to groups automatically.\n\n"
    "<b>Features:</b>\n"
    "- Multi-account management\n"
    "- Per-group message scheduling\n"
    "- AI chatting between accounts\n"
    "- Bulk group joining\n"
    "- Real-time stats\n"
    "- And much more!\n\n"
    "<b>Channel:</b> @AdsGcHelper"
)


@app.on_message(filters.command("start") & filters.private)
@error_handler
async def start_cmd(client, message: types.Message):
    user_id = message.from_user.id
    
    user = await db.get_user(user_id)
    if user and user.get("suspended"):
        return await message.reply_text(
            "<b>Account Suspended</b>\n\n"
            "Your account has been suspended by admin.\n"
            "<b>Reason:</b> Suspicious activity"
        )
        
    await db.add_user(user_id, message.from_user.first_name or "")

    if user_id != config.ADMIN_ID:
        is_joined = True
        for channel in [config.FORCE_CHANNEL_1, config.FORCE_CHANNEL_2]:
            try:
                member = await client.get_chat_member(channel, user_id)
                if str(member.status) in ("ChatMemberStatus.LEFT", "ChatMemberStatus.BANNED", "left", "kicked", "banned"):
                    is_joined = False
                    break
            except Exception as e:
                err_str = str(e).lower()
                if "participant" in err_str:
                    is_joined = False
                    break
                pass
        
        if not is_joined:
            return await message.reply_text(
                "<b>Access Restricted</b>\n\n"
                "You must join our channels to use this bot.\n"
                "Join both channels and click <b>Verify</b>.",
                reply_markup=buttons.force_join_keyboard(
                    config.FORCE_CHANNEL_1, config.FORCE_CHANNEL_2
                ),
            )

    user = await db.get_user(user_id)
    if user and user.get("agreed"):
        is_admin = user_id == config.ADMIN_ID
        return await message.reply_text(
            WELCOME_TEXT,
            reply_markup=buttons.main_menu(is_admin),
        )

    await message.reply_text(
        TERMS_TEXT,
        reply_markup=buttons.terms_keyboard(),
    )


@app.on_callback_query(filters.regex("^force_join_check$"))
@error_handler
async def force_join_check(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id

    is_joined = True
    for channel in [config.FORCE_CHANNEL_1, config.FORCE_CHANNEL_2]:
        try:
            member = await client.get_chat_member(channel, user_id)
            if str(member.status) in ("ChatMemberStatus.LEFT", "ChatMemberStatus.BANNED", "left", "kicked", "banned"):
                is_joined = False
                break
        except Exception as e:
            err_str = str(e).lower()
            if "participant" in err_str:
                is_joined = False
                break
            pass

    if not is_joined:
        return await callback.answer(
            "You haven't joined all channels yet!",
            show_alert=True,
        )

    accounts = await db.get_accounts(user_id)
    for acc in accounts:
        from bot import session_manager
        for channel in [config.FORCE_CHANNEL_1, config.FORCE_CHANNEL_2]:
            try:
                await session_manager.join_channel(
                    acc["session_string"],
                    f"https://t.me/{channel.replace('@', '')}"
                )
            except Exception:
                pass

    user = await db.get_user(user_id)
    await callback.message.delete()
    if user and user.get("agreed"):
        is_admin = user_id == config.ADMIN_ID
        await client.send_message(
            user_id,
            WELCOME_TEXT,
            reply_markup=buttons.main_menu(is_admin),
        )
    else:
        await client.send_message(
            user_id,
            TERMS_TEXT,
            reply_markup=buttons.terms_keyboard(),
        )


@app.on_callback_query(filters.regex("^terms_agree$"))
@error_handler
async def terms_agree(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await db.set_agreed(user_id)
    is_admin = user_id == config.ADMIN_ID
    await callback.answer("Terms accepted!", show_alert=True)
    await callback.message.delete()
    await client.send_message(
        user_id,
        WELCOME_TEXT,
        reply_markup=buttons.main_menu(is_admin),
    )


@app.on_callback_query(filters.regex("^terms_disagree$"))
@error_handler
async def terms_disagree(client, callback: types.CallbackQuery):
    await callback.answer(
        "You must agree to the terms to use this bot.",
        show_alert=True,
    )
    await callback.message.edit_text(
        "<b>Access Denied</b>\n\n"
        "You must agree to our Terms of Service to use this bot.\n"
        "Send /start to try again."
    )


@app.on_callback_query(filters.regex("^back_menu$"))
@error_handler
async def back_to_menu(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    user = await db.get_user(user_id)
    if user and user.get("suspended"):
        return await callback.message.edit_text(
            "<b>Account Suspended</b>\n\n"
            "Your account has been suspended by admin.\n"
            "<b>Reason:</b> Suspicious activity"
        )
        
    is_admin = user_id == config.ADMIN_ID
    await callback.message.edit_text(
        WELCOME_TEXT,
        reply_markup=buttons.main_menu(is_admin),
    )
