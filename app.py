# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# --- 1. AYARLAR ---
st.set_page_config(page_title="OmniHedge v5.0", page_icon="🚀", layout="wide")

if 'positions' not in st.session_state: st.session_state.positions = []
if 'selected_token' not in st.session_state: st.session_state.selected_token = "BTC"

# CSS: rapidox_ Watermark ve Stil
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
    .stMetric { background-color: #1e2329; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR CONFIG ---
st.sidebar.header("⚙️ Terminal Config")
TRADE_AMOUNT_USD = st.sidebar.number_input("Hedge Amount per Leg ($)", min_value=10.0, value=100.0)

with st.sidebar.expander("🔑 API Credentials", expanded=True):
    p_addr = st.text_input("Pacifica Wallet", type="password", key="p_v5")
    v_key = st.text_input("Variational Key", type="password", key="v_v5")
    if p_addr: st.success("✅ Connected")

# --- 3. MODÜLER VERİ MOTORU ---
@st.cache_data(ttl=10)
def fetch_terminal_data():
    res = {"Variational": {}, "Pacifica": {}, "Reya": {}, "Lighter": {}, "Prices": {}, "Status": {}}
    headers = {'User-Agent': 'Mozilla/5.0'}

    # Binance Fiyatları
    try:
        p_res = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=3).json()
        res["Prices"] = {item['symbol'].replace('USDT', ''): float(item['price']) for item in p_res if 'USDT' in item['symbol']}
    except: res["Status"]["Binance"] = "🔴"

    # Pacifica
    try:
        p_data = requests.get("https://api.pacifica.fi/api/v1/info", headers=headers, timeout=5).json()
        if p_data.get("success"):
            res["Pacifica"] = {i.get("symbol"): float(i.get("funding_rate", 0)) for i in p_data.get("data", [])}
    except: res["Status"]["Pacifica"] = "🔴"

    # Variational
    try:
        v_data = requests.get("https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/stats", timeout=5).json()
        res["Variational"] = {i.get("ticker"): float(i.get("funding_rate", 0)) for i in v_data.get("listings", [])}
    except: pass

    # Reya
    try:
        r_data = requests.get("https://api.reya.xyz/v2/markets/summary", timeout=5).json()
        for m in r_data:
            s = m.get("symbol", "").replace("RUSDPERP", "").replace("PERP", "")
            if s.startswith('k') and len(s) > 1 and s[1].isupper(): s = s[1:]
            res["Reya"][s] = float(m.get("fundingRate", "0"))
    except: pass

    return res

# --- 4. ANALİZ VE HESAPLAMA ---
data = fetch_terminal_data()
target_tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'HYPE', 'ADA', 'PAXG', 'AAVE', 'TAO', 'AVAX', 'BNB', 'SUI', 'ENA', 'PUMP', 'BERA', 'IP', 'INJ', 'DOGE', 'VIRTUAL', 'ARB', 'TRUMP', 'LDO', 'LTC', 'EIGEN', 'AERO', 'SEI', 'ZRO', 'TIA', 'TRX', 'UNI', 'PENDLE', 'PEPE', 'ME', 'MOVE', 'WLFI', 'GRASS', 'JUP', 'SHIB', 'JTO', 'TON', 'KAITO', 'CRV', 'LINEA', 'XPL', 'PENGU', 'ONDO', 'NEIRO', 'GOAT', 'NEAR', 'WLD', 'POPCAT', 'LINK', 'SYRUP', 'AI16Z', 'APT', 'PROVE', 'BONK', 'MORPHO', 'S', 'PYTH', 'XAU', 'XAG', 'PLTR', 'NVDA', 'ZEC', 'BCH', 'EURUSD', 'MEGA', 'TSLA', 'PIPPIN']

signals = []
for t in target_tokens:
    v, p, r = data["Variational"].get(t), data["Pacifica"].get(t), data["Reya"].get(t)
    price = data["Prices"].get(t, 0.0)
    valid = {k: val for k, val in {"Var": v, "Pac": p, "Rey": r}.items() if val is not None}
    if len(valid) >= 2:
        spr = (max(valid.values()) - min(valid.values())) * 100
        if spr >= 0.1: # Hassasiyeti biraz artırdık
            signals.append({"Token": t, "Spread": spr, "Short": max(valid, key=valid.get), "Long": min(valid, key=valid.get), "Price": price})

# --- 5. ARAYÜZ ---
st.title("🚀 OmniHedge Ultimate Terminal")
st.caption(f"Status: {data['Status'].get('Binance', '🟢')} CEX | {data['Status'].get('Pacifica', '🟢')} Pacifica | Active Signals: {len(signals)}")

c_radar, c_exec = st.columns([1.3, 1.2])

with c_radar:
    st.subheader("📡 Arbitrage Radar")
    if signals:
        for s in sorted(signals, key=lambda x: x['Spread'], reverse=True):
            btn_label = f"🔔 {s['Token']} | Spread: {s['Spread']:.3f}% | ${s['Price']:.2f}"
            if st.button(btn_label, key=f"btn_{s['Token']}", use_container_width=True):
                st.session_state.selected_token = s['Token']
    else: st.info("Scanning Market Data...")

with c_exec:
    st.subheader("⚡ Integrated Control Panel")
    sel = st.selectbox("Current Asset", target_tokens, index=target_tokens.index(st.session_state.selected_token))
    cur_p = data["Prices"].get(sel, 1.0)
    st.markdown(f"<h1 style='text-align: center; color: #f0b90b;'>${cur_p:.4f}</h1>", unsafe_allow_html=True)

    match = next((s for s in signals if s['Token'] == sel), None)
    s_l, l_l = (match['Short'], match['Long']) if match else ("---", "---")

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**SHORT: {s_l}**")
            st.number_input("TP ($)", value=cur_p * 0.95, key="stp", format="%.4f")
            st.number_input("SL ($)", value=cur_p * 1.05, key="ssl", format="%.4f")
        with col2:
            st.markdown(f"**LONG: {l_l}**")
            st.number_input("TP ($)", value=cur_p * 1.05, key="ltp", format="%.4f")
            st.number_input("SL ($)", value=cur_p * 0.95, key="lsl", format="%.4f")
        
        if st.button("OPEN HEDGE POSITION", type="primary", use_container_width=True):
            st.session_state.positions.append({
                "Token": sel, "Size": TRADE_AMOUNT_USD, "Entry": cur_p, "Spread": match['Spread'] if match else 0,
                "Time": time.time(), "DisplayTime": datetime.now().strftime("%H:%M:%S")
            })
            st.balloons()

    st.divider()
    st.subheader("💼 Live Positions Tracker")
    if st.session_state.positions:
        # PnL Hesaplama: (Spread / 100 / 24 saat) * Geçen Saniye * Size
        for pos in st.session_state.positions:
            elapsed = time.time() - pos['Time']
            pos['PnL'] = (pos['Spread'] / 100 / 86400) * elapsed * pos['Size']
        
        df = pd.DataFrame(st.session_state.positions)[['Token', 'Size', 'Entry', 'DisplayTime', 'PnL']]
        st.dataframe(df.style.format({"PnL": "{:.6f}$", "Entry": "{:.4f}$"}), use_container_width=True, hide_index=True)
        if st.button("Emergency Close All"): st.session_state.positions = []; st.rerun()
    else: st.warning("No active hedge positions.")

time.sleep(1)
st.rerun()
