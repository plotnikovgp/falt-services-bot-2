import typing
from datetime import datetime
from aiogram import types


async def not_enough_money_keyboard():
    return types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton(text='Пополнить →', callback_data='top_up'))


async def choose_top_up_keyboard() -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    for i in range(1, 5):
        cost = i * 30
        keyboard.insert(types.InlineKeyboardMarkup(
            text=float(cost), callback_data=str(cost)))
    keyboard.add(types.InlineKeyboardButton(text='Другая', callback_data='custom'))
    return keyboard


async def show_pay_link_keyboard(pay_url: str):
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton(text='← Назад', callback_data='back'),
        types.InlineKeyboardButton(text='Оплатить', callback_data='pay', url=pay_url))


async def show_record_keyboard(start: datetime, record_id: typing.Union[str, int], notification: bool = False):

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            text='Отменить запись',
            callback_data='cancel_record'
        )
    )
    if notification:
        start_s = start.strftime('%y%m%d%H%M')
        keyboard.add(
            types.InlineKeyboardButton(
                text='Включить уведомление',
                callback_data=f'notif_on_{record_id}_{start_s}'
            )
        )
    return keyboard


async def remove_notification_keyboard(job_id):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            text='Отменить запись',
            callback_data='cancel_record'
        )
    )
    keyboard.add(
        types.InlineKeyboardButton(
            text='Отключить уведомление',
            callback_data='notif_off_' + str(job_id)
        )
    )
    return keyboard
