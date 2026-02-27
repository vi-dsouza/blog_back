import os
from flask import Flask, send_from_directory
from app.auth.routes import auth_bp

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')

def create_app():
    app = Flask(__name__)

    app.config.from_object("app.config.Config")

    app.register_blueprint(auth_bp, url_prefix="/auth")

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(UPLOAD_FOLDER, filename)

    return app