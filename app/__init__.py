from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from dotenv import load_dotenv

load_dotenv()


mail = Mail()
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app) 
    
    from app.routes.api_route import auth_bs
    from app.routes.auth_route import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(auth_bs, url_prefix="/api")

    from app.models import User
    with app.app_context():
        db.create_all()

    return app