import streamlit as st
import pandas as pd
import os
import time
import subprocess
import sys
import json
from datetime import datetime

# ==========================================
# ENTERPRISE UI CONFIG
# ==========================================
st.set_page_config(
    page_title="LeadPulse Pro | SaaS Dashboard",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom SaaS Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #f8fafc; }
    
    .metric-card {
        background: white;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    .metric-label { color: #64748b; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .metric-value { color: #0f172a; font-size: 2.2rem; font-weight: 800; }
    
    .terminal-window {
        background: #0f172a;
        color: #38bdf8;
        padding: 20px;
        border-radius: 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        height: 250px;
        overflow-y: auto;
        border: 1px solid #1e293b;
    }
    </style>
    """, unsafe_allow_html=True)

DB_PATH = 'leads.csv'

def save_to_csv(new_leads):
    if not new_leads: return
    new_df = pd.DataFrame(new_leads)
    cols_to_check = ['Business Name', 'Phone Number']
    if os.path.exists(DB_PATH):
        try:
            old_df = pd.read_csv(DB_PATH)
            merged_df = pd.concat([new_df, old_df], ignore_index=True)
            merged_df = merged_df.drop_duplicates(subset=cols_to_check, keep='first')
        except: merged_df = new_df
    else: merged_df = new_df
    merged_df.to_csv(DB_PATH, index=False, encoding='utf-8-sig')

def load_db():
    if os.path.exists(DB_PATH):
        try:
            df = pd.read_csv(DB_PATH)
            ts_col = next((c for c in ['Timestamp', 'Generated Time', 'Date'] if c in df.columns), None)
            if ts_col:
                df[ts_col] = pd.to_datetime(df[ts_col])
                df = df.sort_values(by=ts_col, ascending=False)
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def get_stats():
    df = load_db()
    if df.empty: return 0, 0, 0
    total = len(df)
    today_str = datetime.now().strftime('%Y-%m-%d')
    ts_col = next((c for c in ['Timestamp', 'Generated Time', 'Date'] if c in df.columns), None)
    if ts_col:
        try:
            today = len(df[pd.to_datetime(df[ts_col]).dt.strftime('%Y-%m-%d') == today_str])
        except: today = total
    else: today = total
    quality = int((len(df.dropna(subset=['Phone Number'])) / total) * 100) if total > 0 else 0
    return total, today, quality

if 'is_scraping' not in st.session_state: st.session_state.is_scraping = False
if 'logs' not in st.session_state: st.session_state.logs = ""
if 'session_leads' not in st.session_state: st.session_state.session_leads = []
if 'session_count' not in st.session_state: st.session_state.session_count = 0

try:
    from google_sheets import is_sheets_connected, save_to_google_sheets
except ImportError:
    def is_sheets_connected(): return False
    def save_to_google_sheets(x): return {}

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1055/1055644.png", width=70)
    st.title("LeadPulse Pro")
    st.markdown("---")
    role = st.selectbox("Switch Workspace", ["User Dashboard", "Admin Dashboard"])
    st.markdown("---")
    st.markdown("### System Status")
    eng_status = "Active" if st.session_state.is_scraping else "Idle"
    st.success(f"Engine: **{eng_status}**")
    if is_sheets_connected(): st.success("🟢 Google Sheets Connected")
    else: st.error("🔴 Offline Mode (CSV Backup)")
    if st.button("Reset Dashboard"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# DASHBOARD
# ==========================================
if role == "User Dashboard":
    st.title("Lead Generation SaaS 🚀")
    
    total_db, total_today, quality_pct = get_stats()
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    c1, c2, c3, c4, c5 = sc1.empty(), sc2.empty(), sc3.empty(), sc4.empty(), sc5.empty()

    def update_cards(t_db, t_td, s_cnt, q_pct, e_st):
        c1.markdown(f'<div class="metric-card"><div class="metric-label">Total Database</div><div class="metric-value">{t_db}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card"><div class="metric-label">Leads Today</div><div class="metric-value">{t_td}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-card"><div class="metric-label">Current Session</div><div class="metric-value">{s_cnt}</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="metric-card"><div class="metric-label">Data Quality</div><div class="metric-value">{q_pct}%</div></div>', unsafe_allow_html=True)
        c5.markdown(f'<div class="metric-card"><div class="metric-label">Engine Status</div><div class="metric-value">{e_st}</div></div>', unsafe_allow_html=True)

    update_cards(total_db, total_today, st.session_state.session_count, quality_pct, eng_status)
    st.divider()

    col_in, col_btn = st.columns([4, 1])
    query = col_in.text_input("Enter Target Niche + Location", placeholder="e.g. Dentists Hyderabad", label_visibility="collapsed")
    
    session_title = st.empty()
    session_table = st.empty()

    if col_btn.button("Generate Leads", type="primary", use_container_width=True, disabled=st.session_state.is_scraping):
        if query:
            st.session_state.is_scraping = True
            st.session_state.session_leads = []
            st.session_state.session_count = 0
            st.session_state.logs = "LOG: Permanent 0-Lead Fix Engine Initializing...\n"
            
            session_title.markdown("### ⚡ Current Session Results (Fresh)")
            session_table.info("Searching Google Maps... please wait.")
            
            log_ph = st.empty()
            
            # Subprocess execution
            process = subprocess.Popen(
                [sys.executable, "scraper.py", query],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True
            )
            
            while True:
                line = process.stdout.readline()
                if line:
                    if line.startswith("DATA:"):
                        try:
                            lead_data = json.loads(line.replace("DATA: ", "").strip())
                            st.session_state.session_leads.append(lead_data)
                            st.session_state.session_count += 1
                            
                            # LIVE UI UPDATE
                            cur_df = pd.DataFrame(st.session_state.session_leads)
                            session_table.dataframe(cur_df.sort_values(by=cur_df.columns[-1], ascending=False), use_container_width=True, hide_index=True)
                            
                            t, td, q = get_stats()
                            update_cards(t, td, st.session_state.session_count, q, "Running")
                        except: pass
                    else:
                        st.session_state.logs += line
                        log_ph.markdown(f'<div class="terminal-window">{"<br>".join(st.session_state.logs.splitlines()[-10:])}</div>', unsafe_allow_html=True)
                
                if process.poll() is not None:
                    # Final Step
                    if st.session_state.session_count == 0:
                        st.error("❌ No fresh leads generated. Check browser debug screenshot or selectors.")
                        if os.path.exists("error_debug.png"):
                            st.image("error_debug.png", caption="Last browser state when 0 leads found")
                    else:
                        # Requirement 9: Force CSV Save
                        save_to_csv(st.session_state.session_leads)
                        if is_sheets_connected():
                            save_to_google_sheets(st.session_state.session_leads)
                        st.success(f"Successfully processed {st.session_state.session_count} leads!")
                    
                    st.session_state.is_scraping = False
                    time.sleep(1)
                    st.rerun()
                    break
        else: st.warning("Please enter a query.")

    # 💎 INTELLIGENCE MASTER DATABASE
    master_df = load_db()
    if not master_df.empty:
        st.subheader("💎 Intelligence Master Database (Latest First)")
        st.dataframe(master_df.head(200), use_container_width=True, hide_index=True)
        st.download_button("📥 Export Master History (CSV)", master_df.to_csv(index=False).encode('utf-8-sig'), "leadpulse_master_history.csv", "text/csv")
    else:
        st.info("Master database is empty. Generate leads to build your history.")

else:
    st.title("Admin Operations Center 🛡️")
    df = load_db()
    st.metric("Total Local Database", len(df))
    st.divider()
    st.dataframe(df, use_container_width=True)

st.markdown("---")
st.caption("LeadPulse Pro v7.2 | 0-Lead Fix Enabled | Submission Ready")
