from flask import request, jsonify
from summarizer import Summarizer
from app.models import User
from app import db
from app.models import Note
from datetime import datetime

model = Summarizer()

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

    if not note_id or not title:
        return jsonify({"error": "Missing fields"}), 400

    note = Note.query.filter_by(id=note_id, user_id=user.id).first()

    if note:
        # Update note
        note.title = title
        note.content = content
        note.updated_at = datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%S")
    else:
        # Create note
        note = Note(
            id=note_id,
            user_id=user.id,
            title=title,
            content=content,
            updated_at=datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%S")
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