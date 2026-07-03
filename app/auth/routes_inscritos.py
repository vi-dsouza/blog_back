import os
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.services.inscritos import inscrever, ativar_inscrito, descadastrar_inscrito, contar_inscritos
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

insc_bp = Blueprint("insc", __name__)

def enviar_email_confirmacao(email_destino, nome_usuario, link_confirmacao):
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = os.environ.get("SMTP_PORT", 587)
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not all([smtp_server, smtp_user, smtp_password]):
        print("❌ Erro: Configurações de SMTP incompletas no arquivo .env")
        return False

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = email_destino
    msg['Subject'] = "Confirme sua inscrição - Newsletter Entre Ideias"

    corpo_html = f"""
    <html>
        <body>
            <h2>Olá, {nome_usuario}!</h2>
            <p>Obrigado por se inscrever na Newsletter Entre Ideias.</p>
            <p>Para ativar sua inscrição, clique no botão ou no link seguro abaixo:</p>
            <p>
                <a href="{link_confirmacao}" style="background-color: #7B5CFF; color: white; padding: 10px 20px; text-decoration: none; display: inline-block; border-radius: 5px;">
                    Confirmar Minha Inscrição
                </a>
            </p>
            <p style="font-size: 11px; color: #555;">Se o botão não funcionar, copie e cole este link no seu navegador:<br>{link_confirmacao}</p>
        </body>
    </html>
    """
    
    msg.attach(MIMEText(corpo_html, 'html'))

    try:
        port = int(smtp_port)
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_server, port)
        else:
            server = smtplib.SMTP(smtp_server, port)
            server.starttls() 

        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, email_destino, msg.as_string())
        server.quit()
        
        print(f"✅ E-mail de confirmação enviado com sucesso para: {email_destino}")
        return True

    except Exception as e:
        print(f"❌ Erro ao enviar e-mail via SMTP: {e}")
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
            link_confirmacao = f"http://localhost:3000/confirmar?token={token}"

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