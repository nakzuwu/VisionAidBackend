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
auth_bp.route('/reset-password-view', methods=['GET'])(auth_controller.reset_password_view)
auth_bp.route('/verify-otp', methods=['POST'])(auth_controller.verify_otp)
auth_bp.route("/login/google")(auth_controller.login_google)
auth_bp.route("/login/callback")(auth_controller.login_callback)
auth_bp.route('/oauth/login', methods=['POST'])(auth_controller.login_google_token)
auth_bp.route('/password', methods=["PUT"])(auth_controller.update_password)
auth_bp.route('/username', methods=["PUT"])(auth_controller.update_username)
auth_bp.route('/history', methods=["GET"])(auth_controller.get_login_history)
auth_bp.route('/save-login', methods=["GETPOST"])(auth_controller.save_login_session)
auth_bp.route('/logout', methods=["POST"])(auth_controller.logout)