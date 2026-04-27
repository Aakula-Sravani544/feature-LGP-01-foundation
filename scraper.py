import time
import random
import pandas as pd
import re
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
    """Initializes the browser with performance-optimized settings."""
    options = uc.ChromeOptions()
    
    # Performance & Anti-Detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # Browser optimizations
    options.add_argument("--disable-extensions")
    options.add_argument("--dns-prefetch-disable")
    options.add_argument("--disable-features=Translate")
    
    is_linux = sys.platform == "linux" or sys.platform == "linux2"
    
    try:
        # Headless mode is mandatory for Render and faster for production
        driver = uc.Chrome(version_main=147, options=options, headless=True)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(f"[RETRY] Driver 147 failed, trying default: {e}")
        try:
            driver = uc.Chrome(options=options, headless=True)
            driver.set_page_load_timeout(30)
            return driver
        except:
            sys.exit(1)

def clean_text(text):
    """Deep cleans text for professional data extraction."""
    if not text: return ""
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    text = re.sub(r'[^\x20-\x7E]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_address_details(address):
    """Parses address into City, State, and Pincode."""
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
# OPTIMIZED SCRAPER LOGIC
# ==========================================

def search_google_maps(driver, query, log_queue=None):
    """Fast search logic with fallbacks."""
    def log(msg):
        if log_queue: log_queue.put(msg)

    driver.get("https://www.google.com/maps")
    try:
        # Fast wait for search box
        search_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input#searchboxinput"))
        )
        search_box.clear()
        for char in query:
            search_box.send_keys(char)
        search_box.send_keys(Keys.ENTER)
        
        # Wait for results or 'no results'
        WebDriverWait(driver, 10).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, 'div[role="feed"]') or 
                     d.find_elements(By.CSS_SELECTOR, 'div.fontBodyMedium')
        )
        return True
    except:
        return False

def scroll_results(driver, target_count=50, log_queue=None):
    """Efficient scrolling to load cards quickly."""
    try:
        feed = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
        )
        
        last_count = 0
        attempts = 0
        while attempts < 5:
            driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', feed)
            time.sleep(1.5) # Optimized delay
            
            results = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
            current_count = len(results)
            
            if log_queue: log_queue.put(f"Loaded {current_count}...")
            
            if current_count >= target_count + 5: break
            if current_count == last_count: attempts += 1
            else: attempts = 0
            last_count = current_count
            
        return driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
    except:
        return []

def extract_details(driver, index):
    """Fast extraction using smart waits."""
    data = {
        'Business Name': '', 'Full Address': '', 'Phone Number': '', 'Website URL': '',
        'Star Rating': '', 'Review Count': '', 'Business Category': '', 'Google Maps URL': '',
        'Business Hours': '', 'Description': '', 'Scraped Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'City': '', 'State': '', 'Pincode': '', 'Latitude': '', 'Longitude': '', 'Open Status': ''
    }
    
    try:
        results = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
        if index >= len(results): return None
        
        # Scroll & Click
        card = results[index]
        driver.execute_script("arguments[0].click();", card) # Click directly for speed
        
        # Wait for title (Panel load)
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf')))
        
        def get_v(selectors, attr="text"):
            for s in selectors:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, s)
                    return el.get_attribute(attr) if attr != "text" else el.text
                except: continue
            return ""

        data['Business Name'] = clean_text(get_v(['h1.DUwDvf']))
        data['Google Maps URL'] = driver.current_url
        data['Business Category'] = clean_text(get_v(['button[jsaction*="category"]']))
        
        # Rating
        rating_text = get_v(['span.ceis6c', 'span.MW4T7d'])
        data['Star Rating'] = rating_text
        rev_text = get_v(['div.F7nice span:nth-child(2) span[aria-label]'])
        data['Review Count'] = re.sub(r'[^\d]', '', rev_text) if rev_text else ""

        # Address & Location
        data['Full Address'] = clean_text(get_v(['button[data-item-id="address"]']))
        data['City'], data['State'], data['Pincode'] = parse_address_details(data['Full Address'])
        
        # Contact
        data['Website URL'] = get_v(['a[data-item-id="authority"]'], "href")
        data['Phone Number'] = clean_text(get_v(['button[data-item-id*="phone"]']))
        
        # Lat/Long
        coords = re.search(r'@([-.\d]+),([-.\d]+)', driver.current_url)
        if coords: data['Latitude'], data['Longitude'] = coords.group(1), coords.group(2)
        
        data['Open Status'] = "Active" # Default
        
    except:
        return None
    return data

def run_scraper(query, log_queue=None):
    """Main production scraper engine."""
    def log(msg):
        if log_queue: log_queue.put(msg)

    log("Launching Browser...")
    driver = setup_driver()
    leads = []
    seen = set()
    
    try:
        log("Opening Google Maps...")
        if not search_google_maps(driver, query, log_queue):
            log("Search Failed.")
            return [], 0
            
        log("Searching Query...")
        log("Loading Results...")
        elements = scroll_results(driver, 55, log_queue)
        
        if not elements:
            log("Low-result area detected.")
            return [], 0
            
        log("Extracting Leads...")
        for i in range(len(elements)):
            # Page stuck/hang protection check could be added here
            lead = extract_details(driver, i)
            if lead and lead['Business Name']:
                uid = f"{lead['Business Name']}_{lead['Full Address']}".lower()
                if uid not in seen:
                    leads.append(lead)
                    seen.add(uid)
                    log(f"Extracted: {lead['Business Name']}")
                
                if len(leads) >= 50:
                    log("Target of 50 leads reached early.")
                    break
            
            # Anti-detection micro-delay
            time.sleep(random.uniform(0.2, 0.5))
            
        log("Removing Duplicates...")
        log("Saving CSV...")
        
        if leads:
            df = pd.DataFrame(leads)
            df.to_csv('day2_leads.csv', index=False, encoding='utf-8-sig', quoting=1)
            
        log("Completed")
        return leads, len(elements)
        
    except Exception as e:
        log(f"Browser Crash: {e}")
        return [], 0
    finally:
        driver.quit()

if __name__ == "__main__":
    query = input("Query: ")
    run_scraper(query)
