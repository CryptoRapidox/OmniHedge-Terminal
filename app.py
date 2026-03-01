# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# --- 1. AYARLAR ---
st.set_page_config(page_title="OmniHedge Pro", page_icon="🚀", layout="wide")
if 'positions' not in st.session_state: st.session_state.positions = []
if 'selected_token' not in st.session_state: st.session_state.selected_token = "BTC"

# CSS: rapidox_ Watermark
st.markdown("""<style>.main::before { content: "rapidox_"; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-25deg); font-size: 15vw; color: rgba(255, 255, 255, 0.02); z-index: 0; pointer-events: none; }</style>""", unsafe_allow_html=True)

# --- 2. SIDEBAR ---
st.sidebar.header("⚙️ System Config")
TRADE_AMOUNT_USD = st.sidebar.number_input("Hedge Amount ($)", min_value=10.0, value=100.0)
with st.sidebar.expander("🔑 API Credentials", expanded=True):
    p_addr = st.text_input("Pacifica Wallet", type="password")
    if p_addr: st.success("✅ Credentials Configured")

# --- 3. AKILLI VERİ MOTORU (CLOUDSafe) ---
@st.cache_data(ttl=10)
def fetch_cloud_stable_data():
    res = {"Variational": {}, "Pacifica": {}, "Reya": {}, "Prices": {}}
    # Header: Bot korumasını geçmek için kritik
    h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # 1. Pacifica (Fiyat + Funding)
    try:
        p = requests.get("https://api.pacifica.fi/api/v1/info", headers=h, timeout=5).json()
        if p.get("success"):
            for i in p.get("data", []):
                s = i.get("symbol")
                res["Pacifica"][s] = float(i.get("funding_rate") or 0)
                # Binance yerine DEX'in kendi fiyatını alıyoruz
                res["Prices"][s] = float(i.get("mark_price") or i.get("index_price") or 0)
    except: pass

    # 2. Variational
    try:
        v = requests.get("https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/stats", headers=h, timeout=5).json()
        for i in v.get("listings", []):
            t = i.get("ticker")
            res["Variational"][t] = float(i.get("funding_rate", 0))
            if t not in res["Prices"] or res["Prices"][t] == 0:
                res["Prices"][t] = float(i.get("last_price", 0))
    except: pass

    # 3. Binance (Yalnızca Yedek Olarak)
    if not res["Prices"].get("BTC"):
        try:
            b = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=3).json()
            for item in b:
                sym = item['symbol'].replace('USDT', '')
                if sym not in res["Prices"]: res["Prices"][sym] = float(item['price'])
        except: pass
    
    return res

# --- 4. ENGINE & UI ---
data = fetch_cloud_stable_data()
target_tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'HYPE', 'ADA', 'PAXG', 'AAVE', 'TAO', 'AVAX', 'BNB', 'SUI', 'ENA', 'PUMP', 'BERA', 'IP', 'INJ', 'DOGE', 'VIRTUAL', 'ARB', 'TRUMP', 'LDO', 'LTC', 'EIGEN', 'AERO', 'SEI', 'ZRO', 'TIA', 'TRX', 'UNI', 'PENDLE', 'PEPE', 'ME', 'MOVE', 'WLFI', 'GRASS', 'JUP', 'SHIB', 'JTO', 'TON', 'KAITO', 'CRV', 'LINEA', 'XPL', 'PENGU', 'ONDO', 'NEIRO', 'GOAT', 'NEAR', 'WLD', 'POPCAT', 'LINK', 'SYRUP', 'AI16Z', 'APT', 'PROVE', 'BONK', 'MORPHO', 'S', 'PYTH', 'XAU', 'XAG', 'PLTR', 'NVDA', 'ZEC', 'BCH', 'EURUSD', 'MEGA', 'TSLA', 'PIPPIN']

signals = []
for t in target_tokens:
    v, p = data["Variational"].get(t), data["Pacifica"].get(t)
    pr = data["Prices"].get(t, 0.0)
    if v is not None and p is not None:
        spr = (v - p) * 100
        if abs(spr) >= 0.1:
            signals.append({"Token": t, "Spread": spr, "Short": "Var" if spr > 0 else "Pac", "Long": "Pac" if spr > 0 else "Var", "Price": pr})

col_radar, col_exec = st.columns([1.3, 1.2])
with col_radar:
    st.subheader("📡 Arbitrage Radar")
    for s in sorted(signals, key=lambda x: abs(x['Spread']), reverse=True):
        if st.button(f"🔔 {s['Token']} | Spread: {s['Spread']:.3f}% | ${s['Price']:.4f}", key=f"s_{s['Token']}", use_container_width=True):
            st.session_state.selected_token = s['Token']

with col_exec:
    st.subheader("⚡ Control & Tracker")
    sel = st.selectbox("Asset", target_tokens, index=target_tokens.index(st.session_state.selected_token))
    p = data["Prices"].get(sel, 0.0)
    st.markdown(f"<h1 style='text-align: center; color: #f0b90b;'>${p:.4f}</h1>", unsafe_allow_html=True)
    if st.button("OPEN HEDGE", type="primary", use_container_width=True):
        st.session_state.positions.append({"Token": sel, "Price": p, "Size": TRADE_AMOUNT_USD, "Time": datetime.now().strftime("%H:%M")})
    st.divider()
    if st.session_state.positions:
        st.dataframe(pd.DataFrame(st.session_state.positions), use_container_width=True, hide_index=True)
        if st.button("Close All"): st.session_state.positions = []; st.rerun()

time.sleep(1)
st.rerun()
