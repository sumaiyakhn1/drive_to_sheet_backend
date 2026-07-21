import os
import io
import re
import requests
import openpyxl
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openpyxl.styles import Font, PatternFill

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
    url_or_id = url_or_id.strip()
    url_or_id = url_or_id.split("?")[0]

    if "/" not in url_or_id:
        return url_or_id

    if "drive.google.com" in url_or_id:
        parts = url_or_id.split("/")
        if "folders" in parts:
            idx = parts.index("folders")
            return parts[idx + 1] if idx + 1 < len(parts) else url_or_id
        if "d" in parts:
            idx = parts.index("d")
            return parts[idx + 1] if idx + 1 < len(parts) else url_or_id

    return url_or_id


# -------------------------------
# HOME
# -------------------------------
@app.get("/")
def home():
    return {
        "ok": True,
        "message": "Backend running on Render! API Key NOT required. Web scraping mode active."
    }


# -------------------------------
# FETCH PUBLIC FOLDER FILES
# -------------------------------
def get_public_folder_files(folder_id: str) -> list:
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise Exception(f"Failed to load Drive folder page (HTTP {resp.status_code}). Make sure the folder is 'Anyone with the link can view'.")

    html = resp.text
    files = []

    pattern1 = re.findall(r'\["([^"\\]+)"(?:,null)+,"([a-zA-Z0-9_-]{20,})"', html)
    for name, file_id in pattern1:
        files.append({"name": name, "id": file_id})

    if not files:
        pattern2 = re.findall(r'"([a-zA-Z0-9_-]{20,})","([^"]{2,})"', html)
        seen = set()
        for file_id, name in pattern2:
            if file_id not in seen and len(name) < 200:
                files.append({"name": name, "id": file_id})
                seen.add(file_id)

    seen_ids = set()
    unique_files = []
    for f in files:
        if f["id"] not in seen_ids:
            unique_files.append(f)
            seen_ids.add(f["id"])

    return unique_files


# -------------------------------
# GENERATE EXCEL FROM GOOGLE DRIVE
# -------------------------------
@app.post("/generate-excel")
def generate_excel_from_drive(folder_id: str = Form(...)):
    try:
        folder_id_clean = extract_id(folder_id)
        files = get_public_folder_files(folder_id_clean)

        if not files:
            raise HTTPException(status_code=404, detail="No files found. Ensure the folder is not empty and shared as 'Anyone with the link can view'.")

        # Create Excel workbook in memory
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Drive Files"

        # Headers
        ws.append(["File Name", "File Link"])
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="1155CC")
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill

        for f in files:
            name = f["name"]
            link = f"https://drive.google.com/file/d/{f['id']}/view?usp=sharing"
            ws.append([name, link])

        ws.column_dimensions["A"].width = 60
        ws.column_dimensions["B"].width = 80

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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# -------------------------------
# RENDER START ENTRYPOINT
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

