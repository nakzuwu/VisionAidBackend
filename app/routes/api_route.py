from flask import Blueprint, request, jsonify
from app.controllers import api_controller

auth_bs = Blueprint("service", __name__)
auth_bs.route('/summarize', methods=['POST'])(api_controller.summarize_text)
auth_bs.route('/notes', methods=['POST'])(api_controller.create_or_update_note)
auth_bs.route('/notes', methods=['GET'])(api_controller.get_notes)
auth_bs.route('/notes/<note_id>', methods=['DELETE'])(api_controller.delete_note)
auth_bs.route('/ocr', methods=['POST'])(api_controller.ocr_image)