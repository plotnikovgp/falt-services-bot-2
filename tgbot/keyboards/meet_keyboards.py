from aiogram import types
import typing


async def accept_or_reject_keyboard(record_id):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.row(
        types.InlineKeyboardButton(
            text='Отклонить',
            callback_data=f'meet_reject_{record_id}'),
        types.InlineKeyboardButton(
            text='Принять',
            callback_data=f'meet_accept_{record_id}'),
    )
    return keyboard