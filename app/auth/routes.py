import os
from flask import Blueprint, request, jsonify
from app.database import get_connection
from app.services.auth_service import criar_usuario
from werkzeug.utils import secure_filename

auth_bp = Blueprint("auth", __name__)
UPLOAD_FOLDER = "uploads"

@auth_bp.route("/test-db")
def test_db():
    from app.database import get_connection

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return {"status": "Banco conectado com sucesso"}
    except Exception as e:
        return {"error": str(e)}, 500

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")

    conn = get_connection()
    cursor = conn.cursor

    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404
    
    return jsonify({"message": "Login válido"})

@auth_bp.route("/register", methods=['POST'])
def register():
    try:
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")
        foto = request.files.get("foto")

        if not nome or not email or not senha:
            return jsonify({"error": "Campos obrigatórios faltando"}), 400
        
        foto_url = None

        if foto:
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            filename = secure_filename(foto.filename)
            caminho = os.path.join(UPLOAD_FOLDER, filename)

            foto.save(caminho)

            foto_url = caminho

        response, status = criar_usuario(nome, email, senha, foto_url=foto_url)
        return jsonify(response), status
    except Exception as e:
        return jsonify({"error": str(e)}), 500