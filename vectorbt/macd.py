import pandas as pd


class MACDCalculator:

    def __init__(
        self,
        fast_period=12,
        slow_period=26,
        signal_period=9
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def ema(self, series, period):
        return series.ewm(
            span=period,
            adjust=False
        ).mean()

    def calculate(self, close):

        fast_ema = self.ema(
            close,
            self.fast_period
        )

        slow_ema = self.ema(
            close,
            self.slow_period
        )

        macd_line = (
            fast_ema
            - slow_ema
        )

        signal_line = self.ema(
            macd_line,
            self.signal_period
        )

        histogram = (
            macd_line
            - signal_line
        )

        return (
            macd_line,
            signal_line,
            histogram
        )