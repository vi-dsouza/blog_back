import os
from flask import send_from_directory
from app import create_app
from app.database import get_connection
from flask_cors import CORS
from app.auth.routes import auth_bp

app = create_app()

CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "http://localhost:3000",                  
                "https://www.entreideias.blog.br",       
                "https://entreideias.blog.br"            
            ]
        }
    },
    supports_credentials=True
)

# @app.route('/config_blog/<path:filename>')
# def serve_config_blog(filename):
#     path_root = os.path.join(os.getcwd(), 'config_blog')
#     return send_from_directory(path_root, filename)

def start_server():
    try:
        host = os.getenv("FLASK_HOST", "127.0.0.1")
        port = int(os.getenv("FLASK_PORT", 5000))
        debug = os.getenv("FLASK_DEBUG", "True") == "True"

        print("\n🚀 Servidor local iniciado com sucesso!")
        print(f"URL: http://{host}:{port}")

        app.run(host=host, port=port, debug=debug)
    except Exception as e:
        print(f"❌ Erro ao iniciar localmente: {e}")

if __name__ == "__main__":
    start_server()