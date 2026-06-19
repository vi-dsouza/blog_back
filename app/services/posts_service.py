from app.database import get_connection
from flask import request
import os

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'posts_image')

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
    
#editar post
#editar post
import uuid
from werkzeug.utils import secure_filename

# editar post (Dinâmico)
def editar_post(id_post):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Busca os dados atuais para poder remover a imagem antiga depois
        cursor.execute(
            "SELECT id_post, post_url FROM postagens WHERE id_post = %s",
            (id_post,)
        )
        post_atual = cursor.fetchone()

        if not post_atual:
            return {"error": "Postagem não encontrada"}, 404

        # 2. Captura os dados do formulário (vêm do request.form)
        titulo = request.form.get('titulo')
        autor = request.form.get('autor')
        hashtags = request.form.get('hashtags')
        conteudo = request.form.get('conteudo')
        data = request.form.get('data')
        
        foto_arquivo = request.files.get('post') # Chave 'post' conforme seu padrão anterior

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

        # Lógica da Foto (Remoção da antiga e salvamento da nova)
        if foto_arquivo and foto_arquivo.filename != '':
            # remove a foto antiga do servidor se ela existir no registro
            if post_atual[1]:
                caminho_antigo = os.path.join(UPLOAD_FOLDER, post_atual[1])
                if os.path.exists(caminho_antigo):
                    os.remove(caminho_antigo)

            # gera nome único para a nova foto
            filename = f"{uuid.uuid4()}_{secure_filename(foto_arquivo.filename)}"
            caminho_novo = os.path.join(UPLOAD_FOLDER, filename)
            
            # Salva fisicamente
            foto_arquivo.save(caminho_novo)

            # Adiciona ao SQL
            campos.append("post_url = %s")
            valores.append(filename)

        # Se nada foi enviado, retorna aviso
        if not campos:
            return {"message": "Nenhum dado enviado para atualizar"}, 400

        # Adiciona o ID ao final para o WHERE
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

#contar postagens
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

# Mudar status de curtida (Toggle Like)
import traceback  # <-- Importe isso no topo do arquivo para ver a linha exata do erro

def alternar_curtida(id_post, action='like'):
    # Print para acompanhar quando a função é chamada e com quais dados
    print(f"\n[DEBUG] Iniciando alternar_curtida - ID: {id_post}, Ação: {action}")
    
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Verifica se o post realmente existe antes de alterar
        cursor.execute("SELECT id_post FROM postagens WHERE id_post = %s", (id_post,))
        if not cursor.fetchone():
            print(f"[DEBUG] Post {id_post} não foi encontrado no banco.")
            return {"error": "Postagem não encontrada"}, 404

        # 2. Executa o UPDATE dinâmico dependendo da ação vinda do Vue.js
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

        # Pega a contagem atualizada do banco de dados
        novo_total_likes = cursor.fetchone()[0]
        conn.commit()
        
        print(f"[DEBUG] Sucesso! Novo total de likes: {novo_total_likes}")
        return {"success": True, "likes_count": novo_total_likes}, 200

    except Exception as e:
        conn.rollback()
        
        # ====== AQUI ESTÁ O SEU CONSOLE DE ERROS ======
        print("\n" + "="*50)
        print("[ERRO CRÍTICO] Falha ao alternar curtida no PostgreSQL:")
        print(f"Mensagem do erro: {e}")
        print("-"*50)
        traceback.print_exc()  # Mostra o caminho e a linha exata do erro no terminal
        print("="*50 + "\n")
        # =============================================
        
        return {"error": str(e)}, 500
    finally:
        cursor.close()
        conn.close()