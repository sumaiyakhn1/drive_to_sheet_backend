import os
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from cryptography.fernet import Fernet

# -----------------------------------
# LOAD ENVIRONMENT VARIABLES
# -----------------------------------
CLIENT_ID = os.getenv("OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")
FERNET_KEY = os.getenv("FERNET_KEY")
ADMIN_KEY = os.getenv("ADMIN_KEY")

if not FERNET_KEY:
    raise Exception("⚠ FERNET_KEY missing in environment variables!")
if not CLIENT_ID or not CLIENT_SECRET:
    raise Exception("⚠ Google OAuth client ID or secret missing!")
if not ADMIN_KEY:
    raise Exception("⚠ ADMIN_KEY missing!")

cipher = Fernet(FERNET_KEY.encode())

# -----------------------------------
# FASTAPI APP
# -----------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------
# LOAD SAVED REFRESH TOKEN
# -----------------------------------
def get_creds():
    with open("refresh_token.enc", "rb") as f:
        encrypted = f.read()

    refresh_token = cipher.decrypt(encrypted).decode()

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=[
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
    )
    return creds


# -----------------------------------
# INDEX ROUTE
# -----------------------------------
@app.get("/")
def home():
    return {"ok": True, "message": "Backend running"}


# -----------------------------------
# ADMIN SET TOKEN ROUTE
# -----------------------------------
@app.post("/admin/set-token")
def admin_set_token(
    refresh_token: str = Form(...),
    admin_key: str = Form(...)
):
    if admin_key != ADMIN_KEY:
        return {"ok": False, "error": "Invalid admin key"}

    encrypted = cipher.encrypt(refresh_token.encode())

    with open("refresh_token.enc", "wb") as f:
        f.write(encrypted)

    return {"ok": True, "message": "Refresh token saved"}


# -----------------------------------
# MAIN SYNC ROUTE (Drive → Sheet)
# -----------------------------------
@app.post("/sync")
def sync_drive_to_sheet(
    folder_id: str = Form(...),
    sheet_id: str = Form(...)
):
    creds = get_creds()

    drive = build("drive", "v3", credentials=creds)
    sheet = build("sheets", "v4", credentials=creds)

    # Fetch files inside folder
    results = drive.files().list(
        q=f"'{folder_id}' in parents",
        fields="files(id, name)"
    ).execute()

    files = results.get("files", [])

    # Prepare table rows
    rows = []
    for f in files:
        file_id = f["id"]
        name = f["name"]
        link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        rows.append([name, link])

    # Write to Google Sheet
    sheet.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Sheet1!A1",
        valueInputOption="RAW",
        body={"values": rows}
    ).execute()

    return {"ok": True, "count": len(rows), "message": "Synced with links!"}
