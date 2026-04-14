import os
from flask import Blueprint, request, jsonify
from app.database import get_connection
from app.services.auth_service import criar_usuario, lista_todos_admins, del_admin, up_admin
from werkzeug.utils import secure_filename
import jwt
import datetime
from functools import wraps
from flask import request, jsonify

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization") # O front deve enviar no Header

        if not token:
            return jsonify({"error": "Token ausente!"}), 401
        
        try:
            # Remove o prefixo "Bearer " se existir
            if "Bearer " in token:
                token = token.split(" ")[1]
            
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user_id = data["user_id"]
        except Exception:
            return jsonify({"error": "Token inválido ou expirado!"}), 401

        return f(current_user_id, *args, **kwargs)
    
    return decorated

auth_bp = Blueprint("auth", __name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
SECRET_KEY = os.getenv("SECRET_KEY")

# @auth_bp.route("/test-db")
# @token_required
# def test_db():
#     from app.database import get_connection

#     try:
#         conn = get_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT 1;")
#         cursor.fetchone()
#         cursor.close()
#         conn.close()
#         return {"status": "Banco conectado com sucesso"}
#     except Exception as e:
#         return {"error": str(e)}, 500

import bcrypt
from flask import request, jsonify

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    # Certifique-se que o front envia 'senha'. Se no Nuxt estiver 'password', mude aqui.
    senha_digitada = data.get("senha") 

    if not email or not senha_digitada:
        return jsonify({"error": "E-mail e senha são obrigatórios"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, senha_hash FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        user_id, hashed_password = user
        
        # 1. Verifica a senha
        if bcrypt.checkpw(senha_digitada.encode('utf-8'), hashed_password.encode('utf-8')):
            
            # 2. SE a senha estiver correta, gera o token (NÃO dê return antes disso)
            payload = {
                "user_id": user_id,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
            
            # 3. Retorna TUDO de uma vez
            return jsonify({
                "message": "Login realizado com sucesso",
                "token": token,
                "user_id": user_id
            }), 200
    
    # Se cair aqui, ou o usuário não existe ou a senha está errada
    return jsonify({"error": "E-mail ou senha incorretos"}), 401


@auth_bp.route("/register", methods=['POST'])
@token_required
def register():
    try:
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")
        is_admin  = str(request.form.get("is_admin")).lower() == "true"
        foto = request.files.get("foto")
        

        if not nome or not email or not senha:
            return jsonify({"error": "Campos obrigatórios faltando"}), 400
        
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
def lista_admins():
    admins = lista_todos_admins()
    return jsonify(admins), 200

@auth_bp.route('/admin/del/<int:id>', methods=["DELETE"])
@token_required
def deletar_admin(id):
    response, status = del_admin(id)
    return jsonify(response), status

@auth_bp.route('/admin/edit/<int:id>', methods=["PUT", "PATCH"])
@token_required
def edit_admin_route(id):
    resultado, status = up_admin(id) 
    return jsonify(resultado), status
