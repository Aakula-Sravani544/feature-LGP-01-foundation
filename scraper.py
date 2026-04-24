import time
import random
import pandas as pd
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import sys

def setup_driver():
    """Initializes the undetected chromedriver with anti-blocking options."""
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    # Adding some common arguments to look more like a real user
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--remote-debugging-port=9222")
    try:
        driver = uc.Chrome(version_main=147,options=options, headless=False)
        return driver
    except Exception as e:
        print(f"Error setting up driver: {e}")
        sys.exit(1)

def search_location(driver, query):
    """Navigates to Google Maps and searches for the keyword."""
    print(f"Searching for: {query}...")
    driver.get("https://www.google.com/maps")
    
    try:
        # Wait for search box and enter query
        search_box = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "searchboxinput"))
        )
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        
        # Wait for results to load
        time.sleep(random.uniform(5, 7))
    except Exception as e:
        print(f"Error during search: {e}")

def scroll_results(driver, target_count=50):
    """Scrolls the left results panel until target_count businesses are loaded."""
    print(f"Scrolling to load at least {target_count} results...")
    
    try:
        # The results panel is usually a div with role='feed'
        # We need to find the scrollable container
        scrollable_div = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
        )
        
        last_count = 0
        attempts = 0
        
        while attempts < 15:
            # Scroll down
            driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrollable_div)
            time.sleep(random.uniform(2, 4))
            
            # Count results
            results = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
            current_count = len(results)
            print(f"Loaded {current_count} results...")
            
            if current_count >= target_count:
                # Scroll a bit more to ensure the last ones are fully rendered
                driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrollable_div)
                time.sleep(2)
                results = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
                break
                
            if current_count == last_count:
                attempts += 1
            else:
                attempts = 0
                
            last_count = current_count
            
        return results
    except Exception as e:
        print(f"Error during scrolling: {e}")
        return driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')

def extract_business(driver, element, index):
    """Clicks on a business card and extracts detail information."""
    data = {
        'Business Name': '',
        'Full Address': '',
        'Phone Number': '',
        'Website URL': '',
        'Star Rating': '',
        'Review Count': '',
        'Business Category': '',
        'Google Maps URL': '',
        'Business Hours': '',
        'Description': '',
        'Scraped Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        # Ensure element is clickable and click it
        driver.execute_script("arguments[0].scrollIntoView();", element)
        time.sleep(0.5)
        
        # Find the link inside the article to click
        try:
            link = element.find_element(By.TAG_NAME, "a")
            link.click()
        except:
            element.click()
            
        time.sleep(random.uniform(3, 5)) # Wait for panel to open
        
        # Helper to find text by selector
        def get_text(selector, attr="text"):
            try:
                el = driver.find_element(By.CSS_SELECTOR, selector)
                return el.get_attribute(attr) if attr != "text" else el.text
            except:
                return ""

        # Extracting details with specific selectors
        data['Business Name'] = get_text('h1.DUwDvf')
        data['Google Maps URL'] = driver.current_url
        
        # Category
        data['Business Category'] = get_text('button[jsaction*="category"]')
        
        # Rating and Reviews
        try:
            rating_container = driver.find_element(By.CSS_SELECTOR, 'span.ceis6c')
            data['Star Rating'] = rating_container.find_element(By.CSS_SELECTOR, 'span.MW4T7d').text
            # Review count is usually after the rating
            data['Review Count'] = rating_container.find_element(By.XPATH, './following-sibling::span//span[@aria-label]').text.replace('(', '').replace(')', '')
        except:
            # Fallback for rating
            data['Star Rating'] = get_text('div.F7nice span span[aria-hidden="true"]')
            data['Review Count'] = get_text('div.F7nice span:nth-child(2) span[aria-label]')

        # Address
        data['Full Address'] = get_text('button[data-item-id="address"]')
        
        # Website
        data['Website URL'] = get_text('a[data-item-id="authority"]', "href")
        
        # Phone
        data['Phone Number'] = get_text('button[data-item-id*="phone"]')
        
        # Hours
        try:
            # Sometimes you need to click the hours to expand them, 
            # but usually the summary is visible
            hours_el = driver.find_element(By.CSS_SELECTOR, 'div[jsaction*="hours.open"]')
            data['Business Hours'] = hours_el.get_attribute("aria-label")
        except:
            data['Business Hours'] = get_text('div.t3971d') # Another possible class

        # Description
        data['Description'] = get_text('div.PYvS2b')

    except Exception as e:
        print(f"Error extracting data for item {index+1}: {e}")
        
    return data

def save_csv(data_list, filename="day2_leads.csv"):
    """Saves the collected data into a CSV file."""
    if not data_list:
        print("No data collected to save.")
        return
        
    df = pd.DataFrame(data_list)
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\nSuccessfully saved {len(df)} leads to {filename}")

def main():
    # Prompt for input
    print("=== LeadPulse Pro Scraper ===")
    query = input("Enter search query (e.g., dentists Bangalore): ").strip()
    if not query:
        print("Query cannot be empty. Exiting.")
        return

    driver = setup_driver()
    
    try:
        search_location(driver, query)
        
        # Target 50+ results
        result_elements = scroll_results(driver, 55) # Get a few extra just in case
        
        print(f"\nFound {len(result_elements)} potential results. Starting extraction...\n")
        
        leads = []
        for i in range(len(result_elements)):
            # Refresh elements list to avoid StaleElementReferenceException
            # This is safer than using the initial list if the page updates
            current_results = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
            
            if i >= len(current_results):
                break
                
            print(f"Collected {i+1}...")
            business_data = extract_business(driver, current_results[i], i)
            
            if business_data and business_data.get('Business Name'):
                leads.append(business_data)
            
            # Anti-blocking delay
            time.sleep(random.uniform(1.5, 3))
            
            # Stop if we have enough
            # if len(leads) >= 60: break

        save_csv(leads)
        print(f"\nTotal leads collected: {len(leads)}")
        
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        input("Press Enter to close browser...")
        driver.quit()

if __name__ == "__main__":
    main()
