import asyncio
import importlib

from pyrogram import idle

from bot import app, config, db, logger, stop, session_manager, tasks
from bot.plugins import all_modules


async def auto_resume_tasks():
    """Bot restart ke baad sabke chal rahe tasks automatically resume karta hai."""
    running = await db.get_all_running_tasks()
    if not running:
        logger.info("No tasks to resume.")
        return

    logger.info(f"Resuming {len(running)} user task(s) after restart...")

    from bot.plugins.messaging import messaging_loop, active_messaging
    from bot.plugins.ai_chat import ai_chat_loop, active_ai_chats

    for entry in running:
        user_id = entry["user_id"]
        msg_state = entry.get("messaging")
        ai_state = entry.get("ai_chat")

        # ── Messaging resume ──
        if msg_state and msg_state.get("active"):
            try:
                msg = await db.get_user_setting(user_id, "global_message")
                accounts = await db.get_accounts(user_id)
                groups = await db.get_enabled_groups(user_id)

                if msg and accounts and groups:
                    task = asyncio.create_task(
                        messaging_loop(app, user_id, msg, accounts, groups)
                    )
                    active_messaging[user_id] = task
                    logger.info(f"Messaging resumed for user {user_id}")

                    try:
                        await app.send_message(
                            user_id,
                            "<b>Bot Restarted</b>\n\n"
                            "Your <b>Messaging</b> task has been automatically resumed.\n"
                            "No work was interrupted.",
                        )
                    except Exception:
                        pass
                else:
                    await db.clear_task_state(user_id, "messaging")
            except Exception as e:
                logger.error(f"Failed to resume messaging for {user_id}: {e}")

        # ── AI Chat resume ──
        if ai_state:
            try:
                selected = ai_state.get("selected_groups", [])
                accounts = await db.get_accounts(user_id)

                if selected and accounts and len(accounts) >= 2:
                    task = asyncio.create_task(
                        ai_chat_loop(app, user_id, accounts, selected)
                    )
                    active_ai_chats[user_id] = task
                    logger.info(f"AI Chat resumed for user {user_id}")

                    try:
                        await app.send_message(
                            user_id,
                            "<b>Bot Restarted</b>\n\n"
                            "Your <b>AI SPAM</b> task has been automatically resumed.\n"
                            "No work was interrupted.",
                        )
                    except Exception:
                        pass
                else:
                    await db.clear_task_state(user_id, "ai_chat")
            except Exception as e:
                logger.error(f"Failed to resume AI SPAM for {user_id}: {e}")


async def main():
    await db.connect()
    await app.boot()

    for module in all_modules:
        importlib.import_module(f"bot.plugins.{module}")
    logger.info(f"Loaded {len(all_modules)} plugins.")

    tasks.append(asyncio.create_task(session_manager.cleanup_loop()))
    logger.info("Session cleanup task started.")

    from bot.core.llm import llm
    tasks.append(asyncio.create_task(llm.initialize()))
    logger.info("Local LLM initialization task started in background.")

    # Auto-resume previously running tasks after restart
    tasks.append(asyncio.create_task(auto_resume_tasks()))
    logger.info("Auto-resume task started.")

    await idle()
    await stop()


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        pass
