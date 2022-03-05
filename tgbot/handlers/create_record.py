import typing
from datetime import date, timedelta, datetime, time

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import md

from tgbot.utils.time_funcs import parse_time_range, diff_in_minutes
import tgbot.keyboards.record_keyboards as keyboards
from tgbot.utils.photo_link import photo_link
from tgbot.utils.schedule import\
    WashSchedule, GymSchedule, MeetSchedule, Record,\
    get_schedule, record_data_repr, merge_records
from tgbot.databases.postrgres_db import Database
from tgbot.handlers.registration import check_if_registered


class CreateRecord(StatesGroup):
    choose_day = State()
    choose_washer = State()
    choose_time = State()
    final_check = State()


async def choose_day(message: types.Message, state: FSMContext):
    is_reg = await check_if_registered(message, state)
    if not is_reg:
        return

    await state.reset_data()

    await CreateRecord.choose_day.set()

    service = message.get_command()[1:]     # remove '/'
    await state.update_data(user_id=message.from_user.id)
    await state.update_data(service=service)
    db: Database = message.bot.get('db')
    user_data = await db.get_user(message.from_user.id)
    await state.update_data(fullname=user_data.get('fullname', ''))

    if service == 'wash':
        await choose_default_day(message, state)
        return

    keyboard = await keyboards.choose_day_keyboard(date.today(), service)
    await message.answer("Выберите день:", reply_markup=keyboard)


async def switch_days(call: types.CallbackQuery, state: FSMContext):
    action = call.data

    data = await state.get_data()
    service = data.get('service')

    first_button_data = call.message.reply_markup.inline_keyboard[0][0].callback_data
    cur_day = date.fromisoformat(first_button_data.split('=')[1])

    diff = timedelta(days=6)
    if action == 'next_days':
        cur_day += diff
    elif action == 'previous_days':
        cur_day -= diff

    keyboard = await keyboards.choose_day_keyboard(cur_day, service)
    await call.message.edit_reply_markup(reply_markup=keyboard)
    await call.answer()


async def get_hide_link(day: date, db: Database, service: str):
    link = await db.get_link(service, day)
    if not link:
        schedule = await get_schedule(db, day, service)
        path = await schedule.create_pic()
        link = await photo_link(path)
        await db.update_link(service, link, day)

    return md.hide_link(link)


async def choose_default_day(message: types.Message, state: FSMContext):
    # TODO mb make same for gym
    day = date.today()
    if datetime.now().hour >= 23:
        day += timedelta(days=1)
    await state.update_data(day=day.isoformat())

    data = await state.get_data()
    service = data.get('service')
    hide_link = await get_hide_link(day, message.bot.get('db'), service)
    await state.update_data(picture_link=hide_link)
    message = await message.answer('ᅠ')
    await after_day_chosen(None, state, message)


async def choose_button_day(call: types.CallbackQuery, state: FSMContext):
    day_isoformat = call.data.split('=')[1]
    await state.update_data(day=day_isoformat)
    day = datetime.fromisoformat(day_isoformat).date()
    data = await state.get_data()

    hide_link = await get_hide_link(day, call.bot.get('db'), data.get('service'))

    await state.update_data(picture_link=hide_link)

    await call.answer()
    await after_day_chosen(call, state)


async def after_day_chosen(call: typing.Optional[types.CallbackQuery],
                           state: FSMContext,
                           message: typing.Optional[types.Message] = None):
    menu_message_id = message.message_id if message else call.message.message_id
    await state.update_data(menu_message_id=menu_message_id)

    data = await state.get_data()
    service = data.get('service')

    if service == 'wash':
        await choose_washer(call, state, message)
    elif service == 'gym' or service == 'meet':
        await choose_time(call, state, message)


async def change_day(call: types.CallbackQuery, state: FSMContext):
    await CreateRecord.choose_day.set()

    data = await state.get_data()
    service = data.get('service')
    keyboard = await keyboards.choose_day_keyboard(date.today(), service)
    await call.message.edit_text("Выберите день:", reply_markup=keyboard)


async def choose_washer(call: typing.Optional[types.CallbackQuery],
                        state: FSMContext,
                        message: typing.Optional[types.Message] = None):
    if call:
        message = call.message
        await call.answer()

    await CreateRecord.choose_washer.set()
    data = await state.get_data()
    keyboard = await keyboards.choose_washer_keyboard()
    await message.edit_text(
        f'{data.get("picture_link")}Выберите номер машинки:', parse_mode='HTML',
        reply_markup=keyboard)


async def washer_chosen(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(washer=int(call.data.split('=')[1]))

    await choose_time(call, state)


async def choose_time(call: typing.Optional[types.CallbackQuery],
                      state: FSMContext,
                      message: typing.Optional[types.Message] = None):
    if call:
        message = call.message
        await call.answer()

    await CreateRecord.choose_time.set()
    data = await state.get_data()
    service = data.get('service')

    day = date.fromisoformat(data.get('day'))
    db = message.bot.get('db')
    keyboard = await keyboards.choose_time_keyboard(db, day, service, data.get('washer'))

    text = None
    if service == 'wash':
        text = 'Выберите предложенное время или введите своё:'
    elif service == 'gym':
        text = 'Выберите время'
    elif service == 'meet':
        text = 'Введите время'

    await message.edit_text(
        f'{data.get("picture_link")}' + text, parse_mode='HTML', reply_markup=keyboard)

    if service == 'meet':
        await custom_time(call, state)


async def button_time(call: types.CallbackQuery, state: FSMContext):
    time_range = await parse_time_range(call.data.split('=')[1])
    await call.answer()

    if not time_range:
        return
    await state.update_data(time_range=[t.isoformat() for t in time_range])
    await time_chosen(call.message, state)


async def custom_time(call: types.CallbackQuery, state: FSMContext):
    keyboard = types.ForceReply(input_field_placeholder='чч:мм-чч:мм')
    message = await call.message.answer(text='Введите время (например, 09:30-11:53)',
                                        reply_markup=keyboard)
    await call.answer()
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', []) + [message.message_id]
    await state.update_data(messages_to_delete=messages_to_delete)


async def get_custom_time(message: types.Message, state: FSMContext):
    time_range = await parse_time_range(message.text)
    keyboard = types.ForceReply(input_field_placeholder='чч:мм-чч:мм')
    data = await state.get_data()
    service = data.get('service')

    menu_message, bot_message = None, None
    if not time_range:
        bot_message = await message.reply(
            "Неправильный формат времени.\nПоробуйте ввести ещё раз.", reply_markup=keyboard)

    elif time_range[0] > time_range[1]:
        bot_message = await message.reply(
            'Конец не может быть раньше начала.\nПоробуйте ввести ещё раз.',
            reply_markup=keyboard, parse_mode='HTML')

    elif await diff_in_minutes(*time_range) < 30:
        bot_message = await message.reply(
            "Минимальное время для бронирования: 30 мин.\nПоробуйте ввести ещё раз.",
            reply_markup=keyboard)
    else:

        schedule = {'wash': WashSchedule, 'gym': GymSchedule, 'meet': MeetSchedule}[service]
        db = message.bot.get('db')
        args = [db, date.fromisoformat(data.get('day')), time_range]
        if service == 'wash':
            args.append(data.get('washer'))

        if not await schedule.is_time_free(*args):
            bot_message = await message.reply(
                "Это время уже прошло или занято, выберите другое.\n",
                reply_markup=keyboard)
        else:
            await state.update_data(time_range=[t.isoformat() for t in time_range])
            # just to get a message instance
            menu_message = await message.bot.edit_message_reply_markup(
                message_id=data.get('menu_message_id'), chat_id=message.from_user.id)

    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete += [message.message_id, bot_message.message_id] if bot_message else [message.message_id]
    await state.update_data(messages_to_delete=messages_to_delete)

    if menu_message:
        await time_chosen(menu_message, state)


async def create_record(data):
    day = date.fromisoformat(data.get('day'))
    dr = [datetime.combine(day, time.fromisoformat(t)) for t in data.get('time_range')]
    record = Record(dr[0], dr[1], data.get('washer'), data.get('fullname'))
    return record


async def time_chosen(message: types.Message, state: FSMContext):
    # called from custom_time or button_time
    data = await state.get_data()

    for message_id in data.get('messages_to_delete', []):
        await message.bot.delete_message(data.get('user_id'), message_id)
    await state.update_data(messages_to_delete=[])

    await CreateRecord.final_check.set()

    record = await create_record(data)
    await state.update_data(record=record.to_dict())

    records = [Record.from_dict(r) for r in data.get('records', [])]
    records.append(record)
    records = await merge_records(records)
    # new_records должны заменить records перед добавлением новой записи или оплатой
    await state.update_data(new_records=[r.to_dict() for r in records])

    text = "Данные записи:\n"
    service = data.get('service')
    if service == 'meet':
        text += 'Боталка, '
    text += await record_data_repr(records, service)

    minute_prices = {'wash': WashSchedule.minute_price, 'gym': GymSchedule.minute_price}
    minutes = sum([r.duration() for r in records])
    cost = minutes * minute_prices.get(service, 0)
    await state.update_data(cost=cost)
    if service != 'meet':
        text += f'\nК оплате: {cost} руб.'

    keyboard = await keyboards.time_chosen_keyboard(service)
    await message.edit_text(text=text, reply_markup=keyboard)


async def add_record(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(records=data.get('new_records'))
    await choose_washer(call, state)

