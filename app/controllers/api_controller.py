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
from app.models import User, Note
from app import db
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required
from datetime import datetime
import whisper
from pathlib import Path

kbbi_cache = {}
model = Summarizer()
reader = easyocr.Reader(['id', 'en'], gpu=False)
model = whisper.load_model("base") 

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

    summary = model(input_text, min_length=50, max_length=150)

    return jsonify({
        "summary": summary
    }), 200

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def create_note():
    data = request.json
    note_id = data.get('id') or str(uuid.uuid4())
    title = data.get('title', 'Untitled Note')
    content = data.get('content', '')
    folder = data.get('folder', 'Default')
    created_at = datetime.utcnow().isoformat()
    updated_at = created_at

    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO notes (id, title, content, folder, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)',
        (note_id, title, content, folder, created_at, updated_at)
    )
    db.commit()

    return jsonify({
        'id': note_id, 'title': title, 'content': content,
        'folder': folder, 'created_at': created_at, 'updated_at': updated_at
    }), 201

def update_note(note_id):
    data = request.json
    title = data.get('title')
    content = data.get('content')
    folder = data.get('folder')
    updated_at = datetime.utcnow().isoformat()

    cursor = db.cursor()
    cursor.execute(
        'UPDATE notes SET title=%s, content=%s, folder=%s, updated_at=%s WHERE id=%s',
        (title, content, folder, updated_at, note_id)
    )
    db.commit()

    if cursor.rowcount == 0:
        return jsonify({'error': 'Note not found'}), 404

    return jsonify({
        'id': note_id, 'title': title, 'content': content,
        'folder': folder, 'updated_at': updated_at
    }), 200

def get_note(note_id):
    cursor = db.cursor()
    cursor.execute('SELECT id, title, content, folder, created_at, updated_at FROM notes WHERE id=%s', (note_id,))
    note = cursor.fetchone()

    if not note:
        return jsonify({'error': 'Note not found'}), 404

    cursor.execute('SELECT filename FROM images WHERE note_id=%s', (note_id,))
    images = cursor.fetchall()

    return jsonify({
        'id': note[0], 'title': note[1], 'content': note[2], 'folder': note[3],
        'created_at': note[4], 'updated_at': note[5],
        'images': [img[0] for img in images]
    }), 200

def get_all_notes():
    cursor = db.cursor()
    cursor.execute('SELECT id, title, folder, created_at, updated_at FROM notes')
    notes = cursor.fetchall()
    return jsonify([
        {'id': n[0], 'title': n[1], 'folder': n[2], 'created_at': n[3], 'updated_at': n[4]}
        for n in notes
    ]), 200

def get_folders():
    cursor = db.cursor()
    cursor.execute('SELECT DISTINCT folder FROM notes')
    folders = cursor.fetchall()
    return jsonify([f[0] for f in folders]), 200

def upload_image(note_id):
    cursor = db.cursor()
    cursor.execute('SELECT id FROM notes WHERE id=%s', (note_id,))
    if not cursor.fetchone():
        return jsonify({'error': 'Note not found'}), 404

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        image_id = uuid.uuid4().hex
        cursor.execute(
            'INSERT INTO images (id, note_id, filename) VALUES (%s, %s, %s)',
            (image_id, note_id, filename)
        )
        db.commit()

        return jsonify({'id': image_id, 'filename': filename, 'url': f'/uploads/{filename}'}), 201

    return jsonify({'error': 'Invalid file type'}), 400

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