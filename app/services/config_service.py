from app.database import get_connection
from flask import request 
import uuid
import os

UPLOAD_BANNER = os.path.join(os.getcwd(), 'config_blog')

#configurar
def configurar(nome_blog, data_atualizacao, autor, tags_do_blog, descricao_blog, banner_url=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO config_geral (nome_blog, data_atualizacao, autor, tags_do_blog, descricao_blog, banner_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id_config;
        """, (nome_blog, data_atualizacao, autor, tags_do_blog, descricao_blog, banner_url)
    )

    config_id = cursor.fetchone()[0]
    
    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "Configuração realizada com sucesso", "id": config_id}, 201

def obter_ultima_configuracao():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Busca a última configuração salva
        cursor.execute("""
            SELECT nome_blog, data_atualizacao, autor, tags_do_blog, descricao_blog, banner_url 
            FROM config_geral 
            ORDER BY id_config DESC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        
        if row:
            return {
                "nome_blog": row[0],
                "data_atualizacao": row[1].strftime('%Y-%m-%d') if row[1] else "",
                "autor": row[2],
                "tags_do_blog": row[3],
                "descricao_blog": row[4],
                "banner_url": row[5]
            }
        return None
    finally:
        cursor.close()
        conn.close()