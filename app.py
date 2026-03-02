# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# --- 1. AYARLAR ---
st.set_page_config(page_title="PacificHedge v28.0", page_icon="🚀", layout="wide")

if 'positions' not in st.session_state: st.session_state.positions = []
if 'selected_token' not in st.session_state: st.session_state.selected_token = "BTC"

st.markdown("""
    <style>
    .main { background-color: #0b0e11; }
    .main::before {
        content: "pacific_hedge_";
        position: fixed; top: 50%; left: 50%;
        transform: translate(-50%, -50%) rotate(-25deg);
        font-size: 10vw; color: rgba(255, 255, 255, 0.02);
        z-index: 0; pointer-events: none; white-space: nowrap; font-weight: bold;
    }
    .stMetric { background-color: #1e2329; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR CONFIG ---
st.sidebar.header("⚙️ Terminal Config")
TRADE_AMOUNT_USD = st.sidebar.number_input("Hedge Amount per Leg ($)", min_value=10.0, value=100.0)

with st.sidebar.expander("🔑 API Credentials", expanded=True):
    p_addr = st.text_input("Pacifica Wallet", type="password", key="p_v28")
    v_key = st.text_input("Variational Key", type="password", key="v_v28")
    if p_addr: st.success("✅ Connected")

# --- 3. MODÜLER VERİ MOTORU (APR NORMALIZER EKLENDİ) ---
@st.cache_data(ttl=10)
def fetch_terminal_data():
    res = {
        "Variational": {}, "Pacifica": {}, "Reya": {}, "Lighter": {}, 
        "Prices": {}, "Status": {}, 
        "SourcePrices": {"Pacifica": 0.0, "Variational": 0.0, "Reya": 0.0, "Lighter": 0.0}
    }
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # Çarpanlar (Elmaları ve Armutları Yıllık % APR'de eşitlemek için)
    HOURLY_TO_APR = 24 * 365 * 100
    ANNUAL_TO_APR = 100

    # 1. Binance
    try:
        p_res = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=3).json()
        res["Prices"] = {item['symbol'].replace('USDT', ''): float(item['price']) for item in p_res if 'USDT' in item['symbol']}
    except: res["Status"]["Binance"] = "🔴"

    # 2. Pacifica (Saatlik veriyi Yıllık APR'ye çeviriyoruz)
    try:
        p_data = requests.get("https://api.pacifica.fi/api/v1/info/prices", headers=headers, timeout=5).json()
        if p_data.get("success"):
            for i in p_data.get("data", []):
                sym = i.get("symbol", "").split("-")[0].upper() # BTC-PERP gelse bile BTC yapar
                # NORMALİZASYON: Pacifica ham verisi -> Yıllık % APR
                res["Pacifica"][sym] = float(i.get("funding") or 0) * HOURLY_TO_APR
                
                price = float(i.get("mark") or i.get("oracle") or 0)
                if sym not in res["Prices"] or res["Prices"][sym] == 0: res["Prices"][sym] = price
                if sym == "BTC": res["SourcePrices"]["Pacifica"] = price
    except: res["Status"]["Pacifica"] = "🔴"

    # 3. Variational (Zaten Yıllık geliyor, sadece 100 ile %'ye çeviriyoruz)
    try:
        v_data = requests.get("https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/stats", timeout=5).json()
        if v_data.get("listings"):
            for i in v_data.get("listings", []):
                t = i.get("ticker", "").split("-")[0].upper()
                res["Variational"][t] = float(i.get("funding_rate", 0)) * ANNUAL_TO_APR
                
                price = float(i.get("last_price", 0))
                if t not in res["Prices"] or res["Prices"][t] == 0: res["Prices"][t] = price
                if t == "BTC": res["SourcePrices"]["Variational"] = price
    except: pass

    # 4. Reya (Saatlik/8 Saatlik -> Yıllık % APR)
    try:
        r_data = requests.get("https://api.reya.xyz/v2/markets/summary", timeout=5).json()
        for m in r_data:
            s_raw = m.get("symbol", "")
            s = s_raw.replace("RUSDPERP", "").replace("PERP", "").split("-")[0].upper()
            if s.startswith('K') and len(s) > 1: s = s[1:]
            
            res["Reya"][s] = float(m.get("fundingRate", "0")) * HOURLY_TO_APR
            
            price = float(m.get("markPrice", 0))
            if s not in res["Prices"] or res["Prices"][s] == 0: res["Prices"][s] = price
            if s == "BTC" or "BTC" in s_raw.upper(): res["SourcePrices"]["Reya"] = price
    except: pass

    # 5. Lighter (Saatlik -> Yıllık % APR)
    try:
        l_res = requests.get("https://mainnet.zklighter.elliot.ai/api/v1/markets", timeout=5).json()
        for i in l_res:
            s_raw = i.get("symbol", "")
            s = s_raw.replace("-PERP", "").replace("-USD", "").split("-")[0].upper()
            
            res["Lighter"][s] = float(i.get("funding_rate", 0)) * HOURLY_TO_APR
            
            price = float(i.get("last_price") or i.get("price") or 0)
            if s not in res["Prices"] or res["Prices"][s] == 0: res["Prices"][s] = price
            if s == "BTC" or "BTC" in s_raw.upper(): res["SourcePrices"]["Lighter"] = price
    except: pass

    return res

# --- 4. KUSURSUZ APR FUNDING MATEMATİĞİ (DELTA-NEUTRAL) ---
data = fetch_terminal_data()
target_tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'HYPE', 'ADA', 'PAXG', 'AAVE', 'TAO', 'AVAX', 'BNB', 'SUI', 'ENA', 'PUMP', 'BERA', 'IP', 'INJ', 'DOGE', 'VIRTUAL', 'ARB', 'TRUMP', 'LDO', 'LTC', 'EIGEN', 'AERO', 'SEI', 'ZRO', 'TIA', 'TRX', 'UNI', 'PENDLE', 'PEPE', 'ME', 'MOVE', 'WLFI', 'GRASS', 'JUP', 'SHIB', 'JTO', 'TON', 'KAITO', 'CRV', 'LINEA', 'XPL', 'PENGU', 'ONDO', 'NEIRO', 'GOAT', 'NEAR', 'WLD', 'POPCAT', 'LINK', 'SYRUP', 'AI16Z', 'APT', 'PROVE', 'BONK', 'MORPHO', 'S', 'PYTH', 'XAU', 'XAG', 'PLTR', 'NVDA', 'ZEC', 'BCH', 'EURUSD', 'MEGA', 'TSLA', 'PIPPIN']

signals = []
for t in target_tokens:
    pac_apr = data["Pacifica"].get(t)
    price = data["Prices"].get(t, 0.0)
    
    if pac_apr is not None and price > 0:
        comparisons = {
            "Var": data["Variational"].get(t), 
            "Rey": data["Reya"].get(t),
            "Lig": data["Lighter"].get(t)
        }
        
        best_net_profit = 0
        best_s_l = None
        best_l_l = None
        
        for ex_name, ex_apr in comparisons.items():
            if ex_apr is not None:
                # ARTIK HER ŞEY EŞİT MİZANDA (YILLIK APR %)
                # Senaryo 1: Pacifica SHORT (+1), Karşı Borsa LONG (-1)
                profit_s1 = (pac_apr * 1) + (ex_apr * -1)
                
                # Senaryo 2: Pacifica LONG (-1), Karşı Borsa SHORT (+1)
                profit_s2 = (pac_apr * -1) + (ex_apr * 1)
                
                if profit_s1 > best_net_profit and profit_s1 >= 0.1:
                    best_net_profit = profit_s1
                    best_s_l, best_l_l = "Pac", ex_name
                    
                if profit_s2 > best_net_profit and profit_s2 >= 0.1:
                    best_net_profit = profit_s2
                    best_s_l, best_l_l = ex_name, "Pac"
                    
        if best_net_profit >= 0.1:
            signals.append({"Token": t, "Profit": best_net_profit, "Short": best_s_l, "Long": best_l_l, "Price": price})

signals = sorted(signals, key=lambda x: x['Profit'], reverse=True)

# --- 5. ARAYÜZ ---
st.title("🚀 PacificHedge Terminal")

st.subheader("📊 Live BTC Price Monitoring (Multi-DEX)")
p_col1, p_col2, p_col3, p_col4 = st.columns(4)
sp = data["SourcePrices"]

p_col1.metric("Pacifica BTC", f"${sp['Pacifica']:,.2f}" if sp['Pacifica'] > 0 else "Syncing...")
p_col2.metric("Variational BTC", f"${sp['Variational']:,.2f}" if sp['Variational'] > 0 else "Syncing...")
p_col3.metric("Reya BTC", f"${sp['Reya']:,.2f}" if sp['Reya'] > 0 else "Syncing...")
p_col4.metric("Lighter BTC", f"${sp['Lighter']:,.2f}" if sp['Lighter'] > 0 else "Syncing...")

st.divider()

if signals:
    best_trade = signals[0]
    st.success(f"💡 **PacificHedge Advisor:** Şu an en kârlı arbitraj fırsatı **{best_trade['Token']}**! "
               f"**{best_trade['Short']}** borsasında SHORT, "
               f"**{best_trade['Long']}** borsasında LONG açarak **Yıllık Net %{best_trade['Profit']:.2f} APR** kâr elde edebilirsiniz.")
else:
    st.info("💡 **PacificHedge Advisor:** Şu an risk-free kârlı bir işlem bulunmuyor. Piyasa taranmaya devam ediliyor...")

st.divider()

c_radar, c_exec = st.columns([1.3, 1.2])

with c_radar:
    st.subheader("📡 Pacifica-Centric Radar (APR %)")
    if signals:
        for s in signals:
            btn_label = f"🔔 {s['Token']} | Net Yıllık APR: %{s['Profit']:.2f} | ${s['Price']:.2f}"
            if st.button(btn_label, key=f"btn_{s['Token']}", width='stretch'):
                st.session_state.selected_token = s['Token']
    else: st.info("Scanning Market Data...")

with c_exec:
    st.subheader("⚡ Integrated Control Panel")
    sel = st.selectbox("Current Asset", target_tokens, index=target_tokens.index(st.session_state.selected_token))
    cur_p = data["Prices"].get(sel, 0.0)
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
                "Token": sel, "Size": TRADE_AMOUNT_USD, "Entry": cur_p, "Profit": match['Profit'] if match else 0,
                "Time": time.time(), "DisplayTime": datetime.now().strftime("%H:%M:%S")
            })
            st.balloons()

    st.divider()
    st.subheader("💼 Live Positions Tracker")
    if st.session_state.positions:
        for pos in st.session_state.positions:
            elapsed = time.time() - pos['Time']
            pos['PnL'] = (pos['Profit'] / 100 / 86400) * elapsed * pos['Size']
        
        df = pd.DataFrame(st.session_state.positions)[['Token', 'Size', 'Entry', 'DisplayTime', 'PnL']]
        st.dataframe(df.style.format({"PnL": "{:.6f}$", "Entry": "{:.4f}$"}), width='stretch', hide_index=True)
        if st.button("Emergency Close All", width='stretch'): st.session_state.positions = []; st.rerun()
    else: st.warning("No active hedge positions.")

time.sleep(1)
st.rerun()
