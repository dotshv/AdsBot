import pyrogram
from pyrogram.client import Client
from pyrogram.raw.types import InputPeerChannel, InputPeerChat, InputPeerUser
from bot import config, logger

# Monkey patch Pyrogram to prevent fatal event loop crashes on uncached peers
import pyrogram.utils
from pyrogram.client import Client
from pyrogram.storage.sqlite_storage import SQLiteStorage
from pyrogram.raw.types import InputPeerChannel, InputPeerChat, InputPeerUser
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid
from pyrogram.raw.functions.updates import GetChannelDifference

# 1. Patch get_peer_type
original_get_peer_type = pyrogram.utils.get_peer_type

def safe_get_peer_type(peer_id: int) -> str:
    try:
        return original_get_peer_type(peer_id)
    except ValueError:
        peer_id_str = str(peer_id)
        if peer_id_str.startswith("-100"):
            return "channel"
        elif peer_id_str.startswith("-"):
            return "group"
        return "user"

pyrogram.utils.get_peer_type = safe_get_peer_type

# 2. Patch get_peer_by_id in Storage
original_get_peer_by_id = SQLiteStorage.get_peer_by_id

async def safe_get_peer_by_id(self, peer_id: int):
    try:
        return await original_get_peer_by_id(self, peer_id)
    except KeyError:
        peer_id_str = str(peer_id)
        if peer_id_str.startswith("-100"):
            return InputPeerChannel(channel_id=int(peer_id_str[4:]), access_hash=0)
        elif peer_id_str.startswith("-"):
            return InputPeerChat(chat_id=int(peer_id_str[1:]))
        return InputPeerUser(user_id=peer_id, access_hash=0)

SQLiteStorage.get_peer_by_id = safe_get_peer_by_id

# 3. Patch Client.invoke to suppress ChannelInvalid during GetChannelDifference
original_invoke = Client.invoke

async def safe_invoke(self, query, *args, **kwargs):
    try:
        return await original_invoke(self, query, *args, **kwargs)
    except ChannelInvalid as e:
        if isinstance(query, GetChannelDifference):
            from pyrogram.raw.types.updates import ChannelDifferenceEmpty
            return ChannelDifferenceEmpty(pts=query.pts, timeout=0, final=True)
        raise e

Client.invoke = safe_invoke


class Bot(pyrogram.Client):
    def __init__(self):
        super().__init__(
            name="adsbot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            parse_mode=pyrogram.enums.ParseMode.HTML,
            max_concurrent_transmissions=7,
        )
        self.admin_id = config.ADMIN_ID
        self.log_group = config.LOG_GROUP

    async def boot(self):
        await super().start()
        self.id = self.me.id
        self.name = self.me.first_name
        self.username = self.me.username
        self.mention = self.me.mention

        try:
            logger.info("Pre-warming Pyrogram cache to prevent Peer ID errors...")
            async for _ in self.get_dialogs():
                pass
            logger.info("Cache warmed up successfully.")
        except Exception as e:
            logger.warning(f"Cache pre-warm skipped/failed: {e}")

        try:
            # Resolve the peer first so Pyrogram caches it (fixes "Peer id invalid")
            chat = await self.get_chat(self.log_group)
            self.log_group = chat.id  # use the resolved ID

            get = await self.get_chat_member(self.log_group, self.id)
            if get.status != pyrogram.enums.ChatMemberStatus.ADMINISTRATOR:
                raise SystemExit("Please promote the bot as admin in the log group.")

            await self.send_message(
                self.log_group,
                f"<b>Bot Started</b>\n\n"
                f"<b>Bot:</b> @{self.username}\n"
                f"<b>Version:</b> 1.0.0"
            )
        except SystemExit:
            raise
        except Exception as ex:
            # Log group not critical — warn and continue
            logger.warning(f"Log group warning: {ex}. Bot will still run.")

        logger.info(f"Bot started as @{self.username}")

    async def exit(self):
        try:
            await self.send_message(
                self.log_group,
                "<b>Bot Stopped</b>"
            )
        except Exception:
            pass
        await super().stop()
        logger.info("Bot stopped.")
