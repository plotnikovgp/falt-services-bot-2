import typing
from typing import Optional, Union
from datetime import datetime, date, timedelta
import asyncio
import asyncpg


# TODO remove code repetitions
class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.pool.Pool] = None

    async def create_pool(self,
                          host: Union[str, int],
                          db_name: str,
                          user: str,
                          password: str):
        # host  - localhost, port - 5432
        self.pool = await asyncpg.create_pool(
            host=host,
            database=db_name,
            user=user,
            password=password,
        )

    async def execute_cmd(self, sql_cmd: str, *args):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                return await connection.execute(sql_cmd, *args)

    async def fetchval(self, sql_cmd: str, *args, column: int = 0):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                return await connection.fetchval(sql_cmd, *args, column=column)

    async def fetch(self, sql_cmd: str, *args):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                return await connection.fetch(sql_cmd, *args)

    async def fetchrow(self, sql_cmd: str, *args):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                return await connection.fetchrow(sql_cmd, *args)

    async def create_tables(self):
        tables_sql = """
        CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        username VARCHAR(32),
        tg_id BIGINT NOT NULL UNIQUE,
        balance REAL NOT NULL,
        passcode VARCHAR(7),
        fullname VARCHAR(128),
        email VARCHAR(128),
        is_registered BOOLEAN DEFAULT FALSE
        );
        
        CREATE TABLE IF NOT EXISTS wash_records( 
        id SERIAL PRIMARY KEY,
        begin TIMESTAMP NOT NULL,
        finish TIMESTAMP NOT NULL,
        washer INT NOT NULL,
        user_tg_id BIGINT NOT NULL REFERENCES Users(tg_id)
        );
        
        CREATE TABLE IF NOT EXISTS gym_records(
        id SERIAL PRIMARY KEY,
        begin TIMESTAMP NOT NULL,
        finish TIMESTAMP NOT NULL,
        user_tg_id BIGINT NOT NULL REFERENCES Users(tg_id)
        );
        
        CREATE TABLE IF NOT EXISTS meet_records(
        id SERIAL PRIMARY KEY,
        begin TIMESTAMP NOT NULL,
        finish TIMESTAMP NOT NULL,
        user_tg_id BIGINT NOT NULL REFERENCES Users(tg_id),
        is_approved BOOLEAN DEFAULT FALSE
        );
        
        CREATE TABLE IF NOT EXISTS wash_photo_links(
        id SERIAL PRIMARY KEY,
        link VARCHAR(400) NOT NULL,
        day DATE UNIQUE
        );
         
        CREATE TABLE IF NOT EXISTS gym_photo_links(
        id SERIAL PRIMARY KEY,
        link VARCHAR(400) NOT NULL,
        day DATE UNIQUE
        );
        
        CREATE TABLE IF NOT EXISTS meet_photo_links(
        id SERIAL PRIMARY KEY,
        link VARCHAR(400) NOT NULL,
        day DATE UNIQUE
        );
        
        CREATE TABLE IF NOT EXISTS working_passcodes(
        id SERIAL PRIMARY KEY,
        passcode VARCHAR(7) NOT NULL DEFAULT '0007573',
        day DATE
        );
        """

        return await self.execute_cmd(tables_sql)

    # users
    async def add_user(self, username: str,
                       tg_id: int,
                       passcode: str,
                       balance: int = 0,
                       fullname: Optional[str] = None,
                       email: Optional[str] = None
                       ) -> str:
        return await self.execute_cmd(
            "INSERT INTO users (username, passcode, tg_id, balance, fullname, email) "
            "VALUES ($1, $2, $3, $4, $5, $6)",
            username, passcode, tg_id, balance, fullname, email)

    async def get_user(self, tg_id: int) -> dict:
        sql = "SELECT * FROM users WHERE tg_id = ($1)"

        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(sql, tg_id)
            return dict(row) if row else {}

    async def get_user_by_username(self, username: str) -> dict:
        sql = "SELECT * FROM users WHERE username = ($1)"

        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(sql, username)
            return dict(row) if row else {}

    async def users_count(self) -> int:
        async with self.pool.acquire() as connection:
            r = await connection.fetchrow('SELECT COUNT(*)  FROM users')
            return r.get('count')

    async def get_users_with_balance(self):
        async with self.pool.acquire() as connection:
            rs = await connection.fetch('SELECT (tg_id, username, balance)  FROM users WHERE balance > 0')
            return rs

    async def change_balance(self, tg_id: int, diff: float) -> bool:
        """
        :param tg_id: tg id of who is committing a payment
        :param diff: in RUB, <0 to reduce balance, >0 to top up balance
        :return: True if given user has balance + diff >= 0, False otherwise
        """
        tg_id = int(tg_id)
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                balance = await connection.fetchval(
                    "SELECT balance FROM users WHERE tg_id = ($1)", tg_id) or 0

                if balance + diff < 0:
                    return False

                balance += diff
                await connection.execute(
                    "UPDATE users SET balance =$1 WHERE tg_id =$2", balance, tg_id)
                return True

    async def change_passcode(self, tg_id: int, passcode: str):
        await self.execute_cmd("UPDATE users SET passcode =$1 WHERE tg_id =$2", passcode, tg_id)

    async def change_fullname(self, tg_id: int, fullname: str):
        await self.execute_cmd("UPDATE users SET fullname =$1 WHERE tg_id =$2", fullname, tg_id)

    async def register_user(self, tg_id: int):
        await self.execute_cmd("UPDATE users SET is_registered = TRUE WHERE tg_id =$1", tg_id)

    # gym/wash/meet records
    async def add_wash_record(self, begin: datetime, end: datetime, washer: int, user_tg_id: int):
        return await self.fetchval(
            "INSERT INTO wash_records (begin, finish, washer, user_tg_id) VALUES ($1, $2, $3, $4) RETURNING id",
            begin, end, washer, user_tg_id)

    async def add_gym_record(self, begin: datetime, end: datetime, user_tg_id: int):
        return await self.fetchval(
            "INSERT INTO gym_records (begin, finish, user_tg_id) VALUES ($1, $2, $3) RETURNING id",
            begin, end, user_tg_id)

    async def add_meet_record(self, begin: datetime, end: datetime, user_tg_id: int):
        return await self.fetchval(
            "INSERT INTO meet_records (begin, finish, user_tg_id) VALUES ($1, $2, $3) RETURNING id",
            begin, end, user_tg_id)

    async def approve_meet_record(self, record_id: int):
        await self.execute_cmd("UPDATE meet_records SET is_approved = TRUE WHERE id =$1", record_id)

    async def count_gym_records(self, begin: datetime, end: datetime):
        return await self.fetchval(
            "SELECT COUNT(*) FROM gym_records WHERE begin >= $1 AND finish <= $2",
            begin, end)

    async def count_wash_records(self, begin: datetime, end: datetime, washer: int):
        return await self.fetchval(
            "SELECT COUNT(*) FROM wash_records WHERE ((begin >= $1 AND begin < $2) OR (finish > $1 AND finish <= $2)"
            " OR (begin <= $1 AND finish >= $2)) AND washer = $3", begin, end, washer)

    async def count_meet_records(self, begin: datetime, end: datetime):
        return await self.fetchval(
            "SELECT COUNT(*) FROM meet_records WHERE ((begin >= $1 AND begin < $2 OR finish > $1 AND finish <= $2)"
            " AND (is_approved = TRUE))",
            begin, end)

    async def get_wash_records(self, day: date):
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)

        records = await self.fetch(
            "SELECT (begin, finish, user_tg_id, washer) FROM wash_records WHERE begin >= $1 AND finish <= $2",
            day_start, day_end)
        return [r['row'] for r in records]

    async def get_gym_records(self, day: date):
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)

        records = await self.fetch(
            "SELECT (begin, finish, user_tg_id) FROM gym_records WHERE begin >= $1 AND finish <= $2",
            day_start, day_end)
        return [r['row'] for r in records]

    async def get_meet_records(self, day: date):
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)

        records = await self.fetch(
            "SELECT (begin, finish, user_tg_id) FROM meet_records WHERE begin >= $1 AND finish <= $2 "
            "AND is_approved = TRUE", day_start, day_end)
        return [r['row'] for r in records]

    async def get_user_wash_records(self,
                                    user_tg_id: int,
                                    start: typing.Optional[datetime] = None,
                                    end: typing.Optional[datetime] = None,
                                    ):
        start = start or datetime.now() - timedelta(hours=2)
        end = end or datetime.now() + timedelta(weeks=30)
        records = await self.fetch(
            "SELECT (id, begin, finish, washer) FROM wash_records WHERE begin >= $1 AND finish <= $2"
            " AND user_tg_id = $3", start, end, user_tg_id)
        return [r['row'] for r in records]

    async def get_user_gym_records(self,
                                   user_tg_id: int,
                                   start: typing.Optional[datetime] = None,
                                   end: typing.Optional[datetime] = None,
                                   ):
        start = start or datetime.now() - timedelta(hours=2)
        end = end or datetime.now() + timedelta(weeks=30)
        records = await self.fetch(
            "SELECT (id, begin, finish) FROM gym_records WHERE begin >= $1 AND finish <= $2"
            " AND user_tg_id = $3", start, end, user_tg_id)
        return [r['row'] for r in records]

    async def get_user_meet_records(self,
                                    user_tg_id: int,
                                    start: typing.Optional[datetime] = None,
                                    end: typing.Optional[datetime] = None,
                                    ):
        start = start or datetime.now() - timedelta(hours=2)
        end = end or datetime.now() + timedelta(weeks=30)
        records = await self.fetch(
            "SELECT (id, begin, finish, is_approved) FROM meet_records WHERE begin >= $1 AND finish <= $2"
            " AND user_tg_id = $3", start, end, user_tg_id)
        return [r['row'] for r in records]

    async def get_wash_record_id(self, record_id: typing.Union[str, int]):
        record = await self.fetchrow(
            "SELECT (begin, finish, washer, user_tg_id) FROM wash_records WHERE id = $1", record_id)
        return record['row'] if record else None

    async def get_gym_record_id(self, record_id: typing.Union[str, int]):
        record = await self.fetchrow(
            "SELECT (begin, finish, user_tg_id) FROM gym_records WHERE id = $1", record_id)
        return record['row'] if record else None

    async def get_meet_record_id(self, record_id: typing.Union[str, int]):
        record = await self.fetchrow(
            "SELECT (begin, finish, user_tg_id, is_approved) FROM meet_records WHERE id = $1", record_id)
        return record['row'] if record else None

    async def delete_wash_record(self, record_id: int):
        return await self.execute_cmd('DELETE FROM wash_records WHERE id = $1', record_id)

    async def delete_gym_record(self, record_id: int):
        return await self.execute_cmd('DELETE FROM gym_records WHERE id = $1', record_id)

    async def delete_meet_record(self, record_id: int):
        return await self.execute_cmd('DELETE FROM meet_records WHERE id = $1', record_id)

    # link
    async def update_link(self, service: str, link: str, day: date):
        tablename = service + "_photo_links"
        cmd = "INSERT INTO " + tablename + " (link, day) VALUES ($1, $2) " \
                                           "ON CONFLICT (day) DO UPDATE SET link = $1"
        await self.execute_cmd(cmd, link, day)

    async def delete_link(self, service: str, day: date):
        tablename = service + "_photo_links"
        cmd = "DELETE FROM " + tablename + " WHERE day = $1"
        await self.execute_cmd(cmd, day)

    async def get_link(self, service: str, day: date):
        tablename = service + "_photo_links"
        cmd = "SELECT link FROM " + tablename + " WHERE day = $1"
        res = await self.fetchrow(cmd, day)
        return res.get('link') if res else None

    # passcode, will be removed soon
    async def update_passcode(self, passcode: str, day: typing.Optional[date] = None):
        day = day or date.today()
        cmd = "INSERT INTO working_passcodes (passcode, day) VALUES ($1, $2)"
        await self.execute_cmd(cmd, passcode, day)

    async def get_passcode(self, day: date = date.today()) -> str:
        res = await self.fetchrow("SELECT passcode FROM working_passcodes WHERE day = $1", day)
        return res.get('passcode') if res else None
