# backtest_runner.py
# ==================================
import logging
from datetime import datetime
import backtrader as bt
import backtrader.indicators as btind
import backtrader.feeds as btfeeds
import backtrader.indicators as btind
import pandas as pd
import matplotlib.pyplot as plt



from macd_kdj_atr.strategy import MACDKDJStrategy

cerebro = bt.Cerebro()
st_date = pd.to_datetime('2020-01-01')
ed_date = pd.to_datetime('2024-12-01')
class GenericCSV(btfeeds.GenericCSVData):
    params = (
        ('fromdate', st_date),
        ('todate', ed_date),
        ('dtformat', ('%Y-%m-%d')),
        ('datetime', 0),
        ('high', 2),
        ('low', 3),
        ('open', 1),
        ('close', 4),
        ('volume', 5),
        ('openinterest', -1),
    )
datafeed1 = GenericCSV(dataname='0981.HK.csv', fromdate=st_date, todate=ed_date)
cerebro.adddata(datafeed1, name='IF')
cerebro.broker.setcash(1000000.0)
cerebro.broker.set_slippage_perc(perc=0.0001) 
cerebro.broker.set_filler(bt.broker.filler.BarPointPerc(minmov=0.1, perc=50))
cerebro.broker.setcommission(commission=0.1, # handling fee of 0.1%
                             mult=300,  # Contract Multiplier
                             margin=0.1, # Margin Ratio
                             percabs=False, 
                             commtype=bt.CommInfoBase.COMM_FIXED,
                             stocklike=False)

cerebro.addstrategy(MACDKDJStrategy)
cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
# Add analyzers before running the strategy
cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharperatio', 
                    riskfreerate=0.02, annualize=True)
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

# Run the strategy
result = cerebro.run()
strat = result[0]

# Create analysis file
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
analysis_filename = f'analysis_results_{timestamp}.txt'

with open(analysis_filename, 'w') as f:
    # Write Strategy Summary
    f.write("Strategy Analysis Results\n")
    f.write("=" * 50 + "\n\n")
    
    # Write Returns Analysis
    f.write("Returns Analysis\n")
    f.write("-" * 20 + "\n")
    returns = strat.analyzers.returns.get_analysis()
    f.write(f"Total Return: {returns['rtot']*100:.2f}%\n")
    f.write(f"Average Return: {returns['ravg']*100:.2f}%\n")
    f.write(f"Annual Return: {returns['rnorm100']:.2f}%\n\n")
    
    # Write Trade Analysis
    f.write("Trade Analysis\n")
    f.write("-" * 20 + "\n")
    trades = strat.analyzers.trades.get_analysis()
    f.write(f"Total Trades: {trades.total.total}\n")
    if trades.total.total > 0:
        f.write(f"Winning Trades: {trades.won.total}\n")
        f.write(f"Losing Trades: {trades.lost.total}\n")
        f.write(f"Win Rate: {(trades.won.total/trades.total.total)*100:.2f}%\n")
        if trades.won.total > 0:
            f.write(f"Average Winning Trade: {trades.won.pnl.average:.2f}\n")
        if trades.lost.total > 0:
            f.write(f"Average Losing Trade: {trades.lost.pnl.average:.2f}\n")
    f.write("\n")
    
    # Write Sharpe Ratio
    f.write("Risk Metrics\n")
    f.write("-" * 20 + "\n")
    
    # Write Sharpe Ratio (handle None)
    sharpe = strat.analyzers.sharperatio.get_analysis()
    sharpe_ratio = sharpe.get('sharperatio', None)
    if sharpe_ratio is not None:
        f.write(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    else:
        f.write("Sharpe Ratio: N/A")

    
    # Write Drawdown Info
    drawdown = strat.analyzers.drawdown.get_analysis()
    f.write(f"Max Drawdown: {drawdown['max']['drawdown']:.2f}%\n")
    f.write(f"Max Drawdown Length: {drawdown['max']['len']} days\n")
    
    # Write Portfolio Value Info
    f.write("\nPortfolio Value\n")
    f.write("-" * 20 + "\n")
    f.write(f"Initial Value: {cerebro.broker.startingcash:.2f}\n")
    f.write(f"Final Value: {cerebro.broker.getvalue():.2f}\n")
    f.write(f"Total Return: {((cerebro.broker.getvalue() / cerebro.broker.startingcash) - 1) * 100:.2f}%\n")

print(f"Trading log saved to: {strat.log_filename}")
print(f"Analysis results saved to: {analysis_filename}")
cerebro.plot()