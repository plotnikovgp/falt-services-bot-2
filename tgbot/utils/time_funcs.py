from typing import Tuple, List, Optional, Union
import re
from datetime import date, timedelta, datetime, time
from dateutil.parser import parse, ParserError


async def day_repr(day: date) -> str:
    weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    if day == date.today():
        return 'Сегодня'
    elif day == date.today() + timedelta(days=1):
        return 'Завтра'
    return weekdays[day.weekday()] + day.strftime(' %d.%m')


def day_repr2(day: date) -> str:
    weekdays = ['ПОНЕДЕЛЬНИК', 'ВТОРНИК', 'СРЕДА',
                'ЧЕТВЕРГ', 'ПЯТНИЦА', 'СУББТОТА', 'ВОСКРЕСЕНЬЕ']
    s_month = str(day.month) if day.month >= 10 else '0' + str(day.month)
    return weekdays[day.weekday()] + ' ' + str(day.day) + '.' + s_month


async def parse_time_range(time_range: str) -> Optional[Tuple[time, time]]:
    """
    examples of correct strings: '9:30-11:57', '22:15 23:16'
    :return: List[time, time] if str is correct, None otherwise
    """
    if not re.fullmatch(r"\d{1,2}:\d{2}[- ]\d{1,2}:\d{2}", time_range):
        return None
    p = re.split('[-, ]', time_range)
    if len(p) != 2 or not (p[0] or p[1]):
        return None
    try:
        return parse(p[0]).time(), parse(p[1]).time()
    except ParserError:
        return None


async def format_record_string(day: date, time_range: List[Union[time, datetime]]) -> str:
    s_day = await day_repr(day)
    s_time = time_range[0].strftime('%H:%M') + '-' + time_range[1].strftime('%H:%M')
    return s_day + ', ' + s_time


async def diff_in_minutes(t1: time, t2: time) -> int:
    return abs((t2.hour - t1.hour) * 60 + t2.minute - t1.minute)


def minute_from_datetime(day: Union[datetime, time, date]) -> int:
    return day.hour * 60 + day.minute


def datetime_time_repr(day: datetime) -> str:
    s_minute = str(day.minute) if day.minute >= 10 else '0' + str(day.minute)
    return str(day.hour) + ':' + s_minute
