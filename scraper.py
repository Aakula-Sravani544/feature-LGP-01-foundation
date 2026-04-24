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
    """Initializes the browser with production-grade anti-detection settings."""
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    try:
        # Use Chrome version 147 as requested for stability
        driver = uc.Chrome(version_main=147, options=options, headless=False)
        return driver
    except Exception as e:
        print(f"[ERROR] Driver setup failed: {e}")
        sys.exit(1)

def clean_text(text):
    """Removes weird symbols, icons, and newlines for a clean CSV."""
    if not text: return ""
    # Remove common Google Maps icons and non-printable characters
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    text = re.sub(r'[^\x20-\x7E]+', ' ', text) # Keep only standard ASCII
    text = re.sub(r'\s+', ' ', text) # Remove multiple spaces
    return text.strip()

def human_typing(element, text):
    """Simulates a human typing slowly to avoid bot detection."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.1, 0.25))

def find_element_safely(parent, selectors, timeout=5):
    """Tries multiple selectors to find an element, handling UI changes."""
    for selector in selectors:
        try:
            return parent.find_element(By.CSS_SELECTOR, selector)
        except:
            continue
    return None

def parse_address_details(address):
    """Splits full address into City, State, and Pincode for India."""
    city, state, pincode = "", "", ""
    if not address: return city, state, pincode
    
    # Regex for 6-digit Indian Pincode
    pin_match = re.search(r'\b\d{6}\b', address)
    if pin_match:
        pincode = pin_match.group(0)
    
    parts = [p.strip() for p in address.split(',')]
    if len(parts) >= 2:
        # State is usually in the last or second to last part with the pincode
        state_part = parts[-1]
        state = state_part.replace(pincode, "").strip()
        
        # City is usually the part before state
        city = parts[-2]
    
    return city, state, pincode

# ==========================================
# CORE SCRAPER FUNCTIONS
# ==========================================

def handle_popups(driver):
    """Closes common Google consent or sign-in popups if they appear."""
    popups = [
        "button[aria-label='Accept all']",
        "button[aria-label='Agree']",
        "div.VtwuBe button",
        "button[aria-label='No thanks']"
    ]
    for selector in popups:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, selector)
            btn.click()
            time.sleep(1)
        except:
            continue

def search_google_maps(driver, query):
    """Robustly searches via the Google Maps search box only."""
    retries = 2
    while retries >= 0:
        try:
            print(f"[INFO] Navigating to Google Maps Homepage (Attempt {3-retries}/3)...")
            driver.get("https://www.google.com/maps")
            handle_popups(driver)
            
            # Fallback selectors for search box
            search_box_selectors = ["input#searchboxinput", "input[name='q']", "input.tactile-searchbox-input"]
            search_box = None
            
            for selector in search_box_selectors:
                try:
                    search_box = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except: continue
            
            if not search_box:
                raise Exception("Search box not found.")
            
            search_box.clear()
            time.sleep(1)
            print(f"[INFO] Typing query: {query}")
            human_typing(search_box, query)
            search_box.send_keys(Keys.ENTER)
            
            # Wait for results to start loading
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
            )
            return True
            
        except Exception as e:
            print(f"[WARNING] Search failed: {e}. Retrying...")
            retries -= 1
            time.sleep(3)
    
    return False

def scroll_results(driver, min_results=50):
    """Scrolls the results panel until 50+ items are found or no more results."""
    print(f"[INFO] Scrolling to load results...")
    try:
        feed_panel = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
        )
        
        last_len = 0
        no_new_results_count = 0
        
        while no_new_results_count < 5:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed_panel)
            time.sleep(random.uniform(2.5, 4))
            
            results = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
            current_len = len(results)
            
            if current_len != last_len:
                print(f"Loaded {current_len}...")
                no_new_results_count = 0
            else:
                no_new_results_count += 1
            
            if current_len >= min_results:
                break
                
            last_len = current_len
            
        return driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
    except Exception as e:
        print(f"[ERROR] Scroll error: {e}")
        return []

def extract_details(driver, index):
    """Extracts 17 detailed fields from a business card."""
    data = {
        'Business Name': '', 'Full Address': '', 'Phone Number': '', 'Website URL': '',
        'Star Rating': '', 'Review Count': '', 'Business Category': '', 'Google Maps URL': '',
        'Business Hours': '', 'Description': '', 'Scraped Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'City': '', 'State': '', 'Pincode': '', 'Latitude': '', 'Longitude': '', 'Open Status': ''
    }
    
    try:
        # Re-locate elements to prevent stale element errors
        all_results = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
        if index >= len(all_results): return None
        
        card = all_results[index]
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", card)
        time.sleep(1)
        
        # Click the link to open the detail panel
        try:
            link = card.find_element(By.CSS_SELECTOR, 'a.hfpxzc')
            link.click()
        except:
            card.click()
            
        # Wait for detail panel (Title is the best anchor)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf')))
        time.sleep(random.uniform(2, 3))
        
        # 1. Business Name (with fallback)
        name_el = find_element_safely(driver, ['h1.DUwDvf', 'div.l699ne h1'])
        data['Business Name'] = clean_text(name_el.text) if name_el else "Unknown"
        
        # 2. URL
        data['Google Maps URL'] = driver.current_url
        
        # 3. Category
        cat_el = find_element_safely(driver, ['button[jsaction*="category"]', 'span.DpwY9c button'])
        data['Business Category'] = clean_text(cat_el.text) if cat_el else ""
        
        # 4. Rating & 5. Reviews
        try:
            rating_el = find_element_safely(driver, ['span.ceis6c', 'span.MW4T7d'])
            data['Star Rating'] = rating_el.text if rating_el else ""
            reviews_el = find_element_safely(driver, ['div.F7nice span:nth-child(2) span[aria-label]'])
            data['Review Count'] = re.sub(r'[^\d]', '', reviews_el.text) if reviews_el else ""
        except: pass
        
        # 6. Address & 7-9 (City, State, Pincode)
        addr_el = find_element_safely(driver, ['button[data-item-id="address"]', 'div.R_Scc button'])
        if addr_el:
            data['Full Address'] = clean_text(addr_el.text)
            data['City'], data['State'], data['Pincode'] = parse_address_details(data['Full Address'])
            
        # 10. Website
        web_el = find_element_safely(driver, ['a[data-item-id="authority"]', 'a[aria-label^="Website"]'])
        data['Website URL'] = web_el.get_attribute("href") if web_el else ""
        
        # 11. Phone
        phone_el = find_element_safely(driver, ['button[data-item-id^="phone"]', 'button[aria-label^="Phone"]'])
        data['Phone Number'] = clean_text(phone_el.text) if phone_el else ""
        
        # 12. Hours
        hours_el = find_element_safely(driver, ['div.t3971d', 'div[aria-label*="Hours"]'])
        data['Business Hours'] = clean_text(hours_el.text) if hours_el else ""
        
        # 13. Description
        desc_el = find_element_safely(driver, ['div.PYvS2b', 'div.w699ne'])
        data['Description'] = clean_text(desc_el.text) if desc_el else ""
        
        # 14-15. Latitude & Longitude
        coords = re.search(r'@([-.\d]+),([-.\d]+)', driver.current_url)
        if coords:
            data['Latitude'], data['Longitude'] = coords.group(1), coords.group(2)
            
        # 16. Open Status
        status_panel = find_element_safely(driver, ['div.m6QErb.W4E9H'])
        if status_panel:
            text = status_panel.text
            if "Permanently closed" in text: data['Open Status'] = "Permanently Closed"
            elif "Temporarily closed" in text: data['Open Status'] = "Temporarily Closed"
            else: data['Open Status'] = "Open / Active"
        else: data['Open Status'] = "Active"

    except Exception as e:
        print(f"[SKIP] Error extracting item {index + 1}: {e}")
        return None
        
    return data

# ==========================================
# MAIN EXECUTION
# ==========================================

def main():
    print("\n" + "="*40)
    print("   LEADPULSE PRO - GOOGLE MAPS SCRAPER")
    print("="*40)
    
    query = input("\nEnter Keyword + City (e.g. dentists Bangalore): ").strip()
    if not query: return
    
    driver = setup_driver()
    leads = []
    seen_identifiers = set() # For duplicate removal
    
    try:
        if search_google_maps(driver, query):
            elements = scroll_results(driver, 55)
            
            if not elements:
                print("[!] No results found after search.")
            else:
                print(f"\n[INFO] Starting deep extraction for {len(elements)} cards...")
                
                for i in range(len(elements)):
                    lead = extract_details(driver, i)
                    
                    if lead and lead['Business Name'] != "Unknown":
                        # Create unique ID from Name + Address (Cleaned)
                        uid = f"{lead['Business Name']}_{lead['Full Address']}".lower()
                        if uid not in seen_identifiers:
                            leads.append(lead)
                            seen_identifiers.add(uid)
                            print(f"[{len(leads)}] Collected: {lead['Business Name']}")
                        else:
                            print(f"[DUPLICATE] Skipping: {lead['Business Name']}")
                    
                    # Anti-blocking delay
                    time.sleep(random.uniform(0.5, 1.5))
                    
                    if len(leads) >= 70: break # Safety cap
                
                # Save Data
                if leads:
                    df = pd.DataFrame(leads)
                    # Reorder columns to match user requirement exactly
                    ordered_cols = [
                        'Business Name', 'Full Address', 'Phone Number', 'Website URL', 
                        'Star Rating', 'Review Count', 'Business Category', 'Google Maps URL', 
                        'Business Hours', 'Description', 'Scraped Date', 'City', 'State', 
                        'Pincode', 'Latitude', 'Longitude', 'Open Status'
                    ]
                    df = df[ordered_cols]
                    df.to_csv('day2_leads.csv', index=False, encoding='utf-8-sig', quoting=1)
                    
                    print("\n" + "="*30)
                    print("       FINAL SUMMARY")
                    print("="*30)
                    print(f"Total Results Loaded: {len(elements)}")
                    print(f"Total Leads Saved:   {len(leads)}")
                    print(f"CSV File Name:       day2_leads.csv")
                    print("="*30)
                else:
                    print("\n[!] No leads could be successfully scraped.")
        else:
            print("[!] Search process failed completely.")
            
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Script crashed: {e}")
    finally:
        print("\n[!] Process Finished.")
        input("Press Enter to close browser...")
        driver.quit()

if __name__ == "__main__":
    main()
