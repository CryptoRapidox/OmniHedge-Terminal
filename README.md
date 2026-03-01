# 🚀 OmniHedge Ultimate Terminal
**Professional Multi-Exchange Arbitrage & PnL Engine**

OmniHedge is a precision algorithmic trading terminal built for the Pacifica Hackathon. It specializes in delta-neutral funding rate arbitrage across major Perpetual DEXs.

## ✨ Key Features
- **Unified Execution Panel:** A single, streamlined interface for multi-exchange trade entry.
- **Dual-Leg Risk Management:** Independent Take Profit (TP) and Stop Loss (SL) controls for both Short and Long legs.
- **Live Price Integration:** Real-time asset pricing via Binance API for accurate target setting.
- **Hedge PnL Tracker:** Sub-second tracking of unrealized funding profits.
- **Locked API Architecture:** Secure, modular credential management for Pacifica and counter-exchanges.

## 🛠️ Tech Stack
- **Frontend:** Streamlit (Python-based Web Framework)
- **Data Engine:** Pandas & Requests for real-time API aggregation
- **Analytics:** Cross-DEX funding normalization engine

## 🚀 Quick Start
1. Install dependencies:
   ```bash
   pip install streamlit requests pandas matplotlib