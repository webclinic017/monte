import pandas as pd

from derived_columns.decorator import derived_column


@derived_column
def net(df: pd.DataFrame, n: int, col: str) -> float:
    """
    Returns the difference in value between the bottom-most row and the nth-to-last row.
    """

    return df.iloc[-n][col] - df.iloc[-1][col]


@derived_column
def mean(df: pd.DataFrame, n: int, col: str) -> float:
    """
    Returns the mean value of the bottom n-rows.
    """

    total = 0

    for i in range(1, n + 1):
        total += df.iloc[-i][col]

    avg = total / n

    return avg


@derived_column
def std_dev(df: pd.DataFrame, n: int, col: str) -> float:
    """
    Returns the standard deviation of the bottom n-rows.
    """
    avg = mean(df, n, col)

    sum_of_squared_differences = sum((df.iloc[-i][col] - avg) ** 2 for i in range(1, n + 1))

    std_dev = (sum_of_squared_differences / n) ** 0.5

    return std_dev


@derived_column
def percent_change(df: pd.DataFrame, n: int, col: str) -> float:
    """
    Returns the percent change over the bottom n-rows.
    """
    initial = df.iloc[-n][col]
    final = df.iloc[-1][col]

    return ((final - initial) / initial) * 100
