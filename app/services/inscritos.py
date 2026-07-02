from app.database import get_connection
from flask import request
import secrets
from datetime import datetime, timedelta, timezone

def inscrever(nome, email, status, consentimento_lgpd, sobrenome=None):
    
    if (sobrenome and sobrenome.strip() != ""):
        print("Bot detectado no backend via Honeypot!")
        return {"message": "Inscrição realizada com sucesso."}, 201

    conn = None
    cursor = None      

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM inscritos WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            
            return {"error": "Já existe um inscrito com esse email!"}, 400

        token = secrets.token_urlsafe(32)
        expiracao = datetime.now(timezone.utc) + timedelta(hours=24)

        cursor.execute("""
            INSERT INTO inscritos (nome, email, status, consentimento_lgpd, token_confirmacao, token_expira_em)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (nome, email, status, consentimento_lgpd, token, expiracao))

        conn.commit()

        return {
            "message": "Inscrição realizada com sucesso. Verifique seu e-mail.",
            "token": token
        }, 201
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Erro interno: {e}") 
        return {"error": "Não foi possível processar sua inscrição no momento."}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def ativar_inscrito(token):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, status, token_expira_em 
            FROM inscritos 
            WHERE token_confirmacao = %s
        """, (token,))
        
        inscrito = cursor.fetchone()

        if not inscrito:
            return {"error": "Link de confirmação inválido."}, 400

        inscrito_id, status_atual, token_expira_em = inscrito

        agora = datetime.now(timezone.utc)
        
        if token_expira_em and agora > token_expira_em:
            return {"error": "Este link de confirmação expirou. Faça o cadastro novamente."}, 400

        if status_atual == "ativo":
            return {"message": "Sua inscrição já foi confirmada anteriormente!"}, 200

        cursor.execute("""
            UPDATE inscritos 
            SET status = 'ativo', 
                token_confirmacao = NULL, 
                token_expira_em = NULL 
            WHERE id = %s
        """, (inscrito_id,))

        conn.commit()
        return {"message": "E-mail confirmado com sucesso! Inscrição ativada."}, 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Erro ao ativar inscrito no banco: {e}")
        return {"error": "Erro no banco de dados ao ativar inscrição."}, 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def descadastrar_inscrito(email):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM inscritos WHERE email = %s", (email,))
        resultado = cursor.fetchone()

        if not resultado:
            return {"error": "E-mail não encontrado na nossa lista."}, 404

        inscrito_id = resultado[0]

        cursor.execute(
            "DELETE FROM inscritos WHERE id = %s",
            (inscrito_id,)
        )

        conn.commit()
        return {"message": "Sua inscrição foi removida com sucesso."}, 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Erro ao remover inscrito: {e}")
        return {"error": "Erro interno ao processar o cancelamento."}, 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def contar_inscritos():
    conn = get_connection()
    cursor = conn.cursor()
    try: 
        cursor.execute("SELECT COUNT(*) FROM inscritos WHERE status = 'ativo'")
        count = cursor.fetchone()[0]
        return count
    finally:
        cursor.close()
        conn.close()