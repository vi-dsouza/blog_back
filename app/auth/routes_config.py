import os
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.auth.routes import token_required 
from app.services.config_service import configurar, obter_ultima_configuracao

blog_bp = Blueprint("blog", __name__)

@blog_bp.route("/configuracao", methods=["POST"])
@token_required
def criar_config(current_user_id):
    try:
        # 1. Dados de texto
        nome_blog = request.form.get("nome_blog")
        autor = request.form.get("autor")
        descricao_blog = request.form.get("descricao_blog")
        tags_do_blog = request.form.get("tags_do_blog")
        
        # 2. Data
        data_str = request.form.get("data_atualizacao")
        data_dt = datetime.strptime(data_str, '%Y-%m-%d') if data_str else datetime.now()

        # 3. Tratamento da Imagem (Chave 'banner')
        # Se o banco recebe null, é porque request.files.get("banner") não encontrava o arquivo
        banner_file = request.files.get("banner") 
        banner_url_nome = None
        
        if banner_file and banner_file.filename != '':
            # Caminho na raiz do projeto
            upload_path = os.path.join(os.getcwd(), 'config_blog')
            os.makedirs(upload_path, exist_ok=True)
            
            # Gerar nome único
            filename = secure_filename(banner_file.filename)
            filename = f"{datetime.now().timestamp()}_{filename}"
            
            # Salvar fisicamente
            banner_file.save(os.path.join(upload_path, filename))
            banner_url_nome = filename
            print(f"✅ Banner salvo: {filename}")
        else:
            print("⚠️ Aviso: Nenhum arquivo recebido na chave 'banner'")

        # 4. Enviar para o Service salvar no Banco
        response, status = configurar(
            nome_blog, data_dt, autor, 
            tags_do_blog, descricao_blog, banner_url_nome
        )
        
        return jsonify(response), status

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@blog_bp.route("/configuracao", methods=["GET"])
@token_required
def buscar_config(current_user_id):
    try:
        config = obter_ultima_configuracao()
        if config:
            return jsonify(config), 200
        return jsonify({"message": "Nenhuma configuração encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500