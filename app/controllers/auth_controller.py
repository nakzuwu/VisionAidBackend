from flask import request, jsonify
from app import db, bcrypt
from app.models import User
from flask_jwt_extended import create_access_token
from app.utils.api_key_generator import generate_api_key
from flask_mail import Message
from app import mail
from app.utils.token import generate_token
from app.utils.token import verify_token
from summarizer import Summarizer

def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    confirm = data.get("confirm")

    if not all([username, email, password, confirm]):
        return jsonify({"msg": "Lengkapi semua data"}), 400

    if password != confirm:
        return jsonify({"msg": "Password tidak cocok"}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"msg": "Username atau email sudah digunakan"}), 400

    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(username=username, email=email, password=hashed)
    user.generate_api_key()

    db.session.add(user)
    db.session.commit()

    return jsonify({
                "msg": "Registrasi berhasil",
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "api_key": user.api_key
                }
            }), 201

def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password, password):
        access_token = create_access_token(identity=user.id)
        return jsonify({
            "msg": "Login berhasil",
            "token": access_token,
            "user": {
                "username": user.username,
                "email": user.email,
                "api_key": user.api_key
            }
        }), 200
    return jsonify({"msg": "Login gagal"}), 401

def request_reset():
    data = request.get_json()
    email = data.get('email')
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"msg": "Email tidak ditemukan"}), 404

    token = generate_token(user.email)
    reset_link = f"http://localhost:5000/api/auth/verify-reset-token?token={token}"

    msg = Message("Reset Password VisionAid", recipients=[user.email])
    msg.body = f"Klik link berikut untuk reset password: {reset_link}"
    mail.send(msg)

    return jsonify({"msg": "Email reset password telah dikirim"}), 200

def verify_reset_token():
    token = request.args.get('token')
    email = verify_token(token)

    if not email:
        return jsonify({"msg": "Token tidak valid atau kadaluarsa"}), 400

    return jsonify({"msg": "Token valid", "email": email}), 200

def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')
    confirm = data.get('confirm_password')

    if not all([token, new_password, confirm]):
        return jsonify({"msg": "Lengkapi semua data"}), 400

    if new_password != confirm:
        return jsonify({"msg": "Password tidak cocok"}), 400

    email = verify_token(token)
    if not email:
        return jsonify({"msg": "Token tidak valid"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "User tidak ditemukan"}), 404

    hashed = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user.password = hashed
    db.session.commit()

    return jsonify({"msg": "Password berhasil direset"}), 200