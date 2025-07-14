from flask import request, jsonify, url_for,current_app
from app import db, bcrypt,mail
from app.models import User, LoginSession
from flask_jwt_extended import create_access_token, get_jwt, jwt_required, decode_token, get_jwt_identity
from app.utils.api_key_generator import generate_api_key
from flask_mail import Message
from app.utils.token import generate_token
from werkzeug.security import check_password_hash, generate_password_hash
from app.utils.token import verify_token
import random
from datetime import timedelta
from flask_dance.contrib.google import make_google_blueprint, google
from extensions import oauth
from datetime import datetime, timedelta
import uuid
from flask import request, render_template
from google.oauth2 import id_token
from google.auth.transport import requests
from blacklist_token import blacklisted_tokens
import requests as http_requests 
from user_agents import parse
import firebase_admin
from firebase_admin import credentials, auth  

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-adminsdk.json")  # Sesuaikan path-nya
    firebase_admin.initialize_app(cred)

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
    username = data['username']
    email = data['email']
    password = data['password']

    user = User.query.filter_by(email=email).first()

    # 🔁 Jika user sudah ada tapi belum verifikasi OTP, update OTP dan kirim ulang
    if user:
        if not user.is_verified:
            user.username = username  # biar user bisa ubah nama pas retry register
            user.password = bcrypt.generate_password_hash(password).decode('utf-8')
            user.otp = str(random.randint(100000, 999999))
            user.created_at = datetime.utcnow()
            db.session.commit()

            send_otp_email(user.email, user.otp)
            return jsonify({"message": "Akun sudah terdaftar tapi belum verifikasi. OTP baru telah dikirim."}), 200
        
        # ✅ Kalau sudah terverifikasi, tolak
        return jsonify({"message": "Email sudah digunakan"}), 409

    # ✳️ Buat akun baru
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    otp = str(random.randint(100000, 999999))

    user = User(
        username=username,
        email=email,
        password=hashed_password,
        api_key=uuid.uuid4().hex,
        is_verified=False,
        otp=otp,
        created_at=datetime.utcnow()
    )
    db.session.add(user)
    db.session.commit()

    send_otp_email(user.email, otp)

    return jsonify({"message": "Akun berhasil dibuat. Silakan verifikasi OTP."}), 201


def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.check_password_hash(user.password, password):  # gunakan bcrypt
        return jsonify({"message": "Username atau password salah"}), 401


    # 🔒 Cek apakah user sudah verifikasi OTP
    if not user.is_verified:
        return jsonify({
            "message": "Akun belum diverifikasi. Silakan cek email untuk OTP."
        }), 403

    # ✅ Login berhasil
    access_token = create_access_token(identity=str(user.id))

    # Ambil JTI token
    decoded = decode_token(access_token)
    jti = decoded.get("jti")

    # Simpan login session
    save_login_session(user.id, jti)

    return jsonify({
        "msg": "Login berhasil",
        "token": access_token,
        "user": {
            "username": user.username,
            "email": user.email,
            "api_key": user.api_key
        }
    }), 200

@jwt_required()
def logout():
    jti = get_jwt()["jti"]  
    blacklisted_tokens.add(jti)
    return jsonify({"msg": "Logout berhasil"}), 200
    
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
    try:
        data = request.get_json()
        token = data.get("id_token")

        if not token:
            return jsonify({"msg": "Token tidak ditemukan"}), 400

        # ✅ Verifikasi token Google via Firebase
        decoded_token = auth.verify_id_token(token)

        email = decoded_token.get("email")
        username = decoded_token.get("name", "user").replace(" ", "").lower()

        if not email:
            return jsonify({"msg": "Email tidak ditemukan dalam token"}), 400

        # ✅ Cari user, buat kalau belum ada
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                username=username,
                email=email,
                password="",       # Tidak digunakan
                otp="",
                is_verified=True,
                api_key=generate_api_key()
            )
            db.session.add(user)
            db.session.commit()

        # ✅ Buat JWT token
        access_token = create_access_token(identity=str(user.id))

        # Ambil JTI untuk sesi login
        decoded = decode_token(access_token)
        jti = decoded.get("jti")

        # Simpan riwayat login
        save_login_session(user.id, jti)

        return jsonify({
            "msg": "Login OAuth berhasil",
            "token": access_token,
            "user": {
                "username": user.username,
                "email": user.email,
                "api_key": user.api_key
            }
        }), 200

    except auth.InvalidIdTokenError as e:
        return jsonify({"msg": "Token tidak valid", "error": str(e)}), 400

    except Exception as e:
        return jsonify({"msg": "Terjadi kesalahan", "error": str(e)}), 500

def request_reset():
    data = request.get_json()
    email = data.get('email')
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"msg": "Email tidak ditemukan"}), 404

    token = generate_token(user.email)
    reset_link = f"https://visionaid.lolihunter.my.id/api/auth/reset-password-view?token={token}"

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

@jwt_required()
def get_login_history():
    current_user_id = get_jwt_identity()
    sessions = LoginSession.query.filter_by(user_id=current_user_id).order_by(LoginSession.login_time.desc()).all()

    return jsonify([{
        "device": s.device_info,
        "ip": s.ip_address,
        "login_time": s.login_time.isoformat()
    } for s in sessions]), 200

def save_login_session(user_id, jti):
    ip = request.headers.get('X-Forwarded-For') or request.remote_addr
    ua_string = request.headers.get('User-Agent', 'Unknown')
    user_agent = parse(ua_string)

    device_info = f"{user_agent.os.family} - {user_agent.device.family} ({user_agent.browser.family})"

    session = LoginSession(
        user_id=user_id,
        ip_address=ip,
        device_info=device_info,
        jwt_jti=jti
    )
    db.session.add(session)
    db.session.commit()


@jwt_required()
def update_username():
    user_id = get_jwt_identity()
    data = request.get_json()
    new_username = data.get('username')

    if not new_username:
        return jsonify({'error': 'Username tidak boleh kosong'}), 400

    user = User.query.get(user_id)
    user.username = new_username
    db.session.commit()

    # Generate new token
    access_token = create_access_token(identity=str(user.id))

    return jsonify({'msg': 'Username updated', 'token': access_token}), 200

@jwt_required()
def update_password():
    user_id = get_jwt_identity()
    data = request.get_json()
    old_pw = data.get('old_password')
    new_pw = data.get('new_password')

    user = User.query.get(user_id)

    if not bcrypt.check_password_hash(user.password, old_pw):
        return jsonify({'error': 'Password lama salah'}), 400

    user.password = bcrypt.generate_password_hash(new_pw)
    db.session.commit()

    # Generate new token
    access_token = create_access_token(identity=str(user.id))

    return jsonify({'msg': 'Password updated', 'token': access_token}), 200



def reset_password_view():
    token = request.args.get('token')
    email = verify_token(token)
    if not email:
        return "Token tidak valid atau kadaluarsa", 400
    return render_template("reset_password.html", token=token)

