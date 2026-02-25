import bcrypt
from app.database import get_connection

def criar_usuario(nome, email, senha, is_admin=False, foto_url=None):
    conn = get_connection()
    cursor = conn.cursor()

    #verifica se email ja existe
    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))

    if cursor.fetchone():
        cursor.close()
        conn.close()

        return {"error": "Email já cadastrado"}, 400
    
    #criptografa a senha
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