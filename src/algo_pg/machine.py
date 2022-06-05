"""
A trading machine is an object that encompasses the running of algorithms with portfolios
attached. These algorithm-portfolio pairs can be either run on historical data or on live data.
"""

from algo_pg.algorithms.base_algorithm import Algorithm
from algo_pg.portfolio import Portfolio
from algo_pg.util import get_list_of_trading_days_in_range
from alpaca_trade_api import TimeFrame
from dataclasses import dataclass


@dataclass
class MachineSettings():
    """
    Used to store all of the trading machine settings so this object can be passed around
    and settings can be synchronized.
    """
    # TODO:
    pass


@dataclass
class AlgoPortfolioPair():
    """
    A trading algorithm-portfolio pair is run together across a trading machine's timeline\
    as one unit.
    """
    algo: Algorithm
    portfolio: Portfolio


class TradingMachine():
    """
    The "trading machine" is meant to represent a machine running an algorithm with data \
    across the timeline that are provided as constructor arguments. This encompasses\
    backtesting (testing on historical data) as well as running an algorithm live.
    """

    def __init__(
            self, alpaca_api, start_date, end_date,
            time_frame=TimeFrame.Hour, stat_dict=None):
        """
        Constructor for the TradingMachine class.

        Args:
            alpaca_api: A bundle of Alpaca APIs all created and authenticated with the keys
                in the repo's alpaca.config.
            start_date: The YYYY-MM-DD formatted date for the trading machine to start its
                run at.
            end_date: The YYYY-MM-DD formatted date for the trading machine to end its
                run at.
            time_frame: An alpaca_trade_api.TimeFrame value corresponding to the time
                delta between price values. Defaults to TimeFrame.Minute.
            TODO: stat_dict
        """

        # TODO: Move this into the algo parent class.
        # time_frames_between_algo_runs: The number of TimeFrames that need to occur for
        # an algorithm's run function to be called once

        # TODO: kwarg for a time_delta for how far the historical data needs to go back

        # Bundled alpaca API dataclass
        self.alpaca_api = alpaca_api

        # Attributes to keep track of the time span of the trading_machine
        self.start_date = start_date
        self.end_date = end_date
        self.current_datetime = None
        self.stat_dict = stat_dict

        # The only supported time frames for this class are minutes, hours, and days.
        self.time_frame = time_frame

        # Generates a list of MarketDay instances in order from self.start_date to
        # self.end_date to represent all of the days the market is open, and *only*
        # the days the market is open.
        self.trading_days = get_list_of_trading_days_in_range(
            self.alpaca_api, self.start_date, self.end_date)

        # Pairs of algorithms and portfolios
        self.algo_portfolio_pairs = []

    def add_algo_portfolio_pair(self, algorithm, portfolio):
        """
        Adds an algorithm-portfolio pair to the list of all such pairs for the trading
        machine. This is useful because the run() function can iterate over these pairs and
        all of the provided algorithms against their corresponding portfolios.

        Args:
            algorithm: A TradingAlgorithm instance or instance of a sub-class.
            portfolio: A Portfolio instance.
        """
        # TODO: Add a check to make sure the algorithm and portfolio are set up correctly
        # before adding (type check)
        algo_portfolio_pair = AlgoPortfolioPair(algorithm, portfolio)
        self.algo_portfolio_pairs.append(algo_portfolio_pair)

    def _pre_run(self):
        """TODO:"""

        # If there is a stat dict, add it to every data manager in the whole machine
        if self.stat_dict is not None:
            for algo_portfolio_pair in self.algo_portfolio_pairs:
                portfolio = algo_portfolio_pair.portfolio

                for position in portfolio.positions:
                    # TODO: Maybe remove this when MachineSettings is working
                    position.data_manager.add_stat_dict(self.stat_dict)
                    position.data_manager.set_time_frame(self.stat_dict)

    def run(self):
        """
        Run the trading machine and run all of the algorithm portfolio pairs from the start
        date to the end date.
        """

        self._pre_run()

        # For every day that the market will be open
        for trading_day in self.trading_days:

            # Update the current date variable in the machine
            self.current_trading_date = trading_day.date

            # For every algo - portfolio pair, simulate an entire day no matter what the
            # time frame is.
            for algo_portfolio_pair in self.algo_portfolio_pairs:

                algo = algo_portfolio_pair.algo
                portfolio = algo_portfolio_pair.portfolio

                portfolio._create_new_daily_row_generators(
                    trading_day.open_time_iso, trading_day.close_time_iso)

                while not portfolio._any_generator_reached_end_of_day():
                    portfolio._increment_all_positions()
                    # TODO: Call algorithm increment/run function here

                    # breakpoint()
                    if not portfolio._any_generator_reached_end_of_day():
                        print(
                            f"{portfolio.get_current_timestamp()}, {round(portfolio.total_value(), 2):,}")