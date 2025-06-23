import uuid
from datetime import datetime
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    otp = db.Column(db.String(6))
    is_verified = db.Column(db.Boolean, default=False)

    def generate_api_key(self):
        self.api_key = uuid.uuid4().hex

class Note(db.Model):
    id = db.Column(db.String(36), primary_key=True)  # pakai UUID string
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # << ini ditambah
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)
    is_draft = db.Column(db.Boolean, default=True)


    user = db.relationship('User', backref=db.backref('notes', lazy=True))

class LoginSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    device_info = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(64))
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    jwt_jti = db.Column(db.String(128), nullable=False)

    user = db.relationship('User', backref=db.backref('login_sessions', lazy=True))

