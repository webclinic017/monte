import gzip
import json
import os
import pathlib
from datetime import date, datetime
from typing import Type, TypeVar

import asks
import pandas as pd
import trio
from alpaca_trade_api import REST, TimeFrame

#############
# CONSTANTS #
#############

REPO_NAME = "monte"
MARKET_DATA_BASE_URL = "https://data.alpaca.markets"
CRYPTO_BASE_URL = "https://data.alpaca.markets/v1beta1/crypto"


##############
# ALPACA API #
##############

class AsyncAlpacaBars():
    """
    A custom Alpaca API client that supports asynchronous requests for getting historical market data bars.
    """

    headers: dict[str, str]
    base_url: str

    # TODO: Rewrite this to use asyncio and aiohttp when Python 3.11 comes out with the new asyncio.TaskGroup
    # class
    # TODO: Move to using the newer Alpaca API (alpaca-py)

    def __init__(self, key_id: str, secret_id: str, base_url: str) -> None:
        # HTTPS header, this contains the API key info to authenticate with Alpaca
        self.headers = {
            "APCA-API-KEY-ID": key_id,
            "APCA-API-SECRET-KEY": secret_id
        }

        # The base url is something like "https://data.alpaca.markets"
        self.base_url = base_url

    async def get_bars(self, symbol: str, time_frame: TimeFrame, start_date: datetime, end_date: datetime,
                       output_dict: dict[str, pd.DataFrame], adjustment: str = 'all', limit: int = 10000) -> None:
        """
        Asynchronously performs one requests for historical bars from the Alpaca API.
        """
        # Create an empty list to store all of the bars received from Alpaca
        list_of_bars = []

        # HTTPS GET request parameters
        params = {
            "adjustment": adjustment,
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "timeframe": str(time_frame),
            "limit": limit
        }

        # Alpaca does not let us request all the data at once, and instead forces us to request it in
        # "pages". This loop goes through all the pages until there is no more data to get.
        while True:

            # Get the data from Alpaca asynchronously
            response = await asks.get(
                f"https://data.alpaca.markets/v2/stocks/{symbol}/bars",
                headers=self.headers,
                params=params,
                follow_redirects=False
            )

            # Response code 200 means success. If the data was received successfully, load it as a dictionary
            if response.status_code == 200:
                try:
                    body_dict = json.loads(str(gzip.decompress(response.body), 'utf-8'))
                except gzip.BadGzipFile:
                    raise ValueError(
                        f"Alpaca does not have any data for {symbol} between {start_date} and {end_date}")

            # Response code 500 means "internal error", retry with the same parameters
            elif response.status_code == 500:
                continue

            elif response.status_code == 400 and len(list_of_bars) >= limit:
                raise OverflowError(
                    "Hit the limit of 10,000 rows in a single request from alpaca. To get around this, "
                    "consider making your data buffer size smaller. This will break up the request into "
                    "smaller requests.")

            # Something went wrong and we can't recover. Raise an error.
            else:
                raise ConnectionError(
                    f"Bad response from Alpaca with response code: {response.status_code}")

            # Add the bars from the latest Alpaca request to the list of all the bars
            list_of_bars.extend(body_dict['bars'])

            # Extract the token ID for the next data 'page' from the parsed body of the HTTPS response.
            next_page_token = body_dict['next_page_token']

            # If there is a next_page_token, add it as an HTTPS parameter for the next request.
            if next_page_token:
                params['next_page_token'] = next_page_token

            # Else, there is no more data to request.
            else:
                break

        # Put the data into a dataframe
        df = pd.DataFrame(list_of_bars)

        # Add the dataframe to the output_dict
        output_dict[symbol] = df

    def get_bulk_bars(self, symbols: list[str], time_frame: TimeFrame, start_date: date, end_date: date,
                      adjustment: str = 'all', limit: int = 10000) -> dict[str, pd.DataFrame]:
        """
        Gets bar data for all of the ``symbols`` using the provided arguments such as``time_frame`` and
        ``start_date``.
        """
        output_dict = {}

        trio.run(
            self._async_get_bulk_bars,
            symbols,
            time_frame,
            start_date,
            end_date,
            output_dict,
            adjustment,
            limit)

        return output_dict

    async def _async_get_bulk_bars(self, symbols: list[str], time_frame: TimeFrame, start_date: datetime,
                                   end_date: datetime, output_dict: dict[str, pd.DataFrame],
                                   adjustment: str = 'all', limit: int = 10000) -> None:
        """
        High-level coroutine that manages getting bar data for all symbols provided. Spawns one coroutine
        per symbol.
        """
        async with trio.open_nursery() as n:
            for symbol in symbols:
                n.start_soon(
                    self.get_bars,
                    symbol,
                    time_frame,
                    start_date,
                    end_date,
                    output_dict,
                    adjustment,
                    limit)


class AlpacaAPIBundle():
    """
    A group of Alpaca APIs that are all instantiated with the API key(s) provided in the repo's
    alpaca_config.json
    """

    _trading_instances: list[REST]
    _market_data_instances: list[REST]
    _crypto_instances: list[REST]
    _async_market_data_instances: list[AsyncAlpacaBars]
    T = TypeVar('T')

    def __init__(self) -> None:
        # Get the repo dir as a string
        repo_dir = self._get_repo_root_dir()

        with open(f"{repo_dir}{os.sep}alpaca_config.json", "r") as alpaca_config_file:
            try:
                self.alpaca_config = json.load(alpaca_config_file)
            except BaseException:
                raise RuntimeError("Failed to load alpaca_config.json")

        # Create an instance of each of alpaca API for each API key-pair
        self._trading_instances = self._create_api_instances(
            REST, self.alpaca_config["ENDPOINT"])
        self._market_data_instances = self._create_api_instances(
            REST, MARKET_DATA_BASE_URL)
        self._crypto_instances = self._create_api_instances(
            REST, CRYPTO_BASE_URL)
        self._async_market_data_instances = self._create_api_instances(
            AsyncAlpacaBars, MARKET_DATA_BASE_URL)

        # Store the number of API instances there are in every instance list. The number of API instances
        # is equivalent to the number of API key pairs
        self._num_api_instances = len(self.alpaca_config["API_KEYS"])

        # Create an index variable to track which instance within the API instance lists
        # should be used
        self._api_instance_index = 0

    @property
    def trading(self) -> REST:
        """
        Returns the least-recently used instance of the Alpaca Trading API.
        """
        # The least recently-used instance should be located at self._api_instance_index, since the instances
        # are stored in a circular queue. The next instance is always the least-recently used one.
        lru_instance = self._trading_instances[self._api_instance_index]
        self._api_instance_index += 1

        # Reset the api instance index if it's past the end of the list
        if self._api_instance_index >= self._num_api_instances:
            self._api_instance_index = 0

        return lru_instance

    @property
    def market_data(self) -> REST:
        """
        Returns the least-recently used instance of the Alpaca Market Data API.
        """
        # The least recently-used instance should be located at self._api_instance_index, since the instances
        # are stored in a circular queue. The next instance is always the least-recently used one.
        lru_instance = self._market_data_instances[self._api_instance_index]
        self._api_instance_index += 1

        # Reset the api instance index if it's past the end of the list
        if self._api_instance_index >= self._num_api_instances:
            self._api_instance_index = 0

        return lru_instance

    @property
    def crypto(self) -> REST:
        """
        Returns the least-recently used instance of the Alpaca Crypto API.
        """
        # The least recently-used instance should be located at self._api_instance_index, since the instances
        # are stored in a circular queue. The next instance is always the least-recently used one.
        lru_instance = self._crypto_instances[self._api_instance_index]
        self._api_instance_index += 1

        # Reset the api instance index if it's past the end of the lsit
        if self._api_instance_index >= self._num_api_instances:
            self._api_instance_index = 0

        return lru_instance

    @property
    def async_market_data_bars(self) -> AsyncAlpacaBars:
        """
        Returns the least-recently used instance of the custom asynchronous bars API.
        """
        # The least recently-used instance should be located at self._api_instance_index, since the instances
        # are stored in a circular queue. The next instance is always the least-recently used one.
        lru_instance = self._async_market_data_instances[self._api_instance_index]
        self._api_instance_index += 1

        # Reset the api instance index if it's past the end of the lsit
        if self._api_instance_index >= self._num_api_instances:
            self._api_instance_index = 0

        return lru_instance

    def _create_api_instances(self, api_class: Type[T], endpoint: str) -> list[T]:
        """
        Create a list of instances of ``api_class``, where each instance is authenticated using a different
        API key from the ones provided in the repo's alpaca_config.json
        """
        api_instance_list = []

        # For every loaded API key-secret key pair, create an instance of the REST API using the "endpoint"
        # argument.
        for api_key in self.alpaca_config["API_KEYS"]:
            api_instance = api_class(
                api_key["API_KEY_ID"],
                api_key["SECRET_KEY"],
                endpoint
            )

            api_instance_list.append(api_instance)

        return api_instance_list

    def _get_repo_root_dir(self) -> str:
        """
        Returns a string containing the path to the root directory of the repository.
        """
        current_file_path = pathlib.Path(__file__)

        while True:

            if (os.path.basename(current_file_path) == 'monte' and
                    os.path.basename(current_file_path.parent) == 'monte'):
                repo_dir = current_file_path.parent
                break

            else:
                current_file_path = current_file_path.parent

        return str(repo_dir)
