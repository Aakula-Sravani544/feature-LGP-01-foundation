# LeadPulse Pro Dashboard - Production v1.1
import streamlit as st
import pandas as pd
import os
import time
from scraper import run_scraper

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="LeadPulse Pro Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1055/1055644.png", width=80)
    st.title("LeadPulse Pro")
    st.markdown("---")
    st.subheader("Project Progress")
    st.success("✅ Day 1: Setup Complete")
    st.success("✅ Day 2: Scraper Ready")
    st.markdown("---")
    st.info("Developed by LeadPulse Team")

# ==========================================
# MAIN INTERFACE
# ==========================================
st.title("LeadPulse Pro Dashboard 🚀")
st.markdown("##### The Ultimate Google Maps Lead Generation Tool")

st.divider()

# Input Section
col1, col2 = st.columns([3, 1])

with col1:
    query = st.text_input(
        "Enter search keyword", 
        placeholder="Example: restaurants hyderabad",
        help="Type keyword followed by location for best results."
    )

with col2:
    st.write("##") # Visual alignment
    run_btn = st.button("Run Scraper", use_container_width=True, type="primary")

# ==========================================
# RUN LOGIC
# ==========================================
if run_btn:
    if query:
        # Progress Tracking
        with st.status("🚀 Initializing Google Maps Scraper...", expanded=True) as status:
            st.write("Setting up browser and anti-detection...")
            
            # Run the scraper function we exposed in scraper.py
            leads, total_loaded = run_scraper(query)
            
            if leads:
                status.update(label="Extraction Complete!", state="complete", expanded=False)
            else:
                status.update(label="Scraping Failed or No Results", state="error", expanded=False)

        if leads:
            st.success("Day 2 Completed Successfully! ✨")
            
            # Metrics Section
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Total Results Found", total_loaded)
            with m2:
                st.metric("Total Leads Saved", len(leads))
            with m3:
                # Calculate duplicates removed
                duplicates = total_loaded - len(leads) if total_loaded > len(leads) else 0
                st.metric("Duplicates Removed", duplicates)
            
            # Data Table
            st.subheader("Data Preview")
            df = pd.DataFrame(leads)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Download Button
            csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Download Lead Data (CSV)",
                data=csv_data,
                file_name="day2_leads.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.error("No results found. Please try a different keyword or location.")
    else:
        st.warning("Please enter a search keyword before running.")

# ==========================================
# RECENT RESULTS (IF EXISTS)
# ==========================================
if os.path.exists("day2_leads.csv") and not run_btn:
    st.divider()
    st.subheader("Previous Scraping Session")
    try:
        df_history = pd.read_csv("day2_leads.csv")
        st.dataframe(df_history.head(10), use_container_width=True, hide_index=True)
        
        # Historical Download Button
        with open("day2_leads.csv", "rb") as f:
            st.download_button(
                label="📥 Download Previous Leads",
                data=f,
                file_name="day2_leads.csv",
                mime="text/csv"
            )
    except Exception as e:
        st.info("Start a new session to see results here.")

st.markdown("---")
st.caption("LeadPulse Pro Dashboard - Day 2 Production Version")
