from asyncio import create_task, sleep
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from tgbot.databases.postrgres_db import Database
from tgbot.handlers.registration import check_if_registered


class Report(StatesGroup):
    get_report = State()


async def cmd_report(message: types.Message, state: FSMContext):
    is_reg = await check_if_registered(message, state)

    if not is_reg:
        return

    await state.update_data(user_id=message.from_user.id)
    keyboard = types.InlineKeyboardMarkup()

    keyboard.insert(
        types.InlineKeyboardButton(
            text='Перенести баланс с yafalt.ru',
            callback_data='restore_balance'
        )
    )
    await message.answer("Опишите вашу проблему/вопрос/предложение.\n", reply_markup=keyboard)
    await Report.get_report.set()


async def send_report_text(message: types.Message, state: FSMContext):
    if len(message.text) > 4000:
        return await message.reply("К сожалению, длина этого сообщения превышает допустимый размер. "
                                   "Пожалуйста, сократи свою мысль и попробуй ещё раз.")
    admin_group_id = message.bot.get("admin_group_id")

    data = await state.get_data()
    db: Database = message.bot.get('db')
    user_info = await db.get_user(data.get('user_id'))

    text = f'Сообщение от {user_info.get("fullname")}:\n\n'
    text += message.text + f"\n\n#id{message.from_user.id}"
    await message.bot.send_message(admin_group_id, text, parse_mode='HTML')

    await message.reply('Ваше сообщение передано, спасибо за обратную связь!')
    await state.finish()


async def send_report_photo(message: types.Message):
    if message.caption and len(message.caption) > 1000:
        return await message.reply("К сожалению, длина подписи медиафайла превышает допустимый размер. "
                                   "Пожалуйста, сократи свою мысль и попробуй ещё раз.")

    admin_group_id = message.bot.get("admin_group_id")

    await message.copy_to(admin_group_id, parse_mode='HTML',
                          caption=((message.caption or "") + f"\n\n#id{message.from_user.id}"))

    await state.finish()


async def restore_balance(call: types.CallbackQuery, state: FSMContext):
    await call.answer('Заявка отправлена.')
    bot = call.bot
    admin_group_id = bot.get("admin_group_id")
    data = await state.get_data()
    db: Database = bot.get('db')
    user_id = data.get('user_id')
    user_info = await db.get_user(user_id)

    text = f'Ответьте на это сообщение "/up [cумма]", чтобы пополнить ' \
           f'баланс пользователя {user_info.get("fullname")}'
    text += f"\n\n#id{user_id}"
    await bot.send_message(admin_group_id, text, parse_mode='HTML')

    await state.finish()
