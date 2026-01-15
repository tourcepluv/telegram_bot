from __future__ import annotations

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    bot_token: str = Field(..., env="BOT_TOKEN")
    admin_ids: str = Field("", env="ADMIN_IDS")
    support_username: str = Field("pluxvpn_help", env="SUPPORT_USERNAME")
    timezone: str = Field("Europe/Moscow", env="TIMEZONE")
    billing_hour: int = Field(0, env="BILLING_HOUR")
    billing_minute: int = Field(5, env="BILLING_MINUTE")
    db_dsn: str = Field("sqlite+aiosqlite:///./pluxvpn.db", env="DB_DSN")

    marzban_base_url: str = Field(..., env="MARZBAN_BASE_URL")
    marzban_api_token: str = Field(..., env="MARZBAN_API_TOKEN")
    marzban_level: int = Field(1, env="MARZBAN_LEVEL")
    marzban_limit_ip: int = Field(2, env="MARZBAN_LIMIT_IP")

    eu_server_tags: str = Field("SERVER_AEZA_GERM_1", env="EU_SERVER_TAGS")
    ru_server_tags: str = Field("SERVER_YANDEX_1", env="RU_SERVER_TAGS")
    eu_server_capacity: int = Field(500, env="EU_SERVER_CAPACITY")
    ru_server_capacity: int = Field(300, env="RU_SERVER_CAPACITY")

    offer_url: str = Field(..., env="OFFER_URL")

    yookassa_shop_id: str = Field(..., env="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field(..., env="YOOKASSA_SECRET_KEY")
    webhook_path: str = Field(..., env="WEBHOOK_PATH")
    return_url: str = Field(..., env="RETURN_URL")

    promo_bonus_rub: int = Field(50, env="PROMO_BONUS_RUB")
    ref_bonus_rub: int = Field(50, env="REF_BONUS_RUB")
    ref_min_payment_rub: int = Field(100, env="REF_MIN_PAYMENT_RUB")

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def admin_id_list(self) -> list[int]:
        if not self.admin_ids:
            return []
        return [int(item.strip()) for item in self.admin_ids.split(",") if item.strip()]

    @property
    def eu_tags_list(self) -> list[str]:
        return [item.strip() for item in self.eu_server_tags.split(",") if item.strip()]

    @property
    def ru_tags_list(self) -> list[str]:
        return [item.strip() for item in self.ru_server_tags.split(",") if item.strip()]


settings = Settings()
