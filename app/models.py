import uuid
from datetime import datetime
from app import db

def generate_uuid():
    return str(uuid.uuid4())

class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    otp = db.Column(db.String(6))
    is_verified = db.Column(db.Boolean, default=False)

    def generate_api_key(self):
        self.api_key = uuid.uuid4().hex


class LoginSession(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    device_info = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(64))
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    jwt_jti = db.Column(db.String(128), nullable=False)

    user = db.relationship('User', backref=db.backref('login_sessions', lazy=True))


class Note(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    folder = db.Column(db.String(128))
    images = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_opened = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    is_draft = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "content": self.content,
            "folder": self.folder,
            "images": self.images,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_opened": self.last_opened.isoformat(),
            "is_deleted": self.is_deleted,
            "is_draft": self.is_draft,
        }

class Reminder(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    date = db.Column(db.String(50))  # e.g., 'Jul 9, 2025'
    time = db.Column(db.String(10))  # e.g., '13:30'
    color = db.Column(db.String(10))  # e.g., '#FF5733'
    day = db.Column(db.Date)  # Date object for easier filtering
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "date": self.date,
            "time": self.time,
            "color": self.color,
            "day": self.day.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_deleted": self.is_deleted,
        }
