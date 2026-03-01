# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# --- 1. AYARLAR VE SESİON STATE ---
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
        transform: translate(-50%, -50%) rotate(-25deg);
        font-size: 15vw; color: rgba(255, 255, 255, 0.02);
        z-index: 0; pointer-events: none; white-space: nowrap; font-weight: bold;
    }
    .stMetric { background-color: #1e2329; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR: KONTROL VE KİLİTLİ API GİRİŞLERİ ---
st.sidebar.header("⚙️ System Config")
TRADE_AMOUNT_USD = st.sidebar.number_input("Hedge Amount per Leg (USD)", min_value=10.0, value=100.0)

st.sidebar.divider()
st.sidebar.subheader("🔑 API Credentials")

with st.sidebar.expander("Pacifica Credentials", expanded=True):
    p_addr = st.text_input("Wallet Address", type="password", key="p_v10")
    p_key = st.text_input("Private Key", type="password", key="pk_v10")
    if p_addr: st.success("✅ Pacifica API Configured")

# --- 3. BULUT SUNUCULARINA UYGUN VERİ MOTORU ---
@st.cache_data(ttl=10)
def fetch_terminal_data():
    results = {"Variational": {}, "Pacifica": {}, "Reya": {}, "Prices": {}, "Status": {}}
    # Header: Streamlit Cloud'un bloklanmasını önleyen profesyonel kimlik bilgisi
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    # 1. Pacifica (Fiyat ve Funding)
    try:
        p_res = requests.get("https://api.pacifica.fi/api/v1/info", headers=headers, timeout=8).json()
        if p_res.get("success"):
            for item in p_res.get("data", []):
                sym = item.get("symbol")
                results["Pacifica"][sym] = float(item.get("funding_rate") or 0)
                # Fiyatı doğrudan DEX Mark Price'dan alıyoruz (Binance'e muhtaç değiliz)
                results["Prices"][sym] = float(item.get("mark_price") or item.get("index_price") or 0)
            results["Status"]["Pacifica"] = "🟢"
    except: results["Status"]["Pacifica"] = "🔴"

    # 2. Variational (Fiyat ve Funding)
    try:
        v_res = requests.get("https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/stats", headers=headers, timeout=8).json()
        for item in v_res.get("listings", []):
            t = item.get("ticker")
            results["Variational"][t] = float(item.get("funding_rate", 0))
            if t not in results["Prices"] or results["Prices"][t] == 0:
                results["Prices"][t] = float(item.get("last_price", 0))
    except: pass

    # 3. Reya (Price & Funding)
    try:
        r_res = requests.get("https://api.reya.xyz/v2/markets/summary", headers=headers, timeout=8).json()
        for m in r_res:
            sym = m.get("symbol", "").replace("RUSDPERP", "").replace("PERP", "")
            if sym.startswith('k') and len(sym) > 1 and sym[1].isupper(): sym = sym[1:]
            results["Reya"][sym] = float(m.get("fundingRate", "0"))
            if sym not in results["Prices"] or results["Prices"][sym] == 0:
                results["Prices"][sym] = float(m.get("markPrice", 0))
    except: pass

    return results

# --- 4. ANALİZ ---
data = fetch_terminal_data()
target_tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'HYPE', 'ADA', 'PAXG', 'AAVE', 'TAO', 'AVAX', 'BNB', 'SUI', 'ENA', 'PUMP', 'BERA', 'IP', 'INJ', 'DOGE', 'VIRTUAL', 'ARB', 'TRUMP', 'LDO', 'LTC', 'EIGEN', 'AERO', 'SEI', 'ZRO', 'TIA', 'TRX', 'UNI', 'PENDLE', 'PEPE', 'ME', 'MOVE', 'WLFI', 'GRASS', 'JUP', 'SHIB', 'JTO', 'TON', 'KAITO', 'CRV', 'LINEA', 'XPL', 'PENGU', 'ONDO', 'NEIRO', 'GOAT', 'NEAR', 'WLD', 'POPCAT', 'LINK', 'SYRUP', 'AI16Z', 'APT', 'PROVE', 'BONK', 'MORPHO', 'S', 'PYTH', 'XAU', 'XAG', 'PLTR', 'NVDA', 'ZEC', 'BCH', 'EURUSD', 'MEGA', 'TSLA', 'PIPPIN']

signals = []
for token in target_tokens:
    v, p, r = data["Variational"].get(token), data["Pacifica"].get(token), data["Reya"].get(token)
    price = data["Prices"].get(token, 0.0)
    valid = {k: val for k, val in {"Var": v, "Pac": p, "Rey": r}.items() if val is not None}
    if len(valid) >= 2:
        spr = (max(valid.values()) - min(valid.values())) * 100
        if spr >= 0.1:
            signals.append({
                "Token": token, "Spread": spr, 
                "Short": max(valid, key=valid.get), "Long": min(valid, key=valid.get), 
                "Price": price
            })

# --- 5. ARAYÜZ (RADAR & EXECUTION) ---
st.title("🚀 OmniHedge Ultimate Terminal")
st.caption(f"Status: {data['Status'].get('Pacifica', '🟢')} Pacifica Connectivity | Pure DEX Analytics | rapidox_")

col_radar, col_exec = st.columns([1.3, 1.2])

with col_radar:
    st.subheader("📡 Arbitrage Radar")
    if signals:
        for s in sorted(signals, key=lambda x: x['Spread'], reverse=True):
            if st.button(f"🔔 {s['Token']} | Spread: {s['Spread']:.3f}% | DEX Price: ${s['Price']:.4f}", key=f"s_{s['Token']}", use_container_width=True):
                st.session_state.selected_token = s['Token']
    else: st.info("Scanning for on-chain spreads... (Please wait for API handshake)")

with col_exec:
    st.subheader("⚡ Integrated Control Panel")
    sel = st.selectbox("Current Asset", target_tokens, index=target_tokens.index(st.session_state.selected_token))
    cur_p = data["Prices"].get(sel, 1.0)
    st.markdown(f"<h1 style='text-align: center; color: #f0b90b;'>${cur_p:.4f}</h1>", unsafe_allow_html=True)

    match = next((s for s in signals if s['Token'] == sel), None)
    s_label = match['Short'] if match else "Pacifica"
    l_label = match['Long'] if match else "Variational"

    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**SHORT: {s_label}**")
            s_tp = st.number_input("TP ($)", value=cur_p * 0.95, format="%.4f", key="stp_v10")
            s_sl = st.number_input("SL ($)", value=cur_p * 1.05, format="%.4f", key="ssl_v10")
        with c2:
            st.markdown(f"**LONG: {l_label}**")
            l_tp = st.number_input("TP ($)", value=cur_p * 1.05, format="%.4f", key="ltp_v10")
            l_sl = st.number_input("SL ($)", value=cur_p * 0.95, format="%.4f", key="lsl_v10")
        
        if st.button("OPEN HEDGE POSITION", type="primary", use_container_width=True):
            st.session_state.positions.append({
                "Token": sel, "Size": TRADE_AMOUNT_USD, "Entry": cur_p, 
                "Spread": match['Spread'] if match else 0,
                "Time": time.time(), "DisplayTime": datetime.now().strftime("%H:%M:%S")
            })
            st.balloons()

    st.divider()
    st.subheader("💼 Live Positions Tracker")
    if st.session_state.positions:
        for pos in st.session_state.positions:
            elapsed = time.time() - pos['Time']
            pos['PnL'] = (pos['Spread'] / 100 / 86400) * elapsed * pos['Size']
        
        df = pd.DataFrame(st.session_state.positions)[['Token', 'Size', 'Entry', 'DisplayTime', 'PnL']]
        st.dataframe(df.style.format({"PnL": "{:.6f}$", "Entry": "{:.4f}$"}), use_container_width=True, hide_index=True)
        if st.button("Emergency Close All", use_container_width=True): 
            st.session_state.positions = []
            st.rerun()
    else: st.warning("No active positions.")

time.sleep(1)
st.rerun()
