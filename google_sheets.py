import gspread
import os
import json
import hashlib
from google.oauth2.service_account import Credentials
import streamlit as st
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
SHEET_NAME = "LeadPulse_Data"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

HEADERS = [
    "lead_id", "name", "address", "phone", "website", "email", 
    "rating", "reviews", "category", "google_maps_url", 
    "description", "hours", "social_media", "additional_data", 
    "scraped_date", "ai_analysis", "validation_status", 
    "validation_notes", "sub_region"
]

def get_google_client():
    """Initializes and returns the Google Sheets client with multi-env support."""
    try:
        # 1. Check Env Variable (for deployment)
        env_creds = os.environ.get('GOOGLE_SHEETS_CREDS_JSON')
        if env_creds:
            info = json.loads(env_creds)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        # 2. Check local file
        elif os.path.exists("creds.json"):
            creds = Credentials.from_service_account_file("creds.json", scopes=SCOPES)
        else:
            return None
        return gspread.authorize(creds)
    except Exception as e:
        import traceback
        print(f"ERROR: Google Auth failed: {str(e)}")
        traceback.print_exc()
        return None

def get_or_create_sheet():
    """Returns the worksheet, creating spreadsheet/headers if not exists."""
    client = get_google_client()
    if not client: return None
    
    try:
        sh = client.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        try:
            sh = client.create(SHEET_NAME)
            # Sharing logic could go here if needed
        except Exception as e:
            print(f"ERROR: Could not create sheet: {e}")
            return None
            
    try:
        sheet = sh.sheet1
        # Auto Create Headers if empty
        existing_headers = sheet.row_values(1)
        if not existing_headers or existing_headers[0] != HEADERS[0]:
            sheet.insert_row(HEADERS, 1)
        return sheet
    except Exception as e:
        print(f"ERROR: Worksheet access failed: {e}")
        return None

def generate_lead_id(name, address):
    """Generates a unique MD5 lead_id based on name and address."""
    clean_name = str(name).lower().strip()
    clean_address = str(address).lower().strip()
    return hashlib.md5(f"{clean_name}{clean_address}".encode()).hexdigest()

def save_to_google_sheets(leads):
    """
    Production-ready batch save with deduplication.
    Expects 'leads' as a list of dictionaries.
    """
    if not leads:
        return {"inserted": 0, "duplicates": 0, "total": 0}
        
    sheet = get_or_create_sheet()
    if not sheet:
        return {"error": "Connection failed", "inserted": 0, "duplicates": 0, "total": len(leads)}

    try:
        # 1. Load existing IDs from Column A
        print("LOG: Loading Existing IDs", flush=True)
        existing_ids = set(sheet.col_values(1))
        
        to_insert = []
        duplicate_count = 0
        batch_ids = set() # Prevent duplicates in same batch

        for lead in leads:
            # Handle both list of dicts and list of lists if needed
            # But we prefer dicts for this professional version
            name = lead.get('name', lead.get('Business Name', 'N/A'))
            address = lead.get('address', lead.get('Address', 'N/A'))
            
            lead_id = lead.get('lead_id')
            if not lead_id:
                lead_id = generate_lead_id(name, address)
            
            if lead_id in existing_ids or lead_id in batch_ids:
                duplicate_count += 1
                continue
            
            # Construct row matching HEADERS
            row = [
                lead_id,
                name,
                address,
                lead.get('phone', lead.get('Phone Number', 'N/A')),
                lead.get('website', lead.get('Website URL', 'N/A')),
                lead.get('email', 'N/A'),
                lead.get('rating', 'N/A'),
                lead.get('reviews', 'N/A'),
                lead.get('category', lead.get('Query', 'N/A')),
                lead.get('google_maps_url', 'N/A'),
                lead.get('description', 'N/A'),
                lead.get('hours', 'N/A'),
                lead.get('social_media', 'N/A'),
                lead.get('additional_data', 'N/A'),
                lead.get('scraped_date', lead.get('Timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))),
                lead.get('ai_analysis', 'N/A'),
                lead.get('validation_status', 'Pending'),
                lead.get('validation_notes', 'N/A'),
                lead.get('sub_region', 'N/A')
            ]
            to_insert.append(row)
            batch_ids.add(lead_id)

        # 2. Batch Write in chunks of 50
        if to_insert:
            chunk_size = 50
            for i in range(0, len(to_insert), chunk_size):
                batch_num = (i // chunk_size) + 1
                print(f"LOG: Writing Batch {batch_num}", flush=True)
                sheet.append_rows(to_insert[i : i + chunk_size], value_input_option='USER_ENTERED')
        
        return {
            "inserted": len(to_insert),
            "duplicates": duplicate_count,
            "total": len(leads)
        }
        
    except Exception as e:
        print(f"ERROR: Batch save failed: {e}")
        return {"error": str(e), "inserted": 0, "duplicates": 0, "total": len(leads)}

def is_sheets_connected():
    """Diagnostic check."""
    return get_google_client() is not None
