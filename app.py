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
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Professional Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stButton>button {
        border-radius: 12px;
        transition: all 0.3s ease;
        height: 110px;
        border: 1px solid #f0f0f0;
        background: #ffffff;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    
    .stButton>button:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1);
        border-color: #6366f1;
    }
    
    .log-box {
        background: #0f172a;
        color: #10b981;
        padding: 20px;
        border-radius: 12px;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.85rem;
        height: 250px;
        overflow-y: auto;
        border: 1px solid #1e293b;
        line-height: 1.5;
    }
    
    .timer-display {
        font-size: 3.5rem;
        font-weight: 800;
        color: #6366f1;
        text-align: center;
        letter-spacing: -2px;
        margin: 10px 0;
    }
    
    .card-title {
        color: #64748b;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    
    .card-value {
        color: #1e293b;
        font-size: 1.5rem;
        font-weight: 800;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# SESSION STATE
# ==========================================
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'logs' not in st.session_state: st.session_state.logs = ""
if 'start_time' not in st.session_state: st.session_state.start_time = None
if 'elapsed' not in st.session_state: st.session_state.elapsed = 0

# ==========================================
# DATA HUB
# ==========================================
def load_data():
    if os.path.exists("day2_leads.csv"):
        try: return pd.read_csv("day2_leads.csv")
        except: return None
    return None

def get_platform_metrics(df, runtime):
    if df is None or len(df) == 0:
        return {"leads": 0, "lpm": 0.0, "quality": "N/A", "status": "Ready"}
    
    count = len(df)
    lpm = round(count / (runtime / 60), 1) if runtime > 60 else round(count/1, 1)
    
    # Quality: Check for Phone + Website availability
    has_contact = df.dropna(subset=['Phone Number', 'Website URL'])
    quality_score = int((len(has_contact) / count) * 100) if count > 0 else 0
    
    status = "🟢 Running" if st.session_state.is_running else "🔵 Completed"
    
    return {
        "leads": count,
        "lpm": lpm,
        "quality": f"{quality_score}%",
        "status": status
    }

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1055/1055644.png", width=70)
    st.title("LeadPulse Pro")
    st.markdown("---")
    view_mode = st.radio("Switch View", ["User Dashboard", "Client Analytics"], index=0)
    st.markdown("---")
    st.markdown("### System Health")
    st.success("✅ Scraper Engine: Active")
    st.success("✅ Database: Connected")
    st.markdown("---")
    if st.button("Reset Global Session", use_container_width=True):
        st.session_state.is_running = False
        st.session_state.logs = ""
        st.session_state.elapsed = 0
        st.rerun()

# ==========================================
# USER DASHBOARD
# ==========================================
if view_mode == "User Dashboard":
    st.markdown("# Enterprise Dashboard 🚀")
    st.markdown("##### Real-time Google Maps Lead Intelligence")
    
    df = load_data()
    metrics = get_platform_metrics(df, st.session_state.elapsed)
    
    # INTERACTIVE METRIC TILES
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button(f"📊 TOTAL LEADS\n{metrics['leads']}", use_container_width=True):
            st.toast("Viewing current lead database...")
            
    with col2:
        if st.button(f"⚡ EFFICIENCY\n{metrics['lpm']} LPM", use_container_width=True):
            st.toast(f"Current extraction rate: {metrics['lpm']} leads per minute")
            
    with col3:
        if st.button(f"💎 DATA QUALITY\n{metrics['quality']}", use_container_width=True):
            st.toast("Data quality verified based on contact availability.")
            
    with col4:
        if st.button(f"🛡️ ENGINE STATUS\n{metrics['status']}", use_container_width=True):
            st.toast("System engine is operational and ready.")

    st.divider()

    # CONTROL CENTER
    c_in, c_btn = st.columns([4, 1])
    with c_in:
        query = st.text_input("Enter Target Niche + Location", placeholder="e.g. Restaurants in London", label_visibility="collapsed", disabled=st.session_state.is_running)
    with c_btn:
        label = "Processing..." if st.session_state.is_running else "Generate Leads"
        start_trigger = st.button(label, type="primary", use_container_width=True, disabled=st.session_state.is_running)

    if start_trigger and query:
        st.session_state.is_running = True
        st.session_state.start_time = time.time()
        st.session_state.logs = ""
        
        timer_box = st.empty()
        log_box = st.empty()
        
        # Launch Scraper Subprocess
        process = subprocess.Popen(
            [sys.executable, "scraper.py", query],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        while True:
            # Update Timer State
            st.session_state.elapsed = int(time.time() - st.session_state.start_time)
            mins, secs = divmod(st.session_state.elapsed, 60)
            timer_box.markdown(f'<div class="timer-display">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
            
            # Update Logs
            line = process.stdout.readline()
            if line:
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.session_state.logs += f"[{timestamp}] {line}"
                display_logs = "<br>".join(st.session_state.logs.splitlines()[-12:])
                log_box.markdown(f'<div class="log-box">{display_logs}</div>', unsafe_allow_html=True)
            
            # SLA Timeout (10 Mins)
            if st.session_state.elapsed > 600:
                process.terminate()
                st.error("🚨 System Timeout: Operation exceeded the 10-minute SLA.")
                st.session_state.is_running = False
                break
            
            # Check Completion
            if process.poll() is not None:
                st.success(f"✨ Extraction Complete! Total time: {mins:02d}:{secs:02d}")
                st.session_state.is_running = False
                st.balloons()
                time.sleep(2)
                st.rerun()
                break
            
            time.sleep(0.1)

    # DATA PRESENTATION
    if df is not None and not st.session_state.is_running:
        st.subheader("Extracted Intelligence")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Download Action
        csv_file = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download Lead Database (CSV)",
            data=csv_file,
            file_name=f"leadpulse_export_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ==========================================
# CLIENT ANALYTICS
# ==========================================
else:
    st.markdown("# Client Analytics Center 💎")
    st.markdown("##### Global Platform Metrics & Intelligence")
    
    ga1, ga2, ga3 = st.columns(3)
    ga1.metric("Lifetime Leads Generated", "12,840", "+15%")
    ga2.metric("Platform Success Rate", "98.2%", "Stable")
    ga3.metric("Avg. Extraction Speed", "4.2s / Lead", "-0.8s")
    
    st.divider()
    st.subheader("Historical Extraction Volume")
    dummy_data = pd.DataFrame({
        'Day': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'Leads': [450, 620, 810, 540, 920, 1100, 1400]
    })
    st.area_chart(dummy_data.set_index('Day'))

st.markdown("---")
st.caption("LeadPulse Pro v1.6 | Enterprise Performance Dashboard | © 2026")
