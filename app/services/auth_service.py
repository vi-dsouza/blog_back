import bcrypt
from app.database import get_connection
from flask import request
import uuid
import os
import os
from werkzeug.utils import secure_filename
import base64

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

def criar_usuario(nome, email, senha, biografia, is_admin=False, foto_url=None):
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
        SELECT id FROM usuarios WHERE email = %s
    """
    valores = (email,)

    cursor.execute(sql, valores)

    if cursor.fetchone():
        cursor.close()
        conn.close()

        return {"error": "Email já cadastrado"}, 400
    
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

    sql = """
        INSERT INTO usuarios (nome, email, senha_hash, biografia, is_admin, foto_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    valores = (nome, email, senha_hash, biografia, is_admin, foto_url)

    cursor.execute(sql, valores)

    user_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "Usuário criado com sucesso", "id": user_id}, 201

def lista_todos_admins():
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
        SELECT id, nome, email, is_admin, biografia, foto_url FROM usuarios
    """
    cursor.execute(sql)

    resultados = cursor.fetchall()

    administradores = []

    for admin in resultados:
        # foto_url = f"{request.host_url}uploads/{admin[5]}" if admin[5] else None
        foto_url = admin[5] if admin[5] else None

        administradores.append({ 
            "id": admin[0],
            "nome": admin[1], 
            "email": admin[2], 
            "is_admin": admin[3], 
            "biografia": admin[4],
            "foto_url": foto_url 
        })

    cursor.close()
    conn.close()

    return administradores

def lista_admin(email):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        sql = """
            SELECT id, email FROM usuarios WHERE email = %s
        """
        valores = (email,)

        cursor.execute(sql, valores)
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return user
        
    except Exception as e:
        cursor.close()
        conn.close()
        return None

def lista_autores():
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
        SELECT nome, biografia, foto_url FROM usuarios
    """
    cursor.execute(sql)

    resultado = cursor.fetchall()
    info_autores = []

    for autor in resultado:
        # foto_url = f"{request.host_url}uploads/{autor[2]}" if autor[2] else None
        foto_url = autor[2] if autor[2] else None

        info_autores.append({
            "nome": autor[0],
            "biografia": autor[1],
            "foto_url": foto_url
        })

    cursor.close()
    conn.close()

    return info_autores

def del_admin(id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        sql = """
            SELECT id FROM usuarios WHERE id = %s
        """
        valores = (id,)

        cursor.execute(sql, valores)

        admin = cursor.fetchone()

        if not admin:
            cursor.close()
            conn.close()
            return {"error": "Administrador não encontrado"}, 404
        
        sql = """
            DELETE FROM usuarios WHERE id = %s
        """
        valores = (id,)

        cursor.execute(sql, valores)

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Administrador deletado com sucesso"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

def up_admin(id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        sql = """
            SELECT id, foto_url, nome, email, senha_hash, is_admin, biografia FROM usuarios WHERE id = %s
        """
        valores = (id,)

        cursor.execute(sql, valores)
        admin_atual = cursor.fetchone()

        if not admin_atual:
            return {"error": "Administrador não encontrado"}, 404

        # foto_antiga_url = admin_atual[1]
        foto_antiga_base64 = admin_atual[1]
        nome_atual = admin_atual[2]
        email_atual = admin_atual[3]
        senha_hash_atual = admin_atual[4]
        is_admin_atual = admin_atual[5]
        biografia_atual = admin_atual[6]

        nome = request.form.get("nome") or nome_atual
        email = request.form.get("email") or email_atual
        biografia = request.form.get("biografia") or biografia_atual

        senha = request.form.get("senha")
        if senha:
            senha_hash = bcrypt.hashpw(
                senha.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
        else:
            senha_hash = senha_hash_atual

        is_admin_raw = request.form.get("is_admin")
        if is_admin_raw is not None:
            is_admin = is_admin_raw in ["1", "true", "True"]
        else:
            is_admin = is_admin_atual

        foto_arquivo = request.files.get("foto")

        if foto_arquivo and foto_arquivo.filename != "":
            conteudo_bytes = foto_arquivo.read()
            encoded_string = base64.b64encode(conteudo_bytes).decode("utf-8")
            mime_type = foto_arquivo.content_type or "image/jpeg"

            foto_url = f"data:{mime_type};base64,{encoded_string}"
        else:
            foto_url = foto_antiga_base64

        sql = """
            UPDATE usuarios
            SET nome = %s,
                email = %s,
                senha_hash = %s,
                is_admin = %s,
                biografia = %s,
                foto_url = %s
            WHERE id = %s
        """

        valores = (nome, email, senha_hash, is_admin, biografia, foto_url, id)

        cursor.execute(sql, valores)
        conn.commit()

        return {"message": "Administrador atualizado com sucesso"}, 200

    except Exception as e:
        conn.rollback()
        print(f"Erro ao atualizar admin: {e}")
        return {"error": str(e)}, 500

    finally:
        cursor.close()
        conn.close()