import sqlite3
import os
import streamlit as st


DB_FILENAME = "Frango Americano.db"




def connect_db(path=None):
    """Retorna uma conexão SQLite com o banco local.
    Usa o arquivo `Frango Americano.db` por padrão. Faz tratamento de erros.
    """
    try:
        db_path = path or os.path.join(os.getcwd(), DB_FILENAME)
        conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES, check_same_thread=False)
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None


def create_table(conn):
    """Cria a tabela principal 'registros' se ela não existir."""
    try:
        sql_create_table = """
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            regional TEXT,
            filial_remetente TEXT,
            destino TEXT,
            produto TEXT,
            quantidade REAL,
            unidade TEXT,
            preco_unitario REAL,
            valor_total REAL,
            nfe TEXT,
            observacoes TEXT,
            tipo_operacao TEXT,
            data_lancamento DATETIME DEFAULT CURRENT_TIMESTAMP,
            usuario_lancamento TEXT
        );
        """
        cursor = conn.cursor()
        cursor.execute(sql_create_table)
        conn.commit()
    except Exception as e:
        st.error(f"Erro ao criar a tabela de registros: {e}")

def create_settings_tables(conn):
    """Cria as tabelas para as listas de opções (regionais, produtos, etc.)."""
    # Nomes das tabelas usados na página de Configurações
    setting_tables = ["regionais", "filiais", "destinos", "produtos", "unidades"]
    try:
        cursor = conn.cursor()
        for table_name in setting_tables:
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            """)
        conn.commit()
    except Exception as e:
        st.error(f"Erro ao criar tabelas de configuração: {e}")

def create_users_table(conn):
    """Cria a tabela 'users' para autenticação se ela não existir."""
    try:
        sql_create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
        """
        cursor = conn.cursor()
        cursor.execute(sql_create_users_table)
        conn.commit()
    except Exception as e:
        st.error(f"Erro ao criar a tabela de usuários: {e}")

def create_log_table(conn):
    """Cria a tabela 'activity_log' para registrar as ações dos usuários."""
    try:
        sql_create_log_table = """
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_name TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT
        );
        """
        cursor = conn.cursor()
        cursor.execute(sql_create_log_table)
        conn.commit()
    except Exception as e:
        st.error(f"Erro ao criar a tabela de log: {e}")

def run_migrations(conn):
    """
    Garante que a estrutura do banco de dados esteja atualizada.
    Adiciona colunas que possam estar faltando em bancos de dados mais antigos.
    """
    try:
        cursor = conn.cursor()
        # Obtém informações sobre as colunas da tabela 'registros'
        cursor.execute("PRAGMA table_info(registros);")
        existing_columns = [row[1] for row in cursor.fetchall()]

        # Define as colunas que devem existir e seus tipos
        all_columns = {
            "nfe": "TEXT",
            "observacoes": "TEXT",
            "tipo_operacao": "TEXT",
            "data_lancamento": "DATETIME",
            "usuario_lancamento": "TEXT"
        }

        for col, col_type in all_columns.items():
            if col not in existing_columns:
                st.info(f"Atualizando banco de dados: Adicionando coluna '{col}'...")
                if col == 'data_lancamento':
                    # Adiciona a coluna sem um valor padrão para compatibilidade com versões mais antigas do SQLite.
                    # O valor será NULL para registros antigos, o que é tratado pela aplicação.
                    cursor.execute(f"ALTER TABLE registros ADD COLUMN {col} {col_type}")
                elif col == 'usuario_lancamento':
                    cursor.execute(f"ALTER TABLE registros ADD COLUMN {col} {col_type} DEFAULT 'N/A'")
                else:
                    cursor.execute(f"ALTER TABLE registros ADD COLUMN {col} {col_type}")
        conn.commit()
    except Exception as e:
        st.error(f"Erro ao executar migrações no banco de dados: {e}")