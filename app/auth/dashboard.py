import sys
import os
import resend
from flask import Blueprint, jsonify
from dotenv import load_dotenv
from app.database import get_connection

load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard/visao-geral', methods=['GET'])
def obter_visao_geral_resend():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM inscritos WHERE status = 'ativo'")
        total_inscritos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM postagens")
        total_posts = cursor.fetchone()[0]
        conn.close()

        emails_enviados = resend.Emails.list()
        lista_emails = emails_enviados.get("data", [])
        
        total_disparados = len(lista_emails)
        total_abertos = 0
        total_clicados = 0
        
        for email in lista_emails:
            evento = email.get("last_event")
            
            if evento == "opened":
                total_abertos += 1
            elif evento == "clicked":
                total_abertos += 1 
                total_clicados += 1

        taxa_abertura = 0
        if total_disparados > 0:
            taxa_abertura = round((total_abertos / total_disparados) * 100, 1)

        lista_disparos_recentes = []
        for email in lista_emails[:3]:
            assunto = email.get("subject") or "Sem assunto"
            evento = email.get("last_event") or "enviado"
            
            lista_disparos_recentes.append({
                "titulo": assunto,
                "detalhe": f"Status: {evento.upper()}" 
            })

        return jsonify({
            "cards": {
                "taxa_abertura": f"{taxa_abertura}%",
                "total_postagens": total_posts,
                "total_inscritos": total_inscritos
            },
            "grafico": {
                "valores": [total_disparados, total_abertos, total_clicados] 
            },
            "top_posts": lista_disparos_recentes
        }), 200

    except Exception as e:
        import traceback
        print("\n🚨 ERRO NO PROCESSAMENTO DO DASHBOARD:", file=sys.stderr)
        traceback.print_exc()
        return jsonify({"error": "Falha ao carregar dados do Resend"}), 500