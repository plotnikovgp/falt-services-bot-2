from aiogram import Dispatcher
from aiogram.dispatcher.filters import IsReplyFilter, IDFilter
from aiogram.types import ContentType
from .create_record import *
from .payment import *
from .registration import *
from .common import *
from .manage_records import *
from .report import *
from .admin_mode import *
from .notification import *
from .approve_meet import *


def register_handlers_common(dp: Dispatcher):
    dp.register_message_handler(
        cmd_start,
        commands="start",
        state="*"
    )
    dp.register_message_handler(
        cmd_help,
        commands="help",
        state="*"
    )


def register_record_handlers(dp: Dispatcher):
    dp.register_message_handler(
        choose_day,
        commands=["wash", "gym", "meet"],
        state="*",
    )
    dp.register_callback_query_handler(
        switch_days,
        lambda c: c.data.endswith("days"),
        state=CreateRecord.choose_day,
    )
    dp.register_callback_query_handler(
        choose_button_day,
        lambda c: c.data.startswith("day=") and not c.data.endswith("closed"),
        state=CreateRecord.choose_day,
    )
    dp.register_callback_query_handler(
        change_day,
        lambda c: c.data == 'change_day',
        state="*",
    )
    dp.register_callback_query_handler(
        washer_chosen,
        lambda c: c.data.startswith('washer'),
        state=CreateRecord.choose_washer,
    )
    dp.register_callback_query_handler(
        button_time,
        lambda c: c.data.startswith('time='),
        state=CreateRecord.choose_time,
    )
    dp.register_callback_query_handler(
        custom_time,
        lambda c: c.data == 'custom_time',
        state=CreateRecord.choose_time,
    )
    dp.register_callback_query_handler(
        choose_washer,
        lambda c: c.data.startswith('change_washer'),
        state=CreateRecord.choose_time,
    )
    dp.register_message_handler(
        get_custom_time,
        state=CreateRecord.choose_time,
    )
    dp.register_callback_query_handler(
        choose_time,
        lambda c: c.data == 'change_time',
        state=CreateRecord.final_check,
    )
    dp.register_callback_query_handler(
        add_record,
        lambda c: c.data == 'add_record',
        state=CreateRecord.final_check,
    )


def register_payment_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(
        check_balance,
        lambda c: c.data == 'pay',
        state="*",
    )
    dp.register_callback_query_handler(
        top_up_balance,
        lambda c: c.data in ['top_up', 'back'],
        state=[Payment.check_balance, Payment.top_up_balance],
    )
    dp.register_callback_query_handler(
        button_top_up,
        lambda c: c.data.isdigit(),
        state=Payment.top_up_balance,
    )
    dp.register_callback_query_handler(
        custom_top_up,
        lambda c: c.data == 'custom',
        state=Payment.top_up_balance,
    )
    dp.register_message_handler(
        get_custom_top_up,
        state=Payment.top_up_balance,
    )


def register_handlers_registration(dp: Dispatcher):
    dp.register_message_handler(
        check_if_registered,
        commands="reg",
        state="*"
    )
    dp.register_message_handler(
        get_photo,
        state=Registration.get_photo.state,
        content_types=[ContentType.PHOTO, ContentType.DOCUMENT]
    )
    dp.register_message_handler(
        invalid_input,
        state=Registration.get_photo
    )
    dp.register_message_handler(
        get_surname,
        state=Registration.get_name
    )
    dp.register_message_handler(
        get_name,
        state=Registration.get_surname
    )

    dp.register_callback_query_handler(
        get_result,
        lambda c: c.data.startswith('accept') or c.data.startswith('reject'),
        state='*',
        chat_id=dp.bot.get('admin_group_id'),
    )


def register_manage_handlers(dp: Dispatcher):
    dp.register_message_handler(
        show_records,
        commands='records',
        state='*'
    )

    dp.register_callback_query_handler(
        delete_record,
        lambda c: c.data.startswith('delete'),
        state=[ManageRecords.show_records, ManageRecords.delete_record],
    )

    dp.register_callback_query_handler(
        show_records_button,
        lambda c: c.data == 'cancel_record',
        state='*'
    )


def register_report_handlers(dp: Dispatcher):
    dp.register_message_handler(
        cmd_report,
        commands='report',
        state='*'
    )

    dp.register_message_handler(
        send_report_text,
        content_types=ContentType.TEXT,
        state=Report.get_report.state,
    )

    dp.register_message_handler(
        send_report_photo,
        content_types=[
            ContentType.ANIMATION, ContentType.AUDIO, ContentType.PHOTO,
            ContentType.DOCUMENT, ContentType.VIDEO, ContentType.VOICE
        ],
        state=Report.get_report,
    )

    dp.register_callback_query_handler(
        restore_balance,
        lambda c: c.data == 'restore_balance',
        state=Report.get_report,
    )


def register_admin_handlers(dp: Dispatcher):
    admin_group_id = dp.bot.get('admin_group_id')

    dp.register_message_handler(
        change_user_balance,
        IsReplyFilter(is_reply=True), IDFilter(chat_id=admin_group_id),
        commands=['up']
    )

    dp.register_message_handler(
        reply_to_user,
        IDFilter(chat_id=admin_group_id),
        commands=['ans']
    )

    dp.register_message_handler(
        get_user_info,
        IsReplyFilter(is_reply=True), IDFilter(chat_id=admin_group_id),
        commands=['user_info']
    )


def register_notification_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(
        turn_on_notification,
        lambda c: c.data.startswith('notif_on'),
        state='*',
    )

    dp.register_callback_query_handler(
        turn_off_notification,
        lambda c: c.data.startswith('notif_off'),
        state='*',
    )


def register_meet_handlers(dp: Dispatcher):
    admin_group_id = dp.bot.get('admin_group_id')
    dp.register_callback_query_handler(
        forward_meet_record,
        lambda c: c.data == 'meet_to_approve',
        state='*',
    )
    dp.register_message_handler(
        accept_meet,
        IsReplyFilter(is_reply=True), IDFilter(chat_id=admin_group_id),
        content_types=ContentType.DOCUMENT,
    )
    dp.register_message_handler(
        reject_meet,
        IsReplyFilter(is_reply=True), IDFilter(chat_id=admin_group_id),
        content_types=ContentType.TEXT,
    )
    dp.register_message_handler(
        set_passcode,
        IDFilter(chat_id=admin_group_id),
        commands=['pass'],
    )


async def register_handlers(dp: Dispatcher):
    await set_menu_commands(dp.bot)
    register_handlers_registration(dp)
    register_record_handlers(dp)
    register_payment_handlers(dp)
    register_handlers_common(dp)
    register_manage_handlers(dp)
    register_report_handlers(dp)
    register_admin_handlers(dp)
    register_notification_handlers(dp)
    register_meet_handlers(dp)