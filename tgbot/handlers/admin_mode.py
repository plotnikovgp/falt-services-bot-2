from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from tgbot.databases.postrgres_db import Database
from aiogram.utils.exceptions import BotBlocked, TelegramAPIError


async def extract_id(message: types.Message) -> int:
    entities = message.entities or message.caption_entities
    if not entities or entities[-1].type != "hashtag":
        raise ValueError("Не удалось извлечь ID для ответа")

    hashtag = entities[-1].get_text(message.text or message.caption)
    if len(hashtag) < 4 or not hashtag[3:].isdigit():
        raise ValueError("Некорректный ID для ответа")
    return int(hashtag[3:])


async def reply_to_user(message: types.Message):
    try:
        user_id = await extract_id(message.reply_to_message)
    except ValueError as ex:
        return await message.reply(str(ex))

    try:
        text = 'Ответ от разработчика: ' + message.get_args()
        await message.bot.send_message(user_id, text)
    except BotBlocked:
        await message.reply("Не удалось отправить сообщение адресату, т.к. бот заблокирован на их стороне")
    except TelegramAPIError as ex:
        await message.reply(f"Не удалось отправить сообщение адресату! Ошибка: {ex}")
    await message.reply('Ответ отправлен.')


async def get_user_info(message: types.Message):
    try:
        user_id = await extract_id(message.reply_to_message)
    except ValueError as ex:
        return await message.reply(str(ex))

    db: Database = message.bot.get('db')
    user_info = await db.get_user(user_id)

    text = ''
    for k, v in user_info.items():
        if k in ['is_registered', 'email']:
            continue
        text += str(k) + ': ' + str(v) + '\n'

    await message.answer(text)


async def change_user_balance(message: types.Message):
    try:
        user_id = await extract_id(message.reply_to_message)
    except ValueError as ex:
        return await message.reply(str(ex))

    db: Database = message.bot.get('db')

    try:
        top_up = float(message.get_args())
    except ValueError:
        return await message.reply("После команды должно быть число.")

    await db.change_balance(tg_id=user_id, diff=top_up)
    await message.reply_to_message.reply('Баланс изменён.')

    user_info = await db.get_user(user_id)
    text = f'Заявка на перенос баланса одобрена.\n'\
           f'Текущий баланс: {user_info.get("balance")}'
    await message.bot.send_message(chat_id=user_id, text=text)


async def set_passcode(message: types.Message):
    passcode = message.get_args()
    passcode.replace(' ', '')
    if len(passcode) != 7:
        await message.reply('Неправильный формат пароля.')
        return
    db: Database = message.bot.get('db')
    await db.update_passcode(passcode)
    await message.reply('Пароль обновлён.')
