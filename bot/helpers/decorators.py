import traceback
import functools
from datetime import datetime, timezone

from bot import config, logger


def error_handler(func):
    @functools.wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        try:
            return await func(client, update, *args, **kwargs)
        except Exception as e:
            user_id = None
            username = "Unknown"
            action = func.__name__

            if hasattr(update, "from_user") and update.from_user:
                user_id = update.from_user.id
                username = update.from_user.mention or str(user_id)
            elif hasattr(update, "message") and hasattr(update.message, "from_user"):
                user_id = update.message.from_user.id
                username = update.message.from_user.mention or str(user_id)

            tb = traceback.format_exc()
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            error_text = (
                f"<b> Error Report</b>\n\n"
                f"<b>User:</b> {username} (<code>{user_id}</code>)\n"
                f"<b>Action:</b> <code>{action}</code>\n"
                f"<b>Time:</b> <code>{now}</code>\n"
                f"<b>Error:</b> <code>{type(e).__name__}: {str(e)[:200]}</code>\n\n"
                f"<b>Traceback:</b>\n<pre>{tb[:2000]}</pre>"
            )

            try:
                await client.send_message(config.LOG_GROUP, error_text)
            except Exception:
                logger.error(f"Failed to send error log: {tb}")

            if user_id:
                try:
                    await client.send_message(
                        user_id,
                        f" <b>An error occurred</b>\n\n"
                        f"Error has been sent to our team automatically. "
                        f"We are working on this and will resolve it soon.\n"
                        f"Contact Developer: {config.DEVELOPER}"
                    )
                except Exception:
                    pass

            logger.error(f"Error in {action} for user {user_id}: {e}")

    return wrapper


def check_force_join(func):
    @functools.wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        user_id = None
        if hasattr(update, "from_user") and update.from_user:
            user_id = update.from_user.id

        if not user_id:
            return await func(client, update, *args, **kwargs)

        if user_id == config.ADMIN_ID:
            return await func(client, update, *args, **kwargs)

        for channel in [config.FORCE_CHANNEL_1, config.FORCE_CHANNEL_2]:
            try:
                member = await client.get_chat_member(channel, user_id)
                if str(member.status) in ("ChatMemberStatus.LEFT", "ChatMemberStatus.BANNED", "left", "kicked", "banned"):
                    from bot.helpers import buttons
                    text = (
                        "<b>Access Restricted</b>\n\n"
                        "You must join our channels to use this bot.\n"
                        "Join both channels and click <b>Verify</b>."
                    )
                    if hasattr(update, "message"):
                        await update.message.reply_text(
                            text,
                            reply_markup=buttons.force_join_keyboard(
                                config.FORCE_CHANNEL_1, config.FORCE_CHANNEL_2
                            ),
                        )
                    elif hasattr(update, "answer"):
                        await update.answer(
                            "Please join our channels first!",
                            show_alert=True,
                        )
                    return
            except Exception as e:
                err_str = str(e).lower()
                if "participant" in err_str:
                    from bot.helpers import buttons
                    text = (
                        "<b>Access Restricted</b>\n\n"
                        "You must join our channels to use this bot.\n"
                        "Join both channels and click <b>Verify</b>."
                    )
                    if hasattr(update, "message"):
                        await update.message.reply_text(
                            text,
                            reply_markup=buttons.force_join_keyboard(
                                config.FORCE_CHANNEL_1, config.FORCE_CHANNEL_2
                            ),
                        )
                    elif hasattr(update, "answer"):
                        await update.answer(
                            "Please join our channels first!",
                            show_alert=True,
                        )
                    return
                pass

        return await func(client, update, *args, **kwargs)

    return wrapper


def check_agreed(func):
    @functools.wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        from bot import db
        user_id = None
        if hasattr(update, "from_user") and update.from_user:
            user_id = update.from_user.id

        if not user_id:
            return await func(client, update, *args, **kwargs)

        if not await db.has_agreed(user_id):
            return

        return await func(client, update, *args, **kwargs)

    return wrapper


def check_suspended(func):
    @functools.wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        from bot import db
        user_id = None
        if hasattr(update, "from_user") and update.from_user:
            user_id = update.from_user.id

        if not user_id:
            return await func(client, update, *args, **kwargs)

        user = await db.get_user(user_id)
        if user and user.get("suspended"):
            reason = user.get("suspend_reason", "No reason provided")
            text = (
                f" <b>Account Suspended</b>\n\n"
                f"Your account has been suspended.\n"
                f"<b>Reason:</b> {reason}"
            )
            if hasattr(update, "message"):
                await update.message.reply_text(text)
            elif hasattr(update, "answer"):
                await update.answer("Your account is suspended!", show_alert=True)
            return

        return await func(client, update, *args, **kwargs)

    return wrapper


def premium_required(func):
    @functools.wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        from bot import db
        user_id = None
        if hasattr(update, "from_user") and update.from_user:
            user_id = update.from_user.id

        if not user_id:
            return await func(client, update, *args, **kwargs)

        if user_id == config.ADMIN_ID:
            return await func(client, update, *args, **kwargs)

        if not await db.is_premium(user_id):
            text = (
                " <b>Premium Feature</b>\n\n"
                "This feature is available for premium users only.\n"
                f"Upgrade for just ₹{config.PREMIUM_PRICE} to unlock unlimited features!"
            )
            from bot.helpers import buttons
            kb = buttons.payment_methods()
            if hasattr(update, "message"):
                await update.message.reply_text(text, reply_markup=kb)
            elif hasattr(update, "answer"):
                await update.answer("Premium feature! Upgrade to access.", show_alert=True)
            return

        return await func(client, update, *args, **kwargs)

    return wrapper
