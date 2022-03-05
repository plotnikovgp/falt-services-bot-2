from aiogram import Dispatcher, Bot, types
from aiogram.types import InputMediaPhoto


# commands showed in menu
async def set_menu_commands(bot: Bot):
    commands = [
        types.BotCommand(command="/wash", description="Записаться на стирку"),
        types.BotCommand(command="/gym", description="Записаться в зал"),
        types.BotCommand(command='/records', description='Посмотреть/отменить записи'),
        types.BotCommand(command="/meet", description="Забронировать комнату для собраний"),
        types.BotCommand(command="/help", description="Контакты отвественных"),
        types.BotCommand(command='/report', description="Сообщить о проблеме")
    ]
    await bot.set_my_commands(commands)


async def cmd_start(message: types.Message):
    await message.answer("*Перед использованем бота просьба ознакомиться с приведёнными ниже правилами и рекомендациями."
                         " по использованию сервисов.*\n\n\n"   
                         "*Стиральная комната*\n\n"
                         "•Забронируйте машинку в удобное для вас время.\n\n"
                         "•В назначенное время придите в стиральную комнату со свои средством для стирки и бельём.\n\n"
                         "•Настоятельно рекомендуется использовать гель или капсулы для стирки, т.к."
                         "обычный порошок для стирки сильно засоряет машинки. Машинки нужно будет реже чистить,"
                         "и они прослужат дольше.\n\n"
                         "•Оставьте мешок для вещей на машинке, чтобы слудующий человек мог достать ваши вещи.\n\n"
                         "•После окончания стирки откройте дверцу стиралки и лоток для порошка для проветривания."
                         "Выключите свет в комнате.\n\n"
                         "•Внимание: стираться разрешается только в забронированное вами время.\n"
                         "_Уважайте своих сожителей, заканчивайте стирку вовремя._\n\n\n"
                         "*Комната для собраний*\n"
                         "TODO\n\n\n"
                         "*Тренажерный зал*\n"
                         "TODO\n\n\n"
                         "*Выберите, что хотите сделать:*\n"
                         "/wash – записаться на стирку\n"
                         "/gym – записаться в зал\n"
                         "/meet - забронировать время в комнате для собраний",
                         parse_mode='markdown')


async def cmd_help(message: types.Message):
    # TODO
    await message.answer("По всем вопросам и проблемам пишите на указанные контакты.\n"
                         "Проблемы в работе бота – @flexzis\n"
                         "Ответсвенный за стиральную комнату – @flexzis\n"
                         "Ответсвенный за зал –  @afanasevda\n"
                         "Ответсвенный за боталку – @Nerv_OS")


# async def cmd_test(message: types.Message):
#    await message.reply_photo(photo="https://ibb.co/N6PySbJ")


