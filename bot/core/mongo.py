import asyncio
from datetime import datetime, timezone
from time import time

from motor.motor_asyncio import AsyncIOMotorClient

from bot import config, logger


class MongoDB:
    def __init__(self):
        self.motor = AsyncIOMotorClient(config.MONGO_URL, serverSelectionTimeoutMS=12500)
        self.db = self.motor.adsbot

        self.users_col = self.db.users
        self.accounts_col = self.db.accounts
        self.groups_col = self.db.groups
        self.payments_col = self.db.payments
        self.stats_col = self.db.stats
        self.settings_col = self.db.settings

        self._users_cache = {}

    async def connect(self):
        try:
            start = time()
            await self.motor.admin.command("ping")
            logger.info(f"Database connected. ({time() - start:.2f}s)")
        except Exception as e:
            raise SystemExit(f"Database connection failed: {type(e).__name__}") from e

    async def close(self):
        self.motor.close()
        logger.info("Database connection closed.")

    async def add_user(self, user_id, name=""):
        now = datetime.now(timezone.utc)
        await self.users_col.update_one(
            {"_id": user_id},
            {"$setOnInsert": {
                "name": name,
                "agreed": False,
                "premium": False,
                "premium_expiry": None,
                "suspended": False,
                "suspend_reason": "",
                "joined_at": now,
            }},
            upsert=True,
        )
        self._users_cache.pop(user_id, None)

    async def get_user(self, user_id):
        if user_id in self._users_cache:
            return self._users_cache[user_id]
        doc = await self.users_col.find_one({"_id": user_id})
        if doc:
            self._users_cache[user_id] = doc
        return doc

    async def set_agreed(self, user_id):
        await self.users_col.update_one(
            {"_id": user_id},
            {"$set": {"agreed": True}},
        )
        self._users_cache.pop(user_id, None)

    async def set_premium(self, user_id, expiry=None):
        await self.users_col.update_one(
            {"_id": user_id},
            {"$set": {"premium": True, "premium_expiry": expiry}},
        )
        self._users_cache.pop(user_id, None)

    async def remove_premium(self, user_id):
        await self.users_col.update_one(
            {"_id": user_id},
            {"$set": {"premium": False, "premium_expiry": None}},
        )
        self._users_cache.pop(user_id, None)

    async def suspend_user(self, user_id, reason=""):
        await self.users_col.update_one(
            {"_id": user_id},
            {"$set": {"suspended": True, "suspend_reason": reason}},
        )
        self._users_cache.pop(user_id, None)

    async def unsuspend_user(self, user_id):
        await self.users_col.update_one(
            {"_id": user_id},
            {"$set": {"suspended": False, "suspend_reason": ""}},
        )
        self._users_cache.pop(user_id, None)

    async def is_premium(self, user_id):
        user = await self.get_user(user_id)
        if not user:
            return False
        if not user.get("premium"):
            return False
        expiry = user.get("premium_expiry")
        if expiry:
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < datetime.now(timezone.utc):
                await self.remove_premium(user_id)
                return False
        return True

    async def is_suspended(self, user_id):
        user = await self.get_user(user_id)
        return user.get("suspended", False) if user else False

    async def remove_premium(self, user_id):
        await self.users_col.update_one(
            {"_id": user_id},
            {"$set": {"premium": False, "premium_expiry": None}},
        )
        self._users_cache.pop(user_id, None)

    async def set_premium(self, user_id, expiry=None):
        update_data = {"premium": True}
        if expiry:
            update_data["premium_expiry"] = expiry
            
        await self.users_col.update_one(
            {"_id": user_id},
            {"$set": update_data},
            upsert=True
        )
        self._users_cache.pop(user_id, None)

    async def has_agreed(self, user_id):
        user = await self.get_user(user_id)
        return user.get("agreed", False) if user else False

    async def get_all_users(self):
        return [doc async for doc in self.users_col.find()]

    async def get_premium_users(self):
        return [doc async for doc in self.users_col.find({"premium": True})]

    async def has_free_trial_expired(self, user_id):
        user = await self.get_user(user_id)
        if not user:
            return True
        if await self.is_premium(user_id):
            return False
        
        joined_at = user.get("joined_at")
        from datetime import timedelta, datetime, timezone
        if not joined_at:
            # Old users without joined_at expire immediately
            joined_at = datetime.now(timezone.utc) - timedelta(hours=24)
            await self.users_col.update_one({"_id": user_id}, {"$set": {"joined_at": joined_at}})
            self._users_cache.pop(user_id, None)

        if joined_at.tzinfo is None:
            joined_at = joined_at.replace(tzinfo=timezone.utc)
            
        if datetime.now(timezone.utc) > joined_at + timedelta(hours=24):
            return True
        return False

    async def get_user_count(self):
        return await self.users_col.count_documents({})

    async def get_premium_count(self):
        return await self.users_col.count_documents({"premium": True})

    async def add_account(self, user_id, phone, session_string):
        now = datetime.now(timezone.utc)
        result = await self.accounts_col.insert_one({
            "user_id": user_id,
            "phone": phone,
            "session_string": session_string,
            "added_at": now,
            "valid": True,
        })
        return result.inserted_id

    async def get_accounts(self, user_id):
        return [doc async for doc in self.accounts_col.find({"user_id": user_id, "valid": True})]

    async def get_account_count(self, user_id):
        return await self.accounts_col.count_documents({"user_id": user_id, "valid": True})

    async def get_all_accounts(self):
        return [doc async for doc in self.accounts_col.find({"valid": True})]

    async def get_total_account_count(self):
        return await self.accounts_col.count_documents({"valid": True})

    async def remove_account(self, user_id, phone):
        await self.accounts_col.delete_one({"user_id": user_id, "phone": phone})

    async def invalidate_account(self, account_id, reason=""):
        doc = await self.accounts_col.find_one({"_id": account_id})
        if doc:
            await self.accounts_col.delete_one({"_id": account_id})
            return doc
        return None

    async def get_account_by_phone(self, user_id, phone):
        return await self.accounts_col.find_one({"user_id": user_id, "phone": phone})

    async def add_group(self, user_id, phone, group_id, group_title):
        existing = await self.groups_col.find_one({
            "user_id": user_id,
            "account_phone": phone,
            "group_id": group_id,
        })
        if existing:
            return existing["_id"]
        result = await self.groups_col.insert_one({
            "user_id": user_id,
            "account_phone": phone,
            "group_id": group_id,
            "group_title": group_title,
            "enabled": True,
            "interval": 60,
            "message": "",
            "ai_chat": False,
        })
        return result.inserted_id

    async def get_groups(self, user_id):
        return [doc async for doc in self.groups_col.find({"user_id": user_id})]

    async def get_groups_by_phone(self, user_id, phone):
        return [doc async for doc in self.groups_col.find({"user_id": user_id, "account_phone": phone})]

    async def get_enabled_groups(self, user_id):
        return [doc async for doc in self.groups_col.find({"user_id": user_id, "enabled": True})]

    async def toggle_group(self, user_id, group_id, enabled):
        await self.groups_col.update_many(
            {"user_id": user_id, "group_id": group_id},
            {"$set": {"enabled": enabled}},
        )

    async def set_group_interval(self, user_id, group_id, interval):
        await self.groups_col.update_many(
            {"user_id": user_id, "group_id": group_id},
            {"$set": {"interval": interval}},
        )

    async def set_all_groups_interval(self, user_id, interval):
        await self.groups_col.update_many(
            {"user_id": user_id},
            {"$set": {"interval": interval}},
        )

    async def set_group_message(self, user_id, group_id, message):
        await self.groups_col.update_many(
            {"user_id": user_id, "group_id": group_id},
            {"$set": {"message": message}},
        )

    async def set_group_ai_chat(self, user_id, group_id, enabled):
        await self.groups_col.update_many(
            {"user_id": user_id, "group_id": group_id},
            {"$set": {"ai_chat": enabled}},
        )

    async def remove_groups_by_phone(self, user_id, phone):
        await self.groups_col.delete_many({"user_id": user_id, "account_phone": phone})

    async def add_payment(self, user_id, method, amount, screenshot_file_id=""):
        now = datetime.now(timezone.utc)
        result = await self.payments_col.insert_one({
            "user_id": user_id,
            "method": method,
            "amount": amount,
            "screenshot_file_id": screenshot_file_id,
            "status": "pending",
            "admin_note": "",
            "created_at": now,
        })
        return result.inserted_id

    async def get_payment(self, payment_id):
        return await self.payments_col.find_one({"_id": payment_id})

    async def approve_payment(self, payment_id):
        await self.payments_col.update_one(
            {"_id": payment_id},
            {"$set": {"status": "approved"}},
        )

    async def reject_payment(self, payment_id, reason=""):
        await self.payments_col.update_one(
            {"_id": payment_id},
            {"$set": {"status": "rejected", "admin_note": reason}},
        )

    async def update_stats(self, user_id, messages=0, accounts=0):
        update = {}
        if messages:
            update["total_messages"] = messages
        if accounts:
            update["total_accounts"] = accounts
        if update:
            await self.stats_col.update_one(
                {"_id": user_id},
                {"$inc": update},
                upsert=True,
            )

    async def get_stats(self, user_id):
        doc = await self.stats_col.find_one({"_id": user_id})
        return doc or {"total_messages": 0, "total_accounts": 0}

    async def get_global_stats(self):
        total_users = await self.get_user_count()
        total_accounts = await self.get_total_account_count()
        total_premium = await self.get_premium_count()
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$total_messages"}}}]
        cursor = self.stats_col.aggregate(pipeline)
        result = [doc async for doc in cursor]
        total_messages = result[0]["total"] if result else 0
        return {
            "total_users": total_users,
            "total_accounts": total_accounts,
            "total_premium": total_premium,
            "total_messages": total_messages,
        }

    async def set_user_setting(self, user_id, key, value):
        await self.settings_col.update_one(
            {"_id": user_id},
            {"$set": {key: value}},
            upsert=True,
        )

    async def get_user_setting(self, user_id, key, default=None):
        doc = await self.settings_col.find_one({"_id": user_id})
        if doc:
            return doc.get(key, default)
        return default

    # ── Task State Persistence (auto-resume on restart) ──────────────────────
    async def save_task_state(self, user_id: int, task_type: str, data: dict):
        """task_type: 'messaging' or 'ai_chat'"""
        await self.settings_col.update_one(
            {"_id": user_id},
            {"$set": {f"task_{task_type}": data}},
            upsert=True,
        )

    async def clear_task_state(self, user_id: int, task_type: str):
        await self.settings_col.update_one(
            {"_id": user_id},
            {"$unset": {f"task_{task_type}": ""}},
        )

    async def get_all_running_tasks(self):
        """Bot restart pe sabke running tasks fetch karta hai."""
        running = []
        async for doc in self.settings_col.find(
            {"$or": [{"task_messaging": {"$exists": True}}, {"task_ai_chat": {"$exists": True}}]}
        ):
            user_id = doc["_id"]
            messaging = doc.get("task_messaging")
            ai_chat = doc.get("task_ai_chat")
            running.append({"user_id": user_id, "messaging": messaging, "ai_chat": ai_chat})
        return running
