import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.redis import RedisStorage2
# from aiogram.contrib.fsm_storage.memory import MemoryStorage

from databases.postrgres_db import Database
from config_reader import read_config
from paysystems.yoomoney import PaySystem

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from handlers.initialize import register_handlers


from datetime import datetime, timedelta, time
logger = logging.getLogger(__name__)


async def db_operations(db: Database, bot=None):
    pass
    # await db.add_user('test', 111111, '1234567')
    # end = datetime.today()
    # start = datetime.today() + timedelta(days=-13)
    # count = await db.count_gym_records(start, end)
    # print(f'Записей в зал: {count}')
    # await db.execute_cmd("UPDATE users SET fullname = 'Беляев Денис' WHERE fullname = $1", "/start Денис")
    # await bot.send_message(chat_id=1334757122, text='Пароль для входа: 0001244#')


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    logger.info("Starting tgbot")
    logger.info(datetime.now().isoformat())

    config = read_config()

    storage = RedisStorage2(host=config.redis.host)

    bot = Bot(token=config.tg_bot.token)

    db = Database()
    await db.create_pool(
        host=config.db.host,
        db_name=config.db.name,
        user=config.db.name,
        password=config.db.password)
    await db.create_tables()

    bot['db'] = db
    bot['ps'] = PaySystem(token=config.pay_system.token)
    bot['scheduler'] = AsyncIOScheduler()
    bot['admin_group_id'] = config.tg_bot.admin_group_id

    logging.getLogger('apscheduler.executors.default').propagate = False
    bot['scheduler'].start()

    await db_operations(db, bot)

    dp = Dispatcher(bot, storage=storage)

    await register_handlers(dp)

    try:
        await dp.start_polling()
    finally:
        bot.get('scheduler').shutdown()

        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
