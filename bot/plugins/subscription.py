from pyrogram import filters, types

from bot import app, config, db
from bot.helpers import buttons
from bot.helpers.decorators import error_handler


@app.on_callback_query(filters.regex("^menu_premium$"))
@error_handler
async def premium_menu(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_prem = await db.is_premium(user_id)

    if is_prem:
        user = await db.get_user(user_id)
        expiry = user.get("premium_expiry")
        expiry_str = str(expiry)[:19] if expiry else "Lifetime"
        await callback.message.edit_text(
            f" <b>Premium Status</b>\n\n"
            f"<b>Status:</b>  Active\n"
            f"<b>Expiry:</b> {expiry_str}\n\n"
            f"<b>Premium Features:</b>\n"
            f"├ Unlimited accounts\n"
            f"├ AI Chatting\n"
            f"├ Priority support\n"
            f"└ All future features\n\n"
            f"Enjoy your premium subscription! ",
            reply_markup=buttons.back_to_menu(),
        )
    else:
        await callback.message.edit_text(
            f" <b>Upgrade to Premium</b>\n\n"
            f"<b>Price:</b> ₹{config.PREMIUM_PRICE}\n\n"
            f"<b>Premium Features:</b>\n"
            f"├ ️ Unlimited accounts\n"
            f"├  AI Chatting\n"
            f"├  Priority support\n"
            f"└  All future features\n\n"
            f"<b>Payment Methods:</b>",
            reply_markup=buttons.payment_methods(),
        )
