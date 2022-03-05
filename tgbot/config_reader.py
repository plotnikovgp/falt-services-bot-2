import os
from dotenv import load_dotenv
from dataclasses import dataclass


@dataclass
class DbConfig:
    host: str
    name: str
    user: str
    password: str


@dataclass
class TgBot:
    token: str
    admin_id: int
    admin_group_id: int


@dataclass
class Redis:
    host: str


@dataclass
class Yoomoney:
    token: str


@dataclass
class Config:
    tg_bot: TgBot
    db: DbConfig
    pay_system: Yoomoney
    redis: Redis


def read_config():
    load_dotenv()
    return Config(
        tg_bot=TgBot(
            token=os.getenv("BOT_TOKEN"),
            admin_id=int(os.getenv("ADMIN_ID")),
            admin_group_id=int(os.getenv("ADMIN_GROUP_ID")),
        ),
        db=DbConfig(
            host=os.getenv("DB_HOST"),
            name=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
        ),
        pay_system=Yoomoney(
            token=os.getenv("YOOMONEY_TOKEN"),
        ),
        redis=Redis(
            host=os.getenv("REDIS_HOST")
        ),
    )
