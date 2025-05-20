from dotenv import load_dotenv
import os
from datetime import timedelta

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS') == 'True'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL') == 'True'
    MAIL_USERNAME = "enkajet439@gmail.com"
    MAIL_PASSWORD = "poel svfb hubs tgea"
    MAIL_DEFAULT_SENDER = "jamal"