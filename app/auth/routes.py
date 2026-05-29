import os
import jwt
import datetime
import bcrypt
from functools import wraps
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Importações internas do seu projeto
from app.database import get_connection
from app.services.auth_service import criar_usuario, lista_todos_admins, del_admin, up_admin

load_dotenv()

auth_bp = Blueprint("auth", __name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
SECRET_KEY = os.getenv("SECRET_KEY")

# --- DECORADOR DE PROTEÇÃO DE ROTA ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"error": "Token ausente!"}), 401
        
        try:
            if "Bearer " in token:
                token = token.split(" ")[1]
            
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user_id = data["user_id"]
        except Exception:
            return jsonify({"error": "Token inválido ou expirado!"}), 401

        # O decorador passa o current_user_id como primeiro argumento para a função f
        return f(current_user_id, *args, **kwargs)
    
    return decorated

# --- ROTAS PÚBLICAS ---

@auth_bp.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return {}, 200

    data = request.get_json(silent=True) or {}
    email = data.get("email")
    senha_digitada = data.get("senha") 

    if not email or not senha_digitada:
        return jsonify({"error": "E-mail e senha são obrigatórios"}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, senha_hash, nome, foto_url FROM usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            user_id, hashed_password, nome_usuario, foto_usuario = user
            
            # Verificação segura com bcrypt
            senha_bytes = senha_digitada.encode('utf-8')
            hash_bytes = hashed_password if isinstance(hashed_password, bytes) else hashed_password.encode('utf-8')

            if bcrypt.checkpw(senha_bytes, hash_bytes):
                payload = {
                    "user_id": user_id,
                    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
                }
            
                token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

                # PyJWT 2.0+ retorna string, mas garantimos aqui
                if isinstance(token, bytes):
                    token = token.decode('utf-8')
                
                return jsonify({
                    "message": "Login realizado com sucesso",
                    "token": token,
                    "user_id": user_id,
                    "user_nome": nome_usuario,
                    "user_foto": foto_usuario
                }), 200
        
        return jsonify({"error": "E-mail ou senha incorretos"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/test-db")
def test_db():
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

# --- ROTAS PROTEGIDAS (Exigem Token) ---

@auth_bp.route("/register", methods=['POST'])
@token_required
def register(): # Recebe o ID do decorador
    try:
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")
        is_admin = str(request.form.get("is_admin")).lower() == "true"
        foto = request.files.get("foto")

        missing_fields = []
        if not nome:
            missing_fields.append("nome")
        if not email:
            missing_fields.append("email")
        if not senha:
            missing_fields.append("senha")

        if missing_fields:
            return jsonify({
                "error": "Campos obrigatórios faltando",
                "missing_fields": missing_fields
            }), 400
        
        foto_url = None
        if foto:
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filename = secure_filename(foto.filename)
            caminho = os.path.join(UPLOAD_FOLDER, filename)
            foto.save(caminho)
            foto_url = filename

        response, status = criar_usuario(nome, email, senha, is_admin=is_admin, foto_url=foto_url)
        return jsonify(response), status
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@auth_bp.route('/admins', methods=['GET'])
@token_required
def lista_admins(current_user_id): # Recebe o ID do decorador
    admins = lista_todos_admins()
    return jsonify(admins), 200

@auth_bp.route('/admin/del/<int:id>', methods=["DELETE"])
@token_required
def deletar_admin(current_user_id, id): # Recebe current_user_id antes do id da URL
    response, status = del_admin(id)
    return jsonify(response), status

@auth_bp.route('/admin/edit/<int:id>', methods=["PUT", "PATCH"])
@token_required
def edit_admin_route(current_user_id, id): # Recebe current_user_id antes do id da URL
    resultado, status = up_admin(id) 
    return jsonify(resultado), status