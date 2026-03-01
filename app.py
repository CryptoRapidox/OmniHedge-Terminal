# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# --- 1. SAYFA VE SESSION STATE ---
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
    .stMetric { background-color: #1e2329; border-radius: 10px; padding: 10px; border: 1px solid #30363d; }
    /* Pozisyonlar tablosunu daha kompakt yap */
    .compact-table { font-size: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR: KONTROL VE KİLİTLİ API GİRİŞLERİ ---
st.sidebar.header("⚙️ System Config")
TRADE_AMOUNT_USD = st.sidebar.number_input("Hedge Amount per Leg (USD)", min_value=10.0, value=100.0)

st.sidebar.divider()
st.sidebar.subheader("🔑 API Credentials")

# Pacifica
with st.sidebar.expander("Pacifica Credentials", expanded=True):
    p_addr = st.text_input("Wallet Address", type="password", key="p_wal_v4")
    p_key = st.text_input("Private Key", type="password", key="p_key_v4")
    if p_addr and p_key: st.success("✅ Pacifica API Active")

# Variational, Reya, Lighter
with st.sidebar.expander("Counter-Exchange APIs", expanded=False):
    v_key = st.text_input("Variational Key", type="password")
    r_id = st.text_input("Reya ID", type="password")
    l_pub = st.text_input("Lighter Public Key", type="password")
    if v_key or r_id or l_pub: st.success("✅ Multi-Exchange Ready")

# --- 3. CANLI VERİ (RATES + PRICES) ---
@st.cache_data(ttl=10)
def fetch_terminal_data():
    results = {"Variational": {}, "Pacifica": {}, "Reya": {}, "Lighter": {}, "Prices": {}}
    try:
        # Binance Canlı Fiyatlar
        p_res = requests.get("https://api.binance.com/api/v3/ticker/price").json()
        results["Prices"] = {item['symbol'].replace('USDT', ''): float(item['price']) for item in p_res if 'USDT' in item['symbol']}
        
        # Funding Oranları
        v_res = requests.get("https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/stats").json()
        results["Variational"] = {item.get("ticker"): float(item.get("funding_rate", 0)) for item in v_res.get("listings", [])}
        
        p_res = requests.get("https://api.pacifica.fi/api/v1/info", headers={"Accept": "*/*"}).json()
        if p_res.get("success"): results["Pacifica"] = {item.get("symbol"): float(item.get("funding_rate", 0)) for item in p_res.get("data", [])}
        
        r_res = requests.get("https://api.reya.xyz/v2/markets/summary", headers={"Accept": "*/*"}).json()
        for m in r_res:
            sym = m.get("symbol", "").replace("RUSDPERP", "").replace("PERP", "")
            if sym.startswith('k') and len(sym) > 1 and sym[1].isupper(): sym = sym[1:]
            results["Reya"][sym] = float(m.get("fundingRate", "0"))
            
        l_res = requests.get("https://mainnet.zklighter.elliot.ai/api/v1/funding-rates").json()
        if l_res.get("code") == 200:
            for item in l_res.get("funding_rates", []):
                if item.get("exchange") == "lighter": results["Lighter"][item.get("symbol").replace("1000", "")] = float(item.get("rate", 0))
    except: pass
    return results

# --- 4. ANALİZ ---
data = fetch_terminal_data()
target_tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'HYPE', 'ADA', 'PAXG', 'AAVE', 'TAO', 'AVAX', 'BNB', 'SUI', 'ENA', 'PUMP', 'BERA', 'IP', 'INJ', 'DOGE', 'VIRTUAL', 'ARB', 'TRUMP', 'LDO', 'LTC', 'EIGEN', 'AERO', 'SEI', 'ZRO', 'TIA', 'TRX', 'UNI', 'PENDLE', 'PEPE', 'ME', 'MOVE', 'WLFI', 'GRASS', 'JUP', 'SHIB', 'JTO', 'TON', 'KAITO', 'CRV', 'LINEA', 'XPL', 'PENGU', 'ONDO', 'NEIRO', 'GOAT', 'NEAR', 'WLD', 'POPCAT', 'LINK', 'SYRUP', 'AI16Z', 'APT', 'PROVE', 'BONK', 'MORPHO', 'S', 'PYTH', 'XAU', 'XAG', 'PLTR', 'NVDA', 'ZEC', 'BCH', 'EURUSD', 'MEGA', 'TSLA', 'PIPPIN']

signals = []
for token in target_tokens:
    v, p, r, l = data["Variational"].get(token), data["Pacifica"].get(token), data["Reya"].get(token), data["Lighter"].get(token)
    price = data["Prices"].get(token, 0.0)
    valid = {k: val for k, val in {"Variational": v, "Pacifica": p, "Reya": r, "Lighter": l}.items() if val is not None}
    if len(valid) >= 2:
        s_ex, l_ex = max(valid, key=valid.get), min(valid, key=valid.get)
        spread = (valid[s_ex] - valid[l_ex]) * 100
        if spread >= 0.3:
            signals.append({"Token": token, "Spread": spread, "Short": s_ex, "Long": l_ex, "Price": price})

# --- 5. ARAYÜZ (DUAL COLUMN) ---
st.title("🚀 OmniHedge Ultimate Terminal")
st.caption("Developed by rapidox_ | Professional Multi-Exchange Arbitrage & PnL Engine")

col_radar, col_exec = st.columns([1.4, 1.2])

with col_radar:
    st.subheader("📡 Arbitrage Radar")
    if signals:
        for sig in sorted(signals, key=lambda x: x['Spread'], reverse=True):
            if st.button(f"🔔 {sig['Token']} | Spread: {sig['Spread']:.3f}% | Price: ${sig['Price']}", key=f"sig_{sig['Token']}", use_container_width=True):
                st.session_state.selected_token = sig['Token']
    else: st.info("Scanning for spreads...")

with col_exec:
    st.subheader("⚡ Integrated Control Panel")
    selected = st.selectbox("Current Asset", target_tokens, index=target_tokens.index(st.session_state.selected_token))
    cur_p = data["Prices"].get(selected, 1.0)
    st.markdown(f"<h1 style='text-align: center; color: #f0b90b;'>${cur_p}</h1>", unsafe_allow_html=True)

    match = next((s for s in signals if s['Token'] == selected), None)
    s_label = match['Short'] if match else "---"
    l_label = match['Long'] if match else "---"

    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**SHORT: {s_label}**")
            s_tp = st.number_input("TP ($)", value=cur_p * 0.95, key="s_tp_v4", format="%.4f")
            s_sl = st.number_input("SL ($)", value=cur_p * 1.05, key="s_sl_v4", format="%.4f")
        with c2:
            st.markdown(f"**LONG: {l_label}**")
            l_tp = st.number_input("TP ($)", value=cur_p * 1.05, key="l_tp_v4", format="%.4f")
            l_sl = st.number_input("SL ($)", value=cur_p * 0.95, key="l_sl_v4", format="%.4f")
        
        if st.button("OPEN HEDGE POSITION", type="primary", use_container_width=True):
            st.session_state.positions.append({
                "Token": selected, 
                "Size": TRADE_AMOUNT_USD, 
                "Entry": cur_p, 
                "Time": datetime.now().strftime("%H:%M:%S"),
                "PnL": 0.0000
            })
            st.balloons()
    
    # --- TAŞINAN BÖLÜM: AKTİF POZİSYONLAR ARTIK BURADA ---
    st.divider()
    st.subheader("💼 Live Positions Tracker")
    if st.session_state.positions:
        pos_df = pd.DataFrame(st.session_state.positions)
        st.dataframe(pos_df, use_container_width=True, hide_index=True)
        if st.button("Close All Positions", use_container_width=True): 
            st.session_state.positions = []
            st.rerun()
    else:
        st.warning("No active hedge positions.")

# Canlı fiyat akışı için otomatik yenileme
time.sleep(2)
st.rerun()