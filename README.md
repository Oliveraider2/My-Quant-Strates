# Quantitative Trading Strategies

This repository contains two systematic trading strategy implementations using Backtrader:

1. **MACD-KDJ-ATR Strategy** (`macd_kdj_atr/`)
2. **Growth_trend_resonance Stock Selection Strategy** (`growth_trend_resonance/`)

---

## Repository Structure


```text
├── macd_kdj_atr/
│   ├── strategy.py
│   ├── backtest_runner.py
│   ├── requirements.txt
│   └── README.md
├── growth_trend_resonance/
│   ├── strategy.py
│   ├── backtest_runner.py
│   ├── requirements.txt
│   └── README.md
├── .gitignore
└── README.md
```
---

## Prerequisites

- Python 3.8 or higher  
- pip

Each sub-project has its own `requirements.txt`.

---

## Installation

### Clone the repository:

git clone https://github.com/Oliveraider2/My-Quant-Strates.git 

### Install dependencies for both strategies:

pip install -r macd_kdj_atr/requirements.txt
pip install -r growth_trend_resonance/requirements.txt

### Usage

#### MACD‑KDJ‑ATR Strategy
```bash
cd macd_kdj_atr
# The script auto‑generates sample data if none is found
python backtest_runner.py path/to/your_data.csv
```

#### Growth_trend_resonance Stock Selection Strategy
```bash
cd growth_trend_resonance
# The script auto-generates sample data if none is found
python backtest_runner.py
```
