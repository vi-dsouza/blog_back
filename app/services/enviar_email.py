import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def enviar_email_recuperacao(email_destino, link_redefinicao):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = email_destino
    msg['Subject'] = "Recuperação de Senha - Painel Administrativo"

    corpo_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h2 style="color: #7B5CFF;">Recuperação de Senha</h2>
                <p>Olá,</p>
                <p>Você solicitou a redefinição de senha para o seu painel de administrador. Clique no botão abaixo para escolher uma nova senha:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{link_redefinicao}" 
                       style="background: #7B5CFF; color: white; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 6px; display: inline-block;">
                        Redefinir Minha Senha
                    </a>
                </div>
                <p style="font-size: 12px; color: #666;">Este link é válido por 15 minutos. Se você não solicitou essa alteração, pode ignorar este e-mail com segurança.</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 11px; color: #999; text-align: center;">Painel Administrativo © 2026</p>
            </div>
        </body>
    </html>
    """
    
    msg.attach(MIMEText(corpo_html, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        
        server.sendmail(smtp_user, email_destino, msg.as_string())
        server.quit()
        
        print(f"E-mail de recuperação enviado com sucesso para {email_destino}")
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail: {str(e)}")
        return False