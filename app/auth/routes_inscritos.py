import os
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify
import resend
from app.services.inscritos import inscrever, ativar_inscrito, descadastrar_inscrito, contar_inscritos
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

insc_bp = Blueprint("insc", __name__)

load_dotenv()
FRONTEND_URL = os.getenv("FRONTEND_URL")

def enviar_email_confirmacao(email_destino, nome_usuario, link_confirmacao):
    resend.api_key = os.getenv("RESEND_API_KEY")

    if not resend.api_key:
        print("❌ Erro: Chave de API do Resend (RESEND_API_KEY) não configurada.")
        return False

    corpo_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h2 style="color: #7B5CFF;">Olá, {nome_usuario}!</h2>
                <p>Obrigado por se inscrever na Newsletter Entre Ideias.</p>
                <p>Para ativar sua inscrição e começar a receber nossos conteúdos, clique no botão seguro abaixo:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{link_confirmacao}" style="background-color: #7B5CFF; color: white; padding: 12px 24px; text-decoration: none; font-weight: bold; display: inline-block; border-radius: 6px;">
                        Confirmar Minha Inscrição
                    </a>
                </p>
                <p style="font-size: 11px; color: #666;">Se o botão acima não funcionar, copie e cole este link no seu navegador:<br>{link_confirmacao}</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 11px; color: #999; text-align: center;">Entre Ideias © 2026</p>
            </div>
        </body>
    </html>
    """

    try:
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": email_destino,
            "subject": "Confirme sua inscrição - Newsletter Entre Ideias",
            "html": corpo_html
        })
        
        print(f"✅ E-mail de confirmação enviado via Resend para: {email_destino}")
        return True

    except Exception as e:
        print(f"❌ Erro ao enviar e-mail via Resend: {e}")
        return False

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

        if status == 201:
            token = response.get("token")
            link_confirmacao = f"{FRONTEND_URL}/confirmar?token={token}"

            enviar_email_confirmacao(email, nome, link_confirmacao)

            if "token" in response:
                del response["token"]

        return jsonify(response), status
    except Exception as e:
        print(f"Erro na rota de inscrição: {e}") 
        return jsonify({"error": "Erro interno no servidor."}), 500

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
    
@insc_bp.route("/descadastrar", methods=["POST", "GET"])
def descadastrar():
    try:
        email = request.form.get("email") or request.args.get("email")
        
        if not email:
            return jsonify({"error": "O e-mail é obrigatório."}), 400
        
        response, status_code = descadastrar_inscrito(email)
        
        return jsonify(response), status_code

    except Exception as e:
        print(f"Erro na rota de descadastro: {e}")
        return jsonify({"error": "Erro interno no servidor."}), 500
    
@insc_bp.route("/qtd_inscritos", methods=["GET"])
def qtd_inscritos():
    count = contar_inscritos()
    return jsonify(count)