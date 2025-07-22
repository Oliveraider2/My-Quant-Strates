# strategy.py
# ------------------------
# This module defines the MACD-KDJ-ATR strategy and custom indicators.
# It encapsulates entry/exit logic, risk management, and logging behavior.
import logging
from datetime import datetime
import backtrader as bt
import backtrader.indicators as btind


class MACDKDJStrategy(bt.Strategy):
    """
    Combines MACD, KDJ, and ATR-based dynamic position sizing.
    Manages entries, exits, pyramiding, stop-loss, and take-profit.
    """
    params = dict(
        N1=15,  # ATR moving average period
        N2=10,  # (unused) placeholder for potential SMA period
    )

    def log(self, txt, dt=None):
        """
        Helper method for logging messages to console and file.
        dt defaults to the current bar's datetime.
        """
        dt = dt or self.datas[0].datetime.datetime(0)
        msg = f"{dt.isoformat()}, {txt}"
        print(msg)
        logging.info(msg)

    def __init__(self):
        # Track pending orders and buy count
        self.order = None
        self.buy_count = 0
        self.last_buy_price = 0

        # Data references for convenience
        self.close = self.data.close
        self.high = self.data.high
        self.low = self.data.low

        # Calculate True Range and ATR
        self.TR = btind.Max(
            self.high(0) - self.low(0),
            abs(self.high(0) - self.close(-1)),
            abs(self.low(0) - self.close(-1))
        )
        self.ATR = btind.SimpleMovingAverage(self.TR, period=self.params.N1)

        # Attach custom indicators
        self.kdj = My_KDJ(self.data)
        self.macd = My_MACD(self.data)

        # Additional filters
        self.rsi = btind.RSI(self.data, period=14)
        self.sma_volume = btind.SimpleMovingAverage(self.data.volume, period=20)
        self.sma10 = btind.SimpleMovingAverage(self.data, period=10)
        self.sma5 = btind.SimpleMovingAverage(self.data, period=5)

        # Configure file logging
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_filename = f"trading_log_{timestamp}.txt"
        logging.basicConfig(
            filename=self.log_filename,
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def next(self):
        """
        Called on each new bar: decides to enter, exit, pyramid, or hold.
        1) Manage existing long/short position
        2) Generate new entry signals when flat
        """
        if self.order:
            # Skip if an order is pending
            return

        # Snapshot indicator values
        k, d, j = self.kdj.k[0], self.kdj.d[0], self.kdj.j[0]
        k_pre, d_pre, j_pre = self.kdj.k[-1], self.kdj.d[-1], self.kdj.j[-1]
        macd_val = self.macd.macd[0]
        signal_val = self.macd.signal[0]
        hist_val = self.macd.histogram[0]
        vol = self.data.volume[0]
        avg_vol = self.sma_volume[0]

        # 1. If long: pyramiding, stop loss, take profit
        if self.position.size > 0:
            # Pyramiding when in profit and volume confirms
            if (self.close[0] > self.last_buy_price + 0.4 * self.ATR[0]
                    and self.buy_count < 3 and vol > avg_vol):
                self._buy_more()
            # Stop loss
            elif self.close[0] < self.last_buy_price - 3 * self.ATR[0]:
                self._exit_all()
            # Take profit
            elif self.close[0] > self.last_buy_price + 2 * self.ATR[0]:
                self._exit_all()

        # 2. If short: mirrored logic for shorts
        elif self.position.size < 0:
            if (self.close[0] < self.last_buy_price - 0.5 * self.ATR[0]
                    and self.buy_count < 3):
                self._sell_more()
            elif self.close[0] > self.last_buy_price + 3 * self.ATR[0]:
                self._exit_all()
            elif hist_val > 0 and (j_pre < k_pre < j) and (j_pre < d_pre < j):
                self._exit_all()

        # 3. Flat: generate new entry signals
        else:
            # Long condition: MACD hist < 0 and KDJ cross up & RSI filter
            if (hist_val < 0 and j_pre < k_pre < j and j_pre < d_pre < j
                    and self.rsi[0] < 70):
                self._enter_long()
            # Short condition: MACD > 0 and KDJ cross down & price filter
            elif (macd_val > 0 and signal_val > 0 and j_pre > k_pre > j
                    and j_pre > d_pre > j and self.close[0] < self.sma10[0]
                    and self.rsi[0] > 30):
                self._enter_short()

    # --- Helper methods for clean order calls ---
    def _enter_long(self):
        """Send buy order and record price and count."""
        size = int(max((self.broker.getvalue() * 0.005) / (self.ATR[0] * 300 * 0.1), 1))
        self.order = self.buy(size=size)
        self.last_buy_price = self.close[0]
        self.buy_count = 1

    def _enter_short(self):
        """Send sell (short) order and record state."""
        size = int(max((self.broker.getvalue() * 0.005) / (self.ATR[0] * 300 * 0.1), 1))
        self.order = self.sell(size=size)
        self.last_buy_price = self.close[0]
        self.buy_count = 1

    def _buy_more(self):
        """Add to an existing long position."""
        size = int(max((self.broker.getvalue() * 0.005) / (self.ATR[0] * 300 * 0.1), 1))
        self.order = self.buy(size=size)
        self.last_buy_price = self.close[0]
        self.buy_count += 1

    def _sell_more(self):
        """Add to an existing short position."""
        size = int(max((self.broker.getvalue() * 0.005) / (self.ATR[0] * 300 * 0.1), 1))
        self.order = self.sell(size=size)
        self.last_buy_price = self.close[0]
        self.buy_count += 1

    def _exit_all(self):
        """Close all positions and reset buy count."""
        self.order = self.close()
        self.buy_count = 0


# Custom MACD indicator
class My_MACD(bt.Indicator):
    """Computes MACD line, signal line, and histogram."""
    lines = ('macd', 'signal', 'histogram',)
    params = (('p1', 12), ('p2', 26), ('p3', 9),)

    def __init__(self):
        em1 = btind.EMA(self.data, period=self.p.p1)
        em2 = btind.EMA(self.data, period=self.p.p2)
        self.l.macd = em1 - em2
        self.l.signal = btind.EMA(self.l.macd, period=self.p.p3)
        self.l.histogram = self.l.macd - self.l.signal


# Custom KDJ indicator
class My_KDJ(bt.Indicator):
    """Derives %K, %D, and J-line from the Stochastic oscillator."""
    lines = ('k', 'd', 'j',)
    params = (('p1', 9), ('p2', 3), ('p3', 3),)

    def __init__(self):
        stoch = btind.Stochastic(
            self.data,
            period=self.p.p1,
            period_dfast=self.p.p2,
            period_dslow=self.p.p3
        )
        self.l.k = stoch.percK
        self.l.d = stoch.percD
        self.l.j = 3 * self.l.k - 2 * self.l.d

        
       