# strategy.py
# Implements the Growth-Momentum Stock Selection Strategy per report.
# 1) Base pool: top 1/3 by TTM growth, then top 50% acceleration > 0
# 2) Hard filters: NPAP > 50%, Solvency > -1, ROE > 0.01, volume top 90%, no recent equity financing, exclude ST
# 3) Add analyst factors, compute composite
# 4) Exclude suspended/limit-up, fill to N
# 5) Rebalance on specified dates

import backtrader as bt
import backtrader.indicators as btind
import numpy as np
import collections
from sklearn.linear_model import LinearRegression
from datetime import timedelta

class PandasDataMore(bt.feeds.PandasData):
    """
    Extend PandasData to include custom financial, analyst forecast, and issuance flag.
    Ensure DataFrame has corresponding columns.
    """
    lines = (
        'net_profit_after', 'net_profit_z', 'con_npgrate_13w',
        'short_term_borrowing', 'short_term_bonds', 'non_current_liabilities_due_in_one_year',
        'monetary_capital', 'trading_finan_assets', 'net_operating_cash',
        'total_assets', 'total_liabilities', 'ROE_after', 'value',
        'analyst_revision', 'analyst_growth', 'recent_issuance', 'is_ST'
    )
    params = tuple((ln, ln) for ln in lines)

class AccIndex(bt.Indicator):
    """Compute acceleration from net_profit_z via quadratic regression."""
    lines = ('acc',)
    params = dict(window=8)
    def __init__(self):
        self.history = collections.deque(maxlen=self.p.window)
    def next(self):
        self.history.append(self.data.net_profit_z[0])
        if len(self.history) == self.p.window:
            X = np.arange(self.p.window).reshape(-1,1)
            X_poly = np.hstack([X**2, X])
            y = np.array(self.history)
            model = LinearRegression().fit(X_poly, y)
            self.lines.acc[0] = model.coef_[0]
        else:
            self.lines.acc[0] = float('nan')

class ImprovedMTM(bt.Indicator):
    """Momentum sum when high/low < k over the given period, implemented via deque."""
    lines = ('improved_mtm',)
    params = dict(k=1.08, period=20)

    def __init__(self):
        # buffer last 'period' returns, masked by high/low ratio
        self.history = collections.deque(maxlen=self.p.period)

    def next(self):
        # calculate ratio and raw return
        ratio = self.data.high[0] / self.data.low[0]
        ret = (self.data.close[0] / self.data.close[-1] - 1)
        # append masked return
        if ratio < self.p.k:
            self.history.append(ret)
        else:
            self.history.append(0.0)
        # sum over history
        self.lines.improved_mtm[0] = sum(self.history)

class SolvencyAbility(bt.Indicator):
    """(Cash - short_term_debt) / net_assets"""
    lines = ('solvency',)
    def next(self):
        st_debt = (
            self.data.short_term_borrowing[0]
            + self.data.short_term_bonds[0]
            + self.data.non_current_liabilities_due_in_one_year[0]
        )
        cash = (
            self.data.monetary_capital[0]
            + self.data.trading_finan_assets[0]
            - self.data.net_operating_cash[0]
        )
        net_assets = self.data.total_assets[0] - self.data.total_liabilities[0]
        self.lines.solvency[0] = ((cash - st_debt) / net_assets
                                  if net_assets != 0 else float('nan'))

class StockSelectStrategy(bt.Strategy):
    """Select top N stocks per composite score on fixed dates."""
    params = dict(
        sel_TTM=0.3, sel_ACC=0.5, sel_NPAP=0.5, sel_Solvency=-1,
        sel_ROE=0.01, sel_daily_value=0.9, sel_analyst_rev=0.2,
        sel_analyst_growth=0.2, selnum_final=30, reserve=0.05,
    )
    def __init__(self):
        self.last_rebalance = None
        self.target_pct = (1.0 - self.p.reserve) / self.p.selnum_final
        self.acc = {d._name: AccIndex(d) for d in self.datas}
        self.ttm = {d._name: (d.net_profit_after / d.net_profit_after(-1) - 1) for d in self.datas}
        self.npap = {d._name: (d.net_profit_after / d.net_profit_after(-1)) for d in self.datas}
        self.solv = {d._name: SolvencyAbility(d) for d in self.datas}
        self.roe = {d._name: d.ROE_after for d in self.datas}
        self.vol = {d._name: btind.SimpleMovingAverage(d.value, period=5) for d in self.datas}
        self.mtm = {d._name: ImprovedMTM(d) for d in self.datas}
        self.rev = {d._name: d.analyst_revision for d in self.datas}
        self.gro = {d._name: d.analyst_growth for d in self.datas}
    def next(self):
        dt = self.datas[0].datetime.date(0)
        if self.last_rebalance == dt: return
        target = {(1,31),(4,30),(7,15),(8,31),(10,31)}
        if (dt - timedelta(days=1)).timetuple()[1:3] in target:
            self.rebalance(); self.last_rebalance = dt
    def rebalance(self):
        names = [d._name for d in self.datas]
        # 1. Base pool: top 1/3 TTM & top 50% acc>0
        universe = names
        ttm_vals = sorted([(n,self.ttm[n][0]) for n in universe], key=lambda x: x[1], reverse=True)
        top_third = [n for n,_ in ttm_vals[:len(universe)//3]]
        acc_vals = sorted([(n,self.acc[n][0]) for n in top_third if self.acc[n][0]>0], key=lambda x: x[1], reverse=True)
        base = [n for n,_ in acc_vals[:len(acc_vals)//2]]
        # 2. Hard filters including equity financing
        raw_vols = [self.vol[n][0] for n in base]
        vol_thresh = np.percentile(raw_vols, 90)
        eligible = []
        for n in base:
            d = next(d for d in self.datas if d._name==n)
            if self.npap[n][0]<=0.5 or self.solv[n][0]<=-1 or self.roe[n][0]<=0.01: continue
            if self.vol[n][0]<vol_thresh or d.recent_issuance[0] or d.is_ST[0]: continue
            eligible.append(n)
        if len(eligible)<self.p.selnum_final: eligible = base
        # normalize
        def norm(arr):
            v=[x for x in arr if not np.isnan(x)]; mn,mx=min(v),max(v)
            return [50 if mn==mx else (x-mn)/(mx-mn)*100 for x in arr]
        ttm_n = norm([self.ttm[n][0] for n in eligible])
        acc_n = norm([self.acc[n][0] for n in eligible])
        npap_n = norm([self.npap[n][0] for n in eligible])
        solv_n = norm([self.solv[n][0] for n in eligible])
        roe_n = norm([self.roe[n][0] for n in eligible])
        vol_n = norm([self.vol[n][0] for n in eligible])
        mtm_n = norm([self.mtm[n][0] for n in eligible])
        rev_n = norm([self.rev[n][0] for n in eligible])
        gro_n = norm([self.gro[n][0] for n in eligible])
        # score
        comp=[]
        for i,n in enumerate(eligible):
            score=(self.p.sel_TTM*ttm_n[i]+self.p.sel_ACC*acc_n[i]+self.p.sel_NPAP*npap_n[i]
                   +(1-self.p.sel_Solvency)*solv_n[i]+self.p.sel_ROE*roe_n[i]
                   +self.p.sel_daily_value*vol_n[i]+mtm_n[i]
                   +self.p.sel_analyst_rev*rev_n[i]+self.p.sel_analyst_growth*gro_n[i])
            comp.append((n,score))
        comp.sort(key=lambda x:x[1],reverse=True)
        # exclude suspended/limit-up and top N
        final=[]; i=0
        while len(final)<self.p.selnum_final and i<len(comp):
            n=comp[i][0]; d=next(d for d in self.datas if d._name==n)
            if not(d.high[0]==d.low[0] or d.volume[0]==0): final.append(n)
            i+=1
        # orders
        for d in self.datas:
            self.order_target_percent(d, target=self.target_pct if d._name in final else 0.0)

