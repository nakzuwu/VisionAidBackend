from PIL import Image
from app.trocr.main import TrocrPredictor
from typing import List
import io

# Load the TrocrPredictor
trocr_model = TrocrPredictor()

def predict_text(files: List[bytes]):
    # Load images
    images = [Image.open(io.BytesIO(file)) for file in files]
    
    # OCR Prediction
    predictions = trocr_model.predict_images(images)
    
    return predictions
