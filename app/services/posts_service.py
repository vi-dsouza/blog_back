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
        sql = """
            SELECT id_post, titulo, data, autor, hashtags, post_url, conteudo, likes_count
            FROM postagens
            WHERE id_post = %s
        """
        valores = (id_post,)
        cursor.execute(sql, valores)

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

    sql = """
        SELECT id_post FROM postagens WHERE titulo = %s
    """
    valores = (titulo,)

    cursor.execute(sql, valores)

    if cursor.fetchone():
        cursor.close()
        conn.close()

        return {"error": "Já existe um post com esse titulo!"}, 400
    
    sql = """
        INSERT INTO postagens (titulo, data, autor, hashtags, conteudo, post_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id_post    
    """
    valores = (titulo, data, autor, hashtags, conteudo, post_url)
    
    cursor.execute(sql, valores)

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
        sql = """
            SELECT id_post, titulo, data, autor, hashtags, post_url, conteudo, likes_count
            FROM postagens
            ORDER BY id_post DESC
        """

        cursor.execute(sql)

        rows = cursor.fetchall()
        
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

        sql = """
            SELECT id_post FROM postagens WHERE id_post = %s
        """
        valores = (id_post,)

        cursor.execute(sql, valores)

        post = cursor.fetchone()

        if not post:
            cursor.close()
            conn.close()
            return {"error": "Postagem não encontrada"}, 404

        sql = """
            DELETE FROM postagens WHERE id_post = %s
        """
        valores = (id_post,)

        cursor.execute(sql, valores)

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
        sql = """
            SELECT id_post, post_url, titulo, autor, hashtags, conteudo, data
            FROM postagens
            WHERE id_post = %s
        """
        valores = (id_post,)

        cursor.execute(sql, valores)

        post_atual = cursor.fetchone()

        if not post_atual:
            return {"error": "Postagem não encontrada"}, 404

        foto_antiga_url = post_atual[1]
        titulo_atual = post_atual[2]
        autor_atual = post_atual[3]
        hashtags_atual = post_atual[4]
        conteudo_atual = post_atual[5]
        data_atual = post_atual[6]

        titulo = request.form.get('titulo') or titulo_atual
        autor = request.form.get('autor') or autor_atual
        hashtags = request.form.get('hashtags') or hashtags_atual
        conteudo = request.form.get('conteudo') or conteudo_atual
        data = request.form.get('data') or data_atual
        
        foto_arquivo = request.files.get('post')

        if foto_arquivo and foto_arquivo.filename != '':
            if foto_antiga_url:
                caminho_antigo = os.path.join(UPLOAD_FOLDER, foto_antiga_url)
                if os.path.exists(caminho_antigo):
                    os.remove(caminho_antigo)

            filename = f"{uuid.uuid4()}_{secure_filename(foto_arquivo.filename)}"
            caminho_novo = os.path.join(UPLOAD_FOLDER, filename)
            
            foto_arquivo.save(caminho_novo)
            foto_url = filename
        else:
            foto_url = foto_antiga_url

        sql = """
            UPDATE postagens
            SET titulo = %s,
                autor = %s,
                hashtags = %s,
                conteudo = %s,
                data = %s,
                post_url = %s
            WHERE id_post = %s
        """
        valores = (titulo, autor, hashtags, conteudo, data, foto_url, id_post)

        cursor.execute(sql, valores)
        conn.commit()

        return {
            "message": "Postagem updated com sucesso"
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
        sql = """
            SELECT COUNT(*) FROM postagens
        """

        cursor.execute(sql)

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
        sql = """
            SELECT id_post FROM postagens WHERE id_post = %s
        """
        valores = (id_post,)

        cursor.execute(sql, valores)
        
        if not cursor.fetchone():
            print(f"[DEBUG] Post {id_post} não foi encontrado no banco.")
            return {"error": "Postagem não encontrada"}, 404

        if action == 'like':
            print("[DEBUG] Executando query de LIKE...")

            sql = """
                UPDATE postagens
                SET likes_count = likes_count + 1
                WHERE id_post = %s
                RETURNING likes_count
            """
            valores = (id_post,)

            cursor.execute(sql, valores)

        elif action == 'unlike':
            print("[DEBUG] Executando query de UNLIKE...")
            
            sql = """
                UPDATE postagens
                SET likes_count = GREATEST(0, likes_count - 1)
                WHERE id_post = %s
                RETURNING likes_count
            """
            valores = (id_post,)

            cursor.execute(sql, valores)
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

def salvar_imagem_interna():
    """
    Recebe uma imagem avulsa vinda do editor de texto, salva no servidor
    e retorna a URL pública necessária para o Quill renderizar.
    """
    try:
        foto_arquivo = request.files.get('image')

        if not foto_arquivo or foto_arquivo.filename == '':
            return {"error": "Nenhum arquivo enviado"}, 400
        
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        filename = f"{uuid.uuid4()}_{secure_filename(foto_arquivo.filename)}"
        caminho_salvamento = os.path.join(UPLOAD_FOLDER, filename)

        foto_arquivo.save(caminho_salvamento)

        url_publica = f"{request.host_url}posts_image/{filename}"

        return {"url": url_publica}, 201

    except Exception as e:
        print("\n" + "="*50)
        print("[ERRO NO UPLOAD DE IMAGEM INTERNA]:")
        print(f"Mensagem do erro: {e}")
        print("-"*50)
        traceback.print_exc()
        print("="*50 + "\n")
        return {"error": str(e)}, 500
