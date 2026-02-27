import bcrypt
from app.database import get_connection
from flask import request

#cria admins
def criar_usuario(nome, email, senha, is_admin=False, foto_url=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))

    if cursor.fetchone():
        cursor.close()
        conn.close()

        return {"error": "Email já cadastrado"}, 400
    
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

    cursor.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, is_admin, foto_url)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id;
    """, (nome, email, senha_hash, is_admin, foto_url))

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
        SELECT id, nome, email, is_admin, foto_url FROM usuarios
    """)

    resultados = cursor.fetchall()

    administradores = []

    for admin in resultados:
        foto_url = f"{request.host_url}uploads/{admin[4]}" if admin[4] else None

        administradores.append({ 
            "id": admin[0],
            "nome": admin[1], 
            "email": admin[2], 
            "is_admin": admin[3], 
            "foto_url": foto_url 
        })

    cursor.close()
    conn.close()

    return administradores

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