from datetime import date, timedelta, datetime, time
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import tgbot.keyboards.manage_keyboards as keyboards
from tgbot.databases.postrgres_db import Database
from tgbot.utils.schedule import\
    WashSchedule, GymSchedule, Record, schedule_from_dict
from tgbot.handlers.registration import check_if_registered


class ManageRecords(StatesGroup):
    show_records = State()
    delete_record = State()


async def show_records(message: types.Message, state: FSMContext, from_delete: bool = False):
    is_reg = await check_if_registered(message, state) if not from_delete else True
    if not is_reg:
        return

    if from_delete:
        data = await state.get_data()
        user_id = data['user_id']
    else:
        await state.reset_data()
        user_id = message.from_user.id
        await state.update_data(user_id=user_id)

    await ManageRecords.show_records.set()
    db: Database = message.bot.get('db')

    user_info = await db.get_user(user_id)

    text = f"Текущий баланс: {user_info.get('balance', 0)} руб.\n\n"

    gym_records = await db.get_user_gym_records(user_id)
    wash_records = await db.get_user_wash_records(user_id)

    keyboard = await keyboards.manage_records_keyboard(gym_records, wash_records)

    if not (gym_records or wash_records):
        text += 'У вас нет предстоящих записей.'
    else:
        text += 'Нажмите на запись, чтобы отменить её.\nВаши записи:'

    if from_delete:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


# TODO merge two functions
async def show_records_button(call: types.CallbackQuery, state: FSMContext, from_delete: bool = False):
    await call.answer()

    if from_delete:
        data = await state.get_data()
        user_id = data['user_id']
    else:
        await state.reset_data()
        user_id = call.from_user.id
        await state.update_data(user_id=user_id)

    await ManageRecords.show_records.set()
    db: Database = call.bot.get('db')

    user_info = await db.get_user(user_id)

    text = f"Текущий баланс: {user_info.get('balance', 0)} руб.\n\n"

    gym_records = await db.get_user_gym_records(user_id)
    wash_records = await db.get_user_wash_records(user_id)

    keyboard = await keyboards.manage_records_keyboard(gym_records, wash_records)

    if not (gym_records or wash_records):
        text += 'У вас нет предстоящих записей.'
    else:
        text += 'Нажмите на запись, чтобы отменить её.\nВаши записи:'

    if from_delete:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await call.bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard)


async def delete_record(call: types.CallbackQuery, state: FSMContext):
    await ManageRecords.delete_record.set()

    data = await state.get_data()
    db: Database = call.bot.get('db')
    _, service, record_id, start_time, cost = call.data.split('_')

    start_time = datetime.fromisoformat(start_time)
    cur_time = datetime.now()

    diff_minutes = (start_time - cur_time).total_seconds() / 60

    if service == 'wash':
        if diff_minutes <= WashSchedule.minutes_to_close:
            await call.answer('Эту запись уже нельзя отменить.')
            await call.message.edit_text(call.message.text, reply_markup=call.message.reply_markup)
            return
        await db.delete_wash_record(int(record_id))
    elif service == 'gym':
        if diff_minutes <= GymSchedule.minutes_to_close:
            await call.answer('Эту запись уже нельзя отменить.')
            await call.message.edit_text(call.message.text, reply_markup=call.message.reply_markup)
            return
        await db.delete_gym_record(int(record_id))

    await call.answer()
    await db.change_balance(data.get('user_id'), float(cost))
    await db.delete_link(service, start_time.date())
    await show_records(call.message, state, True)


