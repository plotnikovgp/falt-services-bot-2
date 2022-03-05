from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import tgbot.keyboards.registration_keyboards as keyboards
from tgbot.databases.postrgres_db import Database
from tgbot.locks.wash_lock import create_passcode


class Registration(StatesGroup):
    get_photo = State()
    get_name = State()
    get_surname = State()
    wait_result = State()


async def check_if_registered(message: types.Message, state: FSMContext) -> bool:
    user_id = message.from_user.id
    db: Database = message.bot.get('db')
    user_info = await db.get_user(user_id)

    if not user_info or not user_info.get('is_registered', False):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        await state.update_data(chat_id=message.chat.id)

        photo = types.InputFile(path_or_bytesio='/app/tgbot/utils/other_pictures/id_example.png')

        await message.answer_photo(
            photo=photo,
            caption="Вам необходимо зарегистрироваться.\n"
                    "Отправьте скриншот вашего электронного студенческого билета."
                    f'Его можно найти в <a href="https://profile.mipt.ru/">личном профиле</a> '
                    f'в разделе "Учебный процесс"',
            reply_markup=keyboard, parse_mode='HTML')

        await Registration.get_photo.set()
        return False
    return True


async def get_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_message_id=message.message_id)
    await message.answer("Введите свою фамилию.")
    await Registration.get_name.set()


async def invalid_input(message: types.Message):
    await message.answer("Неправильный ввод, ожидается фото.")


async def get_surname(message: types.Message, state: FSMContext):
    await state.update_data(surname_message_id=message.message_id)
    await state.update_data(surname=message.text)
    await message.answer("Введите своё имя.")
    await Registration.get_surname.set()


async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name_message_id=message.message_id)
    await state.update_data(name=message.text)
    await forward_data(message, state)


async def forward_data(message: types.Message, state: FSMContext):
    bot = message.bot
    data = await state.get_data()
    fullname = data.get('surname') + ' ' + data.get('name')
    db: Database = message.bot.get('db')
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)

    if not user_data:
        passcode = await create_passcode()
        await db.add_user(username=message.from_user.username,
                          tg_id=message.from_user.id,
                          fullname=fullname,
                          passcode=passcode)

    else:
        passcode = await create_passcode()
        await state.update_data(user_id=user_id)
        await db.change_passcode(tg_id=user_id, passcode=passcode)
        await db.change_fullname(tg_id=user_id, fullname=fullname)

    for message_id in [data.get('photo_message_id'), data.get('name_message_id'), data.get('surname_message_id')]:
        await bot.forward_message(chat_id=bot.get("admin_group_id"),
                                  from_chat_id=message.chat.id,
                                  message_id=message_id)

    await message.answer("Заявка отправлена, в ближайшее время она будет проверена.")
    keyboard = await keyboards.accept_or_reject_keyboard(user_id)
    await bot.send_message(chat_id=bot.get("admin_group_id"),
                           reply_markup=keyboard,
                           text='Зарегистрировать пользователя?')
    await Registration.wait_result.set()


async def get_result(call: types.CallbackQuery, state: FSMContext):
    bot = call.bot
    db: Database = bot.get('db')

    res, user_id = call.data.split('_')
    user_id = int(user_id)
    if res == 'accept':
        await db.register_user(user_id)
        text = 'Регистрация успешно завершена!\n'
        text += "Выберите, что хотите сделать:\n" \
                "/wash – записаться на стирку\n" \
                "/gym – записаться в зал\n" \
                "/meet - забронировать время в комнате для собраний"
        await bot.send_message(chat_id=user_id,
                               text=text)
    elif res == 'reject':
        await bot.send_message(chat_id=user_id,
                               text='Заявка на регистрацию отклонена.\n'
                                    'Проверьте правильность введенных данных и попробуйте ещё раз (/reg).')
    await call.answer()
    await call.message.delete()
    await state.finish()
