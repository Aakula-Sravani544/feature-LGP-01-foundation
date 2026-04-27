# LeadPulse Pro Scraper v7.2 (0-Lead Permanent Fix)
import time
import pandas as pd
import sys
import os
import json
import traceback
import hashlib
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Day 3 & Rescue v7.2 Imports
try:
    from google_sheets import save_to_google_sheets, generate_lead_id
except ImportError:
    def generate_lead_id(n, a): return hashlib.md5(f"{n}{a}".encode()).hexdigest()
    save_to_google_sheets = None

def setup_driver():
    """Initializes a production-ready Chrome driver."""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    if os.environ.get('RENDER'):
        options.add_argument("--headless=new")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(20)
        print("LOG: Chrome launched", flush=True)
        return driver
    except Exception as e:
        print(f"ERROR: Chrome launch failed - {str(e)}", flush=True)
        return None

def run_scraper(query):
    driver = setup_driver()
    if not driver: return

    leads_collected = []
    
    try:
        # STEP 1: OPEN GOOGLE MAPS
        print("LOG: Google Maps Opened", flush=True)
        driver.get("https://www.google.com/maps")
        time.sleep(5)

        # STEP 2: HANDLE SEARCH (MULTI-SELECTOR)
        print("LOG: Finding search box...", flush=True)
        search_box = None
        sb_selectors = [
            (By.ID, "searchboxinput"),
            (By.CSS_SELECTOR, "input[aria-label*='Search']"),
            (By.CSS_SELECTOR, "input[aria-label*='Maps']"),
            (By.CSS_SELECTOR, "input[role='combobox']")
        ]
        
        for by, sel in sb_selectors:
            try:
                search_box = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, sel)))
                if search_box: break
            except: continue
            
        if not search_box:
            driver.save_screenshot("error_debug.png")
            raise Exception("ERROR: Search box not found after multiple attempts.")

        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        print("LOG: Search Submitted", flush=True)
        time.sleep(5)

        # STEP 3: FIND RESULTS PANEL & CARDS (MULTI-SELECTOR + RETRY)
        cards = []
        card_selectors = [
            "div.Nv2PK", 
            "div[role='article']", 
            ".hfpxzc", 
            "a.hfpxzc"
        ]
        
        for attempt in range(3):
            # Find Results Panel
            feed = None
            for f_sel in ['div[role="feed"]', 'div.m6QErb.DxyBCb', "div[aria-label*='Results']"]:
                try:
                    feed = driver.find_element(By.CSS_SELECTOR, f_sel)
                    if feed: break
                except: continue
            
            if feed:
                # Requirement 4: Auto Scroll
                print(f"LOG: Scrolling results (Attempt {attempt+1})...", flush=True)
                for _ in range(8):
                    driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', feed)
                    time.sleep(1.5)
                
                # Check for cards
                for c_sel in card_selectors:
                    cards = driver.find_elements(By.CSS_SELECTOR, c_sel)
                    if len(cards) > 0: break
            
            if len(cards) > 0: break
            time.sleep(3)
            
        print(f"LOG: Cards Found = {len(cards)}", flush=True)
        
        if not cards:
            driver.save_screenshot("error_debug.png")
            raise Exception("No leads extracted from Google Maps. Check selectors.")

        # STEP 4: EXTRACTION LOOP
        total_to_process = min(len(cards), 50)
        
        for i in range(total_to_process):
            print(f"LOG: Processing Card {i+1}", flush=True)
            try:
                # Refetch to avoid stale elements
                curr_cards = driver.find_elements(By.CSS_SELECTOR, card_selectors[0]) if i == 0 else driver.find_elements(By.CSS_SELECTOR, card_selectors[0]) # Simplified for brevity, use same logic as discovery
                # Re-discovery for safety
                found_cards = []
                for c_sel in card_selectors:
                    found_cards = driver.find_elements(By.CSS_SELECTOR, c_sel)
                    if len(found_cards) > 0: break
                
                if i >= len(found_cards): break
                card = found_cards[i]
                
                driver.execute_script("arguments[0].scrollIntoView(true);", card)
                driver.execute_script("arguments[0].click();", card)
                time.sleep(1.5)
                
                # Field Extraction
                name = "N/A"
                try: name = driver.find_element(By.CSS_SELECTOR, 'h1.DUwDvf').text
                except: pass
                
                if name == "N/A" or not name.strip(): continue # Requirement 6: Must have name
                
                address = "N/A"
                try: address = driver.find_element(By.CSS_SELECTOR, 'button[data-item-id="address"]').text
                except: pass
                
                phone = "N/A"
                try: phone = driver.find_element(By.CSS_SELECTOR, 'button[data-item-id*="phone"]').text
                except: pass
                
                website = "N/A"
                try: website = driver.find_element(By.CSS_SELECTOR, 'a[data-item-id="authority"]').get_attribute('href')
                except: pass
                
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                lead_data = {
                    "Business Name": name, "Address": address, "Phone Number": phone,
                    "Website URL": website, "Query": query, "Timestamp": ts,
                    "Generated Time": ts # Standardizing
                }
                
                # Output for app.py
                print(f"DATA: {json.dumps(lead_data)}", flush=True)
                leads_collected.append(lead_data)
                
            except: continue

        if not leads_collected:
            raise Exception("No leads extracted from Google Maps after processing cards.")

        print(f"LOG: Saved {len(leads_collected)} Leads", flush=True)
        print("FINISH: Extraction Completed.", flush=True)
            
    except Exception as e:
        print(f"ERROR: {str(e)}", flush=True)
        # traceback.print_exc() # Hidden to keep logs clean per user preference, but error is printed
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "hotels hyderabad"
    run_scraper(q)
