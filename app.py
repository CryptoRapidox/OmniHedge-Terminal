# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# --- 1. AYARLAR ---
st.set_page_config(page_title="OmniHedge Ultimate", page_icon="🚀", layout="wide")
if 'positions' not in st.session_state: st.session_state.positions = []
if 'selected_token' not in st.session_state: st.session_state.selected_token = "BTC"

# CSS: rapidox_ Watermark
st.markdown("""
    <style>
    .main { background-color: #0b0e11; }
    .main::before {
        content: "rapidox_";
        position: fixed; top: 50%; left: 50%;
        transform: translate(-50%, -50%) rotate(-25deg);
        font-size: 15vw; color: rgba(255, 255, 255, 0.02);
        z-index: 0; pointer-events: none; white-space: nowrap; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR API ---
st.sidebar.header("🔑 API & System")
TRADE_AMOUNT_USD = st.sidebar.number_input("Amount per Leg ($)", min_value=10.0, value=100.0)
with st.sidebar.expander("API Keys", expanded=True):
    p_addr = st.text_input("Pacifica Wallet", type="password", key="p_v51")
    if p_addr: st.success("✅ Pacifica Connected")

# --- 3. ULTRA ROBUST VERİ MOTORU ---
@st.cache_data(ttl=10)
def fetch_robust_data():
    res = {"Variational": {}, "Pacifica": {}, "Reya": {}, "Lighter": {}, "Prices": {}}
    
    # 1. Binance Fiyatları
    try:
        p_res = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=3).json()
        res["Prices"] = {item['symbol'].replace('USDT', ''): float(item['price']) for item in p_res if 'USDT' in item['symbol']}
    except: pass

    # 2. Funding Verileri
    try:
        # Pacifica
        p_data = requests.get("https://api.pacifica.fi/api/v1/info", timeout=3).json()
        if p_data.get("success"):
            res["Pacifica"] = {i.get("symbol"): float(i.get("funding_rate", 0)) for i in p_data.get("data", [])}
    except: pass

    try:
        # Variational
        v_data = requests.get("https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/stats", timeout=3).json()
        res["Variational"] = {i.get("ticker"): float(i.get("funding_rate", 0)) for i in v_data.get("listings", [])}
    except: pass
    
    # Reya & Lighter
    try:
        r_data = requests.get("https://api.reya.xyz/v2/markets/summary", timeout=3).json()
        for m in r_data:
            s = m.get("symbol", "").replace("RUSDPERP", "").replace("PERP", "")
            if s.startswith('k') and len(s) > 1 and s[1].isupper(): s = s[1:]
            res["Reya"][s] = float(m.get("fundingRate", "0"))
    except: pass

    return res

# --- 4. ANALİZ ---
data = fetch_robust_data()
target_tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'HYPE', 'ADA', 'PAXG', 'AAVE', 'TAO', 'AVAX', 'BNB', 'SUI', 'ENA', 'PUMP', 'BERA', 'IP', 'INJ', 'DOGE', 'VIRTUAL', 'ARB', 'TRUMP', 'LDO', 'LTC', 'EIGEN', 'AERO', 'SEI', 'ZRO', 'TIA', 'TRX', 'UNI', 'PENDLE', 'PEPE', 'ME', 'MOVE', 'WLFI', 'GRASS', 'JUP', 'SHIB', 'JTO', 'TON', 'KAITO', 'CRV', 'LINEA', 'XPL', 'PENGU', 'ONDO', 'NEIRO', 'GOAT', 'NEAR', 'WLD', 'POPCAT', 'LINK', 'SYRUP', 'AI16Z', 'APT', 'PROVE', 'BONK', 'MORPHO', 'S', 'PYTH', 'XAU', 'XAG', 'PLTR', 'NVDA', 'ZEC', 'BCH', 'EURUSD', 'MEGA', 'TSLA', 'PIPPIN']

signals = []
for t in target_tokens:
    v, p, r = data["Variational"].get(t), data["Pacifica"].get(t), data["Reya"].get(t)
    price = data["Prices"].get(t, 0.0)
    valid = {k: val for k, val in {"Variational": v, "Pacifica": p, "Reya": r}.items() if val is not None}
    if len(valid) >= 2:
        s_ex, l_ex = max(valid, key=valid.get), min(valid, key=valid.get)
        spr = (valid[s_ex] - valid[l_ex]) * 100
        if spr >= 0.1: signals.append({"Token": t, "Spread": spr, "Short": s_ex, "Long": l_ex, "Price": price})

# --- 5. UI ---
col_radar, col_exec = st.columns([1.3, 1.2])

with col_radar:
    st.subheader("📡 Arbitrage Radar")
    if signals:
        for s in sorted(signals, key=lambda x: x['Spread'], reverse=True):
            price_disp = f"${s['Price']}" if s['Price'] > 0 else "Price N/A"
            if st.button(f"🔔 {s['Token']} | Spread: {s['Spread']:.3f}% | {price_disp}", key=f"s_{s['Token']}", use_container_width=True):
                st.session_state.selected_token = s['Token']
    else: st.info("Scanning Market Data...")

with col_exec:
    st.subheader("⚡ Integrated Control")
    sel = st.selectbox("Asset", target_tokens, index=target_tokens.index(st.session_state.selected_token))
    
    # Fiyat Kontrolü ve Manuel Giriş
    api_price = data["Prices"].get(sel, 0.0)
    if api_price > 0:
        st.markdown(f"<h1 style='text-align: center; color: #f0b90b;'>${api_price}</h1>", unsafe_allow_html=True)
        final_price = api_price
    else:
        st.warning(f"⚠️ {sel} price not found on Binance. Enter manually below:")
        final_price = st.number_input("Manual Price ($)", value=1.0, format="%.4f")

    match = next((s for s in signals if s['Token'] == sel), None)
    s_ex = match['Short'] if match else "Pacifica"
    l_ex = match['Long'] if match else "Variational"

    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**SHORT: {s_ex}**")
            s_tp = st.number_input("TP ($)", value=final_price * 0.95, format="%.4f", key="stp")
            s_sl = st.number_input("SL ($)", value=final_price * 1.05, format="%.4f", key="ssl")
        with c2:
            st.markdown(f"**LONG: {l_ex}**")
            l_tp = st.number_input("TP ($)", value=final_price * 1.05, format="%.4f", key="ltp")
            l_sl = st.number_input("SL ($)", value=final_price * 0.95, format="%.4f", key="lsl")
        
        if st.button("OPEN HEDGE", type="primary", use_container_width=True):
            st.session_state.positions.append({"Token": sel, "Size": TRADE_AMOUNT_USD, "Entry": final_price, "Time": datetime.now().strftime("%H:%M:%S")})
            st.balloons()

    st.divider()
    st.subheader("💼 Active Positions")
    if st.session_state.positions:
        st.table(pd.DataFrame(st.session_state.positions))
    else: st.info("No open positions.")

time.sleep(2)
st.rerun()
