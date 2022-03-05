import typing
from datetime import datetime, date, time, timedelta
from aiogram.dispatcher import FSMContext
from aiogram import types, Dispatcher
from tgbot.keyboards.payment_keyboards import remove_notification_keyboard, show_record_keyboard
from tgbot.databases.postrgres_db import Database
from apscheduler.jobstores.base import JobLookupError


async def send_notification(message: types.Message, record_id):
    db: Database = message.bot.get('db')
    rec = await db.get_wash_record_id(int(record_id))
    if rec:
        await message.answer("Стирка начнется через 15 минут!")


async def turn_on_notification(call: types.CallbackQuery):
    splited = call.data.split('_')
    record_id = splited[-2]
    start_s = splited[-1]
    start = datetime.strptime(start_s, '%y%m%d%H%M')
    job_id = start_s + '#' + record_id

    start_d = start - timedelta(minutes=15)
    if start_d < datetime.now():
        await call.answer('Запись уже началась или начнется совсем скоро.')
        return

    scheduler = call.bot.get('scheduler')
    scheduler.add_job(send_notification, 'date', id=job_id, args=[call.message, record_id],
                      run_date=start_d, max_instances=15, replace_existing=True)

    keyboard = await remove_notification_keyboard(job_id)
    await call.message.edit_text(call.message.text, reply_markup=keyboard)
    await call.answer('Уведомление придет за 15 минут до начала записи.')


async def turn_off_notification(call: types.CallbackQuery):
    scheduler = call.bot.get('scheduler')
    job_id = call.data.split('_')[-1]
    try:
        scheduler.remove_job(job_id=job_id)
        await call.answer('Уведомление отменено.')
    except JobLookupError as ex:
        await call.answer('Уведомление отменено или уже отправлено.')

    [start_s, record_id] = job_id.split('#')
    start = datetime.strptime(start_s, '%y%m%d%H%M')
    keyboard = await show_record_keyboard(start, record_id)
    await call.message.edit_text(text=call.message.text, reply_markup=keyboard)
