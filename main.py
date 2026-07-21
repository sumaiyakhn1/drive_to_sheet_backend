import os
import io
import openpyxl
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from googleapiclient.discovery import build

# -------------------------------
# LOAD ENVIRONMENT VARIABLES
# -------------------------------
API_KEY = os.getenv("GOOGLE_API_KEY")

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
# HOME
# -------------------------------
@app.get("/")
def home():
    return {"ok": True, "message": "Backend running on Render! API Key Mode active."}


# -------------------------------
# LIST ALL FILES (NO 100 LIMIT)
# -------------------------------
def list_all_files(drive, folder_id: str):
    files = []
    page_token = None

    while True:
        response = drive.files().list(
            q=f"'{folder_id}' in parents",
            fields="nextPageToken, files(id, name)",
            pageSize=1000
        ).execute()

        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return files


# -------------------------------
# GENERATE EXCEL FROM GOOGLE DRIVE
# -------------------------------
@app.post("/generate-excel")
def generate_excel_from_drive(folder_id: str = Form(...)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY is not set on the server")

    folder_id = extract_id(folder_id)

    try:
        drive = build("drive", "v3", developerKey=API_KEY)
        files = list_all_files(drive, folder_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch from Google Drive: {str(e)}")

    # Create Excel workbook in memory
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Drive Files"
    
    # Headers
    ws.append(["File Name", "File Link"])

    for f in files:
        file_id = f["id"]
        name = f["name"]
        link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        ws.append([name, link])

    # Save to BytesIO
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    # Return as StreamingResponse
    headers = {
        'Content-Disposition': 'attachment; filename="drive_files.xlsx"'
    }
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )


# -------------------------------
# RENDER START ENTRYPOINT
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
