from flask import request, jsonify
from summarizer import Summarizer
from app.models import User

model = Summarizer()

def summarize_text():
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({"error": "API Key is required"}), 401

    # Cek API Key ke database
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