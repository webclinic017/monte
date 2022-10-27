from __future__ import annotations

from datetime import datetime

from alpaca_trade_api import TimeFrame, TimeFrameUnit

from algorithms import test
from monte.api import AlpacaAPIBundle
from monte.machine import TradingMachine
from monte.machine_settings import MachineSettings


def main():
    alpaca_api = AlpacaAPIBundle()

    ms = MachineSettings(
        start_date=datetime(2016, 3, 8),
        end_date=datetime(2022, 10, 23),
        training_data_percentage=0.1,
        time_frame=TimeFrame(1, TimeFrameUnit.Hour))

    trading_machine = TradingMachine(alpaca_api, ms)

    algo1 = test.TestAlg(alpaca_api, ms, "Test Alg", 10_000)

    trading_machine.add_algo_instance(algo1)

    trading_machine.run()

    breakpoint()


if __name__ == "__main__":
    main()