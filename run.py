import os
from app import create_app
from app.database import get_connection

def start_server():
    try:
        app = create_app()

        host = os.getenv("FLASK_HOST", "127.0.0.1")
        port = int(os.getenv("FLASK_PORT", 5000))
        debug = os.getenv("FLASK_DEBUG" "True") == "True"

        print("\n🚀 Servidor iniciado com sucesso!")
        print(f"Ambiente: {'Desenvolvimento' if debug else 'Produção'}")
        print(f"URL: http://{host}:{port}")

        app.run(host=host, port=port, debug=debug)
    except Exception as e:
        print("❌ Erro ao iniciar o servidor!")
        print(f"Detalhes: {e}")

if __name__ == "__main__":
    start_server()