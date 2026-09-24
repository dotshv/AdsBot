import asyncio
import traceback

from pyrogram import Client
from pyrogram.errors import (
    SessionRevoked,
    AuthKeyUnregistered,
    UserDeactivated,
    UserDeactivatedBan,
    PhoneNumberBanned,
    SessionExpired,
    AuthKeyDuplicated,
)

from bot import config, logger


INVALID_SESSION_ERRORS = (
    SessionRevoked,
    AuthKeyUnregistered,
    UserDeactivated,
    UserDeactivatedBan,
    PhoneNumberBanned,
    SessionExpired,
    AuthKeyDuplicated,
)

ERROR_REASONS = {
    SessionRevoked: "Session was revoked",
    AuthKeyUnregistered: "Auth key unregistered",
    UserDeactivated: "Account deactivated",
    UserDeactivatedBan: "Account banned",
    PhoneNumberBanned: "Phone number banned",
    SessionExpired: "Session expired",
    AuthKeyDuplicated: "Auth key duplicated",
}


class SessionManager:
    def __init__(self):
        self._active_clients = {}

    async def create_session(self, phone):
        client = Client(
            name=f"session_{phone}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            in_memory=True,
        )
        await client.connect()
        sent_code = await client.send_code(phone)
        return client, sent_code.phone_code_hash

    async def complete_login(self, client, phone, phone_code_hash, code, password=None):
        if not client.is_connected:
            await client.connect()

        try:
            if password:
                await client.check_password(password)
            else:
                await client.sign_in(
                    phone_number=phone,
                    phone_code_hash=phone_code_hash,
                    phone_code=code,
                )
        except Exception as e:
            err_str = str(e).lower()
            if not password and ("two-step" in err_str or "session_password_needed" in err_str or "password_hash_invalid" in err_str):
                raise ValueError("2FA_REQUIRED")
            else:
                try:
                    await client.disconnect()
                except:
                    pass
                raise

        session_string = await client.export_session_string()
        me = await client.get_me()
        await client.disconnect()
        return session_string, me.phone_number or phone

    async def validate_session(self, session_string):
        client = Client(
            name="validate",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_string,
            in_memory=True,
        )
        try:
            await client.connect()
            me = await client.get_me()
            await client.disconnect()
            return True, me.phone_number
        except INVALID_SESSION_ERRORS as e:
            reason = ERROR_REASONS.get(type(e), str(e))
            try:
                await client.disconnect()
            except Exception:
                pass
            return False, reason
        except Exception as e:
            try:
                await client.disconnect()
            except Exception:
                pass
            return False, str(e)

    async def get_client(self, session_string):
        if session_string in self._active_clients:
            client = self._active_clients[session_string]
            if client.is_connected:
                return client

        client = Client(
            name="worker",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_string,
            in_memory=True,
        )
        await client.connect()
        self._active_clients[session_string] = client
        return client

    async def disconnect_client(self, session_string):
        if session_string in self._active_clients:
            client = self._active_clients.pop(session_string)
            try:
                await client.disconnect()
            except Exception:
                pass

    async def disconnect_all(self):
        for key in list(self._active_clients.keys()):
            await self.disconnect_client(key)

    async def join_channel(self, session_string, link):
        client = await self.get_client(session_string)
        try:
            await client.join_chat(link)
            return True, "Joined successfully"
        except Exception as e:
            return False, str(e)

    async def send_message_to_group(self, session_string, group_id, text, reply_to_message_id=None):
        client = await self.get_client(session_string)
        try:
            msg = await client.send_message(group_id, text, reply_to_message_id=reply_to_message_id)
            return msg
        except INVALID_SESSION_ERRORS:
            return False
        except Exception:
            return False

    async def get_dialogs_groups(self, session_string):
        client = await self.get_client(session_string)
        groups = []
        try:
            async for dialog in client.get_dialogs():
                if dialog.chat and hasattr(dialog.chat.type, "value"):
                    ctype = dialog.chat.type.value
                else:
                    ctype = str(dialog.chat.type) if dialog.chat else ""
                    
                if ctype in ("supergroup", "group", "ChatType.SUPERGROUP", "ChatType.GROUP"):
                    groups.append({
                        "id": dialog.chat.id,
                        "title": dialog.chat.title,
                    })
        except Exception:
            pass
            
        try:
            from pyrogram.raw import functions, types
            archived = await client.invoke(
                functions.messages.GetDialogs(
                    offset_date=0,
                    offset_id=0,
                    offset_peer=types.InputPeerEmpty(),
                    limit=100,
                    hash=0,
                    folder_id=1
                )
            )
            for chat in archived.chats:
                if isinstance(chat, types.Channel) and getattr(chat, "megagroup", False):
                    groups.append({
                        "id": int(f"-100{chat.id}"),
                        "title": getattr(chat, "title", "Unknown"),
                    })
                elif isinstance(chat, types.Chat):
                    groups.append({
                        "id": -chat.id,
                        "title": getattr(chat, "title", "Unknown"),
                    })
        except Exception:
            pass

        unique_groups = {}
        for g in groups:
            unique_groups[g["id"]] = g
            
        return list(unique_groups.values())

    async def cleanup_loop(self):
        from bot import db, app
        while True:
            await asyncio.sleep(300)
            try:
                all_accounts = await db.get_all_accounts()
                for account in all_accounts:
                    valid, info = await self.validate_session(account["session_string"])
                    if not valid:
                        user_id = account["user_id"]
                        phone = account["phone"]
                        await db.invalidate_account(account["_id"], info)
                        await db.remove_groups_by_phone(user_id, phone)
                        try:
                            await app.send_message(
                                user_id,
                                f" <b>Account Auto-Removed</b>\n\n"
                                f" <b>Phone:</b> <code>{phone}</code>\n"
                                f" <b>Reason:</b> {info}\n\n"
                                f"This account has been automatically removed from your list "
                                f"because the session is no longer valid."
                            )
                        except Exception:
                            pass
                        logger.info(f"Auto-removed invalid account {phone} for user {user_id}: {info}")
                    await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")

    @staticmethod
    def format_otp_hint(raw_code):
        stripped = raw_code.replace(" ", "")
        if stripped.isdigit() and " " not in raw_code and len(stripped) >= 4:
            spaced = " ".join(stripped)
            return (
                f" <b>OTP Format Required</b>\n\n"
                f"Please enter the code with spaces between digits:\n"
                f"<code>{spaced}</code>\n\n"
                f"Example: <code>1 2 3 4 5</code>"
            )
        return None
