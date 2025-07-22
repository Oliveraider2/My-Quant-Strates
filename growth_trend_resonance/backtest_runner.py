# backtest_runner.py
# ==================================
from pathlib import Path
import pandas as pd
import numpy as np
import backtrader as bt
from strategy import StockSelectStrategy, PandasDataMore

# ——— Sample Data Generation ———
data_dir = Path('data')
data_dir.mkdir(exist_ok=True)
data_path = data_dir / 'stock_data.csv'

if not data_path.exists():
    # Generate sample for two tickers AAA and BBB over 20 days
    dates = pd.date_range(start='2020-01-01', end='2020-02-05', freq='D')    
    tickers = ['AAA', 'BBB']
    rows = []
    for sec in tickers:
        for dt in dates:
            openp = np.random.uniform(10, 20)
            high = openp * np.random.uniform(1.00, 1.05)
            low = openp * np.random.uniform(0.95, 1.00)
            close = np.random.uniform(low, high)
            volume = np.random.randint(1000, 5000)
            # Financial fields
            net_profit_after = np.random.uniform(1e6, 5e6)
            net_profit_z = net_profit_after * 0.1
            con_npgrate_13w = np.random.uniform(-0.1, 0.3)
            short_term_borrowing = np.random.uniform(0, 1e6)
            short_term_bonds = np.random.uniform(0, 1e6)
            non_current_liabilities_due_in_one_year = np.random.uniform(0, 1e6)
            monetary_capital = np.random.uniform(1e6, 2e6)
            trading_finan_assets = np.random.uniform(0, 5e5)
            net_operating_cash = np.random.uniform(0, 5e5)
            total_assets = np.random.uniform(5e6, 1e7)
            total_liabilities = np.random.uniform(1e6, 3e6)
            ROE_after = np.random.uniform(0, 0.2)
            analyst_revision = np.random.uniform(-0.05, 0.05)
            analyst_growth = np.random.uniform(-0.1, 0.2)
            recent_issuance = np.random.choice([0, 1], p=[0.8, 0.2])
            is_ST = np.random.choice([0, 1], p=[0.9, 0.1])
            rows.append([
                dt, sec, openp, high, low, close, volume,
                net_profit_after, net_profit_z, con_npgrate_13w,
                short_term_borrowing, short_term_bonds,
                non_current_liabilities_due_in_one_year,
                monetary_capital, trading_finan_assets,
                net_operating_cash, total_assets, total_liabilities,
                ROE_after, volume,
                analyst_revision, analyst_growth,
                recent_issuance, is_ST
            ])

    df_sample = pd.DataFrame(rows, columns=[
        'datetime','sec_code','open','high','low','close','value',
        'net_profit_after','net_profit_z','con_npgrate_13w',
        'short_term_borrowing','short_term_bonds',
        'non_current_liabilities_due_in_one_year',
        'monetary_capital','trading_finan_assets',
        'net_operating_cash','total_assets','total_liabilities',
        'ROE_after','value',
        'analyst_revision','analyst_growth',
        'recent_issuance','is_ST'
    ])
    df_sample.to_csv(data_path, index=False)
    print(f"Sample data generated at {data_path}")

# ——— Backtest Setup ———
cerebro = bt.Cerebro()

# Add analyzers for summary
cerebro.addanalyzer(bt.analyzers.Returns, _name='rets')
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0, annualize=True)
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

# Load data feeds
df = pd.read_csv(data_path, parse_dates=['datetime'])
for sec in df['sec_code'].unique():
    sub = df[df['sec_code'] == sec].set_index('datetime').sort_index()
    data = PandasDataMore(dataname=sub)
    cerebro.adddata(data, name=sec)

# Broker settings
cerebro.broker.setcash(1e8)
cerebro.broker.setcommission(commission=0.003)
cerebro.broker.set_slippage_perc(perc=0.0001)

# Run strategy
results = cerebro.run()
strat = results[0]

# ——— Print Summary ———
port_value = cerebro.broker.getvalue()
rets = strat.analyzers.rets.get_analysis()
sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', None)
dd = strat.analyzers.drawdown.get_analysis()

print("=== Backtest Summary ===")
print(f"Final Portfolio Value: {port_value:,.2f}")
print(f"Total Return: {rets['rtot']*100:.2f}%")
print(f"Annualized Return: {rets['rnorm100']:.2f}%")
if sharpe is not None:
    print(f"Sharpe Ratio: {sharpe:.2f}")
else:
    print("Sharpe Ratio: N/A")
print(f"Max Drawdown: {dd['max']['drawdown']:.2f}% over {dd['max']['len']} bars")

try:
    cerebro.plot()
except Exception as e:
    print(f"Plot skipped due to error: {e}")