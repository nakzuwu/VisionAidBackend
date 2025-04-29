from fastapi import APIRouter, UploadFile, File
from typing import List
from app.controllers import trocr_controller

router = APIRouter()

@router.post("/trocr/predict")
async def predict_trocr(files: List[UploadFile] = File(...)):
    contents = [await file.read() for file in files]
    result = trocr_controller.predict_text(contents)
    return {"results": result}
