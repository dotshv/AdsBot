from pyrogram import filters as f

from bot import config


def admin_filter():
    async def func(_, __, message):
        if hasattr(message, "from_user") and message.from_user:
            return message.from_user.id == config.ADMIN_ID
        return False
    return f.create(func)


def premium_filter():
    async def func(_, __, message):
        from bot import db
        if hasattr(message, "from_user") and message.from_user:
            return await db.is_premium(message.from_user.id)
        return False
    return f.create(func)


def agreed_filter():
    async def func(_, __, message):
        from bot import db
        if hasattr(message, "from_user") and message.from_user:
            return await db.has_agreed(message.from_user.id)
        return False
    return f.create(func)


def not_suspended_filter():
    async def func(_, __, message):
        from bot import db
        if hasattr(message, "from_user") and message.from_user:
            return not await db.is_suspended(message.from_user.id)
        return False
    return f.create(func)


is_admin = admin_filter()
is_premium = premium_filter()
has_agreed = agreed_filter()
is_not_suspended = not_suspended_filter()
