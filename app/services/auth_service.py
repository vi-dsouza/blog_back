import bcrypt
from app.database import get_connection
from flask import request
import uuid
import os

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')

#cria admins
def criar_usuario(nome, email, senha, biografia, is_admin=False, foto_url=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))

    if cursor.fetchone():
        cursor.close()
        conn.close()

        return {"error": "Email já cadastrado"}, 400
    
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

    cursor.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, biografia, is_admin, foto_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (nome, email, senha_hash, biografia, is_admin, foto_url))

    user_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "Usuário criado com sucesso", "id": user_id}, 201

#lista admins
def lista_todos_admins():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, email, is_admin, biografia, foto_url FROM usuarios
    """)

    resultados = cursor.fetchall()

    administradores = []

    for admin in resultados:
        foto_url = f"{request.host_url}uploads/{admin[5]}" if admin[5] else None

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
        cursor.execute("""
            SELECT id, email FROM usuarios WHERE email = %s
        """, (email,))
        
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return user
        
    except Exception as e:
        cursor.close()
        conn.close()
        return None

#lista autores
def lista_autores():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT nome, biografia, foto_url FROM usuarios
    """)

    resultado = cursor.fetchall()
    info_autores = []

    for autor in resultado:
        foto_url = f"{request.host_url}uploads/{autor[2]}" if autor[2] else None

        info_autores.append({
            "nome": autor[0],
            "biografia": autor[1],
            "foto_url": foto_url
        })

    cursor.close()
    conn.close()

    return info_autores

#deleta admins
def del_admin(id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM usuarios WHERE id = %s",
            (id,)
        )

        admin = cursor.fetchone()

        if not admin:
            cursor.close()
            conn.close()
            return {"error": "Administrador não encontrado"}, 404
        
        cursor.execute(
            "DELETE FROM usuarios WHERE id = %s",
            (id,)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Administrador deletado com sucesso"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

#atualizar admin
import os
from werkzeug.utils import secure_filename

def up_admin(id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id, foto_url FROM usuarios WHERE id = %s",
            (id,)
        )

        admin_atual = cursor.fetchone()

        if not admin_atual:
            return {"error": "Administrador não encontrado"}, 404

        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        is_admin = request.form.get('is_admin')
        biografia = request.form.get('biografia')

        foto_arquivo = request.files.get('foto')

        campos = []
        valores = []

        # nome
        if nome:
            campos.append("nome = %s")
            valores.append(nome)

        # email
        if email:
            campos.append("email = %s")
            valores.append(email)

        # senha
        if senha:
            senha_hash = bcrypt.hashpw(
                senha.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')

            campos.append("senha_hash = %s")
            valores.append(senha_hash)

        # is_admin
        if is_admin is not None:
            valor_admin = is_admin in ['1', 'true', 'True']

            campos.append("is_admin = %s")
            valores.append(valor_admin)

        #biografia
        if biografia:
            campos.append("biografia = %s")
            valores.append(biografia)

        # foto
        if foto_arquivo and foto_arquivo.filename != '':
            # remove a foto antiga se existir
            if admin_atual[1]:
                caminho_antigo = os.path.join(UPLOAD_FOLDER, admin_atual[1])

                if os.path.exists(caminho_antigo):
                    os.remove(caminho_antigo)

            # gera nome único
            filename = f"{uuid.uuid4()}_{secure_filename(foto_arquivo.filename)}"

            caminho_novo = os.path.join(UPLOAD_FOLDER, filename)

            foto_arquivo.save(caminho_novo)

            campos.append("foto_url = %s")
            valores.append(filename)

        if not campos:
            return {"message": "Nenhum dado enviado para atualizar"}, 400

        valores.append(id)

        sql = f"""
            UPDATE usuarios
            SET {', '.join(campos)}
            WHERE id = %s
        """

        cursor.execute(sql, tuple(valores))
        conn.commit()

        return {
            "message": "Administrador atualizado com sucesso"
        }, 200

    except Exception as e:
        conn.rollback()
        return {"error": str(e)}, 500

    finally:
        cursor.close()
        conn.close()