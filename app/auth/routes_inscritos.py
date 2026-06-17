import os
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.services.inscritos import inscrever, ativar_inscrito, descadastrar_inscrito

insc_bp = Blueprint("insc", __name__)

@insc_bp.route("/inscrever", methods=["POST"])
def inscricao():
    try:
        nome = request.form.get("nome")
        email = request.form.get("email")
        sobrenome = request.form.get("sobrenome")
        consentimento_bruto = request.form.get("consentimento_lgpd")
        consentimento_lgpd = consentimento_bruto in ['on', 'true', True]
        status_inicial = "pendente"

        response, status = inscrever(
            nome=nome, 
            email=email, 
            status=status_inicial, 
            consentimento_lgpd=consentimento_lgpd,
            sobrenome=sobrenome
        )

        #preparacao para o disparo de email
        if status == 201:
            token = response.get("token")

            #monta o link que o usuario vai clicar no e-mail
            link_confirmacao = f"http://localhost:5000/confirmar?token={token}"

            #funcao temporaria que simula o envio de e-mail
            enviar_email_confirmacao(email, nome, link_confirmacao)

            if "token" in response:
                del response["token"]

        return jsonify(response), status
    except Exception as e:
        print(f"Erro na rota de inscrição: {e}") 
        return jsonify({"error": "Erro interno no servidor."}), 500
    
#funcao provisoria
def enviar_email_confirmacao(email_destino, nome_usuario, link):
    """
    Esta função simula o envio do e-mail. Quando você escolher seu provedor
    (Flask-Mail, SendGrid, etc.), você só precisará mudar o código aqui dentro.
    """
    print("\n" + "="*50)
    print(f"📧 SIMULANDO ENVIO DE E-MAIL PARA: {email_destino}")
    print(f"Olá, {nome_usuario}!")
    print("Obrigado por se inscrever na Newsletter Entre Ideias.")
    print(f"Para ativar sua inscrição, clique no link seguro abaixo:\n")
    print(link)
    print("="*50 + "\n") 

@insc_bp.route("/confirmar", methods=["GET"])
def confirmar():
    try:
        token = request.args.get("token")
        if not token:
            return jsonify({"error": "O token de confirmação está ausente."}), 400
        
        response, status = ativar_inscrito(token)
        return jsonify(response), status
    except Exception as e:
        print(f"Erro na rota de confirmação: {e}")
        return jsonify({"error": "Erro interno ao confirmar a inscrição."}), 500
    
@insc_bp.route("/descadastrar", methods=["POST"])
def descadastrar():
    try:
        # Recebe o e-mail do corpo da requisição
        email = request.form.get("email")
        
        if not email:
            return jsonify({"error": "O e-mail é obrigatório."}), 400
        
        response, status_code = descadastrar_inscrito(email)
        
        return jsonify(response), status_code

    except Exception as e:
        print(f"Erro na rota de descadastro: {e}")
        return jsonify({"error": "Erro interno no servidor."}), 500