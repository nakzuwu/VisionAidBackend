from flask import request, jsonify, url_for,current_app
from app import db, bcrypt
from app.models import User
from flask_jwt_extended import create_access_token
from app.utils.api_key_generator import generate_api_key
from flask_mail import Message
from app import mail
from app.utils.token import generate_token
from app.utils.token import verify_token
import random
from datetime import timedelta
from flask_dance.contrib.google import make_google_blueprint, google
from extensions import oauth
from datetime import datetime, timedelta
from flask import request
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
google = oauth.create_client('google')

def create_custom_token(user_id):
    additional_claims = {
        "sub": user_id,
        "type": "access"
    }
    return create_access_token(
        identity=user_id,
        additional_claims=additional_claims,
        expires_delta=timedelta( 
        days=1)
    )

def send_otp_email(email, otp):
    msg = Message("OTP Verifikasi VisionAid", recipients=[email])
    msg.body = f"Kode OTP kamu adalah: {otp}"
    mail.send(msg)

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
    otp_code = str(random.randint(100000, 999999))

    user = User(username=username, email=email, password=hashed, otp=otp_code, is_verified=False)
    user.generate_api_key()
    db.session.add(user)
    db.session.commit()

    send_otp_email(email, otp_code)

    return jsonify({
        "msg": "Registrasi berhasil, cek email untuk OTP",
        "user": {
            "username": user.username,
            "email": user.email
        }
    }), 201

def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password, password):
        access_token = create_custom_token(user.id)
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
    
def login_google():
    redirect_uri = url_for('auth.login_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

def login_callback():
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()

    email = user_info["email"]
    username = user_info["name"].replace(" ", "").lower()

    # Cek user di database
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            username=username,
            email=email,
            password="",
            otp="",
            is_verified=True
        )
        user.generate_api_key()
        db.session.add(user)
        db.session.commit()

    # Buat token
    access_token = create_custom_token(user.id)

    return jsonify({
        "msg": "Login OAuth berhasil",
        "token": access_token,
        "user": {
            "username": user.username,
            "email": user.email,
            "api_key": user.api_key
        }
    }), 200


def login_google_token():
    data = request.get_json()
    token = data.get("id_token")

    if not token:
        return jsonify({"msg": "Token tidak ditemukan"}), 400

    try:
        # Ambil CLIENT ID dari config
        client_id = current_app.config.get("GOOGLE_CLIENT_ID")

        # Verifikasi token menggunakan Google API
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)

        email = idinfo["email"]
        username = idinfo["name"].replace(" ", "").lower()

        # Lanjutkan login user seperti sebelumnya...
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                username=username,
                email=email,
                password="",
                otp="",
                is_verified=True
            )
            user.generate_api_key()
            db.session.add(user)
            db.session.commit()

        access_token = create_custom_token(user.id)

        return jsonify({
            "msg": "Login OAuth berhasil",
            "token": access_token,
            "user": {
                "username": user.username,
                "email": user.email,
                "api_key": user.api_key
            }
        }), 200

    except ValueError as e:
        return jsonify({"msg": "Token tidak valid", "error": str(e)}), 400


def request_reset():
    data = request.get_json()
    email = data.get('email')
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"msg": "Email tidak ditemukan"}), 404

    token = generate_token(user.email)
    reset_link = f"http://localhost:5000/#/reset-password?token={token}"

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


def verify_otp():
    data = request.get_json()
    email = data.get("email")
    otp_input = data.get("otp")

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"msg": "User tidak ditemukan"}), 404

    # Cek apakah sudah lebih dari 5 menit sejak user dibuat
    if datetime.utcnow() > user.created_at + timedelta(minutes=5):
        db.session.delete(user)
        db.session.commit()
        return jsonify({"msg": "OTP expired. Registrasi dibatalkan."}), 400

    if user.otp != otp_input:
        return jsonify({"msg": "OTP salah"}), 400

    user.is_verified = True
    user.otp = None
    db.session.commit()

    return jsonify({"msg": "Verifikasi berhasil"}), 200