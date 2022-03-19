from asyncio import create_task
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from tgbot.keyboards.meet_keyboards import accept_or_reject_keyboard
from tgbot.databases.postrgres_db import Database
from tgbot.utils.schedule import Record, get_schedule, update_photo_link


async def extract_id(message: types.Message) -> int:
    entities = message.entities or message.caption_entities
    if not entities or entities[-1].type != "hashtag":
        raise ValueError("Не удалось извлечь ID для ответа")

    hashtag = entities[-1].get_text(message.text or message.caption)
    if not hashtag[3:].isdigit():
        raise ValueError("Некорректный ID для ответа")
    return int(hashtag[3:])


async def forward_meet_record(call: types.CallbackQuery, state: FSMContext):
    await call.answer('Заявка отправлена')
    await call.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()
    record = Record.from_dict(data.get('new_records')[0])
    bot = call.bot
    db: Database = bot.get('db')

    d1, d2 = record.begin, record.end
    record_id = await db.add_meet_record(d1, d2, data.get('user_id'))

    record_data_text = d1.strftime('%d.%m') + ', ' + d1.strftime('%H:%M') + '-' + d2.strftime('%H:%M')
    text = f'Заявка на бронь боталки от {data.get("fullname")} на {record_data_text}\n\n' \
           f'Ответьте на это сообщение файлом для печати для принятия заявки или текстом' \
           f' с описанием отказа.' + f"\n\n#id{record_id}"

    # keyboard = accept_or_reject_keyboard(record_id)
    await bot.send_message(chat_id=bot.get("admin_group_id"), text=text, parse_mode='HTML')
    await state.finish()


async def accept_meet(message: types.Message):
    try:
        record_id = await extract_id(message.reply_to_message)
    except ValueError as ex:
        return await message.reply(str(ex))

    db: Database = message.bot.get('db')
    record_info = await db.get_meet_record_id(record_id)
    await db.approve_meet_record(record_id)

    user_id = int(record_info[2])

    text = 'Заявка на бронь одобрена!\n' \
           'Пожалуйста, распечатайте и повесьте это объявления на дверь боталки.'
    await message.copy_to(user_id, parse_mode='HTML', caption=text)
    user_info = await db.get_user(user_id)

    create_task(update_photo_link(db, 'meet', record_info[0].date()))
    await message.reply('Заявка одобрена.')


async def reject_meet(message: types.Message):
    try:
        record_id = await extract_id(message.reply_to_message)
    except ValueError as ex:
        return await message.reply(str(ex))

    db: Database = message.bot.get('db')
    record_info = await db.get_meet_record_id(record_id)
    user_id = int(record_info[2])
    text = 'Заявка на бронь отклонена.\nПричина: ' + message.text
    await message.bot.send_message(user_id, parse_mode='HTML', text=text)
    await message.reply('Заявка отклонена.')
