from aiogram import types
from datetime import date, timedelta, datetime
from tgbot.utils.time_funcs import day_repr, parse_time_range
from tgbot.utils.schedule import WashSchedule, GymSchedule, MeetSchedule
import typing
from tgbot.databases.postrgres_db import Database


async def create_days_labels(day: date, amount: int) -> dict:
    # returns dictionary {date: label}
    days_labels = {}

    for i in range(amount):
        cur_day = day+timedelta(days=i)
        days_labels[cur_day.isoformat()] = await day_repr(cur_day)

    return days_labels


async def choose_day_keyboard(day: date,  service: str):
    # day - с какого дня начинать генерацию клавиатуры
    days_in_row = 3
    keyboard = types.InlineKeyboardMarkup(row_width=days_in_row)
    days_labels = await create_days_labels(day, days_in_row * 2)

    for key, label in days_labels.items():
        is_open = True
        if service == 'gym':
            is_open = await GymSchedule.is_open(date.fromisoformat(key))

        button = types.InlineKeyboardButton(
            text=label if is_open else '—',
            callback_data='day=' + key if is_open else 'day=' + key + '=closed')
        keyboard.insert(button)

    keyboard.row(
        types.InlineKeyboardButton(
            text='←' if date.today() < day else '',
            callback_data='previous_days'),
        types.InlineKeyboardButton(
            text='→',
            callback_data='next_days'),
    )

    return keyboard


async def choose_washer_keyboard():
    washers_amount = len(WashSchedule.is_working)
    keyboard = types.InlineKeyboardMarkup(row_width=washers_amount)
    for i in range(0, washers_amount):
        button = types.InlineKeyboardButton(
            text='#' + str(i + 1),
            callback_data='washer=' + str(i))
        keyboard.insert(button)

    keyboard.add(types.InlineKeyboardButton(
        text='← Выбрать другой день',
        callback_data='change_day'))

    return keyboard


async def choose_time_keyboard(db: Database,
                               day: date,
                               service: str,
                               washer: typing.Optional[int] = None
                               ):
    keyboard = None

    if service == 'wash':
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        time_ranges = ['06:00-08:00', '12:00-14:00', '18:00-20:00',
                       '08:00-10:00', '14:00-16:00', '20:00-22:00',
                       '10:00-12:00', '16:00-18:00', '22:00-23:59']

        for time_range in time_ranges:
            tr = await parse_time_range(time_range)
            is_time_free = await WashSchedule.is_time_free(db, day, tr, washer)

            label = time_range if is_time_free else '—'
            data = time_range if is_time_free else 'busy'

            button = types.InlineKeyboardButton(
                text=label,
                callback_data='time=' + data)
            keyboard.insert(button)

        keyboard.add(
            types.InlineKeyboardButton(
                text='Задать своё время',
                callback_data='custom_time'))
        keyboard.add(
            types.InlineKeyboardButton(
                text='← Назад',
                callback_data='change_washer'))

    elif service == 'gym':
        keyboard = types.InlineKeyboardMarkup(row_width=2)

        trs = await GymSchedule.time_ranges_for_day(day)
        for tr in trs:
            is_time_free = await GymSchedule.is_time_free(db, day, tr)

            tr_str = [t.isoformat(timespec='minutes') for t in tr]
            time_range = tr_str[0] + '-' + tr_str[1]

            label = time_range if is_time_free else '—'
            data = time_range if is_time_free else 'busy'

            button = types.InlineKeyboardButton(
                text=label,
                callback_data='time=' + data)
            keyboard.insert(button)

        keyboard.add(types.InlineKeyboardButton(
            text='← Назад',
            callback_data='change_day'))

    elif service == 'meet':
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(
            text='← Назад',
            callback_data='change_day'))

    return keyboard


async def time_chosen_keyboard(service: str):
    keyboard = types.InlineKeyboardMarkup()
    if service == 'wash':
        keyboard.insert(
            types.InlineKeyboardButton(
                text='Добавить бронь',
                callback_data='add_record'
            )
        )
    keyboard.row(
        types.InlineKeyboardButton(
            text='← Назад',
            callback_data='change_time'),
        types.InlineKeyboardButton(
            text='Оплатить →' if service != 'meet' else 'Отправить заявку →',
            callback_data='pay' if service != 'meet' else 'meet_to_approve'),
    )
    return keyboard

