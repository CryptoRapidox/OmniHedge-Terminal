# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# --- 1. AYARLAR VE HAFIZA ---
st.set_page_config(page_title="OmniHedge Ultimate", page_icon="🚀", layout="wide")

if 'positions' not in st.session_state: st.session_state.positions = []
if 'selected_token' not in st.session_state: st.session_state.selected_token = "BTC"

# CSS: rapidox_ Watermark ve Terminal UI
st.markdown("""
    <style>
    .main { background-color: #0b0e11; }
    .main::before {
        content: "rapidox_";
        position: fixed; top: 50%; left: 50%;
        transform: translate(-50%; -50%) rotate(-25deg);
        font-size: 15vw; color: rgba(255, 255, 255, 0.02);
        z-index: 0; pointer-events: none; white-space: nowrap; font-weight: bold;
    }
    .stMetric { background-color: #1e2329; border-radius: 10px; padding: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR: KİLİTLİ API GİRİŞLERİ ---
st.sidebar.header("⚙️ System Configuration")
TRADE_AMOUNT_USD = st.sidebar.number_input("Hedge Amount per Leg (USD)", min_value=10.0, value=100.0)

st.sidebar.divider()
st.sidebar.subheader("🔑 API Credentials")

with st.sidebar.expander("Pacifica Credentials", expanded=True):
    p_addr = st.text_input("Wallet Address", type="password", key="p_wal_v5")
    p_key = st.text_input("Private Key", type="password", key="p_key_v5")
    if p_addr and p_key: st.success("✅ Pacifica API Active")

with st.sidebar.expander("Counter-Exchange APIs", expanded=False):
    v_key = st.text_input("Variational Key", type="password")
    r_id = st.text_input("Reya ID", type="password")
    l_pub = st.text_input("Lighter Public Key", type="password")
    if v_key or r_id or l_pub: st.success("✅ Multi-Exchange Ready")

# --- 3. DAYANIKLI VERİ ÇEKME MOTORU ---
@st.cache_data(ttl=10)
def fetch_robust_data():
    res = {"Variational": {}, "Pacifica": {}, "Reya": {}, "Lighter": {}, "Prices": {}}
    # Binance Prices
    try:
        p_res = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=5).json()
        res["Prices"] = {item['symbol'].replace('USDT', ''): float(item['price']) for item in p_res if 'USDT' in item['symbol']}
    except: pass
    # Pacifica
    try:
        p_res = requests.get("https://api.pacifica.fi/api/v1/info", headers={"Accept": "*/*"}, timeout=5).json()
        if p_res.get("success"): res["Pacifica"] = {i.get("symbol"): float(i.get("funding_rate", 0)) for i in p_res.get("data", [])}
    except: pass
    # Variational
    try:
        v_res = requests.get("https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/stats", timeout=5).json()
        res["Variational"] = {i.get("ticker"): float(i.get("funding_rate", 0)) for i in v_res.get("listings", [])}
    except: pass
    # Reya
    try:
        r_res = requests.get("https://api.reya.xyz/v2/markets/summary", headers={"Accept": "*/*"}).json()
        for m in r_res:
            s = m.get("symbol", "").replace("RUSDPERP", "").replace("PERP", "")
            if s.startswith('k') and len(s) > 1 and s[1].isupper(): s = s[1:]
            res["Reya"][s] = float(m.get("fundingRate", "0"))
    except: pass
    # Lighter
    try:
        l_res = requests.get("https://mainnet.zklighter.elliot.ai/api/v1/funding-rates").json()
        if l_res.get("code") == 200:
            for i in l_res.get("funding_rates", []):
                if i.get("exchange") == "lighter": res["Lighter"][i.get("symbol").replace("1000", "")] = float(i.get("rate", 0))
    except: pass
    return res

# --- 4. ANALİZ ---
data = fetch_robust_data()
target_tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'HYPE', 'ADA', 'PAXG', 'AAVE', 'TAO', 'AVAX', 'BNB', 'SUI', 'ENA', 'PUMP', 'BERA', 'IP', 'INJ', 'DOGE', 'VIRTUAL', 'ARB', 'TRUMP', 'LDO', 'LTC', 'EIGEN', 'AERO', 'SEI', 'ZRO', 'TIA', 'TRX', 'UNI', 'PENDLE', 'PEPE', 'ME', 'MOVE', 'WLFI', 'GRASS', 'JUP', 'SHIB', 'JTO', 'TON', 'KAITO', 'CRV', 'LINEA', 'XPL', 'PENGU', 'ONDO', 'NEIRO', 'GOAT', 'NEAR', 'WLD', 'POPCAT', 'LINK', 'SYRUP', 'AI16Z', 'APT', 'PROVE', 'BONK', 'MORPHO', 'S', 'PYTH', 'XAU', 'XAG', 'PLTR', 'NVDA', 'ZEC', 'BCH', 'EURUSD', 'MEGA', 'TSLA', 'PIPPIN']

signals = []
for t in target_tokens:
    v, p, r, l = data["Variational"].get(t), data["Pacifica"].get(t), data.get("Reya",{}).get(t), data.get("Lighter",{}).get(t)
    price = data["Prices"].get(t, 0.0)
    valid = {k: val for k, val in {"Variational": v, "Pacifica": p, "Reya": r, "Lighter": l}.items() if val is not None}
    if len(valid) >= 2:
        s_ex, l_ex = max(valid, key=valid.get), min(valid, key=valid.get)
        spr = (valid[s_ex] - valid[l_ex]) * 100
        if spr >= 0.1: signals.append({"Token": t, "Spread": spr, "Short": s_ex, "Long": l_ex, "Price": price})

# --- 5. ARAYÜZ ---
col_radar, col_exec = st.columns([1.4, 1.2])

with col_radar:
    st.subheader("📡 Arbitrage Radar")
    if signals:
        for s in sorted(signals, key=lambda x: x['Spread'], reverse=True):
            if st.button(f"🔔 {s['Token']} | Spread: {s['Spread']:.3f}% | Price: ${s['Price']}", key=f"s_{s['Token']}", use_container_width=True):
                st.session_state.selected_token = s['Token']
    else: st.info("Scanning for opportunities...")

with col_exec:
    st.subheader("⚡ Execution & Live Positions")
    sel = st.selectbox("Asset", target_tokens, index=target_tokens.index(st.session_state.selected_token))
    cur_p = data["Prices"].get(sel, 1.0)
    st.markdown(f"<h1 style='text-align: center; color: #f0b90b;'>${cur_p}</h1>", unsafe_allow_html=True)
    
    match = next((s for s in signals if s['Token'] == sel), None)
    s_l = match['Short'] if match else "Pacifica"
    l_l = match['Long'] if match else "Variational"

    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**SHORT: {s_l}**")
            s_tp = st.number_input("TP ($)", value=cur_p * 0.95, key="stp", format="%.4f")
            s_sl = st.number_input("SL ($)", value=cur_p * 1.05, key="ssl", format="%.4f")
        with c2:
            st.markdown(f"**LONG: {l_l}**")
            l_tp = st.number_input("TP ($)", value=cur_p * 1.05, key="ltp", format="%.4f")
            l_sl = st.number_input("SL ($)", value=cur_p * 0.95, key="lsl", format="%.4f")
        
        if st.button("OPEN HEDGE", type="primary", use_container_width=True):
            st.session_state.positions.append({"Token": sel, "Size": TRADE_AMOUNT_USD, "Entry": cur_p, "Time": datetime.now().strftime("%H:%M:%S")})
            st.balloons()

    st.divider()
    if st.session_state.positions:
        st.dataframe(pd.DataFrame(st.session_state.positions), use_container_width=True, hide_index=True)
        if st.button("Close All"): st.session_state.positions = []; st.rerun()
    else: st.warning("No active positions.")

time.sleep(2)
st.rerun()
