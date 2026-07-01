from app.database import get_connection
from flask import request
import os
import traceback
import uuid
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'posts_image')


def buscar_post_por_id(id_post):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id_post, titulo, data, autor, hashtags, post_url, conteudo, likes_count
            FROM postagens
            WHERE id_post = %s
        """, (id_post,))
        row = cursor.fetchone()

        if not row:
            return {"error": "Postagem não encontrada"}, 404

        post_url = f"{request.host_url}posts_image/{row[5]}" if row[5] else None

        return {
            "id": row[0],
            "titulo": row[1],
            "data": row[2].strftime('%Y-%m-%d') if row[2] else "",
            "autor": row[3],
            "hashtags": row[4],
            "post_url": post_url,
            "conteudo": row[6],
            "likes_count": row[7]
        }, 200
    finally:
        cursor.close()
        conn.close()

#criar posts
def criar_posts(titulo, data, autor, hashtags, conteudo, post_url=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id_post FROM postagens WHERE titulo = %s", (titulo,))

    if cursor.fetchone():
        cursor.close()
        conn.close()

        return {"error": "Já existe um post com esse titulo!"}, 400

    cursor.execute(
        """
            INSERT INTO postagens (titulo, data, autor, hashtags, conteudo, post_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_post
        """, (titulo, data, autor, hashtags, conteudo, post_url))
    
    post_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "Postagem criada com sucesso.", "id": post_id}, 201

#listar posts
def postagens():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id_post, titulo, data, autor, hashtags, post_url, conteudo, likes_count
            FROM postagens
            ORDER BY id_post DESC  -- Removemos o LIMIT 1
        """)
        rows = cursor.fetchall() # Usamos fetchall() para pegar a lista toda
        
        posts = []
        for row in rows:
            post_url = f"{request.host_url}posts_image/{row[5]}" if row[5] else None
            posts.append({
                "id": row[0],
                "titulo": row[1],
                "data": row[2].strftime('%Y-%m-%d') if row[2] else "",
                "autor": row[3],
                "hashtags": row[4],
                "post_url": post_url,
                "conteudo": row[6],
                "likes_count": row[7]
            })
        return posts
    finally:
        cursor.close()
        conn.close()

#deletar posts
def de_post(id_post):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id_post FROM postagens WHERE id_post = %s", (id_post,))
        post = cursor.fetchone()

        if not post:
            cursor.close()
            conn.close()
            return {"error": "Postagem não encontrada"}, 404

        cursor.execute("DELETE FROM postagens WHERE id_post = %s", (id_post,))

        conn.commit()
        cursor.close()
        conn.close()        

        return {"message": "Postagem deletada com sucesso"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

# editar post (Dinâmico)
def editar_post(id_post):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id_post, post_url FROM postagens WHERE id_post = %s",
            (id_post,)
        )
        post_atual = cursor.fetchone()

        if not post_atual:
            return {"error": "Postagem não encontrada"}, 404

        titulo = request.form.get('titulo')
        autor = request.form.get('autor')
        hashtags = request.form.get('hashtags')
        conteudo = request.form.get('conteudo')
        data = request.form.get('data')
        
        foto_arquivo = request.files.get('post')

        campos = []
        valores = []

        # Título
        if titulo:
            campos.append("titulo = %s")
            valores.append(titulo)

        # Autor
        if autor:
            campos.append("autor = %s")
            valores.append(autor)

        # Hashtags
        if hashtags:
            campos.append("hashtags = %s")
            valores.append(hashtags)

        # Conteúdo
        if conteudo:
            campos.append("conteudo = %s")
            valores.append(conteudo)

        # Data
        if data:
            campos.append("data = %s")
            valores.append(data)

        if foto_arquivo and foto_arquivo.filename != '':
            if post_atual[1]:
                caminho_antigo = os.path.join(UPLOAD_FOLDER, post_atual[1])
                if os.path.exists(caminho_antigo):
                    os.remove(caminho_antigo)

            filename = f"{uuid.uuid4()}_{secure_filename(foto_arquivo.filename)}"
            caminho_novo = os.path.join(UPLOAD_FOLDER, filename)
            
            foto_arquivo.save(caminho_novo)

            campos.append("post_url = %s")
            valores.append(filename)

        if not campos:
            return {"message": "Nenhum dado enviado para atualizar"}, 400

        valores.append(id_post)

        # Monta o SQL dinâmico
        sql = f"""
            UPDATE postagens
            SET {', '.join(campos)}
            WHERE id_post = %s
        """

        cursor.execute(sql, tuple(valores))
        conn.commit()

        return {
            "message": "Postagem atualizada com sucesso"
        }, 200

    except Exception as e:
        if conn:
            conn.rollback()
        return {"error": str(e)}, 500

    finally:
        cursor.close()
        conn.close()

def contar_posts():
    conn = get_connection()
    cursor = conn.cursor()
    try: 
        cursor.execute("SELECT COUNT(*) FROM postagens")
        count = cursor.fetchone()[0]
        return count
    finally:
        cursor.close()
        conn.close()

 

def alternar_curtida(id_post, action='like'):
    print(f"\n[DEBUG] Iniciando alternar_curtida - ID: {id_post}, Ação: {action}")
    
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id_post FROM postagens WHERE id_post = %s", (id_post,))
        if not cursor.fetchone():
            print(f"[DEBUG] Post {id_post} não foi encontrado no banco.")
            return {"error": "Postagem não encontrada"}, 404

        if action == 'like':
            print("[DEBUG] Executando query de LIKE...")
            cursor.execute(
                """
                UPDATE postagens 
                SET likes_count = likes_count + 1 
                WHERE id_post = %s 
                RETURNING likes_count
                """, (id_post,)
            )
        elif action == 'unlike':
            print("[DEBUG] Executando query de UNLIKE...")
            cursor.execute(
                """
                UPDATE postagens 
                SET likes_count = GREATEST(0, likes_count - 1) 
                WHERE id_post = %s 
                RETURNING likes_count
                """, (id_post,)
            )
        else:
            print(f"[DEBUG] Ação inválida recebida: {action}")
            return {"error": "Ação inválida. Use 'like' ou 'unlike'."}, 400

        novo_total_likes = cursor.fetchone()[0]
        conn.commit()
        
        print(f"[DEBUG] Sucesso! Novo total de likes: {novo_total_likes}")
        return {"success": True, "likes_count": novo_total_likes}, 200

    except Exception as e:
        conn.rollback()
        
        # ====== CONSOLE DE ERROS ======
        print("\n" + "="*50)
        print("[ERRO CRÍTICO] Falha ao alternar curtida no PostgreSQL:")
        print(f"Mensagem do erro: {e}")
        print("-"*50)
        traceback.print_exc()
        print("="*50 + "\n")
        # =============================================
        
        return {"error": str(e)}, 500
    finally:
        cursor.close()
        conn.close()

