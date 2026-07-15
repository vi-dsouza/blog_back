import os
import traceback
import sys
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.auth.routes import token_required 
from app.services.posts_service import criar_posts, postagens, de_post, editar_post, contar_posts, alternar_curtida, buscar_post_por_id, salvar_imagem_interna
from app.services.email_novos_posts import notifica_inscritos

post_bp = Blueprint("post", __name__)

@post_bp.route("/postar", methods=["POST"])
@token_required
def criar_post(current_user_id):
    print("\n" + "="*50, file=sys.stderr)
    print("🚀 NOVA TENTATIVA DE POSTAGEM", file=sys.stderr)
    
    try:
        titulo = request.form.get("titulo")
        autor = request.form.get("autor")
        hashtags = request.form.get("hashtags")
        conteudo = request.form.get("conteudo")
        data_str = request.form.get("data")
        
        print(f"📝 Título: {titulo}", file=sys.stderr)

        data_final = data_str[:10] if data_str else datetime.now().strftime('%Y-%m-%d')

        post_file = request.files.get("post") 
        post_url_banco = None

        if post_file and post_file.filename != '':
            root_path = os.getcwd() 
            upload_path = os.path.join(root_path, 'posts_image')
            
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
                print(f"📁 Pasta criada: {upload_path}", file=sys.stderr)
            
            extensao = os.path.splitext(post_file.filename)[1]
            filename = f"{datetime.now().timestamp()}{extensao}"
            filename = secure_filename(filename)
            
            caminho_completo = os.path.join(upload_path, filename)
     
            post_file.save(caminho_completo)
            
            post_url_banco = filename
            print(f"✅ ARQUIVO SALVO EM: {caminho_completo}", file=sys.stderr)
        else:
            print("⚠️ Nenhuma imagem recebida no campo 'post'.", file=sys.stderr)

        print("🔗 Gravando no banco de dados...", file=sys.stderr)
        response, status = criar_posts(
            titulo, data_final, autor, 
            hashtags, conteudo, post_url_banco
        )

        if status in [200, 201]:
            print("✉️ Enviando notificações para os inscritos...", file=sys.stderr)

            post_id = response.get("id") if isinstance(response, dict) else None
            base_url = os.getenv("FRONTEND_URL", request.host_url.rstrip("/"))
            link_post = f"{base_url}/postagem/{post_id}" if post_id else f"{base_url}/postagem"

            notifica_inscritos(titulo=titulo, link_post=link_post)
        else:
            print("⚠️ Post não foi criado com sucesso no service. Pulando envio de e-mails.", file=sys.stderr)

        
        print(f"✨ Sucesso! Status: {status}", file=sys.stderr)
        print("="*50 + "\n", file=sys.stderr)
        
        return jsonify(response), status

    except Exception as e:
        print("\n🚨 ERRO NO PROCESSAMENTO:", file=sys.stderr)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@post_bp.route("/postagens", methods=["GET"])
def buscar_posts():
    try:
        posts = postagens()
        if posts:
            return jsonify(posts), 200
        return jsonify({"message": "Nenhuma postagem encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@post_bp.route("/<int:id_post>", methods=["GET"])
def buscar_post_unico(id_post):
    try:
        post, status = buscar_post_por_id(id_post)
        return jsonify(post), status
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

@post_bp.route("/curtir/<int:id_post>/like", methods=["POST"])
def like_post(id_post):
    data = request.get_json() or {}
    action = data.get('action', 'like')

    resultado, status = alternar_curtida(id_post, action)
    return jsonify(resultado), status

@post_bp.route("/upload", methods=["POST"])
@token_required
def upload_imagem_editor(current_user_id):
    resultado, status = salvar_imagem_interna()
    return jsonify(resultado), status