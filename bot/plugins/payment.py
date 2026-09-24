from pyrogram import filters, types
from bson import ObjectId

from bot import app, config, db
from bot.helpers import buttons
from bot.helpers.decorators import error_handler


@app.on_callback_query(filters.regex("^pay_stars$"))
@error_handler
async def pay_with_stars(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id

    import requests
    try:
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendInvoice"
        payload = {
            "chat_id": user_id,
            "title": "AdsBot Premium (30 Days)",
            "description": "Upgrade to Premium for unlimited accounts, AI chatting, and more! Valid for 30 days.",
            "payload": f"premium_{user_id}",
            "currency": "XTR",
            "prices": [{"label": "Premium Plan", "amount": config.PREMIUM_STARS}]
        }
        res = requests.post(url, json=payload).json()
        if not res.get("ok"):
            raise Exception(res.get("description", "Unknown API error"))
        
        await callback.answer("Invoice sent!", show_alert=False)
    except Exception as e:
        await callback.answer(f"Error: {str(e)[:100]}", show_alert=True)


@app.on_callback_query(filters.regex("^__never_match_pre_checkout__$"))
@error_handler
async def pre_checkout_placeholder(client, callback):
    # pre_checkout_query is handled via stars payment flow
    pass


def is_successful_payment(_, __, message: types.Message):
    return bool(getattr(message, "successful_payment", None))

successful_payment_filter = filters.create(is_successful_payment)

@app.on_message(successful_payment_filter & filters.private)
@error_handler
async def successful_payment(client, message: types.Message):
    user_id = message.from_user.id
    from datetime import datetime, timezone, timedelta
    expiry_date = datetime.now(timezone.utc) + timedelta(days=30)
    await db.set_premium(user_id, expiry=expiry_date)
    await db.add_payment(user_id, "telegram_stars", config.PREMIUM_STARS)

    await message.reply_text(
        " <b>Payment Successful!</b>\n\n"
        " Your premium subscription has been activated!\n\n"
        "<b>Premium Features:</b>\n"
        "├ ️ Unlimited accounts\n"
        "├  AI Chatting\n"
        "├  Priority support\n"
        "└  All future features\n\n"
        "Thank you for your purchase!",
        reply_markup=buttons.back_to_menu(),
    )

    from bot.helpers.utils import send_log_message
    await send_log_message(
        f"<b>Telegram Stars Payment</b>\n\n"
        f"<b>User:</b> {message.from_user.mention} (<code>{user_id}</code>)\n"
        f"<b>Amount:</b> {config.PREMIUM_STARS} stars\n"
        f"<b>Status:</b> Auto-approved"
    )


@app.on_callback_query(filters.regex("^pay_upi$"))
@error_handler
async def pay_with_upi(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text(
        f" <b>Pay with UPI</b>\n\n"
        f"<b>Amount:</b> ₹{config.PREMIUM_PRICE}\n"
        f"<b>UPI ID:</b> <code>{config.UPI_ID}</code>\n\n"
        f"1️⃣ Send ₹{config.PREMIUM_PRICE} to the UPI ID above\n"
        f"2️⃣ Take a screenshot of the payment\n"
        f"3️⃣ Send the screenshot here\n\n"
        f"Waiting for your payment screenshot...",
        reply_markup=buttons.back_to_menu(),
    )
    await db.set_user_setting(user_id, "pending_payment", "upi")


@app.on_callback_query(filters.regex("^pay_usdt$"))
@error_handler
async def pay_with_usdt(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    usdt_addr = config.USDT_ADDRESS or "Contact @dotshv for USDT address"
    await callback.message.edit_text(
        f" <b>Pay with USDT (BEP20)</b>\n\n"
        f"<b>Amount:</b> ${config.USDT_PRICE}\n"
        f"<b>Address:</b> <code>{usdt_addr}</code>\n\n"
        f"1️⃣ Send ${config.USDT_PRICE} to the address above\n"
        f"2️⃣ Take a screenshot of the transaction\n"
        f"3️⃣ Send the screenshot here\n\n"
        f"Waiting for your payment screenshot...",
        reply_markup=buttons.back_to_menu(),
    )
    await db.set_user_setting(user_id, "pending_payment", "usdt")


@app.on_message(filters.photo & filters.private)
@error_handler
async def handle_screenshot(client, message: types.Message):
    user_id = message.from_user.id
    pending = await db.get_user_setting(user_id, "pending_payment")

    if not pending:
        return

    await db.set_user_setting(user_id, "pending_payment", None)

    photo_file_id = message.photo.file_id
    payment_id = await db.add_payment(
        user_id, pending, config.PREMIUM_PRICE, photo_file_id
    )

    await message.reply_text(
        " <b>Screenshot Received!</b>\n\n"
        "Your payment is being reviewed by admin.\n"
        "You will be notified once it's approved or rejected.\n\n"
        " Usually takes a few minutes.",
        reply_markup=buttons.back_to_menu(),
    )

    try:
        user_mention = message.from_user.mention or str(user_id)
        await client.send_photo(
            config.ADMIN_ID,
            photo=photo_file_id,
            caption=(
                f" <b>New Payment Screenshot</b>\n\n"
                f"<b>User:</b> {user_mention} (<code>{user_id}</code>)\n"
                f"<b>Method:</b> {pending.upper()}\n"
                f"<b>Amount:</b> ₹{config.PREMIUM_PRICE}\n"
                f"<b>Payment ID:</b> <code>{payment_id}</code>"
            ),
            reply_markup=buttons.payment_approve_reject(str(payment_id), user_id),
        )
    except Exception:
        from bot.helpers.utils import send_log_message
        await send_log_message(
            f"Failed to send payment screenshot to admin.\n"
            f"User: {user_id}, Payment: {payment_id}"
        )


@app.on_callback_query(filters.regex(r"^pay_approve_(.+)_(\d+)$"))
@error_handler
async def approve_payment(client, callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        return await callback.answer(" Admin only!", show_alert=True)

    payment_id = callback.matches[0].group(1)
    pay_user_id = int(callback.matches[0].group(2))

    await db.approve_payment(ObjectId(payment_id))
    from datetime import datetime, timezone, timedelta
    expiry_date = datetime.now(timezone.utc) + timedelta(days=30)
    await db.set_premium(pay_user_id, expiry=expiry_date)

    await callback.answer(" Approved!", show_alert=True)
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n <b>APPROVED</b>"
    )

    try:
        await client.send_message(
            pay_user_id,
            " <b>Payment Approved!</b>\n\n"
            " Your premium subscription has been activated!\n\n"
            "<b>Premium Features:</b>\n"
            "├ ️ Unlimited accounts\n"
            "├  AI Chatting\n"
            "├  Priority support\n"
            "└  All future features\n\n"
            "Thank you for your purchase!",
            reply_markup=buttons.back_to_menu(),
        )
    except Exception:
        pass


@app.on_callback_query(filters.regex(r"^pay_reject_(.+)_(\d+)$"))
@error_handler
async def reject_payment(client, callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        return await callback.answer(" Admin only!", show_alert=True)

    payment_id = callback.matches[0].group(1)
    pay_user_id = int(callback.matches[0].group(2))

    from bot.plugins.account import login_states
    login_states[callback.from_user.id] = {
        "step": "reject_reason",
        "payment_id": payment_id,
        "pay_user_id": pay_user_id,
    }

    await callback.answer(" Send rejection reason", show_alert=True)
    await callback.message.reply_text(
        f" Send the rejection reason for payment <code>{payment_id}</code>:"
    )
