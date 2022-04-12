import typing
from asyncio import create_task
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import types, Dispatcher

from uuid import uuid4
from datetime import datetime, timedelta, time, date

from tgbot.databases.postrgres_db import Database
from tgbot.handlers.create_record import CreateRecord
import tgbot.keyboards.payment_keyboards as keyboards
from tgbot.utils.schedule import Record, get_schedule, record_data_repr, update_photo_link
from tgbot.paysystems.yoomoney import PaySystem
from apscheduler.jobstores.base import JobLookupError


class Payment(StatesGroup):
    check_balance = State()
    top_up_balance = State()


async def check_balance(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(records=data.get('new_records'))

    await Payment.check_balance.set()
    await call.answer()

    await try_to_pay(call.message, state)


async def try_to_pay(message: types.Message, state: FSMContext):
    db = message.bot.get('db')

    data = await state.get_data()
    user_id = data.get('user_id')
    user_data = await db.get_user(user_id)

    paid = await db.change_balance(user_id, diff=-data.get('cost', 0))
    if paid:
        await after_payment(message, state)
    else:
        text = f"На балансе недостаточно средств.\n" \
               f"Текущий баланс: {user_data.get('balance', 0)} руб.\n"
        keyboard = await keyboards.not_enough_money_keyboard()
        await message.edit_text(text=text, reply_markup=keyboard)


async def top_up_balance(call: types.CallbackQuery):
    await Payment.top_up_balance.set()

    keyboard = await keyboards.choose_top_up_keyboard()
    await call.message.edit_text(
        text='Выберите сумму для пополнения или введите свою: ',
        reply_markup=keyboard,
    )
    await call.answer()


async def custom_top_up(call: types.CallbackQuery):
    keyboard = types.ForceReply()
    await call.message.answer(
        text='Введите сумму в руб: ',
        reply_markup=keyboard,
    )
    await call.answer()


async def show_pay_link(message: types.Message, state: FSMContext):
    data = await state.get_data()

    cost = data.get('top_up')
    pay_label = uuid4().hex

    await state.update_data(pay_label=pay_label)

    ps = message.bot.get('ps')
    pay_url = await ps.create_pay_url(cost, label=pay_label, name=data.get('fullname'))

    keyboard = await keyboards.show_pay_link_keyboard(pay_url=pay_url)
    await message.edit_text(
        text=f'К оплате: {cost} руб.\nОплата принимается в течение 20 минут.',
        reply_markup=keyboard,
    )
    scheduler = message.bot.get('scheduler')

    d1 = datetime.now()
    d2 = d1 + timedelta(minutes=20)
    scheduler.add_job(check_payment, 'interval', args=[ps, pay_label, message, state],
                      start_date=d1, end_date=d2, seconds=1,
                      id='check_payment_' + str(pay_label), max_instances=15,
                      replace_existing=True)
    scheduler.add_job(try_to_pay, 'date', args=[message, state],
                      run_date=d2, id='payment_time_left_' + str(pay_label), max_instances=15,
                      replace_existing=True)


async def get_custom_top_up(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.reply(
            text='Неправильный формат: ожидается число.\n Попробуйте ввести ещё раз.',
            reply_markup=types.ForceReply())
        return

    await state.update_data(top_up=float(message.text))
    data = await state.get_data()

    # just to get a message instance
    bot_message = await message.bot.edit_message_reply_markup(
        message_id=data.get('menu_message_id'), chat_id=message.from_user.id)
    await show_pay_link(bot_message, state)


async def button_top_up(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(top_up=float(call.data))
    await show_pay_link(call.message, state)
    await call.answer()


async def check_payment(ps: PaySystem, label: str, message: types.Message, state: FSMContext):
    completed = await ps.is_payment_successful(label)
    if completed:
        db = message.bot.get('db')
        data = await state.get_data()
        await db.change_balance(data.get('user_id'), data.get('top_up'))
        scheduler = message.bot.get('scheduler')
        try:
            scheduler.remove_job(job_id='check_payment_' + label)
        except JobLookupError as ex:
            print(f'Payment remove_job error:\n {ex}')
        await try_to_pay(message, state)


async def after_payment(message: types.Message, state: FSMContext):
    db: Database = message.bot.get('db')
    data = await state.get_data()
    service = data.get('service')

    recs = [Record.from_dict(r) for r in data.get('records')]

    user_id = data.get('user_id')
    user_info = await db.get_user(user_id)

    record_id = None
    for r in recs:
        cur_record_id = None
        if service == 'wash':
            cur_record_id = await db.add_wash_record(r.begin, r.end, r.washer, user_id)
        elif service == 'gym':
            cur_record_id = await db.add_gym_record(r.begin, r.end, user_id)

        record_id = cur_record_id if not record_id else record_id

    create_task(update_photo_link(db, service, recs[0].begin.date()))

    text = f'Вы успешно записаны.\n'
    text += f"Текущий баланс: {user_info.get('balance', 0)} руб.\n\n"
    text += "Данные записи:\n"
    text += await record_data_repr(recs, service)
    if service == 'wash':
        for i in range(50):
            passcode = await db.get_passcode(date.today() - timedelta(days=i))
            if passcode:
                break
        else:
            passcode = '0003405'
        text += f"\nКод для входа:\n{passcode}#"

    keyboard = await keyboards.show_record_keyboard(recs[0].begin, record_id, service == 'wash')
    await message.edit_text(text=text, reply_markup=keyboard)

    await state.finish()


