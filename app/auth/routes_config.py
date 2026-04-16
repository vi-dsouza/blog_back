from flask import Blueprint, request, jsonify
# Importa o decorador que você já criou
from app.auth.routes import token_required 
from app.services.config_service import configurar, obter_ultima_configuracao
# Importa a conexão com o banco
from app.database import get_connection
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from datetime import datetime
import traceback # Adicione este import no topo

load_dotenv()

blog_bp = Blueprint("blog", __name__)

UPLOAD_BANNER = os.path.join(os.getcwd(), 'config_blog')
SECRET_KEY = os.getenv("SECRET_KEY")

@blog_bp.route("/configuracao", methods=["POST"])
@token_required
def criar_config(current_user_id):
    try:
        # 1. Captura dos dados do formulário
        nome_blog = request.form.get("nome_blog")
        autor = request.form.get("autor")
        descricao_blog = request.form.get("descricao_blog")
        
        # 2. Tratamento da DATA (String -> Objeto Python)
        # Se vier vazio do front, usamos a data e hora atual
        data_str = request.form.get("data_atualizacao")
        if data_str:
            try:
                # Ajuste o formato '%Y-%m-%d' se o seu front enviar algo diferente
                data_atualizacao = datetime.strptime(data_str, '%Y-%m-%d')
            except ValueError:
                data_atualizacao = datetime.now()
        else:
            data_atualizacao = datetime.now()

        # 3. Tratamento das TAGS
        # Se você enviar um array pelo Nuxt, ele pode chegar como string separada por vírgulas
        tags_do_blog = request.form.get("tags_do_blog") 

        # 4. Tratamento do BANNER (Imagem)
        banner = request.files.get("foto")
        banner_url = None
        
        if banner and banner.filename != '':
            os.makedirs(UPLOAD_BANNER, exist_ok=True)
            filename = secure_filename(banner.filename)
            # Adicionamos um timestamp ao nome do arquivo para evitar nomes duplicados
            filename = f"{datetime.now().timestamp()}_{filename}"
            caminho = os.path.join(UPLOAD_BANNER, filename)
            banner.save(caminho)
            banner_url = filename

        # 5. Chamada da função de service (passando os dados processados)
        # Dica: É bom passar o current_user_id para saber quem alterou a config
        response, status = configurar(
            nome_blog, 
            data_atualizacao, 
            autor, 
            tags_do_blog, 
            descricao_blog, 
            banner_url
        )
        
        return jsonify(response), status

    # except Exception as e:
    #     print(f"Erro ao criar config: {e}") # Log no terminal para você debugar
    #     return jsonify({"error": "Erro interno ao salvar configurações"}), 500
    except Exception as e:
        print("\n" + "="*50)
        print("ERRO DETALHADO NO BACKEND:")
        traceback.print_exc() # Isso imprime o caminho completo do erro no terminal
        print("="*50 + "\n")
        return jsonify({"error": str(e)}), 500
    
@blog_bp.route("/configuracao", methods=["GET"])
@token_required
def buscar_config(current_user_id):
    try:
        # Chama a função do serviço
        config = obter_ultima_configuracao()
        
        if config:
            return jsonify(config), 200
        
        # Caso não exista nenhuma configuração no banco ainda
        return jsonify({"message": "Nenhuma configuração encontrada"}), 404
        
    except Exception as e:
        print(f"Erro ao buscar config: {e}")
        return jsonify({"error": "Erro interno ao buscar configurações"}), 500