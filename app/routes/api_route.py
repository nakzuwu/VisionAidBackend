from flask import Blueprint, request, jsonify
from app.controllers import api_controller

auth_bs = Blueprint("service", __name__)
auth_bs.route('/summarize', methods=['POST'])(api_controller.summarize_text)