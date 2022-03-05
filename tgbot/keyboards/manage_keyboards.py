from aiogram import types
from datetime import date, timedelta, datetime
from tgbot.utils.time_funcs import day_repr, parse_time_range
from tgbot.utils.schedule import WashSchedule, GymSchedule
from typing import List
from tgbot.utils.time_funcs import format_record_string, diff_in_minutes


async def manage_records_keyboard(gym_records: List, wash_records: List):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    d = datetime.today()
    d.date().isoformat()

    for gr in gym_records:
        label = 'Зал: '
        day = gr[1].date()
        time_range = [gr[1].time(), gr[2].time()]
        label += await format_record_string(day, time_range)

        cost = await diff_in_minutes(time_range[1], time_range[0])
        cost *= GymSchedule.minute_price

        button = types.InlineKeyboardButton(
            text=label,
            callback_data=f'delete_gym_{gr[0]}_{gr[1].isoformat()}_{cost}')
        keyboard.insert(button)

    for wr in wash_records:
        label = 'Стирка: '
        day = wr[1].date()
        time_range = [wr[1].time(), wr[2].time()]
        label += await format_record_string(day, time_range)
        label += ', машинка #' + str(wr[3] + 1)

        cost = await diff_in_minutes(time_range[1], time_range[0])
        cost *= WashSchedule.minute_price

        button = types.InlineKeyboardButton(
            text=label,
            callback_data=f'delete_wash_{wr[0]}_{wr[1].isoformat()}_{cost}')
        keyboard.insert(button)

    return keyboard

