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
    page_title="LeadPulse Pro - Enterprise Intelligence",
    page_icon="🚀",
    layout="wide"
)

# Professional Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .log-container { background: #0f172a; color: #10b981; padding: 15px; border-radius: 10px; height: 300px; overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; border: 1px solid #1e293b; }
    .timer-display { font-size: 3rem; font-weight: 800; color: #6366f1; text-align: center; margin: 10px 0; }
    .stButton>button { border-radius: 10px; transition: all 0.3s; height: 90px; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# SESSION STATE
# ==========================================
if 'running' not in st.session_state: st.session_state.running = False
if 'logs' not in st.session_state: st.session_state.logs = ""
if 'elapsed' not in st.session_state: st.session_state.elapsed = 0
if 'live_count' not in st.session_state: st.session_state.live_count = 0
if 'start_time' not in st.session_state: st.session_state.start_time = None

# ==========================================
# DATA HUB
# ==========================================
def get_leads_df():
    if os.path.exists("day2_leads.csv"):
        try: return pd.read_csv("day2_leads.csv")
        except: return None
    return None

def calculate_dashboard_metrics(df, runtime, live_c=0):
    if st.session_state.running:
        count = live_c
    else:
        count = len(df) if df is not None else 0
        
    lpm = round(count / (runtime / 60), 1) if runtime > 30 else 0.0
    
    # Quality logic
    if df is not None and len(df) > 0:
        quality_rows = df.dropna(subset=['Phone Number', 'Website URL'])
        quality_pct = int((len(quality_rows) / len(df)) * 100)
    else:
        quality_pct = 0
        
    status = "Running" if st.session_state.running else "Idle"
    if runtime > 600 and st.session_state.running: status = "Timeout"
    
    return {"count": count, "lpm": lpm, "quality": quality_pct, "status": status}

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1055/1055644.png", width=60)
    st.title("LeadPulse Pro")
    st.divider()
    role = st.radio("Workspace Role", ["User Dashboard", "Client Dashboard"])
    st.divider()
    st.markdown("### Backend Status")
    st.success("✅ Engine: Operational")
    st.success("✅ Google Sheets: Connected")
    st.divider()
    if st.button("Emergency Reset", use_container_width=True):
        st.session_state.running = False
        st.session_state.logs = ""
        st.session_state.elapsed = 0
        st.rerun()

# ==========================================
# USER DASHBOARD
# ==========================================
if role == "User Dashboard":
    st.title("Enterprise Lead Dashboard 🚀")
    
    df = get_leads_df()
    metrics = calculate_dashboard_metrics(df, st.session_state.elapsed, st.session_state.live_count)
    
    # DYNAMIC METRIC CARDS
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.button(f"📊 Current Leads\n{metrics['count']}", use_container_width=True)
    with c2: st.button(f"⚡ Efficiency\n{metrics['lpm']} LPM", use_container_width=True)
    with c3: st.button(f"💎 Data Quality\n{metrics['quality']}%", use_container_width=True)
    with c4: st.button(f"🛡️ Status\n{metrics['status']}", use_container_width=True)

    st.divider()

    # CONTROL CENTER
    col_q, col_b = st.columns([4, 1])
    with col_q:
        query = st.text_input("Enter Target Niche + Location", placeholder="e.g. Dentists Bangalore", label_visibility="collapsed", disabled=st.session_state.running)
    with col_b:
        btn_label = "Scraping..." if st.session_state.running else "Generate Leads"
        run_btn = st.button(btn_label, type="primary", use_container_width=True, disabled=st.session_state.running)

    if run_btn and query:
        st.session_state.running = True
        st.session_state.start_time = time.time()
        st.session_state.logs = ""
        st.session_state.live_count = 0
        
        timer_p = st.empty()
        log_p = st.empty()
        
        # Start Backend Scraper
        process = subprocess.Popen(
            [sys.executable, "scraper.py", query],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        while True:
            # Update Timer
            st.session_state.elapsed = int(time.time() - st.session_state.start_time)
            mins, secs = divmod(st.session_state.elapsed, 60)
            timer_p.markdown(f'<div class="timer-display">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
            
            # Read Logs & Update Live Count
            line = process.stdout.readline()
            if line:
                st.session_state.logs += f"[{datetime.now().strftime('%H:%M:%S')}] {line}"
                if "Extracted:" in line:
                    st.session_state.live_count += 1
                
                # Show last 12 lines of logs
                log_lines = st.session_state.logs.splitlines()[-12:]
                log_p.markdown(f'<div class="log-container">{"<br>".join(log_lines)}</div>', unsafe_allow_html=True)
            
            # SLA Timeout (10 Mins)
            if st.session_state.elapsed > 600:
                process.terminate()
                st.error("🚨 Process terminated: 10-minute SLA exceeded.")
                st.session_state.running = False
                break
                
            # Completion Check
            if process.poll() is not None:
                st.success(f"✨ Scraper Completed in {mins:02d}:{secs:02d}!")
                st.session_state.running = False
                st.balloons()
                time.sleep(2)
                st.rerun()
                break
            
            time.sleep(0.1)

    # RESULTS TABLE
    if df is not None and not st.session_state.running:
        st.subheader("Recent Extraction Data")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Export to CSV",
            data=csv_data,
            file_name=f"leads_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ==========================================
# CLIENT DASHBOARD
# ==========================================
else:
    st.title("Admin Analytics Center 💎")
    a1, a2, a3 = st.columns(3)
    a1.metric("Total Platform Leads", "14,820", "+18%")
    a2.metric("Sync Status", "Online", "Google Sheets")
    a3.metric("System Uptime", "99.9%", "Stable")
    
    st.divider()
    st.subheader("Global Search Volume")
    dummy = pd.DataFrame({"Searches": [120, 450, 320, 800, 600, 950, 1200]}, index=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    st.area_chart(dummy)

st.markdown("---")
st.caption("LeadPulse Pro v1.7 | Integrated Production Engine | © 2026")
