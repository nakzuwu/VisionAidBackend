from functools import wraps
from flask import request, jsonify, current_app
from summarizer import Summarizer
import os
import re
import easyocr
import numpy as np
import cv2
import uuid
import difflib
from kbbi import KBBI
from unidecode import unidecode
from app.models import User, Note, Reminder
from app import db
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import whisper
from pathlib import Path

kbbi_cache = {}
reader = easyocr.Reader(['id', 'en'], gpu=False)
model = whisper.load_model("base") 
model_summary = Summarizer()

UPLOAD_FOLDER = 'uploads'
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)


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

    summary = model_summary(input_text, min_length=50, max_length=150)

    return jsonify({
        "summary": summary
    }), 200

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@jwt_required()
def sync_note():
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or 'id' not in data:
        return jsonify({"error": "Invalid payload"}), 400

    note = Note.query.filter_by(id=data['id'], user_id=user_id).first()

    client_updated = datetime.fromisoformat(data['updated_at'])
    client_created = datetime.fromisoformat(data['created_at'])
    client_last_opened = datetime.fromisoformat(data['last_opened']) if data.get('last_opened') else None

    if note:
        if client_updated > note.updated_at:
            note.title = data['title']
            note.content = data['content']
            note.folder = data['folder']
            note.images = data.get('images', [])
            note.updated_at = client_updated
            note.last_opened = client_last_opened or note.last_opened
            note.is_deleted = data.get('is_deleted', False)
    else:
        note = Note(
            id=data['id'],
            user_id=user_id,
            title=data['title'],
            content=data['content'],
            folder=data['folder'],
            images=data.get('images', []),
            created_at=client_created,
            updated_at=client_updated,
            last_opened=client_last_opened,
            is_deleted=data.get('is_deleted', False)
        )
        db.session.add(note)

    db.session.commit()
    return jsonify({"msg": "Note synced"}), 200


@jwt_required()
def get_notes():
    user_id = get_jwt_identity()
    notes = Note.query.filter_by(user_id=user_id, is_deleted=False).all()
    return jsonify([n.to_dict() for n in notes])

@jwt_required()
def delete_note(note_id):
    user_id = get_jwt_identity()
    note = Note.query.filter_by(id=note_id, user_id=user_id).first()

    if not note:
        return jsonify({"error": "Note not found"}), 404

    note.is_deleted = True
    note.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"msg": "Note deleted"}), 200

@jwt_required()
def sync_reminder():
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or 'id' not in data:
        return jsonify({"error": "Invalid payload"}), 400

    reminder = Reminder.query.filter_by(id=data['id'], user_id=user_id).first()

    client_updated_str = data.get('updated_at')
    if client_updated_str:
        client_updated = datetime.fromisoformat(client_updated_str)
    else:
        client_updated = datetime.utcnow()

    client_created_str = data.get('created_at')
    if client_created_str:
        client_created = datetime.fromisoformat(client_created_str)
    else:
        client_created = datetime.utcnow()

    client_day = datetime.fromisoformat(data['day']).date()

    if reminder:
        if client_updated > reminder.updated_at:
            reminder.title = data['title']
            reminder.description = data['description']
            reminder.date = data['date']
            reminder.time = data.get('time', '')
            reminder.color = data.get('color', '#0000FF')
            reminder.day = client_day
            reminder.updated_at = client_updated
            reminder.is_deleted = data.get('is_deleted', False)
    else:
        reminder = Reminder(
            id=data['id'],
            user_id=user_id,
            title=data['title'],
            description=data.get('description', ''),
            date=data['date'],
            time=data.get('time', ''),
            color=data.get('color', '#0000FF'),
            day=client_day,
            created_at=client_created,
            updated_at=client_updated,
            is_deleted=data.get('is_deleted', False)
        )
        db.session.add(reminder)

    db.session.commit()
    return jsonify({"msg": "Reminder synced"}), 200

@jwt_required()
def get_reminders():
    user_id = get_jwt_identity()
    reminders = Reminder.query.filter_by(user_id=user_id, is_deleted=False).all()
    return jsonify([r.to_dict() for r in reminders])

@jwt_required()
def delete_reminder(reminder_id):
    user_id = get_jwt_identity()
    reminder = Reminder.query.filter_by(id=reminder_id, user_id=user_id).first()

    if not reminder:
        return jsonify({"error": "Reminder not found"}), 404

    reminder.is_deleted = True
    reminder.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"msg": "Reminder deleted"}), 200


@jwt_required()
def transcribe_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    audio_file = request.files['file']
    if audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(audio_file.filename)
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    audio_file.save(save_path)

    try:
        result = model.transcribe(save_path, language="indonesian")
        transcript = result['text']
        return jsonify({'transcript': transcript}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



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
