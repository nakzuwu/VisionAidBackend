from flask import request, jsonify
from summarizer import Summarizer
import re
import easyocr
import numpy as np
import cv2
import uuid
import difflib
from kbbi import KBBI
from unidecode import unidecode
from app.models import User, Note
from app import db
from datetime import datetime

kbbi_cache = {}
model = Summarizer()
reader = easyocr.Reader(['id', 'en'], gpu=False)

kamus_kata = [
    "belajar", "menulis", "rapi", "mudah", "dibaca", "muharjo", "seorang", "xenofobia",
    "universal", "yang", "pada", "warga", "jazirah", "contohnya", "qatar",
    "the", "quick", "brown", "fox", "jumps", "over", "lazy",
    "air", "beriak", "tanda", "tak", "dalam"
]

def summarize_text():
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({"error": "API Key is required"}), 401

    user = User.query.filter_by(api_key=api_key).first()
    if not user:
        return jsonify({"error": "Unauthorized. Invalid API Key."}), 401

    # Lanjut kalau API Key valid
    data = request.get_json()
    input_text = data.get('text')

    if not input_text:
        return jsonify({"error": "No text provided."}), 400

    summary = model(input_text, min_length=50, max_length=150)

    return jsonify({
        "summary": summary
    }), 200

def create_or_update_note():
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({"error": "API Key is required"}), 401

    user = User.query.filter_by(api_key=api_key).first()
    if not user:
        return jsonify({"error": "Unauthorized. Invalid API Key."}), 401

    data = request.get_json()
    note_id = data.get('id')
    title = data.get('title')
    content = data.get('content')
    updated_at = data.get('updated_at')
    is_draft = data.get('is_draft', 0)  # Default ke 0 (final)

    if not note_id or not title:
        return jsonify({"error": "Missing fields"}), 400

    try:
        updated_at_dt = datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return jsonify({"error": "Invalid date format for updated_at"}), 400

    note = Note.query.filter_by(id=note_id, user_id=user.id).first()

    if note:
        # Update note
        note.title = title
        note.content = content
        note.updated_at = updated_at_dt
        note.is_draft = is_draft
    else:
        # Create note
        note = Note(
            id=note_id,
            user_id=user.id,
            title=title,
            content=content,
            updated_at=updated_at_dt,
            is_draft=is_draft
        )
        db.session.add(note)

    db.session.commit()

    return jsonify({"msg": "Note synced successfully!"}), 200

def get_notes():
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({"error": "API Key is required"}), 401

    user = User.query.filter_by(api_key=api_key).first()
    if not user:
        return jsonify({"error": "Unauthorized. Invalid API Key."}), 401

    notes = Note.query.filter_by(user_id=user.id).all()
    result = []
    for note in notes:
        result.append({
            "id": note.id,
            "title": note.title,
            "content": note.content,
            "updated_at": note.updated_at.isoformat()
        })

    return jsonify(result), 200

def delete_note(note_id):
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({"error": "API Key is required"}), 401

    user = User.query.filter_by(api_key=api_key).first()
    if not user:
        return jsonify({"error": "Unauthorized. Invalid API Key."}), 401

    note = Note.query.filter_by(id=note_id, user_id=user.id).first()
    if not note:
        return jsonify({"error": "Note not found"}), 404

    db.session.delete(note)
    db.session.commit()

    return jsonify({"msg": "Note deleted successfully"}), 200



# ======================================KODE OCR===============================================



def is_valid_kbbi(word):
    word = word.lower()
    if word in kbbi_cache:
        return kbbi_cache[word]
    try:
        KBBI.lookup(word)
        kbbi_cache[word] = True
        return True
    except:
        kbbi_cache[word] = False
        return False

def spell_correct(word, threshold=0.85):
    """Gunakan KBBI atau kamus lokal untuk koreksi kata"""
    if is_valid_kbbi(word):
        return word
    hasil = difflib.get_close_matches(word.lower(), kamus_kata, n=1, cutoff=threshold)
    return hasil[0] if hasil else word

def postprocess_text(teks):
    """Bersihkan teks dari simbol aneh & koreksi ejaan dasar"""
    teks = unidecode(teks)
    teks = re.sub(r'[^\w\s.,]', '', teks)
    hasil = [spell_correct(kata) for kata in teks.split()]
    return ' '.join(hasil)

def preprocess_image(image):
    """Grayscale + sedikit blur untuk mengurangi noise"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR)

def ocr_image():
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({"error": "API Key is required"}), 401

    user = User.query.filter_by(api_key=api_key).first()
    if not user:
        return jsonify({"error": "Unauthorized. Invalid API Key."}), 401

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    img_bytes = file.read()

    img_array = np.frombuffer(img_bytes, np.uint8)
    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    preprocessed_image = preprocess_image(image)

    results = reader.readtext(preprocessed_image, detail=1, paragraph=True)

    filtered_results = []
    for res in results:
        if len(res) == 3:
            _, text, confidence = res
            if confidence > 0.5 and re.search(r'[a-zA-Z0-9]', text):
                filtered_results.append(text)
        elif len(res) == 2:
            _, text = res
            if re.search(r'[a-zA-Z0-9]', text):
                filtered_results.append(text)

    extracted_text = "\n".join(filtered_results)

    # Koreksi dan normalisasi
    extracted_text = postprocess_text(extracted_text)

    timestamp = datetime.utcnow()
    note_title = f"Scan - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

    pre_note = Note(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title=note_title,
        content=extracted_text,
        updated_at=timestamp,
        is_draft=1
    )
    db.session.add(pre_note)
    db.session.commit()

    return jsonify({
        "text": extracted_text,
        "note_id": pre_note.id,
        "title": note_title,
        "message": "OCR completed. Text saved as draft note.",
        "options": {
            "save_directly": False,  # default sebagai draft
            "summarize_available": True  # user bisa pilih untuk merangkum nanti
        }
    }), 200