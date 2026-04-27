import time
import pandas as pd
import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def run_scraper(query):
    print("Launching browser", flush=True)
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Check for Render environment
    is_render = os.environ.get('RENDER') is not None
    if is_render:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

    driver = None
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        # Anti-detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("Opening Maps", flush=True)
        driver.get("https://www.google.com/maps")
        time.sleep(10) # Full load wait
        
        # Dismiss initial popups (Sign In, Cookies, etc)
        try:
            popups = driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Accept'], button[aria-label*='Agree'], button[aria-label*='Dismiss']")
            if popups:
                popups[0].click()
                time.sleep(2)
        except: pass

        print("Searching", flush=True)
        # Multi-selector search box detection
        search_box = None
        selectors = [
            (By.ID, "searchboxinput"),
            (By.CSS_SELECTOR, "input[aria-label*='Search']"),
            (By.NAME, "q"),
            (By.TAG_NAME, "input")
        ]
        
        for by, selector in selectors:
            try:
                search_box = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((by, selector)))
                if search_box: 
                    # Click first to ensure focus
                    driver.execute_script("arguments[0].click();", search_box)
                    time.sleep(1)
                    break
            except: continue
            
        if not search_box:
            raise Exception("Search box not found after multiple attempts")
            
        search_box.clear()
        # Type slowly to mimic human
        for char in query:
            search_box.send_keys(char)
            time.sleep(0.05)
        search_box.send_keys(Keys.ENTER)
        
        print("Waiting for results...", flush=True)
        time.sleep(8) 
        
        print("Scrolling", flush=True)
        # Find the results panel
        try:
            panel = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
            )
            print("Results feed detected", flush=True)
        except:
            print("Warning: Results feed role='feed' not found, using fallback", flush=True)
            try:
                panel = driver.find_element(By.CSS_SELECTOR, 'div[aria-label*="Results for"]')
            except:
                panel = driver.find_element(By.TAG_NAME, "body")

        for i in range(15):
            driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', panel)
            time.sleep(2)
            if i % 5 == 0: print(f"Scrolling... {i+1}/15", flush=True)

        print("Extracting", flush=True)
        leads = []
        # Google Maps results cards
        results = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
        print(f"Detected {len(results)} potential results", flush=True)
        
        seen_names = set()
        for res in results:
            try:
                # Basic extraction from the card
                name = ""
                address = ""
                phone = ""
                website = ""
                
                try: name = res.get_attribute("aria-label")
                except: pass
                
                if not name:
                    try: name = res.find_element(By.CSS_SELECTOR, ".fontHeadlineSmall").text
                    except: pass

                if not name or name in seen_names: continue
                seen_names.add(name)
                
                # Try to get more info from the card text
                card_text = res.text.split("\n")
                if len(card_text) > 1:
                    # Address is often the line with rating or similar, or just next line
                    for line in card_text[1:]:
                        if any(char.isdigit() for char in line) and len(line) > 10:
                            address = line
                            break

                leads.append({
                    "Business Name": name,
                    "Full Address": address,
                    "Phone Number": phone,
                    "Website URL": website,
                    "Date": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                print(f"SUCCESS: {name}", flush=True)
                
                if len(leads) >= 60: break
            except: continue

        if leads:
            print("Saving CSV", flush=True)
            df = pd.DataFrame(leads)
            df.to_csv("leads.csv", index=False, encoding='utf-8-sig')
            
        print("Completed", flush=True)
        if not is_render:
            time.sleep(5)
            
    except Exception as e:
        print(f"Error happened: {e}", flush=True)
        if not is_render and driver:
            # Only wait for input if NOT running in a subprocess that app.py might kill
            # But for debugging, we can keep it for a bit
            time.sleep(10)
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "dentists hyderabad"
    run_scraper(q)
