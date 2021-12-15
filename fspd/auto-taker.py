"""
Description:
    Paradigm FSPD Automated Market Taker.

    Written December 2021.

    Functionality:
    - Submits MARKET orders for each Strategy
    at the specified magnitude and cadence.

    High Level Workflow:
    - Pulls all available Strategies.
    - Creates Order submission payloads.
    - Submits Order payloads.

Usage:
    python3 auto-taker.py

Environment Variables:
    PARADIGM_ENVIRONMENT - Paradigm Operating Environment. 'TEST'.
    LOGGING_LEVEL - Logging Level. 'INFO'.
    PARADIGM_TAKER_ACCOUNT_NAME - Paradigm Venue API Key Name.
    PARADIGM_TAKER_ACCESS_KEY - Paradgim Taker Access Key.
    PARADIGM_TAKER_SECRET_KEY - Paradigm Taker Secret Key.
    ORDER_NUMBER_PER_STRATEGY - Number of Orders to maintain per side of each Strategy.
    ORDER_SUBMISSION_LOWER_BOUNDARY - Lower Time boundary in seconds to delay between Orders submission.
    ORDER_SUBMISSION_HIGHER_BOUNDARY - Upper Time boundary in seconds to delay between Orders submission.

Requirements:
    pip3 install aiohttp
"""

# built ins
import asyncio
import json
import os
import logging
import base64
import hmac
import time
from random import uniform
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum, auto

# installed
import aiohttp


class TradeAction(Enum):
    BUY = auto()
    SELL = auto()


class OrderType(Enum):
    LIMIT = auto()
    MARKET = auto()


@dataclass
class Strategy:
    id: str
    min_block_size: int

    def __init__(
        self,
        id: str,
        min_block_size: int
            ) -> None:
        self.id: str = id
        self.min_block_size: int = min_block_size


class Order:
    def __init__(
        self,
        id: str,
        side: TradeAction,
        amount: int,
        account_name: str,
        type: OrderType = OrderType.MARKET.name,
        price: str = None
            ) -> None:
        self.id: str = id
        self.side: TradeAction = side
        self.amount: int = amount
        self.account_name: str = account_name
        self.type: OrderType = type
        self.price: str = price

    @property
    def order_payload(self):
        _order_payload: Dict = {
                                'account_name': self.account_name,
                                'strategy_id': self.id,
                                'type': self.type,
                                'amount': self.amount,
                                'side': self.side
                                }
        if self.price:
            _order_payload['price'] = self.price

        return _order_payload


class AutoTaker():
    def __init__(
        self,
        paradigm_http_url: str,
        paradigm_taker_account_name: str,
        paradigm_taker_access_key: str,
        paradigm_taker_secret_key: str,
        order_number_per_strategy: str,
        order_submission_lower_boundary: str,
        order_submission_higher_boundary: str
            ) -> None:
        # Instance Variables
        self.paradigm_http_url: str = paradigm_http_url
        self.paradigm_taker_account_name: str = paradigm_taker_account_name
        self.paradigm_taker_access_key: str = paradigm_taker_access_key
        self.paradigm_taker_secret_key: str = paradigm_taker_secret_key
        self.order_number_per_strategy: int = int(order_number_per_strategy)
        self.order_submission_lower_boundary: int = int(order_submission_lower_boundary)
        self.order_submission_higher_boundary: int = int(order_submission_higher_boundary)

        # Async Event Loop
        self.loop = asyncio.get_event_loop()

        # Initialize Instrument Ingestion
        self.loop.run_until_complete(
            self.manager()
            )

    async def manager(self):
        """
        Primary management coroutine.
        """
        # Pull all available Strategies
        self.availabile_strateies: List[Strategy] = await self.ingest_available_strategies()

        # Construct Order Payloads
        self.order_payloads: List[Order] = await self.construct_order_payloads()

        while True:
            submitted_orders: List[asyncio.Task] = []

            for order in self.order_payloads:
                submitted_order: asyncio.Task = self.loop.create_task(
                    self.post_order(
                        order_payload=order.order_payload
                    )
                    )
                submitted_orders.append(submitted_order)

            await asyncio.gather(*submitted_orders)

            await asyncio.sleep(
                uniform(
                    self.order_submission_lower_boundary,
                    self.order_submission_higher_boundary
                )
                )

    async def construct_order_payloads(self) -> List[Order]:
        """
        Creates all Order Payloads from available strategies.
        """
        order_payloads: List[Order] = []

        for strategy in self.availabile_strateies:
            for side in [*TradeAction]:
                order: Order = Order(
                    id=strategy.id,
                    side=side.name,
                    amount=strategy.min_block_size,
                    account_name=self.paradigm_taker_account_name
                    )
                order_payloads.append(order)
        return order_payloads

    async def ingest_available_strategies(self) -> List[Strategy]:
        """
        - Pulls all available Strategies from Paradigm
        - Ingests key attributes of each.
        """
        available_strategies: List[Strategy] = []

        response: Dict = await self.get_strategies()

        for strategy in response['results']:
            _strategy: Strategy = Strategy(
                id=strategy['id'],
                min_block_size=strategy['min_block_size']
                )
            available_strategies.append(_strategy)

        return available_strategies

    async def post_order(
        self,
        order_payload: Dict
            ) -> None:
        """
        Paradigm RESToverHTTP endpoint.
        [POST] /orders
        """
        method: str = 'POST'
        path: str = '/v1/fs/orders'

        _payload: str = json.dumps(order_payload)

        headers: Dict = await self.create_rest_headers(
            method=method,
            path=path,
            body=_payload
            )

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    paradigm_http_url+path,
                    headers=headers,
                    json=order_payload
                        ) as response:
                    status_code: int = response.status
                    response: Dict = await response.json(content_type=None)
                    if status_code == 201:
                        logging.info(f'Order Create {status_code} | Response: {response}')
                    else:
                        logging.info('Unable to [POST] /orders')
                        logging.info(f'Status Code: {status_code}')
                        logging.info(f'Response Text: {response}')
                        logging.info(f'Order Payload: {order_payload}')
            except aiohttp.ClientConnectorError as e:
                logging.info(f'[POST] /orders ClientConnectorError: {e}')

    async def get_strategies(self) -> Dict:
        """
        Paradigm RESToverHTTP endpoint.
        [GET] /strategies
        """
        method: str = 'GET'
        path: str = '/v1/fs/strategies?page_size=100'
        payload: str = ''

        headers: Dict = await self.create_rest_headers(
            method=method,
            path=path,
            body=payload
            )

        async with aiohttp.ClientSession() as session:
            async with session.get(
                paradigm_http_url+path,
                headers=headers
                    ) as response:
                status_code: int = response.status
                if status_code == 200:
                    response: Dict = await response.json()
                else:
                    message: str = 'Unable to [GET] /strategies'
                    logging.error(message)
                    logging.error(f'Status Code: {status_code}')
                    logging.error(f'Response Text: {response}')
        return response

    async def sign_request(
        self,
        paradigm_secret_key: str,
        method: str,
        path: str,
        body: Dict
            ) -> Tuple[int, bytes]:
        """
        Creates the required signature neccessary
        as apart of all RESToverHTTP requests with Paradigm.
        """
        _secret_key: bytes = paradigm_secret_key.encode('utf-8')
        _method: bytes = method.encode('utf-8')
        _path: bytes = path.encode('utf-8')
        _body: bytes = body.encode('utf-8')
        signing_key: bytes = base64.b64decode(_secret_key)
        timestamp: str = str(int(time.time() * 1000)).encode('utf-8')
        message: bytes = b'\n'.join([timestamp, _method.upper(), _path, _body])
        digest: hmac.digest = hmac.digest(signing_key, message, 'sha256')
        signature: bytes = base64.b64encode(digest)

        return timestamp, signature

    async def create_rest_headers(
        self,
        method: str,
        path: str,
        body: Dict
            ) -> Dict:
        """
        Creates the required headers to authenticate
        Paradigm RESToverHTTP requests.
        """
        timestamp, signature = await self.sign_request(
            paradigm_secret_key=self.paradigm_taker_secret_key,
            method=method,
            path=path,
            body=body
            )

        headers: Dict = {
            'Paradigm-API-Timestamp': timestamp.decode('utf-8'),
            'Paradigm-API-Signature': signature.decode('utf-8'),
            'Authorization': f'Bearer {self.paradigm_taker_access_key}'
            }

        return headers


if __name__ == "__main__":
    # Local Testing
    os.environ['LOGGING_LEVEL'] = 'INFO'
    os.environ['PARADIGM_TAKER_ACCOUNT_NAME'] = '<venue-api-key-name-on-paradigm>'
    os.environ['PARADIGM_TAKER_ACCESS_KEY'] = '<access-key>'
    os.environ['PARADIGM_TAKER_SECRET_KEY'] = '<secret-key>'

    os.environ['ORDER_NUMBER_PER_STRATEGY'] = "1"
    os.environ['ORDER_SUBMISSION_LOWER_BOUNDARY'] = "1"
    os.environ['ORDER_SUBMISSION_HIGHER_BOUNDARY'] = "1"

    # Paradigm Connection URLs
    paradigm_environment = os.getenv('PARADIGM_ENVIRONMENT', 'TEST')
    paradigm_http_url: str = f'https://api.fs.{paradigm_environment.lower()}.paradigm.co'

    # Logging
    logging.basicConfig(
        level=os.environ['LOGGING_LEVEL'],
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
        )

    main: AutoTaker = AutoTaker(
        paradigm_http_url=paradigm_http_url,
        paradigm_taker_account_name=os.environ['PARADIGM_TAKER_ACCOUNT_NAME'],
        paradigm_taker_access_key=os.environ['PARADIGM_TAKER_ACCESS_KEY'],
        paradigm_taker_secret_key=os.environ['PARADIGM_TAKER_SECRET_KEY'],
        order_number_per_strategy=os.environ['ORDER_NUMBER_PER_STRATEGY'],
        order_submission_lower_boundary=os.environ['ORDER_SUBMISSION_LOWER_BOUNDARY'],
        order_submission_higher_boundary=os.environ['ORDER_SUBMISSION_HIGHER_BOUNDARY']
        )
