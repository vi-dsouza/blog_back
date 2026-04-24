import os
from flask import Flask, send_from_directory
from app.auth.routes import auth_bp
from app.auth.routes_config import blog_bp
from app.auth.routes_posts import post_bp

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
POSTS_FOLDER = os.path.join(os.getcwd(), 'posts_image')

def create_app():
    app = Flask(__name__)

    app.config.from_object("app.config.Config")

    app.register_blueprint(auth_bp, url_prefix="/auth")

    app.register_blueprint(blog_bp, url_prefix='/blog')

    app.register_blueprint(post_bp, url_prefix='/post')

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(UPLOAD_FOLDER, filename)
    
    @app.route('/posts_image/<filename>')
    def serve_posts(filename):
        return send_from_directory(POSTS_FOLDER, filename)

    return app