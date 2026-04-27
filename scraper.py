import time
import random
import pandas as pd
import re
import os
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import sys

# ==========================================
# CONFIGURATION & UTILITIES
# ==========================================

def setup_driver():
    """Initializes the browser with cross-platform (Windows/Linux) support."""
    options = uc.ChromeOptions()
    
    # Check if running on Render
    is_render = os.environ.get('RENDER') is not None
    is_linux = sys.platform == "linux" or sys.platform == "linux2"
    
    # Production-grade flags
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Use headless for Linux/Render automatically
    headless = True if (is_render or is_linux) else False
    
    try:
        # On Render, we might need to specify binary path if custom installed
        chrome_bin = os.environ.get('CHROME_BIN')
        if is_render and chrome_bin:
            options.binary_location = chrome_bin
            
        driver = uc.Chrome(options=options, headless=headless)
        driver.set_page_load_timeout(60)
        return driver
    except Exception as e:
        print(f"Driver Initialization Failed: {e}")
        # Final fallback for cloud environments
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        except Exception as e2:
            print(f"Critical Error: All browser engines failed. {e2}")
            return None

def clean_text(text):
    if not text: return ""
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    text = re.sub(r'[^\x20-\x7E]+', ' ', text)
    return text.strip()

def parse_address_details(address):
    city, state, pincode = "", "", ""
    if not address: return city, state, pincode
    pin_match = re.search(r'\b\d{6}\b', address)
    if pin_match: pincode = pin_match.group(0)
    parts = [p.strip() for p in address.split(',')]
    if len(parts) >= 2:
        state = parts[-1].replace(pincode, "").strip()
        city = parts[-2]
    return city, state, pincode

# ==========================================
# SCRAPER LOGIC
# ==========================================

def search_google_maps(driver, query):
    driver.get("https://www.google.com/maps")
    try:
        search_box = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input#searchboxinput"))
        )
        search_box.clear()
        for char in query:
            search_box.send_keys(char)
        search_box.send_keys(Keys.ENTER)
        WebDriverWait(driver, 20).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, 'div[role="feed"]') or 
                     d.find_elements(By.CSS_SELECTOR, 'div.fontBodyMedium')
        )
        return True
    except:
        return False

def scroll_results(driver, target=55):
    try:
        feed = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
        )
        last_count = 0
        for _ in range(15):
            driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', feed)
            time.sleep(2)
            results = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
            if len(results) >= target: break
            if len(results) == last_count: break
            last_count = len(results)
        return driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
    except:
        return []

def extract_details(driver, index):
    data = {'Business Name': '', 'Full Address': '', 'Phone Number': '', 'Website URL': '', 'Star Rating': '', 'Review Count': '', 'Business Category': '', 'Google Maps URL': '', 'Business Hours': '', 'Description': '', 'Scraped Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'City': '', 'State': '', 'Pincode': '', 'Latitude': '', 'Longitude': '', 'Open Status': ''}
    try:
        results = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
        if index >= len(results): return None
        card = results[index]
        driver.execute_script("arguments[0].click();", card)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf')))
        
        def get_v(sel, attr="text"):
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                return el.get_attribute(attr) if attr != "text" else el.text
            except: return ""

        data['Business Name'] = clean_text(get_v('h1.DUwDvf'))
        data['Google Maps URL'] = driver.current_url
        data['Business Category'] = clean_text(get_v('button[jsaction*="category"]'))
        data['Star Rating'] = get_v('span.ceis6c')
        data['Full Address'] = clean_text(get_v('button[data-item-id="address"]'))
        data['Phone Number'] = clean_text(get_v('button[data-item-id*="phone"]'))
        data['Website URL'] = get_v('a[data-item-id="authority"]', "href")
        data['City'], data['State'], data['Pincode'] = parse_address_details(data['Full Address'])
        
        coords = re.search(r'@([-.\d]+),([-.\d]+)', driver.current_url)
        if coords: data['Latitude'], data['Longitude'] = coords.group(1), coords.group(2)
        data['Open Status'] = "Active"
    except:
        return None
    return data

def run_scraper(query):
    print(f"Launching Scraper Engine for: {query}")
    driver = setup_driver()
    if not driver:
        print("Scraper Engine Failed to Start. Checking for fallback data...")
        return [], 0
    
    leads = []
    seen = set()
    try:
        if search_google_maps(driver, query):
            print("Google Maps Opened Successfully.")
            elements = scroll_results(driver, 55)
            print(f"Found {len(elements)} possible results. Starting extraction...")
            
            for i in range(len(elements)):
                lead = extract_details(driver, i)
                if lead and lead['Business Name']:
                    uid = f"{lead['Business Name']}_{lead['Full Address']}".lower()
                    if uid not in seen:
                        leads.append(lead)
                        seen.add(uid)
                        print(f"[{len(leads)}] Extracted: {lead['Business Name']}")
                if len(leads) >= 50: break
                time.sleep(random.uniform(0.1, 0.3))
            
            if leads:
                df = pd.DataFrame(leads)
                df.to_csv('day2_leads.csv', index=False, encoding='utf-8-sig', quoting=1)
                print("CSV Generated Successfully.")
        return leads, len(leads)
    except Exception as e:
        print(f"Scraper Error: {e}")
        return [], 0
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    import sys
    query_str = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Query: ")
    run_scraper(query_str)
