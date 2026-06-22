"""
MACD Crossover Strategy - Nautilus Trader implementation
==========================================================
Instrument : EUR/USD
Timeframe  : 1 Hour
Logic      : Long-only. Enter long when MACD line crosses above the signal
             line. Exit to flat when MACD line crosses below the signal line.

The MACD/EMA math is implemented manually in `ManualMacd` below. This does
NOT use Nautilus's built-in `MovingAverageConvergenceDivergence` indicator
(nautilus_trader.indicators.macd) -- the EMA recursion and MACD/signal math
are hand-rolled, mirroring the exact same formula used in the vectorbt and
MT5 implementations so results are directly comparable.
"""

from decimal import Decimal

from nautilus_trader.common.enums import LogColor
from nautilus_trader.config import PositiveInt
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.trading.strategy import Strategy


class ManualMacd:
    """
    Hand-rolled MACD calculation (no library indicator).

    Maintains a fast EMA, slow EMA, and a signal EMA-of-MACD, all updated
    recursively bar-by-bar using the standard formula:

        alpha   = 2 / (period + 1)
        EMA_t   = alpha * price_t + (1 - alpha) * EMA_{t-1}

    `value` is the MACD line, `signal` is the signal line. Both are
    `float('nan')` until the indicator has seen its first input.
    """

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

        self._alpha_fast = 2.0 / (fast_period + 1.0)
        self._alpha_slow = 2.0 / (slow_period + 1.0)
        self._alpha_signal = 2.0 / (signal_period + 1.0)

        self._ema_fast: float | None = None
        self._ema_slow: float | None = None

        self.value: float = float("nan")     # MACD line
        self.signal: float = float("nan")    # Signal line
        self.histogram: float = float("nan")
        self.initialized: bool = False
        self._count: int = 0

    def update_raw(self, price: float) -> None:
        self._count += 1

        if self._ema_fast is None:
            # Seed both EMAs with the first observed price.
            self._ema_fast = price
            self._ema_slow = price
            self.value = self._ema_fast - self._ema_slow   # = 0.0 on seed bar
            self.signal = self.value
            self.histogram = 0.0
            return

        self._ema_fast = self._alpha_fast * price + (1.0 - self._alpha_fast) * self._ema_fast
        self._ema_slow = self._alpha_slow * price + (1.0 - self._alpha_slow) * self._ema_slow
        self.value = self._ema_fast - self._ema_slow
        self.signal = self._alpha_signal * self.value + (1.0 - self._alpha_signal) * self.signal
        self.histogram = self.value - self.signal

        # Consider the indicator "initialized" (warmed up) once we have at
        # least slow_period + signal_period bars, similar in spirit to how
        # Nautilus's built-in indicators report `initialized`.
        if self._count >= (self.slow_period + self.signal_period):
            self.initialized = True

    def reset(self) -> None:
        self.__init__(self.fast_period, self.slow_period, self.signal_period)


class MACDCrossConfig(StrategyConfig, frozen=True):
    """
    Configuration for ``MACDCross``.

    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument ID for the strategy.
    bar_type : BarType
        The bar type for the strategy (drives `on_bar` calls).
    trade_size : Decimal
        The position size per trade.
    fast_ema_period : int, default 12
        The fast EMA period used in the MACD calculation.
    slow_ema_period : int, default 26
        The slow EMA period used in the MACD calculation.
    signal_ema_period : int, default 9
        The signal-line EMA period (applied to the MACD line).
    close_positions_on_stop : bool, default True
        If all open positions should be closed when the strategy stops.

    """

    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    fast_ema_period: PositiveInt = 12
    slow_ema_period: PositiveInt = 26
    signal_ema_period: PositiveInt = 9
    close_positions_on_stop: bool = True


class MACDCross(Strategy):
    """
    Long-only MACD crossover strategy with a hand-rolled MACD calculation.

    - Goes long (market BUY) when the MACD line crosses above the signal
      line.
    - Flattens any open long (market SELL) when the MACD line crosses
      below the signal line.

    Parameters
    ----------
    config : MACDCrossConfig
        The configuration for the instance.

    """

    def __init__(self, config: MACDCrossConfig) -> None:
        super().__init__(config)

        self.instrument: Instrument = None  # set in on_start

        self.macd = ManualMacd(
            fast_period=config.fast_ema_period,
            slow_period=config.slow_ema_period,
            signal_period=config.signal_ema_period,
        )

        # Track previous bar's MACD-vs-signal relationship to detect crosses
        self._prev_state: int = 0  # 0 = unknown, 1 = MACD above signal, -1 = below

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument for {self.config.instrument_id}")
            self.stop()
            return

        # NOTE: we deliberately do NOT call self.register_indicator_for_bars()
        # here, because that mechanism is for Nautilus's built-in Indicator
        # classes. Our ManualMacd is updated by hand inside on_bar() instead.
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar) -> None:
        self.log.info(repr(bar), LogColor.CYAN)

        if bar.is_single_price():
            return  # No real market information for this bar

        # Update our hand-rolled MACD with this bar's close price
        self.macd.update_raw(float(bar.close))

        if not self.macd.initialized:
            self.log.info("Waiting for MACD to warm up...", color=LogColor.BLUE)
            self._prev_state = 0
            return

        current_state = 1 if self.macd.value > self.macd.signal else -1

        if self._prev_state != 0:
            if current_state == 1 and self._prev_state == -1:
                # MACD crossed above signal -> go long
                if self.portfolio.is_flat(self.config.instrument_id):
                    self._buy()
            elif current_state == -1 and self._prev_state == 1:
                # MACD crossed below signal -> flatten
                if self.portfolio.is_net_long(self.config.instrument_id):
                    self.close_all_positions(self.config.instrument_id)

        self._prev_state = current_state

    def _buy(self) -> None:
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(self.config.trade_size),
            time_in_force=TimeInForce.IOC,
        )
        self.submit_order(order)

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        if self.config.close_positions_on_stop:
            self.close_all_positions(self.config.instrument_id)
        self.unsubscribe_bars(self.config.bar_type)

    def on_reset(self) -> None:
        self.macd.reset()
        self._prev_state = 0