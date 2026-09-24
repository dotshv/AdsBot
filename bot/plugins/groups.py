from pyrogram import filters, types
import pyrogram.errors

from bot import app, db, session_manager
from bot.helpers import buttons
from bot.helpers.decorators import error_handler
from bot.helpers.utils import format_time


@app.on_callback_query(filters.regex("^menu_groups$"))
@error_handler
async def groups_menu(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    accounts = await db.get_accounts(user_id)

    if not accounts:
        return await callback.message.edit_text(
            " <b>Accounts List</b>\n\n"
            "No accounts found. Add accounts first.",
            reply_markup=buttons.back_to_menu(),
        )

    await callback.message.edit_text(
        " <b>Select Account</b>\n\n"
        "Tap an account to manage its groups:",
        reply_markup=buttons.account_select_groups(accounts),
    )

@app.on_callback_query(filters.regex(r"^grp_acc_(\+?\d+)$"))
@error_handler
async def account_groups_menu(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    phone = callback.matches[0].group(1)
    
    groups = await db.get_groups_by_phone(user_id, phone)

    try:
        await callback.message.edit_text(
            f" <b>Group List:</b> {phone}\n\n"
            "Tap a group to manage its settings:",
            reply_markup=buttons.group_list(groups, phone=phone, page=1),
        )
    except pyrogram.errors.MessageNotModified:
        pass


@app.on_callback_query(filters.regex(r"^grp_page_(\+?\d+)_(\d+)$"))
@error_handler
async def groups_menu_page(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    phone = callback.matches[0].group(1)
    page = int(callback.matches[0].group(2))
    
    groups = await db.get_groups_by_phone(user_id, phone)

    try:
        await callback.message.edit_reply_markup(
            reply_markup=buttons.group_list(groups, phone=phone, page=page),
        )
    except pyrogram.errors.MessageNotModified:
        pass
    await callback.answer()


@app.on_callback_query(filters.regex(r"^grp_manage_(\+?\d+)_(-?\d+)$"))
@error_handler
async def manage_group(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    phone = callback.matches[0].group(1)
    group_id = int(callback.matches[0].group(2))

    grp = await db.groups_col.find_one({"user_id": user_id, "account_phone": phone, "group_id": group_id})
    if not grp:
        return await callback.answer("Group not found!", show_alert=True)

    title = grp.get("group_title", "Unknown")
    interval = grp.get("interval", 60)
    enabled = grp.get("enabled", True)
    status = "Enabled" if enabled else "Disabled"

    text = (
        f" <b>Group Details</b>\n\n"
        f"<b>Title:</b> {title}\n"
        f"<b>Status:</b> {status}\n"
        f"<b>Time Interval:</b> {format_time(interval)}\n\n"
        f"Choose an option below:"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=buttons.group_details(grp, phone=phone),
        )
    except pyrogram.errors.MessageNotModified:
        pass


@app.on_callback_query(filters.regex(r"^grp_toggle_(\+?\d+)_(-?\d+)$"))
@error_handler
async def toggle_group(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    phone = callback.matches[0].group(1)
    group_id = int(callback.matches[0].group(2))

    grp = await db.groups_col.find_one({"user_id": user_id, "account_phone": phone, "group_id": group_id})
    if not grp:
        return await callback.answer("Group not found!")

    new_state = not grp.get("enabled", True)
    await db.groups_col.update_one(
        {"user_id": user_id, "account_phone": phone, "group_id": group_id},
        {"$set": {"enabled": new_state}}
    )

    status = "enabled" if new_state else "disabled"
    await callback.answer(f"Group {status}", show_alert=False)

    grp = await db.groups_col.find_one({"user_id": user_id, "account_phone": phone, "group_id": group_id})
    
    title = grp.get("group_title", "Unknown")
    interval = grp.get("interval", 60)
    enabled = grp.get("enabled", True)
    status_text = "Enabled" if enabled else "Disabled"

    text = (
        f" <b>Group Details</b>\n\n"
        f"<b>Title:</b> {title}\n"
        f"<b>Status:</b> {status_text}\n"
        f"<b>Time Interval:</b> {format_time(interval)}\n\n"
        f"Choose an option below:"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=buttons.group_details(grp, phone=phone),
        )
    except pyrogram.errors.MessageNotModified:
        pass


@app.on_callback_query(filters.regex(r"^grp_time_(\+?\d+)_(-?\d+)$"))
@error_handler
async def group_time_menu(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    phone = callback.matches[0].group(1)
    group_id = int(callback.matches[0].group(2))

    grp = await db.groups_col.find_one({"user_id": user_id, "account_phone": phone, "group_id": group_id})
    if not grp:
        return await callback.answer("Group not found!")

    title = grp.get("group_title", "Unknown")
    current_interval = grp.get("interval", 60)

    try:
        await callback.message.edit_text(
            f" <b>Set Interval</b>\n\n"
            f"<b>Group:</b> {title}\n"
            f"<b>Current:</b> {format_time(current_interval)}\n\n"
            f"Select a preset or choose Custom:",
            reply_markup=buttons.group_time_options(group_id, phone=phone),
        )
    except pyrogram.errors.MessageNotModified:
        pass


@app.on_callback_query(filters.regex(r"^grp_settime_(\+?\d+)_(-?\d+)_(\w+)$"))
@error_handler
async def set_group_time(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    phone = callback.matches[0].group(1)
    group_id = int(callback.matches[0].group(2))
    value = callback.matches[0].group(3)

    if value == "custom":
        from bot.plugins.account import login_states
        login_states[user_id] = {"step": "set_custom_time", "group_id": group_id, "phone": phone}
        return await callback.message.edit_text(
            " <b>Custom Interval</b>\n\n"
            "Send the interval in seconds.\n"
            "Minimum: 1 second, No maximum.\n\n"
            "Examples:\n"
            "• <code>5</code> → 5 seconds\n"
            "• <code>30s</code> → 30 seconds\n"
            "• <code>5m</code> → 5 minutes\n"
            "• <code>1h</code> → 1 hour\n\n"
            "Type <code>cancel</code> to abort."
        )

    interval = int(value)
    await db.groups_col.update_one(
        {"user_id": user_id, "account_phone": phone, "group_id": group_id},
        {"$set": {"interval": interval}}
    )
    await callback.answer(f" Interval set to {format_time(interval)}", show_alert=True)

    grp = await db.groups_col.find_one({"user_id": user_id, "account_phone": phone, "group_id": group_id})
    if not grp:
        return

    title = grp.get("group_title", "Unknown")
    interval = grp.get("interval", 60)
    enabled = grp.get("enabled", True)
    status_text = "Enabled" if enabled else "Disabled"

    text = (
        f" <b>Group Details</b>\n\n"
        f"<b>Title:</b> {title}\n"
        f"<b>Status:</b> {status_text}\n"
        f"<b>Time Interval:</b> {format_time(interval)}\n\n"
        f"Choose an option below:"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=buttons.group_details(grp, phone=phone),
        )
    except pyrogram.errors.MessageNotModified:
        pass


@app.on_callback_query(filters.regex("^grp_refresh$"))
@error_handler
async def refresh_groups(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await callback.answer(" Refreshing groups...")

    accounts = await db.get_accounts(user_id)
    new_count = 0

    for acc in accounts:
        try:
            groups = await session_manager.get_dialogs_groups(acc["session_string"])
            for grp in groups:
                existing = await db.groups_col.find_one({
                    "user_id": user_id,
                    "account_phone": acc["phone"],
                    "group_id": grp["id"],
                })
                if not existing:
                    await db.add_group(user_id, acc["phone"], grp["id"], grp["title"])
                    new_count += 1
        except Exception:
            continue

    try:
        await callback.message.edit_text(
            f" <b>Group Refresh Complete</b>\n\n"
            f" {new_count} new groups found across all accounts.\n\n"
            f"Tap an account to manage its groups:",
            reply_markup=buttons.account_select_groups(accounts),
        )
    except pyrogram.errors.MessageNotModified:
        pass
