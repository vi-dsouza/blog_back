import os
import traceback
import sys
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

# Certifique-se de que os caminhos de importação estão corretos para o seu projeto
from app.auth.routes import token_required 
from app.services.posts_service import criar_posts, postagens, de_post, editar_post, contar_posts

post_bp = Blueprint("post", __name__)

@post_bp.route("/postar", methods=["POST"])
@token_required
def criar_post(current_user_id):
    print("\n" + "="*50, file=sys.stderr)
    print("🚀 NOVA TENTATIVA DE POSTAGEM", file=sys.stderr)
    
    try:
        # 1. Captura dos dados do formulário
        titulo = request.form.get("titulo")
        autor = request.form.get("autor")
        hashtags = request.form.get("hashtags")
        conteudo = request.form.get("conteudo")
        data_str = request.form.get("data")
        
        print(f"📝 Título: {titulo}", file=sys.stderr)

        # 2. Tratamento da Data (Evitando o erro do Reloader no Windows)
        # Pegamos apenas a parte YYYY-MM-DD se a string for longa
        data_final = data_str[:10] if data_str else datetime.now().strftime('%Y-%m-%d')

        # 3. Lógica Robusta de Salvamento de Imagem
        post_file = request.files.get("post") 
        post_url_banco = None

        if post_file and post_file.filename != '':
            # --- DEFINIÇÃO DO CAMINHO ABSOLUTO ---
            # Isso garante que a pasta seja criada na raiz do projeto, não importa o terminal
            # 'os.getcwd()' aponta para a pasta onde você deu o comando 'python' ou 'flask run'
            root_path = os.getcwd() 
            upload_path = os.path.join(root_path, 'posts_image')
            
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
                print(f"📁 Pasta criada: {upload_path}", file=sys.stderr)
            
            # Gerar nome único com timestamp para evitar substituição de arquivos iguais
            extensao = os.path.splitext(post_file.filename)[1]
            filename = f"{datetime.now().timestamp()}{extensao}"
            filename = secure_filename(filename)
            
            # Caminho Final
            caminho_completo = os.path.join(upload_path, filename)
            
            # SALVAMENTO FÍSICO
            post_file.save(caminho_completo)
            
            post_url_banco = filename
            print(f"✅ ARQUIVO SALVO EM: {caminho_completo}", file=sys.stderr)
        else:
            print("⚠️ Nenhuma imagem recebida no campo 'post'.", file=sys.stderr)

        # 4. Chamada do Service para o Banco de Dados
        # Passamos a data tratada e o nome do arquivo salvo
        print("🔗 Gravando no banco de dados...", file=sys.stderr)
        response, status = criar_posts(
            titulo, data_final, autor, 
            hashtags, conteudo, post_url_banco
        )
        
        print(f"✨ Sucesso! Status: {status}", file=sys.stderr)
        print("="*50 + "\n", file=sys.stderr)
        
        return jsonify(response), status

    except Exception as e:
        print("\n🚨 ERRO NO PROCESSAMENTO:", file=sys.stderr)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@post_bp.route("/postagens", methods=["GET"])
@token_required
def buscar_posts(current_user_id):
    try:
        posts = postagens()
        if posts:
            return jsonify(posts), 200
        return jsonify({"message": "Nenhuma postagem encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@post_bp.route("/del_post/<int:id_post>", methods=["DELETE"])
@token_required
def deletar_post(current_user_id, id_post):
    resultado, status = de_post(id_post)
    return jsonify(resultado), status

@post_bp.route("update_post/<int:id_post>", methods=["PUT", "PATCH"])
@token_required
def atualizar_post(current_user_id, id_post):
    resultado, status = editar_post(id_post)
    return jsonify(resultado), status

@post_bp.route("/qtd_posts", methods=["GET"])
@token_required
def qtd_posts(current_user_id):
    count = contar_posts()
    return jsonify(count)