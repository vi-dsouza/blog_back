import os
import jwt
import datetime
import bcrypt
from functools import wraps
from threading import Lock
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import traceback
from app.database import get_connection
from app.services.auth_service import criar_usuario, lista_todos_admins, del_admin, up_admin, lista_autores, lista_admin
from app.services.enviar_email import enviar_email_recuperacao

load_dotenv()

auth_bp = Blueprint("auth", __name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
SECRET_KEY = os.getenv("SECRET_KEY")
MAX_FAILED_ATTEMPTS = int(os.getenv("MAX_FAILED_ATTEMPTS", "3"))
LOCKOUT_SECONDS = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "60"))
FRONTEND_URL = os.getenv("FRONTEND_URL")
failed_login_attempts = {}
failed_login_lock = Lock()


def _get_login_attempt_key(email):
    normalized_email = (email or "").strip().lower()
    return (normalized_email, request.remote_addr or "unknown")


def _get_failed_login_state(key):
    with failed_login_lock:
        now = datetime.datetime.utcnow()
        state = failed_login_attempts.get(key)
        if state and state.get("blocked_until") and state["blocked_until"] <= now:
            failed_login_attempts.pop(key, None)
            return None
        return state


def _register_failed_login(key):
    with failed_login_lock:
        now = datetime.datetime.utcnow()
        state = failed_login_attempts.get(key)
        if not state:
            state = {"count": 0, "blocked_until": None}

        state["count"] += 1
        if state["count"] >= MAX_FAILED_ATTEMPTS:
            state["blocked_until"] = now + datetime.timedelta(seconds=LOCKOUT_SECONDS)

        failed_login_attempts[key] = state
        return state


def _clear_failed_login(key):
    with failed_login_lock:
        failed_login_attempts.pop(key, None)


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

        return f(current_user_id, *args, **kwargs)
    
    return decorated

@auth_bp.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return {}, 200

    data = request.get_json(silent=True) or {}
    email = data.get("email")
    senha_digitada = data.get("senha")

    if not email or not senha_digitada:
        return jsonify({"error": "E-mail e senha são obrigatórios"}), 400

    attempt_key = _get_login_attempt_key(email)
    failed_state = _get_failed_login_state(attempt_key)
    
    # 1. Verifica se já está bloqueado
    if failed_state and failed_state.get("blocked_until") and failed_state["blocked_until"] > datetime.datetime.utcnow():
        remaining_seconds = max(1, int((failed_state["blocked_until"] - datetime.datetime.utcnow()).total_seconds()))
        return jsonify({
            "error": f"Muitas tentativas incorretas. Tente novamente em {remaining_seconds} segundos."
        }), 403

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, senha_hash, nome, foto_url FROM usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        autenticado = False
        user_id, nome_usuario, foto_usuario = None, None, None

        if user:
            user_id, hashed_password, nome_usuario, foto_usuario = user
            senha_bytes = senha_digitada.encode('utf-8')
            hash_bytes = hashed_password if isinstance(hashed_password, bytes) else hashed_password.encode('utf-8')
            
            # Verifica a senha real
            if bcrypt.checkpw(senha_bytes, hash_bytes):
                autenticado = True
        else:
            # Isso impede o timing attack sem estourar erro no Python
            hash_falso = b'$2b$12$Lg9k2M1V8m7S8g9K01234Oeb2vG9FkRzQWxzNl9o2vG9FkRzQWxzN'
            bcrypt.checkpw(senha_digitada.encode('utf-8'), hash_falso)
            autenticado = False

        if autenticado:
            # Sucesso: limpa as falhas e gera o token
            _clear_failed_login(attempt_key)

            payload = {
                "user_id": user_id,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
            if isinstance(token, bytes):
                token = token.decode('utf-8')

            return jsonify({
                "message": "Login realizado com sucesso",
                "token": token,
                "user_id": user_id,
                "user_nome": nome_usuario,
                "user_foto": foto_usuario
            }), 200

        # Se chegou aqui, falhou (seja por senha errada ou usuário inexistente)
        failed_state = _register_failed_login(attempt_key)
        
        if failed_state["count"] >= MAX_FAILED_ATTEMPTS:
            return jsonify({
                # Texto alterado para segundos para o front ler perfeitamente os 60s
                "error": f"Conta temporariamente bloqueada por {LOCKOUT_SECONDS} segundos após várias tentativas incorretas."
            }), 403

        # Mensagem genérica para não dar pistas ao atacante
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

        link_redefinicao = f"{FRONTEND_URL}/admin/redefinir-senha?token={token}"
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
def lista_admins(current_user_id):
    admins = lista_todos_admins()
    return jsonify(admins), 200

@auth_bp.route('/autores', methods=["GET"])
def info_autores():
    autores = lista_autores()
    return jsonify(autores), 200

@auth_bp.route('/admin/del/<int:id>', methods=["DELETE"])
@token_required
def deletar_admin(current_user_id, id):
    response, status = del_admin(id)
    return jsonify(response), status

@auth_bp.route('/admin/edit/<int:id>', methods=["PUT", "PATCH"])
@token_required
def edit_admin_route(current_user_id, id):
    resultado, status = up_admin(id) 
    return jsonify(resultado), status