# Growth-Trend-Resonance Stock Selection Strategy (REPRODUCED)

This strategy selects the top 30 stocks monthly by a composite score of:
1. TTM growth rate (top 1/3)  
2. Acceleration (top 50% & >0)  
3. NPAP ratio (>50%)  
4. Solvency (>–1)  
5. ROE (>1%)  
6. Daily value (volume top 90%)  
7. Analyst revision & growth forecasts  

It rebalances on five fixed dates (Jan 31, Apr 30, Jul 15, Aug 31, Oct 31),  
excludes equity‑financing firms, ST stocks, and suspended/limit‑up,  
then equally weights the final list.

## Files

- `strategy.py` – core stock‑selection logic and indicators  
- `backtest_runner.py` – auto‑sample data + backtest + summary  
- `requirements.txt` – dependencies (`backtrader`, `pandas`, `numpy`, `scikit-learn`)  
- `README.md` – this file  

## Usage

```bash
cd growth_trend_resonance
pip install -r requirements.txt
python backtest_runner.py
```
