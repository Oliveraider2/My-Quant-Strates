# MACD-KDJ-ATR Backtrader Strategy

This is a systematic trading strategy using Backtrader, combining:
- **MACD** (12,26,9)  
- **KDJ** (Stochastic with J‑line)  
- **ATR**‑based dynamic position sizing  
- Volume filters and pyramiding (max 3 adds)  
- Stop‑loss and take‑profit via ATR multiples  

## Files

- `strategy.py` – core strategy and custom indicators  
- `backtest_runner.py` – loads CSV, runs Cerebro, prints summary  
- `requirements.txt` – dependencies  
- `README.md` – this file  

## Usage

```bash
cd macd_kdj_atr
pip install -r requirements.txt
python backtest_runner.py path/to/your_data.csv