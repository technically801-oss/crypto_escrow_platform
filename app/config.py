from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    bot_token: str = ''
    app_base_url: str = 'http://localhost:8000'
    telegram_bot_username: str = ''
    database_url: str = 'sqlite+aiosqlite:///./escrow.db'
    admin_chat_ids: str = ''
    secret_key: str = "change-this-secret-key"

    usdt_wallet_address: str = ''
    usdc_wallet_address: str = ''
    btc_wallet_address: str = ''

    platform_client_fee_percent: int = 20
    platform_seller_fee_percent: int = 20
    auto_release_days: int = 5
    reminder_hours: int = 12

    @property
    def admin_ids(self) -> list[int]:
        ids: list[int] = []
        for item in self.admin_chat_ids.split(','):
            item = item.strip()
            if item.isdigit():
                ids.append(int(item))
        return ids

    @property
    def db_url(self) -> str:
        url = self.database_url
        if url.startswith('postgresql://'):
            return url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        return url

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
