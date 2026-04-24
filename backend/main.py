from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import shutil

app = FastAPI()

# ✅ Enable frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Folder to store images
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ✅ Test route
@app.get("/")
def read_root():
    return {"message": "Backend is running 🚀"}

# ✅ OLD API (keep if needed)
@app.post("/predict")
def predict():
    return {"status": "Food is Fresh"}

# ✅ NEW MAIN FEATURE (IMPORTANT)
@app.post("/add-food")
async def add_food(
    food_name: str = Form(...),
    quantity: str = Form(...),
    prepared_time: str = Form(...),
    expiry_time: str = Form(...),
    image: UploadFile = File(...)
):
    # Save image
    file_path = os.path.join(UPLOAD_DIR, image.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # Convert time
    prepared = datetime.fromisoformat(prepared_time)
    expiry = datetime.fromisoformat(expiry_time)

    # Logic for freshness
    now = datetime.now()

    if expiry < now:
        status = "Expired"
    elif (expiry - now).total_seconds() <= 7200:
        status = "Going to Expire Soon"
    else:
        status = "Fresh"

    return {
        "message": "Food added successfully",
        "food_name": food_name,
        "quantity": quantity,
        "prepared_time": prepared_time,
        "expiry_time": expiry_time,
        "food_status": status,
        "image_path": file_path
    }
