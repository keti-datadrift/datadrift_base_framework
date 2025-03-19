from fastapi import FastAPI, UploadFile, File, HTTPException
import os
import shutil

app = FastAPI()

DATA_DIR = "data/"
MODEL_DIR = "models/"

# 디렉터리 생성
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "Welcome to dd-hub!"}

# 데이터 업로드 API
@app.post("/upload/data/")
def upload_data(file: UploadFile = File(...)):
    file_path = os.path.join(DATA_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"message": f"Data {file.filename} uploaded successfully!"}

# 모델 업로드 API
@app.post("/upload/model/")
def upload_model(file: UploadFile = File(...)):
    file_path = os.path.join(MODEL_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"message": f"Model {file.filename} uploaded successfully!"}

# 데이터 목록 조회
@app.get("/list/data/")
def list_data():
    return {"data_files": os.listdir(DATA_DIR)}

# 모델 목록 조회
@app.get("/list/models/")
def list_models():
    return {"model_files": os.listdir(MODEL_DIR)}

# 데이터 다운로드 API
@app.get("/download/data/{filename}")
def download_data(filename: str):
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return {"download_url": f"/data/{filename}"}

# 모델 다운로드 API
@app.get("/download/model/{filename}")
def download_model(filename: str):
    file_path = os.path.join(MODEL_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return {"download_url": f"/models/{filename}"}