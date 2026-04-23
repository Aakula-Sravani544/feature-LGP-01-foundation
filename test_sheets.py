import gspread
from google.oauth2.service_account import Credentials

scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
# Note: creds.json must be provided by the user in the project root
try:
    creds = Credentials.from_service_account_file("creds.json", scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("LeadPulse_Data").sheet1
    sheet.append_row(["Day 1", "Working"])
    print("Connected to Google Sheets!")
except Exception as e:
    print(f"Error connecting to Google Sheets: {e}")
    print("Make sure 'creds.json' exists and the sheet 'LeadPulse_Data' is shared with the client email.")
