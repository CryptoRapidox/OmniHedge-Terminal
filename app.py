# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# --- 1. AYARLAR ---
st.set_page_config(page_title="PacificHedge v35.0", page_icon="🚀", layout="wide")

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

# --- 2. BAKIYE SORGULAMA MOTORU ---
def get_account_balance(exchange, identifier1, identifier2=None):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        if exchange == "Reya" and identifier1:
            res = requests.get(f"https://api.reya.xyz/v2/wallet/{identifier1}/accountBalances", timeout=2).json()
            if isinstance(res, list):
                return sum(float(b.get("realBalance", 0)) for b in res if b.get("asset") == "RUSD")
                
        elif exchange == "Pacifica" and identifier1:
            res = requests.get(f"https://api.pacifica.fi/api/v1/wallet/{identifier1}/balances", headers=headers, timeout=2).json()
            if res.get("success"):
                return float(res.get("data", {}).get("available_balance", 0))
                
        elif exchange == "Lighter" and identifier1:
            res = requests.get(f"https://mainnet.zklighter.elliot.ai/api/v1/accounts/{identifier1}/balances", timeout=2).json()
            if isinstance(res, list):
                return sum(float(b.get("balance", 0)) for b in res if b.get("currency") == "USDC")
                
    except Exception as e:
        return None 
    return None

# --- 3. SIDEBAR (API & CÜZDAN YÖNETİMİ) ---
st.sidebar.header("⚙️ API & Wallet Config")

with st.sidebar.expander("🌊 Pacifica Config", expanded=False):
    pac_addr = st.text_input("Wallet Address", key="pac_addr")
    pac_key = st.text_input("API Key / Signature", type="password", key="pac_key")
    if pac_addr:
        bal = get_account_balance("Pacifica", pac_addr)
        if bal is not None: st.success(f"✅ Connected | Balance: **${bal:,.2f}**")
        else: st.warning("⚠️ Syncing or Invalid Address")

with st.sidebar.expander("⚡ Reya Config", expanded=False):
    reya_addr = st.text_input("Wallet Address", key="reya_addr")
    reya_key = st.text_input("API / Private Key", type="password", key="reya_key")
    if reya_addr:
        bal = get_account_balance("Reya", reya_addr)
        if bal is not None: st.success(f"✅ Connected | Balance: **${bal:,.2f}**")
        else: st.warning("⚠️ Syncing or Invalid Address")

with st.sidebar.expander("🔥 Lighter Config", expanded=False):
    lig_addr = st.text_input("Wallet Address", key="lig_addr")
    lig_key = st.text_input("API Key", type="password", key="lig_key")
    if lig_addr:
        bal = get_account_balance("Lighter", lig_addr)
        if bal is not None: st.success(f"✅ Connected | Balance: **${bal:,.2f}**")
        else: st.warning("⚠️ Syncing or Invalid Address")

with st.sidebar.expander("🌌 Variational Config", expanded=False):
    st.info("ℹ️ Variational resmi dokümanlarına göre Trading API henüz aktif değildir (Development aşamasında). Bakiye okuma şu an desteklenmiyor.")

# --- 4. KUSURSUZ CANLI VERİ MOTORU ---
@st.cache_data(ttl=1)
def fetch_terminal_data():
    res = {
        "Variational": {}, "Pacifica": {}, "Reya": {}, "Lighter": {}, 
        "Prices": {}, "Status": {},
        "SourcePrices": {"Pacifica": 0.0, "Variational": 0.0, "Reya": 0.0, "Lighter": 0.0} 
    }
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        p_res = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=2).json()
        res["Prices"] = {item['symbol'].replace('USDT', ''): float(item['price']) for item in p_res if 'USDT' in item['symbol']}
    except: pass

    try:
        p_data = requests.get("https://api.pacifica.fi/api/v1/info/prices", headers=headers, timeout=2).json()
        if p_data.get("success"):
            for i in p_data.get("data", []):
                sym = i.get("symbol", "").split("-")[0].upper()
                funding_val = float(i.get("funding") or 0)
                if funding_val != 0: res["Pacifica"][sym] = funding_val * 24 * 365 * 100
                price = float(i.get("mark") or i.get("oracle") or 0)
                if price > 0: res["Prices"][sym] = price
                if sym.startswith("BTC"): res["SourcePrices"]["Pacifica"] = price
    except: pass

    # VARIATIONAL DÜZELTMESİ (DOKÜMANA BİREBİR UYGUN)
    try:
        v_data = requests.get("https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/stats", timeout=2).json()
        if "listings" in v_data:
            for i in v_data["listings"]:
                t = i.get("ticker", "").split("-")[0].upper()
                funding_val = float(i.get("funding_rate", 0))
                interval_s = float(i.get("funding_interval_s", 28800)) # Saniye cinsinden aralık
                
                if funding_val != 0 and interval_s > 0: 
                    # Bir yıldaki saniye (31536000) / interval = Yılda kaç kez fonlama kestiği
                    # Formül: Oran * (Yıllık Kesim Sayısı) * 100 = Yıllık APY
                    res["Variational"][t] = funding_val * (31536000 / interval_s) * 100
                
                # FİYAT İÇİN last_price DEĞİL, DOKÜMANDAKİ mark_price KULLANILDI
                price = float(i.get("mark_price", 0))
                if price > 0: res["Prices"][t] = price
                if t.startswith("BTC"): res["SourcePrices"]["Variational"] = price
    except: pass

    try:
        r_data = requests.get("https://api.reya.xyz/v2/markets/summary", timeout=2).json()
        for m in r_data:
            s_raw = m.get("symbol", "")
            s = s_raw.replace("RUSDPERP", "").replace("PERP", "").split("-")[0].upper()
            if s.startswith('K') and len(s) > 1: s = s[1:]
            funding_val = float(m.get("fundingRate", "0"))
            if funding_val != 0: res["Reya"][s] = funding_val * 24 * 365 * 100
            price = float(m.get("throttledPoolPrice", 0))
            if price > 0: res["Prices"][s] = price
            if s_raw.upper().startswith("BTC"): res["SourcePrices"]["Reya"] = price
    except: pass

    try:
        l_res = requests.get("https://mainnet.zklighter.elliot.ai/api/v1/markets", timeout=2).json()
        for i in l_res:
            s_raw = i.get("symbol", "")
            s = s_raw.replace("-PERP", "").replace("-USD", "").split("-")[0].upper()
            funding_val = float(i.get("funding_rate", 0))
            if funding_val != 0: res["Lighter"][s] = funding_val * 100
            price = float(i.get("last_price") or i.get("price") or 0)
            if price > 0: res["Prices"][s] = price
            if s_raw.upper().startswith("BTC"): res["SourcePrices"]["Lighter"] = price
    except: pass

    return res

# --- 5. GÜNLÜK DELTA-NEUTRAL MATEMATİĞİ ---
data = fetch_terminal_data()
target_tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'HYPE', 'ADA', 'PAXG', 'AAVE', 'TAO', 'AVAX', 'BNB', 'SUI', 'ENA', 'PUMP', 'BERA', 'IP', 'INJ', 'DOGE', 'VIRTUAL', 'ARB', 'TRUMP', 'LDO', 'LTC', 'EIGEN', 'AERO', 'SEI', 'ZRO', 'TIA', 'TRX', 'UNI', 'PENDLE', 'PEPE', 'ME', 'MOVE', 'WLFI', 'GRASS', 'JUP', 'SHIB', 'JTO', 'TON', 'KAITO', 'CRV', 'LINEA', 'XPL', 'PENGU', 'ONDO', 'NEIRO', 'GOAT', 'NEAR', 'WLD', 'POPCAT', 'LINK', 'SYRUP', 'AI16Z', 'APT', 'PROVE', 'BONK', 'MORPHO', 'S', 'PYTH', 'XAU', 'XAG', 'PLTR', 'NVDA', 'ZEC', 'BCH', 'EURUSD', 'MEGA', 'TSLA', 'PIPPIN']

signals = []
for t in target_tokens:
    pac_apr = data["Pacifica"].get(t)
    price = data["Prices"].get(t, 0.0)
    
    if pac_apr is not None and pac_apr != 0 and price > 0:
        comparisons = {"Var": data["Variational"].get(t), "Rey": data["Reya"].get(t), "Lig": data["Lighter"].get(t)}
        best_net_apr = 0
        best_s_l = None
        best_l_l = None
        
        for ex_name, ex_apr in comparisons.items():
            if ex_apr is not None and ex_apr != 0:
                profit_s1_apr = (pac_apr * 1) + (ex_apr * -1)
                profit_s2_apr = (pac_apr * -1) + (ex_apr * 1)
                
                if profit_s1_apr > best_net_apr and profit_s1_apr >= 7.0:
                    best_net_apr = profit_s1_apr
                    best_s_l, best_l_l = "Pac", ex_name
                    
                if profit_s2_apr > best_net_apr and profit_s2_apr >= 7.0:
                    best_net_apr = profit_s2_apr
                    best_s_l, best_l_l = ex_name, "Pac"
                    
        if 7.0 <= best_net_apr <= 3650.0:
            daily_net_profit = best_net_apr / 365
            signals.append({"Token": t, "Profit": daily_net_profit, "Short": best_s_l, "Long": best_l_l, "Price": price})

signals = sorted(signals, key=lambda x: x['Profit'], reverse=True)

# --- 6. ARAYÜZ ---
st.title("🚀 PacificHedge Terminal")

st.subheader("📊 Live BTC Price Monitoring")
p_col1, p_col2, p_col3, p_col4 = st.columns(4)
sp = data["SourcePrices"] 

p_col1.metric("Pacifica BTC", f"${sp['Pacifica']:,.2f}" if sp['Pacifica'] > 0 else "Syncing...")
p_col2.metric("Variational BTC", f"${sp['Variational']:,.2f}" if sp['Variational'] > 0 else "Syncing...")
p_col3.metric("Reya BTC", f"${sp['Reya']:,.2f}" if sp['Reya'] > 0 else "Syncing...")
p_col4.metric("Lighter BTC", f"${sp['Lighter']:,.2f}" if sp['Lighter'] > 0 else "Syncing...")

st.divider()

if signals:
    best_trade = signals[0]
    st.success(f"💡 **PacificHedge Advisor:** Şu anki en mantıklı işlem **{best_trade['Token']}**! "
               f"**{best_trade['Short']}** borsasında SHORT, "
               f"**{best_trade['Long']}** borsasında LONG açarak **24 Saatte Net %{best_trade['Profit']:.3f}** kâr elde edebilirsiniz.")
else:
    st.info("💡 **PacificHedge Advisor:** Şu an Pacifica merkezli risk-free (günlük net %0.02 üzeri) kârlı bir işlem bulunmuyor. Gerçekçi piyasa taranıyor...")

st.divider()

c_radar, c_exec = st.columns([1.3, 1.2])

with c_radar:
    st.subheader("📡 Pacifica-Centric Radar (Gerçek 24s Kâr)")
    if signals:
        for s in signals:
            btn_label = f"🔔 {s['Token']} | 24s Net: %{s['Profit']:.3f} | ${s['Price']:.2f}"
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
    if st.session_state.positions:
        for pos in st.session_state.positions:
            elapsed = time.time() - pos['Time']
            pos['PnL'] = (pos['Profit'] / 100 / 86400) * elapsed * pos['Size']
        
        df = pd.DataFrame(st.session_state.positions)[['Token', 'Size', 'Entry', 'DisplayTime', 'PnL']]
        st.dataframe(df.style.format({"PnL": "{:.6f}$", "Entry": "{:.4f}$"}), width='stretch', hide_index=True)
        if st.button("Emergency Close All", width='stretch'): st.session_state.positions = []; st.rerun()

time.sleep(1)
st.rerun()
