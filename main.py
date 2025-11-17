import os
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from cryptography.fernet import Fernet

# -------------------------------
# LOAD ENVIRONMENT VARIABLES
# -------------------------------
CLIENT_ID = os.getenv("OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")
FERNET_KEY = os.getenv("FERNET_KEY")
ADMIN_KEY = os.getenv("ADMIN_KEY")
REFRESH_TOKEN_ENV = os.getenv("REFRESH_TOKEN")

cipher = Fernet(FERNET_KEY.encode())

# -------------------------------
# FASTAPI APP
# -------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# EXTRACT ID FROM URL
# -------------------------------
def extract_id(url_or_id: str):
    if "/" not in url_or_id:
        return url_or_id
    
    if "drive.google.com" in url_or_id:
        parts = url_or_id.split("/")
        if "folders" in parts:
            return parts[parts.index("folders") + 1]
        if "d" in parts:
            return parts[parts.index("d") + 1]

    return url_or_id


# -------------------------------
# GET GOOGLE API CREDS
# -------------------------------
def get_creds():
    if not REFRESH_TOKEN_ENV:
        raise Exception("REFRESH_TOKEN missing in Render ENV!")

    refresh_token = cipher.decrypt(REFRESH_TOKEN_ENV.encode()).decode()

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=[
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )
    return creds


# -------------------------------
# HOME
# -------------------------------
@app.get("/")
def home():
    return {"ok": True, "message": "Backend running on Render!"}


# -------------------------------
# ADMIN TOKEN SETTER
# -------------------------------
@app.post("/admin/set-token")
def admin_set_token(refresh_token: str = Form(...), admin_key: str = Form(...)):
    if admin_key != ADMIN_KEY:
        return {"ok": False, "error": "Invalid admin key"}

    encrypted = cipher.encrypt(refresh_token.encode()).decode()

    return {
        "ok": True,
        "message": "Copy this encrypted token into Render ENV as REFRESH_TOKEN",
        "encrypted_token": encrypted
    }


# -------------------------------
# SYNC GOOGLE DRIVE → GOOGLE SHEET
# -------------------------------
@app.post("/sync")
def sync_drive_to_sheet(folder_id: str = Form(...), sheet_id: str = Form(...)):
    folder_id = extract_id(folder_id)
    sheet_id = extract_id(sheet_id)

    creds = get_creds()

    drive = build("drive", "v3", credentials=creds)
    sheet = build("sheets", "v4", credentials=creds)

    # List files in Drive folder
    results = drive.files().list(
        q=f"'{folder_id}' in parents",
        fields="files(id, name)"
    ).execute()

    files = results.get("files", [])

    rows = []
    for f in files:
        file_id = f["id"]
        name = f["name"]
        link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        rows.append([name, link])

    sheet.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Sheet1!A2",
        valueInputOption="RAW",
        body={"values": rows}
    ).execute()

    return {
        "ok": True,
        "count": len(rows),
        "message": "Drive folder synced successfully!"
    }


# -------------------------------
# RENDER START ENTRYPOINT
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
