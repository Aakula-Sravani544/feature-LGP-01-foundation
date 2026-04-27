import streamlit as st
import pandas as pd
import os
import time
import subprocess
import sys
from datetime import datetime

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="LeadPulse Pro - Enterprise Dashboard",
    page_icon="🚀",
    layout="wide"
)

# Custom Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stButton>button { border-radius: 10px; transition: all 0.3s; height: 100px; }
    .stButton>button:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
    .log-container { background: #1e1e1e; color: #32cd32; padding: 15px; border-radius: 8px; height: 300px; overflow-y: auto; font-family: monospace; font-size: 0.85rem; border: 1px solid #333; }
    .timer-val { font-size: 3rem; font-weight: 800; color: #6366f1; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'logs' not in st.session_state: st.session_state.logs = ""
if 'start_time' not in st.session_state: st.session_state.start_time = None
if 'elapsed_time' not in st.session_state: st.session_state.elapsed_time = 0
if 'current_view' not in st.session_state: st.session_state.current_view = "Table"

# ==========================================
# DATA UTILITIES
# ==========================================
def get_leads_df():
    if os.path.exists("day2_leads.csv"):
        try: return pd.read_csv("day2_leads.csv")
        except: return None
    return None

def calculate_metrics(df, duration):
    if df is None or len(df) == 0:
        return {"count": 0, "lpm": 0.0, "quality": 0}
    
    count = len(df)
    lpm = round(count / (duration / 60), 1) if duration > 0 else 0.0
    
    # Quality: Has Phone AND Website
    quality_rows = df.dropna(subset=['Phone Number', 'Website URL'])
    quality_pct = int((len(quality_rows) / count) * 100) if count > 0 else 0
    
    return {"count": count, "lpm": lpm, "quality": quality_pct}

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1055/1055644.png", width=60)
    st.title("LeadPulse Pro")
    st.divider()
    role = st.radio("Access Level", ["User Dashboard", "Client Dashboard"])
    st.divider()
    st.info(f"System: {'🟢 Running' if st.session_state.is_running else '⚪ Idle'}")
    if st.button("Reset Session"):
        st.session_state.is_running = False
        st.session_state.logs = ""
        st.rerun()

# ==========================================
# MAIN DASHBOARD (USER)
# ==========================================
if role == "User Dashboard":
    st.title("Enterprise Dashboard 💎")
    
    df = get_leads_df()
    metrics = calculate_metrics(df, st.session_state.elapsed_time)
    
    # CLICKABLE CARDS
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button(f"📊 Current Leads\n{metrics['count']}", use_container_width=True):
            st.session_state.current_view = "Table"
    with c2:
        if st.button(f"⚡ Efficiency\n{metrics['lpm']} LPM", use_container_width=True):
            st.info("Efficiency: Leads Generated Per Minute during the last run.")
    with c3:
        if st.button(f"💎 Data Quality\n{metrics['quality']}%", use_container_width=True):
            st.info("Data Quality: Percentage of leads with complete phone and website info.")
    with c4:
        status_txt = "Active" if st.session_state.is_running else "Ready"
        if st.button(f"🛡️ Status\n{status_txt}", use_container_width=True):
            st.info("System Status: Checks if the scraping engine is currently engaged.")

    st.divider()

    # SEARCH & GENERATE
    col_q, col_b = st.columns([4, 1])
    with col_q:
        query = st.text_input("Target Keyword", placeholder="e.g., Dentists Bangalore", label_visibility="collapsed", disabled=st.session_state.is_running)
    with col_b:
        btn_label = "Scraping..." if st.session_state.is_running else "Generate Leads"
        start_btn = st.button(btn_label, type="primary", use_container_width=True, disabled=st.session_state.is_running)

    # PROCESS EXECUTION
    if start_btn and query:
        st.session_state.is_running = True
        st.session_state.start_time = time.time()
        st.session_state.logs = ""
        st.session_state.elapsed_time = 0
        
        timer_placeholder = st.empty()
        log_placeholder = st.empty()
        
        # Execute Scraper
        # Use sys.executable to ensure we use the same environment
        process = subprocess.Popen(
            [sys.executable, "scraper.py", query],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # MONITORING LOOP
        while True:
            # Update Timer
            st.session_state.elapsed_time = int(time.time() - st.session_state.start_time)
            mm = st.session_state.elapsed_time // 60
            ss = st.session_state.elapsed_time % 60
            timer_placeholder.markdown(f'<div class="timer-val">{mm:02d}:{ss:02d}</div>', unsafe_allow_html=True)
            
            # Read Logs
            line = process.stdout.readline()
            if line:
                st.session_state.logs += f"{datetime.now().strftime('%H:%M:%S')} | {line}"
                # Limit logs for performance
                lines = st.session_state.logs.splitlines()[-15:]
                log_placeholder.markdown(f'<div class="log-container">{"<br>".join(lines)}</div>', unsafe_allow_html=True)
            
            # Timeout Check (10 mins = 600s)
            if st.session_state.elapsed_time > 600:
                process.terminate()
                st.error("❌ Critical Timeout: Process terminated after 10 minutes.")
                st.session_state.is_running = False
                break
                
            # Process Completion
            if process.poll() is not None:
                st.success(f"✅ Generation Completed in {mm:02d}:{ss:02d}!")
                st.session_state.is_running = False
                st.balloons()
                time.sleep(2)
                st.rerun()
                break
            
            time.sleep(0.1) # Small delay to prevent UI lockup

    # DISPLAY RESULTS
    if df is not None and not st.session_state.is_running:
        st.subheader("Live Results")
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Download Lead Database (CSV)", data=csv, file_name="day2_leads.csv", mime="text/csv", use_container_width=True)

# ==========================================
# MAIN DASHBOARD (CLIENT)
# ==========================================
else:
    st.title("Client Analytics Dashboard 📈")
    st.markdown("### Global Platform Performance")
    
    # Mock Global Analytics
    ga1, ga2, ga3 = st.columns(3)
    ga1.metric("Total Platform Leads", "18,420", "+12%")
    ga2.metric("System Uptime", "99.9%", "Stable")
    ga3.metric("API Efficiency", "240ms", "-15ms")
    
    st.divider()
    st.subheader("Global Search Volume")
    chart_data = pd.DataFrame({
        'Date': pd.date_range(start='2026-04-01', periods=7),
        'Searches': [120, 150, 180, 140, 210, 250, 300]
    })
    st.line_chart(chart_data.set_index('Date'))

# ==========================================
# FOOTER
# ==========================================
st.divider()
st.caption("LeadPulse Pro v1.5 | Enterprise Edition | © 2026")
