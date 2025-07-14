from flask import Blueprint, send_from_directory, current_app
from app.controllers import api_controller

auth_bs = Blueprint("service", __name__)
auth_bs.route('/summarize', methods=['POST'])(api_controller.summarize_text)
auth_bs.route('/ocr', methods=['POST'])(api_controller.ocr_image)
auth_bs.route('/transcribe', methods=['POST'])(api_controller.transcribe_audio)
auth_bs.route('/notes/sync', methods=['POST'])(api_controller.sync_note)
auth_bs.route('/notes/all', methods=['GET'])(api_controller.get_notes)
auth_bs.route('/notes/<note_id>/delete', methods=['POST'])(api_controller.delete_note)
auth_bs.route('/reminders/sync', methods=['POST'])(api_controller.sync_reminder)
auth_bs.route('/reminders/all', methods=['GET'])(api_controller.get_reminders)
auth_bs.route('/reminders/<reminder_id>/delete', methods=['POST'])(api_controller.delete_reminder)


auth_bs.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)