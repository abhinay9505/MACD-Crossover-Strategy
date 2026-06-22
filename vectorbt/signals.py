from macd import MACDCalculator


def generate_signals(close):

    macd_calc = MACDCalculator()

    macd, signal, hist = (
        macd_calc.calculate(close)
    )

    entries = (
        (macd > signal)
        &
        (macd.shift(1)
         <= signal.shift(1))
    )

    exits = (
        (macd < signal)
        &
        (macd.shift(1)
         >= signal.shift(1))
    )

    return (
        entries,
        exits,
        macd,
        signal
    )