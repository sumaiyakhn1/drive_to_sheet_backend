import requests
import webbrowser
from urllib.parse import urlencode
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

BACKEND_ADMIN_URL = os.getenv("BACKEND_ADMIN_URL")
ADMIN_KEY = os.getenv("ADMIN_KEY")

SCOPES = (
    "https://www.googleapis.com/auth/drive.readonly "
    "https://www.googleapis.com/auth/spreadsheets"
)

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ CLIENT_ID or CLIENT_SECRET missing in .env")
    exit()

params = {
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": SCOPES,
    "access_type": "offline",
    "prompt": "consent"
}

auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
print("Opening browser...")
webbrowser.open(auth_url)

code = input("Paste the code here: ")

token = requests.post(
    "https://oauth2.googleapis.com/token",
    data={
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
).json()

print(token)

refresh = token.get("refresh_token")
print("Refresh token:", refresh)

res = requests.post(
    BACKEND_ADMIN_URL,
    data={"refresh_token": refresh, "admin_key": ADMIN_KEY}
)

print("Backend response:", res.text)
