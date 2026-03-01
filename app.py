# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# --- 1. SETUP ---
st.set_page_config(page_title="OmniHedge Master", page_icon="🚀", layout="wide")

if 'positions' not in st.session_state: st.session_state.positions = []
if 'selected_token' not in st.session_state: st.session_state.selected_token = "BTC"

# CSS: rapidox_ Watermark
st.markdown("""<style>.main::before { content: "rapidox_"; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-25deg); font-size: 15vw; color: rgba(255, 255, 255, 0.02); z-index: 0; pointer-events: none; }</style>""", unsafe_allow_html=True)

# --- 2. SIDEBAR: 4-DEX API CREDENTIALS ---
st.sidebar.header("⚙️ Master Configuration")
TRADE_AMOUNT_USD = st.sidebar.number_input("Hedge Amount per Leg ($)", min_value=10.0, value=100.0)

st.sidebar.divider()
st.sidebar.subheader("🔑 Secure API Gateway")

# 4 Borsa da burada, hiçbirini eksik bırakmadım
with st.sidebar.expander("1. Pacifica (Primary)", expanded=True):
    p_addr = st.text_input("Wallet Address", type="password", key="p_v15_a")
    p_key = st.text_input("Private Key", type="password", key="p_v15_k")

with st.sidebar.expander("2. Variational", expanded=False):
    v_key = st.text_input("API Key", type="password", key="v_v15")

with st.sidebar.expander("3. Reya Network", expanded=False):
    r_id = st.text_input("Account ID", type="password", key="r_v15")

with st.sidebar.expander("4. Lighter", expanded=False):
    l_pub = st.text_input("Public Key", type="password", key="l_v15")

# --- 3. CLOUD-READY DATA ENGINE ---
@st.cache_data(ttl=5)
def fetch_terminal_v15():
    res = {"Variational": {}, "Pacifica": {}, "Reya": {}, "Lighter": {}, "Prices": {}, "Logs": []}
    h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # Pacifica
    try:
        p = requests.get("https://api.pacifica.fi/api/v1/info", headers=h, timeout=5).json()
        if p.get("success"):
            for i in p.get("data", []):
                s = i.get("symbol")
                res["Pacifica"][s] = float(i.get("funding_rate") or 0)
                res["Prices"][s] = float(i.get("mark_price") or i.get("index_price") or 0)
    except Exception as e: res["Logs"].append(f"Pacifica: {str(e)}")

    # Variational
    try:
        v = requests.get("https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/stats", headers=h, timeout=5).json()
        for i in v.get("listings", []):
            t = i.get("ticker")
            res["Variational"][t] = float(i.get("funding_rate", 0))
            if t not in res["Prices"]: res["Prices"][t] = float(i.get("last_price", 0))
    except Exception as e: res["Logs"].append(f"Variational: {str(e)}")

    # Reya
    try:
        r = requests.get("https://api.reya.xyz/v2/markets/summary", headers=h, timeout=5).json()
        for m in r:
            s = m.get("symbol", "").replace("RUSDPERP", "").replace("PERP", "")
            if s.startswith('k') and len(s) > 1 and s[1].isupper(): s = s[1:]
            res["Reya"][s] = float(m.get("fundingRate", "0"))
            if s not in res["Prices"]: res["Prices"][s] = float(m.get("markPrice", 0))
    except Exception as e: res["Logs"].append(f"Reya: {str(e)}")

    return res

# --- 4. ENGINE RUN ---
data = fetch_terminal_v15()
if data["Logs"]: 
    with st.sidebar.expander("⚠️ API Debug Logs"):
        for log in data["Logs"]: st.write(log)

target_tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'HYPE', 'ADA', 'PAXG', 'AAVE', 'TAO', 'AVAX', 'BNB', 'SUI', 'ENA', 'PUMP', 'BERA', 'IP', 'INJ', 'DOGE', 'VIRTUAL', 'ARB', 'TRUMP', 'LDO', 'LTC', 'EIGEN', 'AERO', 'SEI', 'ZRO', 'TIA', 'TRX', 'UNI', 'PENDLE', 'PEPE', 'ME', 'MOVE', 'WLFI', 'GRASS', 'JUP', 'SHIB', 'JTO', 'TON', 'KAITO', 'CRV', 'LINEA', 'XPL', 'PENGU', 'ONDO', 'NEIRO', 'GOAT', 'NEAR', 'WLD', 'POPCAT', 'LINK', 'SYRUP', 'AI16Z', 'APT', 'PROVE', 'BONK', 'MORPHO', 'S', 'PYTH', 'XAU', 'XAG', 'PLTR', 'NVDA', 'ZEC', 'BCH', 'EURUSD', 'MEGA', 'TSLA', 'PIPPIN']

signals = []
for t in target_tokens:
    v, p, r = data["Variational"].get(t), data["Pacifica"].get(t), data["Reya"].get(t)
    pr = data["Prices"].get(t, 0.0)
    valid = {k: val for k, val in {"Var": v, "Pac": p, "Rey": r}.items() if val is not None}
    if len(valid) >= 2:
        spr = (max(valid.values()) - min(valid.values())) * 100
        if spr >= 0.1:
            signals.append({"Token": t, "Spread": spr, "Short": max(valid, key=valid.get), "Long": min(valid, key=valid.get), "Price": pr})

# --- 5. UI (UPDATED WITH 2026 SYNTAX) ---
st.title("🚀 OmniHedge Master Terminal")
st.caption("Developed by rapidox_ for Pacifica Hackathon")

col_radar, col_exec = st.columns([1.3, 1.2])

with col_radar:
    st.subheader("📡 Arbitrage Radar")
    if signals:
        for s in sorted(signals, key=lambda x: x['Spread'], reverse=True):
            # use_container_width=True YERİNE width='stretch' KULLANILDI
            if st.button(f"🔔 {s['Token']} | Spread: {s['Spread']:.3f}% | ${s['Price']:.4f}", key=f"s_{s['Token']}", width='stretch'):
                st.session_state.selected_token = s['Token']
    else: st.info("Scanning for on-chain opportunities...")

with col_exec:
    st.subheader("⚡ Integrated Control")
    sel = st.selectbox("Asset", target_tokens, index=target_tokens.index(st.session_state.selected_token))
    p = data["Prices"].get(sel, 0.0)
    st.markdown(f"<h1 style='text-align: center; color: #f0b90b;'>${p:.4f}</h1>", unsafe_allow_html=True)
    
    # width='stretch' GÜNCELLEMESİ
    if st.button("OPEN DUAL-LEG HEDGE", type="primary", width='stretch'):
        st.session_state.positions.append({"Token": sel, "Price": p, "Size": TRADE_AMOUNT_USD, "Time": datetime.now().strftime("%H:%M")})
        st.balloons()

    st.divider()
    st.subheader("💼 Active Position Tracker")
    if st.session_state.positions:
        # width='stretch' GÜNCELLEMESİ
        st.dataframe(pd.DataFrame(st.session_state.positions), width='stretch', hide_index=True)
        if st.button("Close All", width='stretch'): st.session_state.positions = []; st.rerun()
    else: st.warning("No active positions.")

time.sleep(1)
st.rerun()
