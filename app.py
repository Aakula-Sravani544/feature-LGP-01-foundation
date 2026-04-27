import streamlit as st
import pandas as pd
import os
import time
import threading
import queue
from datetime import datetime
from scraper import run_scraper

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="LeadPulse Pro - Enterprise Dashboard",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium UI Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; border: 1px solid #f0f0f0; }
    .log-terminal { background: #0f172a; color: #10b981; padding: 15px; border-radius: 8px; font-family: 'Courier New', monospace; height: 180px; overflow-y: auto; font-size: 0.85rem; }
    .timer-panel { background: white; padding: 20px; border-radius: 15px; border: 2px solid #e2e8f0; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1055/1055644.png", width=60)
    st.title("LeadPulse Pro")
    st.markdown("---")
    role = st.selectbox("Switch Workspace", ["User Dashboard", "Client Dashboard"], index=0)
    st.markdown("---")
    st.success("✅ Day 1 Status: Complete")
    st.success("✅ Day 2 Status: Complete")
    st.info("Performance Engine: Active")

# ==========================================
# UTILITIES
# ==========================================
def format_time(seconds):
    return time.strftime("%M:%S", time.gmtime(max(0, seconds)))

def get_leads_df():
    if os.path.exists("day2_leads.csv"):
        return pd.read_csv("day2_leads.csv")
    return None

def render_timer(elapsed):
    max_allowed = 600
    remaining = max_allowed - elapsed if elapsed < max_allowed else 0
    color = "#10b981" if elapsed < max_allowed else "#ef4444"
    bg = "#ecfdf5" if elapsed < max_allowed else "#fef2f2"
    
    timer_html = f"""
    <div style="background: {bg}; padding: 20px; border-radius: 15px; border: 2px solid {color}; text-align: center;">
        <h3 style="color: {color}; margin: 0; font-size: 1.1rem;">🕒 Production Performance Monitor</h3>
        <div style="display: flex; justify-content: space-around; margin-top: 15px;">
            <div><small style="color: #64748b;">Elapsed</small><br><b style="font-size: 1.5rem;">{format_time(elapsed)}</b></div>
            <div><small style="color: #64748b;">Remaining</small><br><b style="font-size: 1.5rem; color: {color};">{format_time(remaining)}</b></div>
            <div><small style="color: #64748b;">Max Allowed</small><br><b style="font-size: 1.5rem;">10:00</b></div>
        </div>
        {f'<div style="color: #ef4444; font-weight: bold; margin-top: 10px;">⚠️ Optimization required - exceeded target time</div>' if elapsed >= max_allowed else ''}
    </div>
    """
    return timer_html

# ==========================================
# USER DASHBOARD
# ==========================================
if role == "User Dashboard":
    st.title("User Dashboard 🚀")
    
    # Clickable Stats Cards
    leads_df = get_leads_df()
    total_leads = len(leads_df) if leads_df is not None else 0
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.button(f"📊 Current Leads\n{total_leads}", use_container_width=True)
    with c2: st.button("⚡ Efficiency\nHigh Speed", use_container_width=True)
    with c3: st.button("💎 Data Quality\nVerified", use_container_width=True)
    with c4: st.button("🛡️ Status\nOptimized", use_container_width=True)

    st.divider()

    # Search Section
    col_in, col_btn = st.columns([4, 1])
    with col_in:
        query = st.text_input("Search Keyword", placeholder="e.g., IT Companies Chennai", label_visibility="collapsed")
    with col_btn:
        run_btn = st.button("Generate Leads", use_container_width=True, type="primary")

    if run_btn:
        if query:
            log_queue = queue.Queue()
            res_box = {"leads": [], "total": 0, "err": None}
            
            def scrape_thread():
                try:
                    res_box["leads"], res_box["total"] = run_scraper(query, log_queue)
                except Exception as e:
                    res_box["err"] = str(e)

            thread = threading.Thread(target=scrape_thread)
            thread.start()
            
            # UI Placeholders
            timer_p = st.empty()
            progress_p = st.empty()
            log_p = st.empty()
            
            start_time = time.time()
            logs = []
            
            while thread.is_alive():
                elapsed = time.time() - start_time
                
                # Drain logs
                while not log_queue.empty():
                    msg = log_queue.get()
                    logs.append(f"[{format_time(time.time()-start_time)}] {msg}")
                
                # Update UI
                timer_p.markdown(render_timer(elapsed), unsafe_allow_html=True)
                log_p.markdown(f'<div class="log-terminal">{"<br>".join(logs[-10:])}</div>', unsafe_allow_html=True)
                progress_p.progress(min(int(elapsed/600 * 100), 100))
                
                time.sleep(1)
            
            # Finalize
            duration = time.time() - start_time
            if res_box["leads"]:
                st.success(f"Day 2 Completed Successfully! Generated {len(res_box['leads'])} leads in {format_time(duration)}")
                
                # Stats Summary
                s1, s2, s3 = st.columns(3)
                s1.metric("Total Leads Generated", len(res_box["leads"]))
                s2.metric("Total Time Taken", format_time(duration))
                s3.metric("Leads Per Minute", round(len(res_box["leads"])/(duration/60), 1))
                
                st.balloons()
                st.rerun()
            elif res_box["err"]:
                st.error(f"Scraper Error: {res_box['err']}")
            else:
                st.warning("No results found or process stopped.")
        else:
            st.warning("Enter a keyword first.")

    # Data Display
    if leads_df is not None:
        st.subheader("Extracted Results")
        st.dataframe(leads_df, use_container_width=True, hide_index=True)
        st.download_button("📥 Download CSV", data=leads_df.to_csv(index=False).encode('utf-8-sig'), file_name="day2_leads.csv", mime="text/csv")

# ==========================================
# CLIENT DASHBOARD
# ==========================================
else:
    st.title("Client Dashboard 💎")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Leads", "1,520")
    m2.metric("Searches Today", "42")
    m3.metric("User Count", "12")
    m4.metric("Status", "Online")
    st.divider()
    st.subheader("Global Search Trends")
    st.line_chart(pd.DataFrame({"Searches": [10, 25, 15, 40, 35, 50]}, index=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]))

st.markdown("---")
st.caption("LeadPulse Pro v1.4 | Performance Production Engine")
