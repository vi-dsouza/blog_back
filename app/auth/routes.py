import os
import jwt
import datetime
import bcrypt
from functools import wraps
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import traceback
# Importações internas do seu projeto
from app.database import get_connection
from app.services.auth_service import criar_usuario, lista_todos_admins, del_admin, up_admin, lista_autores, lista_admin
# No topo do routes.py, garanta que o import está exatamente assim:
from app.services.enviar_email import enviar_email_recuperacao

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

@auth_bp.route("/esqueci-senha", methods=['POST'])
def esqueci_senha():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email")

        print(f"\n--- [LOG] Iniciando recuperação de senha para: {email} ---")

        if not email:
            print("[LOG WN] E-mail não foi enviado no corpo da requisição.")
            return jsonify({"error": "O e-mail é obrigatório"}), 400

        user = lista_admin(email)
        print(f"[LOG] Resultado da busca pelo usuário: {user}")

        if not user:
            print(f"[LOG WN] Usuário com e-mail {email} não encontrado no banco.")
            return jsonify({"message": "Se o e-mail existir, um link de redefinição foi enviado."}), 200

        user_id = user[0] 
        print(f"[LOG] ID do usuário encontrado: {user_id}")

        payload = {
            "reset_user_id": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        link_redefinicao = f"http://localhost:3000/admin/redefinir-senha?token={token}"
        print(f"[LOG] Token gerado com sucesso. Link: {link_redefinicao}")
        
        # Envia o e-mail
        enviar_email_recuperacao(email, link_redefinicao)

        return jsonify({"message": "E-mail de redefinição enviado com sucesso."}), 200
        
    except Exception as e:
        print("\n❌ --- [ERRO CRÍTICO NA ROTA /ESQUECI-SENHA] ---")
        traceback.print_exc()
        print("--------------------------------------------------\n")
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/redefinir-senha", methods=['POST'])
def redefinir_senha():
    try:
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        nova_senha = data.get("password")

        print("\n--- [LOG] Tentando redefinir senha ---")

        if not token or not nova_senha:
            print("[LOG WN] Token ou nova senha ausentes.")
            return jsonify({"error": "Token e nova senha são obrigatórios."}), 400

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id = payload["reset_user_id"]
            print(f"[LOG] Token validado com sucesso para o usuário ID: {user_id}")
        except jwt.ExpiredSignatureError:
            print("[LOG ER] O token JWT expirou.")
            return jsonify({"error": "O link de redefinição expirou!"}), 400
        except jwt.InvalidTokenError:
            print("[LOG ER] Token JWT inválido.")
            return jsonify({"error": "Token inválido!"}), 400

        salt = bcrypt.gensalt()
        senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), salt).decode('utf-8')

        print("[LOG] Atualizando senha no banco de dados...")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET senha_hash = %s WHERE id = %s", (senha_hash, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        print("[LOG SUCCESS] Senha atualizada com sucesso no banco.")
        return jsonify({"message": "Senha alterada com sucesso!"}), 200
        
    except Exception as e:
        print("\n❌ --- [ERRO CRÍTICO NA ROTA /REDEFINIR-SENHA] ---")
        traceback.print_exc() 
        print("--------------------------------------------------\n")
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
def register(current_user_id):
    try:
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")
        is_admin = str(request.form.get("is_admin")).lower() == "true"
        biografia = request.form.get("biografia")
        foto = request.files.get("foto")

        missing_fields = []
        if not nome:
            missing_fields.append("nome")
        if not email:
            missing_fields.append("email")
        if not senha:
            missing_fields.append("senha")
        if not biografia:
            missing_fields.append("biografia")

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

        response, status = criar_usuario(nome, email, senha, biografia, is_admin=is_admin, foto_url=foto_url)
        return jsonify(response), status
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@auth_bp.route('/admins', methods=['GET'])
@token_required
def lista_admins(current_user_id): # Recebe o ID do decorador
    admins = lista_todos_admins()
    return jsonify(admins), 200

@auth_bp.route('/autores', methods=["GET"])
def info_autores():
    autores = lista_autores()
    return jsonify(autores), 200


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