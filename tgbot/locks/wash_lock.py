# from datetime import datetime
# import aiohttp
# import hmac
# import hashlib
# from urllib.parse import urlencode, parse_qs
# import requests
# from Crypto.Cipher import AES
# from binascii import hexlify, unhexlify
# import json
# import time
# from tgbot.bot import logger

from uuid import uuid4


async def create_passcode() -> str:
    passcode = '000' + str(uuid4().int)[:4]
    return passcode
#
#
# class SmartLock:
#     def __init__(self,
#                  device_id: str,
#                  client_id: str,
#                  client_secret: str,
#                  base_url: str = 'https://openapi-weaz.tuyaeu.com'):
#         self.device_id = device_id
#         self.client_id = client_id
#         self.client_secret = client_secret
#         self.base_url = base_url
#         self.token = ''
#         self.token_expire_time = 0
#         self.ticket_id = None
#         self.ticket_key = None
#
#     @staticmethod
#     async def _get_time() -> int:
#         return int(datetime.now().timestamp() * 1000)
#
#     @staticmethod
#     async def _hash_string(s: str) -> str:
#         return hashlib.sha256(s.encode('utf-8')).hexdigest().lower()
#
#     async def get_token(self):
#         t = str(await self._get_time())
#         if self.token and ((int(t) - 10) < self.token_expire_time):
#             return self.token
#         method = 'GET'
#         content_hash = await self._hash_string('')
#         sign_url = '/v1.0/token?grant_type=1'
#         string_to_sign = '\n'.join([method, content_hash, '', sign_url])
#         sign_str = self.client_id + t + string_to_sign
#         sign = hmac.new(key=bytes(self.client_secret, 'utf-8'),
#                         msg=bytes(sign_str, 'utf-8'),
#                         digestmod=hashlib.sha256).hexdigest().upper()
#         headers = {
#             't': t,
#             'sign_method': 'HMAC-SHA256',
#             'client_id': self.client_id,
#             'sign': sign,
#         }
#         url = self.base_url + sign_url
#         async with aiohttp.ClientSession() as session:
#             async with session.get(url, headers=headers) as response:
#                 if not response.ok:
#                     print(f'Error while getting token: {response.text()}')
#                     return None
#                 res = await response.json()
#                 print(res)
#                 self.token = res.get('result').get('access_token')
#                 return self.token
#
#     async def get_request_sign(self,
#                                path: str,
#                                method: str,
#                                params: dict = None,
#                                body_str: str = '',
#                                ):
#         if '?' in path:
#             [uri, path_query] = path.split('?')
#             query_merged = {**path_query, **params}
#         else:
#             uri = path
#             query_merged = params
#
#         if query_merged:
#             query_merged = dict(sorted(query_merged.items()))
#             query_merged_str = urlencode(query_merged)
#             url = f'{uri}?{query_merged_str}'
#         else:
#             url = uri
#
#         content_hash = await self._hash_string(body_str)
#
#         string_to_sign = '\n'.join([method, content_hash, '', url])
#         await self.get_token()
#
#         t = str(await self._get_time())
#         sign_str = self.client_id + self.token + t + string_to_sign
#         sign = hmac.new(key=self.client_secret.encode('utf-8'),
#                         msg=sign_str.encode('utf-8'),
#                         digestmod=hashlib.sha256).hexdigest().upper()
#
#         return {
#             't': t,
#             'path': url,
#             'client_id': self.client_id,
#             'sign_method': 'HMAC-SHA256',
#             'sign': sign,
#             'access_token': self.token
#         }
#
#     async def get_key_for_password_encryption(self):
#         method = 'POST'
#         url = f'/v1.0/devices/{self.device_id}/door-lock/password-ticket'
#         req_headers = await self.get_request_sign(url, method)
#         url = self.base_url + req_headers['path']
#
#         async with aiohttp.ClientSession() as session:
#             async with session.post(url, headers=req_headers) as response:
#                 resp = await response.json()
#                 if not resp['success']:
#                     print(f'Error while getting key: {resp}')
#                     return None
#                 self.ticket_key = resp['result']['ticket_key']
#                 self.ticket_id = resp['result']['ticket_id']
#                 print(resp)
#
#     @staticmethod
#     async def _pad(text, block_size):
#         """
#         Performs padding on the given plaintext to ensure that it is a multiple
#         of the given block_size value in the parameter. Uses the PKCS7 standard
#         for performing padding.
#         """
#         no_of_blocks = int(len(text) / float(block_size)) + 1
#         pad_value = int(no_of_blocks * block_size - len(text))
#
#         if pad_value == 0:
#             return text + chr(block_size) * block_size
#         else:
#             return text + chr(pad_value) * pad_value
#
#     async def encrypt_passcode(self, passcode: str):
#         cipher = AES.new(unhexlify(self.client_secret), AES.MODE_ECB)
#         key = cipher.decrypt(unhexlify(self.ticket_key))
#
#         cipher = AES.new(key, AES.MODE_ECB)
#         passcode_pad = await self._pad(passcode, cipher.block_size)
#         password = cipher.encrypt(bytes(passcode_pad, 'utf-8'))
#
#         return password.hex().upper()
#
#     async def add_password(self,
#                            passcode: str,
#                            name: str,
#                            start: datetime,
#                            end: datetime
#                            ):
#         start = int(start.timestamp())
#         end = int(end.timestamp())
#         await self.get_key_for_password_encryption()
#         password = await self.encrypt_passcode(passcode)
#
#         body = {
#             "password": password,
#             #"password_type": "ticket",
#             "ticket_id": self.ticket_id,
#             "effective_time": start,
#             "invalid_time": end,
#             #"type": 0,
#             "name": name,
#         }
#         body2 = {
#             'nick_name': 'bogdan',
#             'sex': 1,
#         }
#         url = f'/v1.0/devices/{self.device_id}/door-lock/temp-password'
#         # url = f'/v1.0/devices/{self.device_id}/door-lock/offline-temp-password'
#         # url = f'/v1.0/devices/{self.device_id}/door-lock/password-free/open-door'
#         body_str = json.dumps(body, separators=(',', ':'))
#         req_headers = await self.get_request_sign(path=url, method='POST', body_str=body_str)
#
#         url = self.base_url + req_headers['path']
#         async with aiohttp.ClientSession() as session:
#             async with session.post(url, headers=req_headers, data=body_str) as response:
#                 resp = await response.json()
#                 if not resp['success']:
#                     print(f'Error while sending password: {resp}')
#                     return None
#                 print(resp)
#
#     @staticmethod
#     async def create_passcode() -> str:
#         passcode = '000' + str(uuid4().int)[:4]
#         return passcode
#
