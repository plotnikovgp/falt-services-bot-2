import typing
from datetime import datetime, date, time, timedelta

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
from marshmallow import fields

import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
from matplotlib.patches import FancyBboxPatch

from tgbot.databases.postrgres_db import Database
import tgbot.utils.time_funcs as tf
from tgbot.utils.time_funcs import format_record_string
from tgbot.utils.photo_link import photo_link


@dataclass_json
@dataclass
class Record:
    begin: datetime = field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format='iso')
        )
    )
    end: datetime = field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format='iso')
        )
    )
    washer: typing.Optional[int] = None
    name: typing.Optional[str] = ''

    def duration(self) -> int:
        """Returns the duration between the end and begin dates in minutes"""
        delta = self.end - self.begin
        return round(delta.total_seconds() / 60)

    def cost(self, service: str) -> float:
        if service == 'gym':
            return 30
        minute_prices = {'wash': 0.25 if self.washer != 5 else 0.125, 'gym': 0.5, 'meet': 0.}
        cost = self.duration() * minute_prices[service]
        return round(cost * 2) / 2


async def merge_records(records: typing.List[Record]):
    recs_by_washers = {}
    for r in records:
        w = r.washer or -1
        if recs_by_washers.get(w):
            recs_by_washers[w].append(r)
        else:
            recs_by_washers[w] = [r]

    res = []
    for recs in recs_by_washers.values():
        recs.sort(key=lambda x: x.begin)
        res.append(recs[0])
        for r in recs[1:]:
            r1 = res[-1]
            if r.begin > r1.end or r.end < r1.begin:
                res.insert(0, r)
            else:
                merged_r = Record(min(r.begin, r1.begin), max(r.end, r1.end), r.washer, r.name)
                res.pop()
                res.append(merged_r)
    return res


async def record_data_repr(records: typing.Iterable[Record], service: str) -> str:
    text = ''
    for rec in records:
        rec = Record.from_dict(rec)
        time_range = [rec.begin, rec.end]
        text += await format_record_string(rec.begin.date(), time_range)
        if service == 'wash':
            text += ', машинка #' + str(rec.washer + 1)
        text += '\n'
    return text


@dataclass_json
@dataclass
class BaseSchedule:
    day: date = field(
        metadata=config(
            encoder=date.isoformat,
            decoder=date.fromisoformat,
            mm_field=fields.DateTime(format='iso')
        ))
    records: typing.List[Record]

    @staticmethod
    async def _set_font():
        font_dir = ['../']
        for font in font_manager.findSystemFonts(font_dir):
            font_manager.fontManager.addfont(font)
        plt.rcParams['font.family'] = 'Source Sans Pro'


@dataclass_json
@dataclass
class WashSchedule(BaseSchedule):
    is_working: typing.Tuple[int] = (1, 1, 1, 1, 1, 1)
    minutes_to_close: int = 30

    @staticmethod
    async def draw_record(ax, record: Record):
        begin = tf.minute_from_datetime(record.begin)
        end = tf.minute_from_datetime(record.end)

        xlen = ax.get_xlim()[1] - ax.get_xlim()[0]
        xdist_from_edge = 24
        alpha = 0.85
        p_record = FancyBboxPatch((xdist_from_edge + 4, begin + 5),
                                  xlen - 2 * xdist_from_edge, end - begin - 4,
                                  zorder=2, fc='#a4e4fc', alpha=alpha, ec='#429BDB')
        ax.add_patch(p_record)

        s_time = tf.datetime_time_repr(record.begin) + "-" + tf.datetime_time_repr(record.end)

        name = record.name
        if name and ' ' in name:
            splited = name.split(' ')
            [l_name, f_name] = splited[0], splited[-1]
            name = l_name + ' ' + f_name[0] + '.' if f_name else l_name
        # ax.text(0, begin + (end - begin) / 2., s_time, ha='left', va='center', fontsize='10')
        ax.text(xlen / 2. + 10, begin + (end - begin) / 2., s_time + ' ' + str(name),
                ha='center', va='center', fontsize='10')

    @staticmethod
    async def draw_column(ax, ncol: int, is_working: bool = (1, 1, 1, 1, 1, 1)):
        minutes_in_day = 1440

        ax.set(title='#' + (str(ncol + 1) if ncol != 5 else '6 (Сушилка)'),
               ylim=(minutes_in_day, 0), xlim=(0, minutes_in_day),
               xticks=[], yticks=[j * 120 for j in range(13)], yticklabels=[])

        ax.grid(axis='y', ls='--', color='#dedede')
        ax.yaxis.set_ticks_position('none')

        color = '#ffffff' if is_working else '#D9D9D9'
        p = FancyBboxPatch((0, 0), minutes_in_day, minutes_in_day, color=color)

        ax.add_patch(p)

    @staticmethod
    async def draw_time_ticks(ax, pos: str):
        time_ticks = ['00:00', '02:00', '04:00', '06:00', '08:00', '10:00',
                      '12:00', '14:00', '16:00', '18:00', '20:00', '22:00', '24:00']
        ax.set(yticklabels=time_ticks)
        ax.yaxis.set_ticks_position(pos)

    async def create_pic(self) -> str:
        # Creates schedule as png file for given day
        n = len(self.is_working)
        column_width = 2.4
        column_height = 7.0

        await self._set_font()
        fig, axes = plt.subplots(ncols=n, figsize=[n * column_width, column_height])
        fig.suptitle(tf.day_repr2(self.day), fontsize=20)

        for i, ax in enumerate(axes):
            await self.draw_column(ax, i, bool(self.is_working[i]))

        for record in self.records:
            await self.draw_record(axes[record.washer], record)

        await self.draw_time_ticks(axes[0], 'left')
        await self.draw_time_ticks(axes[5], 'right')

        plt.tight_layout()
        fname = f'/app/tgbot/utils/schedule_pictures/wash-{self.day.isoformat()}.png'
        plt.savefig(fname)
        return fname

    @classmethod
    async def is_time_free(cls,
                           db: Database,
                           day: date,
                           time_range: typing.Tuple[time, time],
                           washer: int,
                           ) -> bool:
        [d1, d2] = [datetime.combine(day, t) for t in time_range]
        recs = await db.count_wash_records(d1, d2, washer)
        return recs == 0 and datetime.now() - timedelta(minutes=20) <= d1


@dataclass_json
@dataclass
class MeetSchedule(BaseSchedule):
    @staticmethod
    async def draw_record(ax, record: Record):
        begin = tf.minute_from_datetime(record.begin)
        end = tf.minute_from_datetime(record.end)

        xlen = ax.get_xlim()[1] - ax.get_xlim()[0]
        xdist_from_edge = 24
        alpha = 0.85
        p_record = FancyBboxPatch((xdist_from_edge + 3, begin + 4),
                                  xlen - 2 * xdist_from_edge, end - begin - 3,
                                  zorder=2, fc='#a4e4fc', alpha=alpha, ec='#429BDB')
        ax.add_patch(p_record)
        s_time = tf.datetime_time_repr(record.begin) + "-" + tf.datetime_time_repr(record.end)
        name = record.name

        fontsize = 12 if begin - end >= 40 else 10
        ax.text(xlen / 2., begin + (end - begin) / 2., s_time + '  ' + str(name),
                ha='center', va='center', fontsize=fontsize)

    @staticmethod
    async def draw_column(ax):
        minutes_in_day = 1440
        ax.set(ylim=(minutes_in_day, 0), xlim=(0, minutes_in_day),
               xticks=[], yticks=[j * 1440 / 4 for j in range(5)], yticklabels=[])

        ax.grid(axis='y', ls='--', color='#dedede')
        ax.yaxis.set_ticks_position('none')

        color = '#ffffff'
        p = FancyBboxPatch((0, 0), minutes_in_day, minutes_in_day, color=color)
        ax.add_patch(p)

    @staticmethod
    async def draw_time_ticks(ax, pos: str):
        time_ticks = ['00:00', '06:00', '12:00', '18:00', '24:00']
        ax.set(yticklabels=time_ticks)
        ax.yaxis.set_ticks_position(pos)

    async def create_pic(self) -> str:
        column_width = 3.5
        column_height = 7.0

        await self._set_font()
        fig, ax = plt.subplots(ncols=1, figsize=[column_width, column_height])
        fig.suptitle(tf.day_repr2(self.day), fontsize=20)

        await self.draw_column(ax)

        for record in self.records:
            await self.draw_record(ax, record)
        await self.draw_time_ticks(ax, 'left')

        fname = f'/app/tgbot/utils/schedule_pictures/meet-{self.day.isoformat()}.png'
        # fname = f'utils/schedule_pictures/meet-{self.day.isoformat()}.png'
        plt.savefig(fname)
        return fname

    @classmethod
    async def is_time_free(cls,
                           db: Database,
                           day: date,
                           time_range: typing.Tuple[time, time],
                           ) -> bool:
        [d1, d2] = [datetime.combine(day, t) for t in time_range]
        recs = await db.count_meet_records(d1, d2)
        return recs == 0 and datetime.now() <= d1


@dataclass_json
@dataclass
class GymSchedule(BaseSchedule):
    max_people: int = 7
    minutes_to_close: int = 5

    @classmethod
    async def is_open(cls, day: date):
        return await cls.time_ranges_for_day(day) is not None

    @classmethod
    async def time_ranges_for_day(cls, day: date):
        regular_time_range = ((time(hour=18, minute=0), time(hour=19, minute=30)),
                              (time(hour=19, minute=30), time(hour=21, minute=0)))
        saturday = ((time(hour=12, minute=0), time(hour=13, minute=0)),
                    (time(hour=13, minute=0), time(hour=14, minute=0)))
        sunday = ((time(hour=11, minute=0), time(hour=12, minute=30)),
                    (time(hour=12, minute=30), time(hour=14, minute=0)))
        schedule = {
            1: None,
            2: regular_time_range,
            3: regular_time_range,
            4: regular_time_range,
            5: None,
            6: saturday,
            7: sunday
        }
        return schedule.get(day.isoweekday())

    async def get_records_in_range(self, time_range: typing.Tuple[time, time]) -> list:
        res = []
        for r in self.records:
            if r.begin.time() <= time_range[0] and time_range[1] <= r.end.time():
                res.append(r)
        return res

    @classmethod
    async def is_time_free(cls,
                           db: Database,
                           day: date,
                           time_range: typing.Tuple[time, time],
                           ) -> bool:
        [d1, d2] = [datetime.combine(day, t) for t in time_range]
        recs = await db.count_gym_records(d1, d2)
        return recs < cls.max_people and (datetime.now() - timedelta(minutes=20) <= d1)

    async def _draw_records(self, ax, begin_time: time, time_range: typing.Tuple[time, time]):

        records_in_tr = await self.get_records_in_range(time_range)
        frees_slots = self.max_people - len(records_in_tr)

        begin = await tf.diff_in_minutes(time_range[0], begin_time)
        end = await tf.diff_in_minutes(time_range[1], begin_time)

        xlen = ax.get_xlim()[1] - ax.get_xlim()[0]
        xdist_from_edge = 1
        alpha = 1
        height = (end - begin) // (self.max_people + 1)
        p_free_slots = FancyBboxPatch((0, begin), xlen, height,
                                  zorder=2, fc='#FFFFFF', alpha=alpha, ec='#429BDB', lw=1.5)
        ax.add_patch(p_free_slots)

        tr_s = [t.isoformat(timespec='minutes') for t in time_range]
        tr_s = tr_s[0] + '-' + tr_s[1]
        ax.text(xlen / 2., begin + (height) / 2., f'{tr_s} Свободных мест: {frees_slots}',
                ha='center', va='center', fontsize='14', zorder=2, fontweight='bold')

        for i, record in enumerate(records_in_tr):
            ax.text(xdist_from_edge, begin + (i + 1 + 1 / 2) * height,
                    f'{i + 1}) {record.name}',
                    ha='left', va='center', fontsize='12', fontweight='bold')

    async def _draw_column(self, ax, is_working: bool = True):
        tr = await self.time_ranges_for_day(self.day)
        minutes_in_day = await tf.diff_in_minutes(tr[0][0], tr[-1][-1]) if tr else 120

        ax.set(ylim=(minutes_in_day, 0), xlim=(0, minutes_in_day), xticks=[], yticks=[])

        color = '#FFFFFF'
        p = FancyBboxPatch((0, 0), minutes_in_day, minutes_in_day, color=color)
        ax.add_patch(p)

    async def create_pic(self) -> str:
        """Creates schedule as png file for given day
        washers: tuple containing 1 (works) and 0 (broken)"""
        column_width = 4
        column_height = 7.5

        await self._set_font()
        fig, ax = plt.subplots(figsize=[column_width, column_height])
        fig.suptitle(tf.day_repr2(self.day), fontsize=20, fontweight='bold')

        day_time_ranges = await self.time_ranges_for_day(self.day)

        if not day_time_ranges:
            return ''

        await self._draw_column(ax)

        begin_time = day_time_ranges[0][0]
        for time_range in day_time_ranges:
            await self._draw_records(ax, begin_time, time_range)

        for spine in ax.spines.values():
            spine.set_edgecolor('#429BDB')
            spine.set_linewidth(1.5)

        fname = f'/app/tgbot/utils/schedule_pictures/gym-{self.day.isoformat()}.png'
        plt.savefig(fname)
        return fname


async def schedule_from_dict(service: str,
                             dict_schedule: dict,
                             ) -> BaseSchedule:
    if service == 'wash':
        return WashSchedule.from_dict(dict_schedule)
    elif service == 'gym':
        return GymSchedule.from_dict(dict_schedule)


async def get_schedule(db: Database,
                       day: date,
                       service: str) -> BaseSchedule:
    schedule = None
    if service == 'wash':
        recs = await db.get_wash_records(day)
        records = [Record(r[0], r[1], r[3], (await db.get_user(r[2]))['fullname']) for r in recs]
        schedule = WashSchedule(day, records)
    elif service == 'gym':
        recs = await db.get_gym_records(day)
        records = [Record(r[0], r[1], name=(await db.get_user(r[2]))['fullname']) for r in recs]
        schedule = GymSchedule(day, records)
    elif service == 'meet':
        recs = await db.get_meet_records(day)
        records = [Record(r[0], r[1], name=(await db.get_user(r[2]))['fullname']) for r in recs]
        schedule = MeetSchedule(day, records)
    return schedule


async def update_photo_link(db: Database, service, day: date):
    schedule = await get_schedule(db, day, service)
    path = await schedule.create_pic()
    link = await photo_link(path)
    await db.update_link(service, link, day)
