import traceback
from datetime import datetime, timezone

from pyrogram import filters, types

from bot import app, config, logger


error_tracking = {}


@app.on_message(filters.command("resolve") & filters.private)
async def resolve_error(client, message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return

    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: /resolve <user_id>\n"
            "This will notify the user that their error has been resolved."
        )

    try:
        target_id = int(message.command[1])
        await client.send_message(
            target_id,
            " <b>Error Resolved</b>\n\n"
            "The error you encountered has been fixed.\n"
            "You can continue using the bot normally.\n\n"
            "Thank you for your patience! "
        )
        await message.reply_text(f" User {target_id} notified about error resolution.")
    except ValueError:
        await message.reply_text(" Invalid user ID.")
    except Exception as e:
        await message.reply_text(f" Failed to notify: {e}")


@app.on_raw_update(group=-999)
async def global_error_catcher(client, update, users, chats):
    pass
