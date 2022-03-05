import typing
import aiohttp
import asyncio
from glQiwiApi import YooMoneyAPI


class PaySystem:
    def __init__(self, token: str):
        """
        :param token: token for working with Yoomoney API, Can be received from get_token function
        """
        self.token = token

    @classmethod
    async def get_token(cls, client_id: str, redirect_uri: str,) -> str:
        """
        :param client_id: ID received when registering the application here https://yoomoney.ru/myservices/new
        :param redirect_uri: the link specified during registration above in the Redirect URI field
        :returns token for working with Yoomoneу api
        """

        # generating link for authorization and receiving token
        url = await YooMoneyAPI.build_url_for_auth(
            scope=["account-info", "operation-history", "operation-details", "payment-p2p"],
            client_id=client_id,
            redirect_uri=redirect_uri)
        print(url)

        code = input('Введите код, полученный с этой ссылки: ')
        token = await YooMoneyAPI.get_access_token(
                    code=code,
                    client_id=client_id,
                    redirect_uri=redirect_uri)
        return token

    async def create_pay_url(self, sum: float, label: str, name: str='')->str:
        wallet_number = None
        async with YooMoneyAPI(self.token) as w:
            acc_info = await w.retrieve_account_info()
            wallet_number = acc_info.account
        # see https://yoomoney.ru/docs/payment-buttons/using-api/forms
        payment_params = {
            "receiver": wallet_number,
            "quickpay-form": "shop",
            "sum": sum,
            "paymentType": "",
            "label": label,
            # change this parameters for your case
            "targets": f"Сервисы ФАЛТ: пополнение баланса пользователя {name}",
            "formcomment": "Сервисы ФАЛТ: пополнение баланса",
            "short-dest": "Сервисы ФАЛТ: пополнение баланса",
            "successURL": "t.me/FaltServicesBot"
        }

        base_url = "https://yoomoney.ru/quickpay/confirm.xml?"

        async with aiohttp.ClientSession() as session:
            async with session.post(base_url, params=payment_params) as resp:
                return str(resp.url)

    async def is_payment_successful(self, label: typing.Union[str, int]):
        # returns: True if last deposition with such label on account was successful
        async with YooMoneyAPI(api_access_token=self.token) as w:
            transactions = (await w.transactions(label=label))
            return transactions[0].status == 'success' if transactions else False

