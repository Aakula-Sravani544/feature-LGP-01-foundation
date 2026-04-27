import gspread
import os
import json
from google.oauth2.service_account import Credentials

def initialize_db():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_json = os.environ.get('GOOGLE_SHEETS_JSON')
    
    try:
        if creds_json:
            info = json.loads(creds_json)
            creds = Credentials.from_service_account_info(info, scopes=scope)
        elif os.path.exists("creds.json"):
            creds = Credentials.from_service_account_file("creds.json", scopes=scope)
        else:
            print("Credentials missing.")
            return

        client = gspread.authorize(creds)
        
        try:
            sh = client.open("LeadPulse_Data")
            print(f"Verified: Spreadsheet 'LeadPulse_Data' exists.")
        except gspread.SpreadsheetNotFound:
            print("Spreadsheet 'LeadPulse_Data' not found. Creating it now...")
            sh = client.create("LeadPulse_Data")
            # Share with the service account email if needed (usually it is the owner)
            # sheet1 is created by default
            print("Successfully created 'LeadPulse_Data'.")
            
    except Exception as e:
        print(f"Error during initialization: {e}")

if __name__ == "__main__":
    initialize_db()
