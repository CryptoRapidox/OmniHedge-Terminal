# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# --- 1. AYARLAR ---
st.set_page_config(page_title="OmniHedge v23.0", page_icon="🚀", layout="wide")

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
    p_addr = st.text_input("Pacifica Wallet", type="password", key="p_v23")
    v_key = st.text_input("Variational Key", type="password", key="v_v23")
    if p_addr: st.success("✅ Connected")

# --- 3. MODÜLER VERİ MOTORU (YENİ PACIFICA API UYUMLU) ---
@st.cache_data(ttl=10)
def fetch_terminal_data():
    res = {
        "Variational": {}, "Pacifica": {}, "Reya": {}, "Lighter": {}, 
        "Prices": {}, "Status": {}, 
        "SourcePrices": {"Pacifica": 0.0, "Variational": 0.0, "Reya": 0.0, "Lighter": 0.0}
    }
    headers = {'User-Agent': 'Mozilla/5.0'}

    # 1. Binance Fiyatları
    try:
        p_res = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=3).json()
        res["Prices"] = {item['symbol'].replace('USDT', ''): float(item['price']) for item in p_res if 'USDT' in item['symbol']}
    except: res["Status"]["Binance"] = "🔴"

    # 2. Pacifica (RESMİ API DOCS GÜNCELLEMESİ)
    try:
        # Endpoint '/api/v1/info/prices' olarak güncellendi
        p_data = requests.get("https://api.pacifica.fi/api/v1/info/prices", headers=headers, timeout=5).json()
        if p_data.get("success"):
            for i in p_data.get("data", []):
                sym = i.get("symbol", "")
                # Field isimleri 'funding' ve 'mark' olarak düzeltildi
                res["Pacifica"][sym] = float(i.get("funding") or 0)
                if "BTC" in sym.upper():
                    res["SourcePrices"]["Pacifica"] = float(i.get("mark") or i.get("oracle") or 0)
    except: res["Status"]["Pacifica"] = "🔴"

    # 3. Variational
    try:
        v_data = requests.get("https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/stats", timeout=5).json()
        if v_data.get("listings"):
            for i in v_data.get("listings", []):
                t = i.get("ticker", "")
                res["Variational"][t] = float(i.get("funding_rate", 0))
                if "BTC" in t.upper():
                    res["SourcePrices"]["Variational"] = float(i.get("last_price", 0))
    except: pass

    # 4. Reya
    try:
        r_data = requests.get("https://api.reya.xyz/v2/markets/summary", timeout=5).json()
        for m in r_data:
            s_raw = m.get("symbol", "")
            if "BTC" in s_raw.upper():
                res["SourcePrices"]["Reya"] = float(m.get("markPrice", 0))
            
            s = s_raw.replace("RUSDPERP", "").replace("PERP", "")
            if s.startswith('k') and len(s) > 1 and s[1].isupper(): s = s[1:]
            res["Reya"][s] = float(m.get("fundingRate", "0"))
    except: pass

    # 5. Lighter
    try:
        l_res = requests.get("https://mainnet.zklighter.elliot.ai/api/v1/markets", timeout=5).json()
        for i in l_res:
            s_raw = i.get("symbol", "")
            if "BTC" in s_raw.upper():
                res["SourcePrices"]["Lighter"] = float(i.get("last_price") or i.get("price") or 0)
    except: pass

    return res

# --- 4. PACIFICA MERKEZLİ ANALİZ ---
data = fetch_terminal_data()
target_tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'HYPE', 'ADA', 'PAXG', 'AAVE', 'TAO', 'AVAX', 'BNB', 'SUI', 'ENA', 'PUMP', 'BERA', 'IP', 'INJ', 'DOGE', 'VIRTUAL', 'ARB', 'TRUMP', 'LDO', 'LTC', 'EIGEN', 'AERO', 'SEI', 'ZRO', 'TIA', 'TRX', 'UNI', 'PENDLE', 'PEPE', 'ME', 'MOVE', 'WLFI', 'GRASS', 'JUP', 'SHIB', 'JTO', 'TON', 'KAITO', 'CRV', 'LINEA', 'XPL', 'PENGU', 'ONDO', 'NEIRO', 'GOAT', 'NEAR', 'WLD', 'POPCAT', 'LINK', 'SYRUP', 'AI16Z', 'APT', 'PROVE', 'BONK', 'MORPHO', 'S', 'PYTH', 'XAU', 'XAG', 'PLTR', 'NVDA', 'ZEC', 'BCH', 'EURUSD', 'MEGA', 'TSLA', 'PIPPIN']

signals = []
for t in target_tokens:
    pacifica_rate = data["Pacifica"].get(t)
    price = data["Prices"].get(t, 0.0)
    
    if pacifica_rate is not None:
        comparisons = {
            "Var": data["Variational"].get(t),
            "Rey": data["Reya"].get(t)
        }
        
        best_spread = 0
        best_counter_exchange = None
        
        for ex_name, ex_rate in comparisons.items():
            if ex_rate is not None:
                spread = abs(pacifica_rate - ex_rate) * 100
                if spread > best_spread:
                    best_spread = spread
                    best_counter_exchange = ex_name
                    
        if best_spread >= 0.1 and best_counter_exchange:
            if pacifica_rate > comparisons[best_counter_exchange]:
                s_l, l_l = "Pac", best_counter_exchange
            else:
                s_l, l_l = best_counter_exchange, "Pac"
                
            signals.append({"Token": t, "Spread": best_spread, "Short": s_l, "Long": l_l, "Price": price})

# --- 5. ARAYÜZ ---
st.title("🚀 OmniHedge Ultimate Terminal")

st.subheader("📊 Live BTC Price Monitoring (Multi-DEX)")
p_col1, p_col2, p_col3, p_col4 = st.columns(4)
sp = data["SourcePrices"]

p_col1.metric("Pacifica BTC", f"${sp['Pacifica']:,.2f}" if sp['Pacifica'] > 0 else "Syncing...")
p_col2.metric("Variational BTC", f"${sp['Variational']:,.2f}" if sp['Variational'] > 0 else "Syncing...")
p_col3.metric("Reya BTC", f"${sp['Reya']:,.2f}" if sp['Reya'] > 0 else "Syncing...")
p_col4.metric("Lighter BTC", f"${sp['Lighter']:,.2f}" if sp['Lighter'] > 0 else "Syncing...")

st.divider()

st.caption(f"Status: {data['Status'].get('Binance', '🟢')} CEX | {data['Status'].get('Pacifica', '🟢')} Pacifica | Active Signals: {len(signals)}")

c_radar, c_exec = st.columns([1.3, 1.2])

with c_radar:
    st.subheader("📡 Pacifica-Centric Radar")
    if signals:
        for s in sorted(signals, key=lambda x: x['Spread'], reverse=True):
            btn_label = f"🔔 {s['Token']} | Spread: {s['Spread']:.3f}% | ${s['Price']:.2f}"
            if st.button(btn_label, key=f"btn_{s['Token']}", width='stretch'):
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
        
        if st.button("OPEN HEDGE POSITION", type="primary", width='stretch'):
            st.session_state.positions.append({
                "Token": sel, "Size": TRADE_AMOUNT_USD, "Entry": cur_p, "Spread": match['Spread'] if match else 0,
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
        st.dataframe(df.style.format({"PnL": "{:.6f}$", "Entry": "{:.4f}$"}), width='stretch', hide_index=True)
        if st.button("Emergency Close All", width='stretch'): st.session_state.positions = []; st.rerun()
    else: st.warning("No active hedge positions.")

time.sleep(1)
st.rerun()
