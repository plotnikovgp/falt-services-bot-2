from aiogram import types
import typing


async def accept_or_reject_keyboard(user_id):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.row(
        types.InlineKeyboardButton(
            text='Отклонить',
            callback_data=f'reject_{user_id}'),
        types.InlineKeyboardButton(
            text='Принять',
            callback_data=f'accept_{user_id}'),
    )
    return keyboard

