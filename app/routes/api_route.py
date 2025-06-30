from flask import Blueprint, send_from_directory, current_app
from app.controllers import api_controller

auth_bs = Blueprint("service", __name__)
auth_bs.route('/summarize', methods=['POST'])(api_controller.summarize_text)
# auth_bs.route('/notes', methods=['POST'])(api_controller.create_or_update_note)
# auth_bs.route('/notes', methods=['GET'])(api_controller.get_notes)
# auth_bs.route('/notes/<note_id>', methods=['DELETE'])(api_controller.delete_note)
auth_bs.route('/ocr', methods=['POST'])(api_controller.ocr_image)
auth_bs.route('/notes', methods=['POST'])(api_controller.create_note)
auth_bs.route('/notes/<note_id>', methods=['PUT'])(api_controller.update_note)
auth_bs.route('/notes/<note_id>', methods=['GET'])(api_controller.get_note)
auth_bs.route('/notes', methods=['GET'])(api_controller.get_all_notes)
auth_bs.route('/notes/folders', methods=['GET'])(api_controller.get_folders)
auth_bs.route('/notes/<note_id>/images', methods=['POST'])(api_controller.upload_image)
auth_bs.route('/transcribe', methods=['POST'])(api_controller.transcribe_audio)

auth_bs.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)