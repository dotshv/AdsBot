from os import getenv


class Config:
    def __init__(self):
        self.API_ID = int(getenv("API_ID", "35404283"))
        self.API_HASH = getenv("API_HASH", "3684648897cea8aa6505a046541ab6f7")
        self.BOT_TOKEN = getenv("BOT_TOKEN", "8929419983:AAFXDEgXjWBncprmTf0jhR8X1gmL5a2cCDg")
        self.MONGO_URL = getenv("MONGO_URL", "mongodb+srv://hnyx:wywyw2@cluster0.9dxlslv.mongodb.net/?retryWrites=true&w=majority")
        self.ADMIN_ID = int(getenv("ADMIN_ID", "7953559026"))
        self.LOG_GROUP = int(getenv("LOG_GROUP", "-1003824746394"))
        self.FORCE_CHANNEL_1 = getenv("FORCE_CHANNEL_1", "Techofy")
        self.FORCE_CHANNEL_2 = getenv("FORCE_CHANNEL_2", "Techofy")
        self.UPI_ID = getenv("UPI_ID", "devghunawat@fam")
        self.USDT_ADDRESS = getenv("USDT_ADDRESS", "0x2E77a41E18e62Eb65e2E51F5a8646a0cd9a334A3")
        self.PREMIUM_PRICE = int(getenv("PREMIUM_PRICE", "499"))
        self.USDT_PRICE = int(getenv("USDT_PRICE", "5"))
        self.PREMIUM_STARS = int(getenv("PREMIUM_STARS", "300"))
        self.FREE_ACCOUNT_LIMIT = int(getenv("FREE_ACCOUNT_LIMIT", "1"))
        self.DEVELOPER = "@dotshv"
        self.CHANNEL = "@Techofy"
        self.ADMIN_USERNAME = "@dotshv"

    def check(self):
        missing = [
            var for var in [
                "API_ID", "API_HASH", "BOT_TOKEN", "MONGO_URL",
                "ADMIN_ID", "LOG_GROUP"
            ]
            if not getattr(self, var)
        ]
        if missing:
            raise SystemExit(
                f"Missing required config: {', '.join(missing)}"
            )
