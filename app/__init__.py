import os
from flask import Flask, send_from_directory
from app.auth.routes import auth_bp
from app.auth.routes_config import blog_bp
from app.auth.routes_posts import post_bp
from app.auth.routes_inscritos import insc_bp
from app.auth.dashboard import dashboard_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
POSTS_FOLDER = os.path.join(BASE_DIR, 'posts_image')
CONFIG_BLOG_FOLDER = os.path.join(BASE_DIR, 'config_blog')

def create_app():
    app = Flask(__name__)

    app.config.from_object("app.config.Config")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(blog_bp, url_prefix='/blog')
    app.register_blueprint(post_bp, url_prefix='/post')
    app.register_blueprint(insc_bp, url_prefix='/insc')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(UPLOAD_FOLDER, filename)
    
    @app.route('/posts_image/<filename>')
    def serve_posts(filename):
        return send_from_directory(POSTS_FOLDER, filename)

    @app.route('/config_blog/<path:filename>')
    def serve_config_blog(filename):
        return send_from_directory(CONFIG_BLOG_FOLDER, filename)

    return app