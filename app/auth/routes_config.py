import os
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.auth.routes import token_required 
from app.services.config_service import configurar, obter_ultima_configuracao
import base64

blog_bp = Blueprint("blog", __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_PATH = os.path.join(BASE_DIR, 'config_blog')

@blog_bp.route("/configuracao", methods=["POST"])
@token_required
def criar_config(current_user_id):
    try:
        nome_blog = request.form.get("nome_blog")
        autor = request.form.get("autor")
        descricao_blog = request.form.get("descricao_blog")
        tags_do_blog = request.form.get("tags_do_blog")

        data_str = request.form.get("data_atualizacao")
        data_dt = datetime.strptime(data_str, '%Y-%m-%d') if data_str else datetime.now()

        banner_file = request.files.get("banner") 
        banner_base64 = None
        
        # Converte a imagem para Data URL Base64
        if banner_file and banner_file.filename != '':
            conteudo_bytes = banner_file.read()
            encoded_string = base64.b64encode(conteudo_bytes).decode('utf-8')
            mime_type = banner_file.content_type or "image/jpeg"
            
            # Formato completo legível direto no navegador: data:image/png;base64,...
            banner_base64 = f"data:{mime_type};base64,{encoded_string}"

        # Envia a string do Base64 diretamente para o serviço do banco
        response, status = configurar(
            nome_blog, data_dt, autor, 
            tags_do_blog, descricao_blog, banner_base64
        )
        
        return jsonify(response), status

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
# def criar_config(current_user_id):
#     try:
#         nome_blog = request.form.get("nome_blog")
#         autor = request.form.get("autor")
#         descricao_blog = request.form.get("descricao_blog")
#         tags_do_blog = request.form.get("tags_do_blog")

#         data_str = request.form.get("data_atualizacao")
#         data_dt = (
#             datetime.strptime(data_str, "%Y-%m-%d")
#             if data_str
#             else datetime.now()
#         )

#         banner_file = request.files.get("banner")
#         banner_url_nome = None

#         if banner_file and banner_file.filename != "":
#             os.makedirs(UPLOAD_PATH, exist_ok=True)

#             filename = secure_filename(banner_file.filename)
#             filename = f"{datetime.now().timestamp()}_{filename}"

#             caminho_completo = os.path.join(UPLOAD_PATH, filename)
#             banner_file.save(caminho_completo)

#             banner_url_nome = filename
#             print(f"✅ Banner salvo com sucesso em: {caminho_completo}")
#         else:
#             print("⚠️ Aviso: Nenhum arquivo recebido na chave 'banner'")

#         response, status = configurar(
#             nome_blog,
#             data_dt,
#             autor,
#             tags_do_blog,
#             descricao_blog,
#             banner_url_nome,
#         )

#         return jsonify(response), status

#     except Exception as e:
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500

@blog_bp.route("/configuracao", methods=["GET"])
def buscar_config():
    try:
        config = obter_ultima_configuracao()
        if config:
            return jsonify(config), 200
        return jsonify({"message": "Nenhuma configuração encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500