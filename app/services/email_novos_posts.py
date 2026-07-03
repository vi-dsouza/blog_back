import os 
import resend
from urllib.parse import quote
from dotenv import load_dotenv
from app.database import get_connection
from flask import request

load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")

def busca_leitores():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        sql = """
            SELECT email FROM inscritos WHERE status = 'ativo'
        """

        cursor.execute(sql)

        emails = [linha[0] for linha in cursor.fetchall()]
        conn.close()

        return emails
    except Exception as e:
        print(f"Erro ao buscar os emails no banco de dados: {e}")
        return []
    finally:
        if conn:
            conn.close()
    
def gera_html_email(titulo, link_post, email_destino=None):
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    unsubscribe_url = f"{frontend_url.rstrip('/')}/descadastrar"

    if email_destino:
        unsubscribe_url = f"{unsubscribe_url}?email={quote(email_destino)}"

    return f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; background-color: #f4f4f7; padding: 20px; margin: 0;">
            <div style="max-width: 600px; margin: 0 auto; padding: 30px; background: #ffffff; border: 1px solid #e8e8e8; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <h2 style="color: #7B5CFF; margin-top: 0; font-size: 24px;">{titulo}</h2>
                <p style="font-size: 16px; color: #555;">Olá! Acabamos de publicar um novo artigo no blog que você acompanha. Não perca as últimas novidades!</p>
                
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{link_post}" 
                       style="background: #7B5CFF; color: white; padding: 14px 28px; text-decoration: none; font-weight: bold; border-radius: 6px; display: inline-block; font-size: 16px; box-shadow: 0 3px 5px rgba(123,92,255,0.3);">
                        Clique Aqui para Ler o Post
                    </a>
                </div>
                
                <p style="font-size: 14px; color: #666;">Se o botão acima não funcionar, copie e leve o link ao seu navegador:<br>
                <a href="{link_post}" style="color: #7B5CFF;">{link_post}</a></p>
                
                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #999; text-align: center; line-height: 1.4;">
                    Você recebeu este e-mail porque está inscrito em nossa newsletter de testes.<br>
                    <a href="{unsubscribe_url}" style="color: #7B5CFF; text-decoration: underline;">Descadastrar-se</a>
                </p>
            </div>
        </body>
    </html>
    """

def notifica_inscritos(titulo, link_post):
    lista_destinatarios = busca_leitores()

    if not lista_destinatarios:
        print("Aviso: Nenhum email encontrado no banco.")
        lista_destinatarios = ["entreideiasvs@gmail.com"]

    sucesso = True

    for email_unico in lista_destinatarios:
        html_email = gera_html_email(titulo, link_post, email_unico)

        try:
            print(f"Enviando e-mail individual para: {email_unico}...")
            resend.Emails.send({
                "from": "Entre Ideias <contato@entreideias.blog.br>",
                "to": email_unico,
                "subject": f"Novo Post: {titulo}",
                "html": html_email
            })
        except Exception as error:
            print(f"\n[ERRO NO RESEND ao enviar para {email_unico}]: {error}")
            sucesso = False

    return sucesso

