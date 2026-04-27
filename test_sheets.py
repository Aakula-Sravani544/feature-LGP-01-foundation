# LeadPulse Pro - Day 3 Test Suite
from google_sheets import save_to_google_sheets, is_sheets_connected
import random
import string

def generate_sample_leads(count):
    leads = []
    for i in range(count):
        # Generate some random strings to ensure unique IDs for first run
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
        leads.append({
            "name": f"Test Business {i} {suffix}",
            "address": f"{i} Main St, Test City",
            "phone": "555-0000",
            "website": "http://example.com"
        })
    return leads

def test_write_100_records():
    if not is_sheets_connected():
        print("ERROR: Not connected to Google Sheets")
        return

    print("Connected to Google Sheets")
    
    # 1. First Run: Insert 100
    sample_leads = generate_sample_leads(100)
    res1 = save_to_google_sheets(sample_leads)
    print(f"Inserted {res1['inserted']} rows")
    
    # 2. Second Run: Insert same 100 (should be 0)
    res2 = save_to_google_sheets(sample_leads)
    print(f"Re-run inserted {res2['inserted']} rows")
    print(f"Duplicates skipped {res2['duplicates']}")

if __name__ == "__main__":
    test_write_100_records()
