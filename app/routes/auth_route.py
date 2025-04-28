from flask import Blueprint, request, jsonify
from app import db, bcrypt
from app.models import User
from app.controllers import auth_controller
from flask_jwt_extended import create_access_token

auth_bp = Blueprint("auth", __name__)
auth_bp.route("/register", methods=["POST"])(auth_controller.register)
auth_bp.route("/login", methods=["POST"])(auth_controller.login)
auth_bp.route('/verify-reset-token', methods=['GET'])(auth_controller.verify_reset_token)
auth_bp.route('/request-reset', methods=['POST'])(auth_controller.request_reset)
auth_bp.route('/reset-password', methods=['POST'])(auth_controller.reset_password)
    