import asyncio
import random

from pyrogram import filters, types
import pyrogram.errors
from pyrogram.errors import FloodWait

from bot import app, db, session_manager, config
from bot.helpers import buttons
from bot.helpers.decorators import error_handler

active_ai_chats = {}
ai_selected_groups = {}

CHAT_PHRASES = [
    "Hey, what's up?", "How's everyone doing?", "Good vibes today!",
    "Anyone here?", "What's going on in this group?", "Hi all!",
    "Long time no see!", "Interesting topic here", "I agree with that!",
    "That's a great point!", "Can someone explain more?", "Thanks for sharing!",
    "Really appreciate it", "This is helpful", "Wow, nice!",
    "Great discussion!", "I was thinking the same", "Makes sense to me",
    "Let me know your thoughts", "What does everyone think?",
    "Totally agree!", "That's awesome!", "Keep it up!",
    "Exactly what I was looking for", "Very informative",
    "Couldn't agree more", "Well said!", "This is amazing!",
    "Love this community", "Happy to be here",
    "Been following this for a while", "Learned something new today",
]

REPLY_PHRASES = [
    "Yeah, I think so too!", "Totally!", "That makes sense.",
    "I was just thinking about this", "Good point!",
    "Couldn't have said it better", "Right on!", "100%",
    "Interesting perspective", "I agree", "Sure thing!",
    "Thanks for mentioning that", "Exactly!", "For real!",
    "True that!", "Well put!", "I second that!",
    "Great take on this", "Yep, absolutely!", "Makes total sense",
]


@app.on_callback_query(filters.regex("^menu_ai_chat$"))
@error_handler
async def ai_chat_menu(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id

    is_prem = await db.is_premium(user_id)
    if not is_prem and user_id != config.ADMIN_ID:
        return await callback.answer(
            " Premium feature! Upgrade to access AI Chat.",
            show_alert=True,
        )

    is_running = user_id in active_ai_chats
    accounts = await db.get_accounts(user_id)
    selected = ai_selected_groups.get(user_id, [])

    await callback.message.edit_text(
        f" <b>AI Chat</b>\n\n"
        f"<b>Status:</b> {' Running' if is_running else ' Stopped'}\n"
        f"<b>Accounts:</b> {len(accounts)}\n"
        f"<b>Selected Groups:</b> {len(selected)}\n\n"
        f"Your accounts will chat with each other in selected groups.\n"
        f"Non-selected groups will receive normal messages.",
        reply_markup=buttons.ai_chat_controls(is_running),
    )


@app.on_callback_query(filters.regex("^ai_select_groups$"))
@error_handler
async def ai_select_groups_handler(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    accounts = await db.get_accounts(user_id)

    if not accounts:
        return await callback.answer(
            "No accounts found! Add accounts first.",
            show_alert=True,
        )

    await callback.message.edit_text(
        " <b>Select Account for AI Chat</b>\n\n"
        "Tap an account to see its groups and select them for AI chat:",
        reply_markup=buttons.account_select_ai(accounts),
    )


@app.on_callback_query(filters.regex(r"^ai_acc_(\+?\d+)$"))
@error_handler
async def ai_account_groups_menu(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    phone = callback.matches[0].group(1)
    
    groups = await db.get_groups_by_phone(user_id, phone)
    selected = ai_selected_groups.get(user_id, [])

    try:
        await callback.message.edit_text(
            f" <b>Select Groups for AI Chat</b>\n"
            f"<b>Account:</b> {phone}\n\n"
            f" = Selected |  = Not selected\n\n"
            f"Tap groups to select/deselect, then confirm:",
            reply_markup=buttons.ai_group_selector(groups, phone, selected),
        )
    except pyrogram.errors.MessageNotModified:
        pass


@app.on_callback_query(filters.regex(r"^ai_toggle_(\+?\d+)_(-?\d+)$"))
@error_handler
async def ai_toggle_group(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    phone = callback.matches[0].group(1)
    group_id = int(callback.matches[0].group(2))

    if user_id not in ai_selected_groups:
        ai_selected_groups[user_id] = []

    if group_id in ai_selected_groups[user_id]:
        ai_selected_groups[user_id].remove(group_id)
    else:
        ai_selected_groups[user_id].append(group_id)

    groups = await db.get_groups_by_phone(user_id, phone)
    try:
        await callback.message.edit_reply_markup(
            reply_markup=buttons.ai_group_selector(groups, phone, ai_selected_groups[user_id]),
        )
    except pyrogram.errors.MessageNotModified:
        pass


@app.on_callback_query(filters.regex(r"^ai_confirm_(\+?\d+)$"))
@error_handler
async def ai_confirm_selection(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id
    selected = ai_selected_groups.get(user_id, [])

    if not selected:
        return await callback.answer(
            " Select at least one group!",
            show_alert=True,
        )

    await callback.answer(f" {len(selected)} groups selected!", show_alert=True)

    is_running = user_id in active_ai_chats
    accounts = await db.get_accounts(user_id)

    try:
        await callback.message.edit_text(
            f" <b>AI Chat</b>\n\n"
            f"<b>Status:</b> {' Running' if is_running else ' Stopped'}\n"
            f"<b>Accounts:</b> {len(accounts)}\n"
            f"<b>Selected Groups:</b> {len(selected)}\n\n"
            f"Click Start to begin AI chatting!",
            reply_markup=buttons.ai_chat_controls(is_running),
        )
    except pyrogram.errors.MessageNotModified:
        pass


@app.on_callback_query(filters.regex("^ai_start$"))
@error_handler
async def start_ai_chat(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if user_id in active_ai_chats:
        return await callback.answer("Already running!", show_alert=True)

    selected = ai_selected_groups.get(user_id, [])
    if not selected:
        return await callback.answer(
            " Select groups first!",
            show_alert=True,
        )

    accounts = await db.get_accounts(user_id)
    if len(accounts) < 2:
        return await callback.answer(
            " Need at least 2 accounts for AI chat!",
            show_alert=True,
        )

    await callback.answer(" Checking accounts...", show_alert=False)

    # Check if all accounts are in the selected groups
    missing_accounts = False
    for group_id in selected:
        for acc in accounts:
            grp = await db.groups_col.find_one({"user_id": user_id, "account_phone": acc["phone"], "group_id": group_id})
            if not grp:
                missing_accounts = True
                break
        if missing_accounts:
            break

    if missing_accounts:
        from bot.plugins.account import login_states
        login_states[user_id] = {"step": "ai_join_link"}
        return await callback.message.edit_text(
            " <b>Missing Accounts in Group</b>\n\n"
            "Not all of your accounts are in the selected groups.\n"
            "Please add all your IDs to the groups manually, OR provide the group invite link below and I will automatically join all your accounts to it.\n\n"
            "Send the link (e.g. t.me/group), or type <code>cancel</code> to abort."
        )

    await start_ai_loop_for_user(client, user_id, accounts, selected, callback.message)


async def start_ai_loop_for_user(client, user_id, accounts, selected, message):
    # State MongoDB me save karo (restart pe resume ke liye)
    await db.save_task_state(user_id, "ai_chat", {"selected_groups": selected})

    task = asyncio.create_task(
        ai_chat_loop(client, user_id, accounts, selected)
    )
    active_ai_chats[user_id] = task

    try:
        await message.edit_text(
            f" <b>AI Chat Running!</b>\n\n"
            f"<b>Accounts:</b> {len(accounts)}\n"
            f"<b>Groups:</b> {len(selected)}\n\n"
            f"Accounts are chatting with each other.\n"
            f"Click Stop to end.",
            reply_markup=buttons.ai_chat_controls(True),
        )
    except pyrogram.errors.MessageNotModified:
        pass


@app.on_callback_query(filters.regex("^ai_stop$"))
@error_handler
async def stop_ai_chat(client, callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if user_id in active_ai_chats:
        active_ai_chats[user_id].cancel()
        del active_ai_chats[user_id]
        await callback.answer(" AI Chat Stopped!", show_alert=True)
    else:
        await callback.answer("Not running!", show_alert=True)

    # State clear karo — manual stop tha, restart pe resume mat karo
    await db.clear_task_state(user_id, "ai_chat")

    try:
        await callback.message.edit_text(
            " <b>AI Chat Stopped</b>\n\n"
            "All AI chatting has been stopped.",
            reply_markup=buttons.ai_chat_controls(False),
        )
    except pyrogram.errors.MessageNotModified:
        pass


async def ai_chat_loop(client, user_id, accounts, selected_groups):
    from bot.core.llm import llm
    
    group_history = {gid: [] for gid in selected_groups}
    
    try:
        while True:
            if await db.has_free_trial_expired(user_id):
                active_ai_chats.pop(user_id, None)
                await db.clear_task_state(user_id, "ai_chat")
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

            for group_id in selected_groups:
                if user_id not in active_ai_chats:
                    return

                try:
                    # Sync accounts dynamically from DB
                    fresh_accounts = await db.get_accounts(user_id)
                    if fresh_accounts and len(fresh_accounts) >= 2:
                        accounts = fresh_accounts

                    if len(accounts) < 2:
                        await asyncio.sleep(5)
                        continue

                    # Choose starter account
                    starter = random.choice(accounts)

                    # 1. First account starts the chat
                    phrase = await llm.generate_initial_message()
                    if phrase.lower() in [m.lower() for m in group_history[group_id]]:
                        phrase = await llm.generate_initial_message()

                    sent_msg = None
                    try:
                        sent_msg = await session_manager.send_message_to_group(
                            starter["session_string"], group_id, phrase
                        )
                        if sent_msg:
                            group_history[group_id].append(phrase)
                            if len(group_history[group_id]) > 30:
                                group_history[group_id] = group_history[group_id][-15:]
                            await db.update_stats(user_id, messages=1)
                    except FloodWait as fw:
                        await asyncio.sleep(fw.value + 3)
                    except Exception:
                        pass

                    last_msg_id = getattr(sent_msg, "id", None) if sent_msg else None
                    last_text = phrase
                    last_sender_phone = starter["phone"]

                    # 2. Continue conversation back-and-forth in the SAME thread (4-7 turns)
                    num_turns = random.randint(4, 7)
                    for _ in range(num_turns):
                        if user_id not in active_ai_chats:
                            return

                        # Fast pause (1-2 sec) before each reply
                        await asyncio.sleep(random.uniform(1.0, 2.0))

                        # Pick a different account from the last sender to reply
                        available_responders = [a for a in accounts if a["phone"] != last_sender_phone]
                        if not available_responders:
                            break
                        responder = random.choice(available_responders)

                        reply = await llm.generate_reply(last_text, group_history[group_id])

                        try:
                            reply_msg = await session_manager.send_message_to_group(
                                responder["session_string"], 
                                group_id, 
                                reply,
                                reply_to_message_id=last_msg_id
                            )
                            if reply_msg:
                                group_history[group_id].append(reply)
                                if len(group_history[group_id]) > 30:
                                    group_history[group_id] = group_history[group_id][-15:]
                                await db.update_stats(user_id, messages=1)
                                
                                # Thread continues: update pointer to THIS reply
                                last_msg_id = getattr(reply_msg, "id", last_msg_id)
                                last_text = reply
                                last_sender_phone = responder["phone"]
                        except FloodWait as fw:
                            await asyncio.sleep(fw.value + 3)
                        except Exception:
                            pass

                    # Short pause before next conversation thread
                    await asyncio.sleep(random.uniform(3.0, 6.0))

                except Exception as inner_e:
                    await asyncio.sleep(3)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        from bot.helpers.utils import send_error_log
        await send_error_log(client, e, user_id, "ai_chat_loop")
    finally:
        active_ai_chats.pop(user_id, None)

