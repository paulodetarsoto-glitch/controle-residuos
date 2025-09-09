import streamlit as st
import pandas as pd
import sqlite3
from sqlite3 import Error
import io
import plotly.express as px
from datetime import datetime
import base64
import hashlib
import numpy as np

def calculate_total(quantity, unit_price):
    """Calcula o valor total a partir da quantidade e preço unitário."""
    try:
        # Tenta converter os valores para float para garantir que são numéricos.
        # Isso lida com tipos padrão do Python (int, float) e tipos do NumPy.
        q = float(quantity)
        p = float(unit_price)
        return q * p
    except (ValueError, TypeError):
        # Retorna 0.0 se a conversão falhar ou se os tipos forem inválidos (None, etc.)
        return 0.0

def log_activity(conn, user_name, action, details=""):
    """Registra uma atividade no log."""
    try:
        sql = "INSERT INTO activity_log (user_name, action, details) VALUES (?, ?, ?)"
        cursor = conn.cursor()
        cursor.execute(sql, (user_name, action, details))
        conn.commit()
    except Error as e:
        st.warning(f"Não foi possível registrar a atividade no log: {e}")

# --- Funções de Gerenciamento de Usuário ---

def hash_password(password):
    """Gera um hash seguro para a senha usando SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_hash, provided_password):
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    return stored_hash == hash_password(provided_password)

def add_user(conn, username, password, role='User'):
    """Adiciona um novo usuário ao banco de dados com senha hasheada."""
    if not username or not password:
        st.error("Nome de usuário e senha não podem ser vazios.")
        return False
    try:
        password_hash = hash_password(password)
        sql = "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)"
        cursor = conn.cursor()
        cursor.execute(sql, (username, password_hash, role))
        conn.commit()
        st.success(f"Usuário '{username}' criado com sucesso! Você já pode fazer o login.")
        return True
    except sqlite3.IntegrityError:
        st.error(f"❌ Usuário '{username}' já existe.")
        return False
    except Error as e:
        st.error(f"❌ Erro ao criar usuário: {e}")
        return False

def get_user(conn, username):
    """
    Busca um usuário pelo nome de usuário e retorna um dicionário 
    com id, username, e password_hash.
    """
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        conn.row_factory = None # Resetar para o padrão
        
        if user_row:
            return dict(user_row)
        return None
    except Error as e:
        st.error(f"Erro ao buscar usuário: {e}")
        return None

def get_all_users(conn):
    """Busca todos os usuários (username, role), exceto 'Administrador'."""
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Exclui o superusuário da lista para evitar que ele seja modificado
        cursor.execute("SELECT username, role FROM users WHERE username != 'Administrador' ORDER BY username ASC")
        rows = cursor.fetchall()
        conn.row_factory = None # Resetar para o padrão
        return [dict(row) for row in rows]
    except Error as e:
        st.error(f"Falha ao buscar usuários: {e}")
        return []

def update_user_password(conn, admin_user, target_user, new_password):
    """Atualiza a senha de um usuário específico."""
    if not new_password:
        st.error("A nova senha não pode ser vazia.")
        return False
    try:
        new_password_hash = hash_password(new_password)
        sql = "UPDATE users SET password_hash = ? WHERE username = ?"
        cursor = conn.cursor()
        cursor.execute(sql, (new_password_hash, target_user))
        conn.commit()
        log_activity(conn, admin_user, "Reset de Senha", f"Senha do usuário '{target_user}' foi resetada.")
        st.success(f"Senha do usuário '{target_user}' foi atualizada com sucesso!")
        return True
    except Error as e:
        st.error(f"Falha ao atualizar a senha: {e}")
        return False

def delete_user(conn, admin_user, target_user):
    """Exclui um usuário do banco de dados."""
    try:
        sql = "DELETE FROM users WHERE username = ?"
        cursor = conn.cursor()
        cursor.execute(sql, (target_user,))
        conn.commit()
        log_activity(conn, admin_user, "Excluir Usuário", f"Usuário '{target_user}' foi excluído.")
        st.success(f"Usuário '{target_user}' excluído com sucesso!")
    except Error as e:
        st.error(f"Falha ao excluir usuário: {e}")

def update_user_role(conn, admin_user, target_user, new_role):
    """Atualiza a função (role) de um usuário específico."""
    try:
        sql = "UPDATE users SET role = ? WHERE username = ?"
        cursor = conn.cursor()
        cursor.execute(sql, (new_role, target_user))
        conn.commit()
        log_activity(conn, admin_user, "Atualizar Função", f"Função do usuário '{target_user}' alterada para '{new_role}'.")
        st.success(f"Função do usuário '{target_user}' atualizada para '{new_role}' com sucesso!")
        return True
    except Error as e:
        st.error(f"Falha ao atualizar a função do usuário: {e}")
        return False

# --- Funções de Gerenciamento de Registros ---

def add_record(conn, user_name, data, tipo_operacao, regional, remetente, destino, produto, quantidade, unidade, preco_unitario, valor_total, nfe, observacoes):
    """Insere um novo registro no banco de dados."""
    # Padroniza os valores de texto para garantir consistência
    tipo_operacao = str(tipo_operacao).strip().title()
    regional = str(regional).strip().title()
    remetente = str(remetente).strip().title()
    destino = str(destino).strip().title()
    produto = str(produto).strip().title()
    unidade = str(unidade).strip().title()
    nfe = str(nfe).strip()
    observacoes = str(observacoes).strip()

    # Validação de entrada para garantir a integridade dos dados
    if not (quantidade > 0):
        st.error("❌ Falha ao adicionar registro: A 'Quantidade' deve ser maior que zero.")
        return False

    try:
        # Para garantir a consistência, se o Valor Total for fornecido, ele tem prioridade
        # e o Preço Unitário é recalculado.
        if valor_total > 0 and quantidade > 0:
            final_valor_total = valor_total
            final_preco_unitario = valor_total / quantidade
        else:
            final_valor_total = calculate_total(quantidade, preco_unitario)
            final_preco_unitario = preco_unitario

        # Usar um dicionário para mapear valores para as colunas de forma explícita.
        # Isso torna o código mais robusto e evita erros de ordenação.
        registro_dict = {
            "data": data,
            "tipo_operacao": tipo_operacao,
            "regional": regional,
            "filial_remetente": remetente,
            "destino": destino,
            "produto": produto,
            "quantidade": quantidade,
            "unidade": unidade,
            "preco_unitario": final_preco_unitario,
            "valor_total": final_valor_total,
            "nfe": nfe,
            "observacoes": observacoes,
            "usuario_lancamento": user_name
        }

        sql = ''' INSERT INTO registros(data, tipo_operacao, regional, filial_remetente, destino, produto, quantidade, unidade, preco_unitario, valor_total, nfe, observacoes, usuario_lancamento)
                  VALUES(:data, :tipo_operacao, :regional, :filial_remetente, :destino, :produto, :quantidade, :unidade, :preco_unitario, :valor_total, :nfe, :observacoes, :usuario_lancamento) '''
        cursor = conn.cursor()
        cursor.execute(sql, registro_dict)
        conn.commit()
        st.success(f"✅ Registro adicionado com sucesso!")
        # Log da atividade
        log_activity(conn, user_name, "Adicionar Registro", f"ID do novo registro: {cursor.lastrowid}")
        return True
    except Error as e:
        st.error(f"❌ Falha ao adicionar registro: {e}")
        return False

def delete_all_records(conn, user_name):
    """Exclui TODOS os registros da tabela 'registros'."""
    try:
        sql = 'DELETE FROM registros'
        cursor = conn.cursor()
        cursor.execute(sql)
        # Reseta a sequência do autoincremento para o SQLite
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='registros'")
        conn.commit()
        log_activity(conn, user_name, "Excluir Todos os Registros", "Todos os registros foram apagados.")
        st.success("✅ Todos os registros foram excluídos com sucesso!")
    except Error as e:
        st.error(f"❌ Falha ao excluir todos os registros: {e}")

def get_record_by_id(conn, record_id):
    """Busca um único registro pelo seu ID de forma eficiente, sem usar pandas."""
    try:
        # Usar um cursor para buscar uma única linha é mais performático que carregar o pandas.
        conn.row_factory = sqlite3.Row  # Permite acessar colunas pelo nome
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM registros WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        conn.row_factory = None  # Resetar para o padrão para não afetar outras funções

        if row is None:
            return None

        # Converte o objeto sqlite3.Row em um dicionário e renomeia as chaves
        return {
            'ID': row['id'],
            'Data': row['data'],
            'Data de Lançamento': row['data_lancamento'],
            'Usuário': row['usuario_lancamento'],
            'Tipo de Operação': row['tipo_operacao'],
            'Regional': row['regional'],
            'Filial Remetente': row['filial_remetente'],
            'Destino': row['destino'],
            'Produto': row['produto'],
            'Quantidade': float(row['quantidade'] or 0.0),
            'Unidade': row['unidade'],
            'Preço Unitário': float(row['preco_unitario'] or 0.0),
            'Valor Total': float(row['valor_total'] or 0.0),
            'NFe': row['nfe'] or '',
            'Observacoes': row['observacoes'] or ''
        }
    except Error as e:
        st.error(f"Falha ao buscar o registro: {e}")
        return None

def update_record(conn, user_name, record_id, data, tipo_operacao, regional, remetente, destino, produto, quantidade, unidade, preco_unitario, valor_total, nfe, observacoes):
    """Atualiza um registro existente no banco de dados."""
    # Busca a role do usuário para garantir que apenas Admins possam editar.
    user = get_user(conn, user_name)
    if not user or user.get('role') != 'Admin':
        st.error("❌ Ação não permitida. Você não tem permissão para editar registros.")
        log_activity(conn, user_name, "Tentativa de Edição Negada", f"Usuário sem permissão tentou editar o registro ID {record_id}.")
        return

    try:
        tipo_operacao = str(tipo_operacao).strip().title()
        # Padroniza os valores de texto para garantir consistência
        regional = str(regional).strip().title()
        remetente = str(remetente).strip().title()
        destino = str(destino).strip().title()
        produto = str(produto).strip().title()
        unidade = str(unidade).strip().title()
        nfe = str(nfe).strip()
        observacoes = str(observacoes).strip()

        # Lógica de consistência: prioriza o Valor Total se ele for editado.
        if valor_total > 0 and quantidade > 0:
            final_valor_total = valor_total
            final_preco_unitario = valor_total / quantidade
        else:
            final_valor_total = calculate_total(quantidade, preco_unitario)
            final_preco_unitario = preco_unitario

        # Usa um dicionário para mapear valores para as colunas de forma explícita, evitando erros de ordenação.
        registro_dict = {
            "data": data,
            "tipo_operacao": tipo_operacao,
            "regional": regional,
            "filial_remetente": remetente,
            "destino": destino,
            "produto": produto,
            "quantidade": quantidade,
            "unidade": unidade,
            "preco_unitario": final_preco_unitario,
            "valor_total": final_valor_total,
            "nfe": nfe,
            "observacoes": observacoes,
            "id": record_id
        }
        
        sql = ''' UPDATE registros
                  SET data = :data, tipo_operacao = :tipo_operacao, regional = :regional, filial_remetente = :filial_remetente,
                      destino = :destino, produto = :produto, quantidade = :quantidade,
                      unidade = :unidade, preco_unitario = :preco_unitario, valor_total = :valor_total,
                      nfe = :nfe, observacoes = :observacoes 
                  WHERE id = :id '''
        cursor = conn.cursor()
        cursor.execute(sql, registro_dict)
        conn.commit()
        st.success(f"✅ Registro ID {record_id} atualizado com sucesso!")
        log_activity(conn, user_name, "Editar Registro", f"Registro ID {record_id} foi modificado.")
    except Error as e:
        st.error(f"❌ Falha ao atualizar o registro: {e}")

def delete_record(conn, user_name, record_id):
    """Exclui um registro individual do banco de dados."""
    # Busca a role do usuário para garantir que apenas Admins possam excluir.
    user = get_user(conn, user_name)
    if not user or user.get('role') != 'Admin':
        st.error("❌ Ação não permitida. Você não tem permissão para excluir registros.")
        log_activity(conn, user_name, "Tentativa de Exclusão Negada", f"Usuário sem permissão tentou excluir o registro ID {record_id}.")
        return

    try:
        sql = 'DELETE FROM registros WHERE id = ?'
        cursor = conn.cursor()
        cursor.execute(sql, (record_id,))
        conn.commit()
        log_activity(conn, user_name, "Excluir Registro", f"Registro ID {record_id} foi excluído.")
        st.success(f"✅ Registro ID {record_id} excluído com sucesso!")
    except Error as e:
        st.error(f"❌ Falha ao excluir o registro: {e}")

def delete_records_bulk(conn, user_name, record_ids):
    """Exclui múltiplos registros do banco de dados de uma vez."""
    # Busca a role do usuário para garantir que apenas Admins possam excluir.
    user = get_user(conn, user_name)
    if not user or user.get('role') != 'Admin':
        st.error("❌ Ação não permitida. Você não tem permissão para excluir registros.")
        log_activity(conn, user_name, "Tentativa de Exclusão em Massa Negada", f"Usuário sem permissão tentou excluir múltiplos registros.")
        return

    if not record_ids:
        st.warning("Nenhum registro selecionado para exclusão.")
        return
    try:
        # Cria a string de placeholders (?, ?, ?) para a cláusula IN
        placeholders = ', '.join('?' for _ in record_ids)
        sql = f'DELETE FROM registros WHERE id IN ({placeholders})'
        
        cursor = conn.cursor()
        cursor.execute(sql, record_ids)
        conn.commit()
        
        num_deleted = cursor.rowcount
        log_activity(conn, user_name, "Excluir Múltiplos Registros", f"{num_deleted} registros foram excluídos. IDs: {', '.join(map(str, record_ids))}")
        st.success(f"✅ {num_deleted} registros excluídos com sucesso!")
    except Error as e:
        st.error(f"❌ Falha ao excluir os registros: {e}")

def migrate_old_records(conn):
    """Padroniza os dados de texto existentes na tabela de registros."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, regional, filial_remetente, destino, produto, unidade FROM registros")
        records = cursor.fetchall()

        updates_to_perform = []
        for record in records:
            rec_id, regional, remetente, destino, produto, unidade = record

            # Aplica as mesmas regras de padronização dos formulários
            std_regional = str(regional).strip().title()
            std_remetente = str(remetente).strip().title()
            std_destino = str(destino).strip().title()
            std_produto = str(produto).strip().title()
            std_unidade = str(unidade).strip().title()

            # Verifica se houve alguma mudança para evitar updates desnecessários
            if (std_regional != regional or
                std_remetente != remetente or
                std_destino != destino or
                std_produto != produto or
                std_unidade != unidade):
                updates_to_perform.append((std_regional, std_remetente, std_destino, std_produto, std_unidade, rec_id))

        if not updates_to_perform:
            st.info("✅ Todos os registros já estão padronizados. Nenhuma ação foi necessária.")
            return

        sql_update = "UPDATE registros SET regional = ?, filial_remetente = ?, destino = ?, produto = ?, unidade = ? WHERE id = ?"
        cursor.executemany(sql_update, updates_to_perform)
        conn.commit()
        st.success(f"✅ Migração concluída! {len(updates_to_perform)} registros foram atualizados para o novo padrão.")
    except Error as e:
        st.error(f"❌ Ocorreu um erro durante a migração dos dados: {e}")

def run_user_role_migration(conn):
    """Adiciona a coluna 'role' à tabela de usuários se ela não existir."""
    try:
        cursor = conn.cursor()
        # Verifica se a coluna 'role' já existe
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'role' not in columns:
            st.info("Aplicando migração: adicionando coluna 'role' aos usuários...")
            # Adiciona a coluna com um valor padrão 'User'
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'User' NOT NULL")
            # Define o 'Administrador' como 'Admin'
            cursor.execute("UPDATE users SET role = 'Admin' WHERE username = 'Administrador'")
            conn.commit()
            st.success("Migração de função de usuário concluída.")
    except Error as e:
        st.error(f"Erro durante a migração da função de usuário: {e}")

def get_setting_options(conn, table_name):
    """Busca todas as opções de uma tabela de configuração."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM {table_name} ORDER BY name ASC")
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except Error as e:
        st.error(f"Falha ao buscar opções de '{table_name}': {e}")
        return []

def get_distinct_field_options(conn, field_name):
    """Busca valores únicos de um campo específico na tabela de registros."""
    try:
        cursor = conn.cursor()
        # A construção da query é segura aqui, pois 'field_name' é controlado internamente.
        cursor.execute(f"SELECT DISTINCT {field_name} FROM registros WHERE {field_name} IS NOT NULL AND {field_name} != '' ORDER BY {field_name} ASC")
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except Error as e:
        st.error(f"Falha ao buscar opções distintas para '{field_name}': {e}")
        return []

def add_setting_option(conn, table_name, name):
    """Adiciona uma nova opção a uma tabela de configuração."""
    # Padroniza o nome antes de inserir para manter a consistência
    standardized_name = str(name).strip().title()
    
    if not standardized_name:
        st.warning("O nome da opção não pode ser vazio.")
        return

    try:
        sql = f"INSERT INTO {table_name} (name) VALUES (?)"
        cursor = conn.cursor()
        cursor.execute(sql, (standardized_name,))
        conn.commit()
        st.success(f"Opção '{standardized_name}' adicionada com sucesso!")
    except Error as e:
        st.error(f"❌ Falha ao adicionar opção: {e}. Verifique se a opção já existe.")

def delete_setting_option(conn, table_name, name):
    """Remove uma opção de uma tabela de configuração."""
    try:
        sql = f"DELETE FROM {table_name} WHERE name = ?"
        cursor = conn.cursor()
        cursor.execute(sql, (name,))
        conn.commit()
        st.success(f"Opção '{name}' removida com sucesso!")
    except Error as e:
        st.error(f"❌ Falha ao remover opção: {e}")

def get_activity_log(conn):
    """Busca todos os registros do log de atividades."""
    try:
        query = "SELECT timestamp, user_name, action, details FROM activity_log ORDER BY timestamp DESC"
        df = pd.read_sql_query(query, conn, parse_dates=['timestamp'])
        df.rename(columns={
            'timestamp': 'Data e Hora', 'user_name': 'Usuário', 
            'action': 'Ação', 'details': 'Detalhes'
        }, inplace=True)
        return df
    except (Error, pd.errors.DatabaseError) as e:
        st.error(f"Falha ao buscar o log de atividades: {e}")
        return pd.DataFrame()

def get_all_records(conn):
    """Busca todos os registros no banco de dados e retorna um DataFrame."""
        # Esta função foi refatorada para ser mais limpa e robusta.
    try:
        # Lê os dados diretamente para um DataFrame, convertendo a coluna 'data' para datetime.
        query = "SELECT * FROM registros ORDER BY id DESC"
        df = pd.read_sql_query(query, conn, parse_dates=['data', 'data_lancamento'])

        if df.empty:
            return pd.DataFrame()

        # Renomeia as colunas do banco de dados para nomes mais amigáveis para exibição.
        df.rename(columns={
            'id': 'ID', 'data': 'Data', 'data_lancamento': 'Data de Lançamento',
            'usuario_lancamento': 'Usuário', 'tipo_operacao': 'Tipo de Operação', 
            'regional': 'Regional',
            'filial_remetente': 'Filial Remetente', 'destino': 'Destino',
            'produto': 'Produto', 'quantidade': 'Quantidade', 'observacoes': 'Observacoes',
            'unidade': 'Unidade', 'preco_unitario': 'Preço Unitário',
            'valor_total': 'Valor Total', 'nfe': 'NFe'
        }, inplace=True)

        # Garante que as colunas numéricas sejam do tipo correto, tratando possíveis erros.
        numeric_cols = ['Quantidade', 'Preço Unitário', 'Valor Total']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df

    except (Error, pd.errors.DatabaseError) as e:
        st.error(f"Falha ao buscar registros: {e}")
        return pd.DataFrame()

def get_records_count(conn, search_query: str = "") -> int:
    """Conta o número total de registros, opcionalmente filtrando por uma query de busca."""
    cursor = conn.cursor()
    query = "SELECT COUNT(*) FROM registros"
    params = []
    if search_query:
        search_term = f"%{search_query.lower()}%"
        # Concatena colunas para uma busca ampla. Usa COALESCE para tratar valores NULL.
        query += """ 
            WHERE LOWER(COALESCE(regional, '') || ' ' || 
                       COALESCE(filial_remetente, '') || ' ' || 
                       COALESCE(destino, '') || ' ' || 
                       COALESCE(produto, '') || ' ' || 
                       COALESCE(unidade, '') || ' ' || 
                       COALESCE(nfe, '') || ' ' || 
                       COALESCE(tipo_operacao, '') || ' ' ||
                       COALESCE(usuario_lancamento, '')) LIKE ?
        """
        params.append(search_term)
    
    cursor.execute(query, params)
    count = cursor.fetchone()[0]
    return count

def get_paginated_records(conn, limit: int, offset: int, search_query: str = "") -> pd.DataFrame:
    """Busca uma 'página' de registros do banco de dados com opção de busca."""
    query = "SELECT * FROM registros"
    params = []
    if search_query:
        search_term = f"%{search_query.lower()}%"
        query += """ 
            WHERE LOWER(COALESCE(regional, '') || ' ' || 
                       COALESCE(filial_remetente, '') || ' ' || 
                       COALESCE(destino, '') || ' ' || 
                       COALESCE(produto, '') || ' ' || 
                       COALESCE(unidade, '') || ' ' || 
                       COALESCE(nfe, '') || ' ' || 
                       COALESCE(tipo_operacao, '') || ' ' ||
                       COALESCE(usuario_lancamento, '')) LIKE ?
        """
        params.append(search_term)

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    df = pd.read_sql_query(query, conn, params=params, parse_dates=['data', 'data_lancamento'])

    if df.empty:
        return pd.DataFrame()

    # Renomeia as colunas para consistência com o resto do app, evitando erros de chave
    df.rename(columns={
        'id': 'ID', 'data': 'Data', 'data_lancamento': 'Data de Lançamento',
        'usuario_lancamento': 'Usuário', 'tipo_operacao': 'Tipo de Operação', 'regional': 'Regional',
        'filial_remetente': 'Filial Remetente', 'destino': 'Destino',
        'produto': 'Produto', 'quantidade': 'Quantidade', 'observacoes': 'Observacoes',
        'unidade': 'Unidade', 'preco_unitario': 'Preço Unitário',
        'valor_total': 'Valor Total', 'nfe': 'NFe'
    }, inplace=True)

    # Garante que as colunas numéricas sejam do tipo correto
    for col in ['Quantidade', 'Preço Unitário', 'Valor Total']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    return df

def get_dashboard_data(conn, start_date, end_date, regional, branch, product, destination, operation_type, unit, user):
    """Busca dados filtrados do banco de dados especificamente para o dashboard."""
    query = "SELECT * FROM registros WHERE data BETWEEN ? AND ?"
    params = [start_date, end_date]

    # Adiciona filtros dinamicamente à consulta SQL
    if regional and regional != "Todos":
        query += " AND regional = ?"
        params.append(regional)
    if branch and branch != "Todos":
        query += " AND filial_remetente = ?"
        params.append(branch)
    if product and product != "Todos":
        query += " AND produto = ?"
        params.append(product)
    if destination and destination != "Todos":
        query += " AND destino = ?"
        params.append(destination)
    if operation_type and operation_type != "Todos":
        query += " AND tipo_operacao = ?"
        params.append(operation_type)
    if unit and unit != "Todos":
        query += " AND unidade = ?"
        params.append(unit)
    if user and user != "Todos":
        query += " AND usuario_lancamento = ?"
        params.append(user)

    # Executa a consulta e carrega os dados em um DataFrame
    df = pd.read_sql_query(query, conn, params=params, parse_dates=['data', 'data_lancamento'])

    # Renomeia as colunas para nomes mais amigáveis
    df.rename(columns={
        'id': 'ID', 'data': 'Data', 'data_lancamento': 'Data de Lançamento',
        'usuario_lancamento': 'Usuário', 'tipo_operacao': 'Tipo de Operação', 
        'regional': 'Regional',
        'filial_remetente': 'Filial Remetente', 'destino': 'Destino',
        'produto': 'Produto', 'quantidade': 'Quantidade', 'observacoes': 'Observacoes',
        'unidade': 'Unidade', 'preco_unitario': 'Preço Unitário',
        'valor_total': 'Valor Total', 'nfe': 'NFe'
    }, inplace=True)

    # Garante que as colunas numéricas sejam do tipo correto
    numeric_cols = ['Quantidade', 'Preço Unitário', 'Valor Total']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df

def display_dashboard(conn):
    """Exibe um dashboard interativo que busca dados sob demanda."""
    # Busca as datas mínima e máxima para o seletor de datas de forma eficiente.
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MIN(data), MAX(data) FROM registros")
        min_date_str, max_date_str = cursor.fetchone()

        if not min_date_str or not max_date_str:
            st.info("ℹ️ Não há dados para exibir o dashboard. Adicione registros primeiro.")
            return

        min_date = datetime.strptime(min_date_str, '%Y-%m-%d').date()
        max_date = datetime.strptime(max_date_str, '%Y-%m-%d').date()
    except (Error, TypeError):
        st.info("ℹ️ Não há dados para exibir o dashboard. Adicione registros primeiro.")
        return

    st.header("♻️ Dashboard de Análise de Resíduos")

    # --- Filtros ---
    with st.popover("📅 Filtros de Análise", use_container_width=True):
        col_filter1, col_filter2 = st.columns(2)
        all_option_str = "Todos"

        with col_filter1:
            start_date = st.date_input("Data de Início", min_date, min_value=min_date, max_value=max_date)
            
            # Busca as opções de filtro diretamente da tabela de registros para refletir os dados existentes
            regionals = get_distinct_field_options(conn, "regional")
            selected_regional = st.selectbox(
                "Regional",
                options=[all_option_str] + regionals
            )

            branches = get_distinct_field_options(conn, "filial_remetente")
            selected_branch = st.selectbox(
                "Filial Remetente",
                options=[all_option_str] + branches
            )

            operation_types = get_distinct_field_options(conn, "tipo_operacao")
            selected_operation_type = st.selectbox(
                "Tipo de Operação",
                options=[all_option_str] + operation_types
            )

            users = get_distinct_field_options(conn, "usuario_lancamento")
            selected_user = st.selectbox(
                "Usuário de Lançamento",
                options=[all_option_str] + users
            )

        with col_filter2:
            end_date = st.date_input("Data de Fim", max_date, min_value=min_date, max_value=max_date)

            destinations = get_distinct_field_options(conn, "destino")
            selected_destination = st.selectbox(
                "Destino",
                options=[all_option_str] + destinations
            )

            products = get_distinct_field_options(conn, "produto")
            selected_product = st.selectbox(
                "Produto",
                options=[all_option_str] + products
            )

            units = get_distinct_field_options(conn, "unidade")
            selected_unit = st.selectbox(
                "Unidade",
                options=[all_option_str] + units
            )

    # Busca os dados no banco de dados com base nos filtros selecionados
    with st.spinner("Buscando e processando dados..."):
        df_filtered = get_dashboard_data(
            conn, start_date=start_date, end_date=end_date,
            regional=selected_regional, branch=selected_branch,
            product=selected_product, destination=selected_destination,
            operation_type=selected_operation_type,
            unit=selected_unit, user=selected_user
        )

    if df_filtered.empty:
        st.warning("⚠️ Nenhum registro encontrado para os filtros selecionados.")
        return

    # --- Botões de Exportação ---
    # O restante da função continua igual, pois já opera sobre o df_filtered
    st.subheader("Exportar Dados Filtrados")
    col_export1, col_export2, _ = st.columns([1, 1, 4])

    with col_export1:
        # Exportar para Excel
        try:
            st.markdown(
                get_table_download_link(
                    df_filtered,
                    f"relatorio_residuos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    "Exportar para Excel",
                    "excellogo.png"
                ),
                unsafe_allow_html=True
            )
        except FileNotFoundError:
            # Fallback para o botão padrão se o logo não for encontrado
            st.download_button(
                label="📥 Exportar para Excel (logo não encontrado)",
                data=to_excel(df_filtered),
                file_name=f"relatorio_residuos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    with col_export2:
        # Exportar para CSV
        csv_data = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Exportar para CSV",
            data=csv_data,
            file_name=f"relatorio_residuos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    st.divider()

    # --- KPIs ---
    st.subheader("Indicadores Chave de Performance (KPIs)")
    total_revenue = df_filtered['Valor Total'].sum()
    total_quantity = df_filtered['Quantidade'].sum()
    num_records = len(df_filtered)
    
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Receita Total", value=f"R$ {total_revenue:,.2f}")
    col2.metric(label="Quantidade Total (KG/Un)", value=f"{total_quantity:,.2f}")
    col3.metric(label="Total de Registros", value=f"{num_records:,}")

    # --- NARRATIVAS ---
    st.subheader("Análises e Narrativas")
    try:
        # Principais Influenciadores
        top_regional_revenue = df_filtered.groupby('Regional')['Valor Total'].sum()
        if not top_regional_revenue.empty:
            top_regional = top_regional_revenue.idxmax()
            st.markdown(f"🏆 **Regional Destaque:** A regional **{top_regional}** foi a que gerou maior receita no período selecionado.")

        top_filial_revenue = df_filtered.groupby('Filial Remetente')['Valor Total'].sum()
        if not top_filial_revenue.empty:
            top_filial = top_filial_revenue.idxmax()
            st.markdown(f"🏢 **Filial Destaque:** A filial **{top_filial}** foi a principal contribuinte para a receita.")

        top_product_revenue = df_filtered.groupby('Produto')['Valor Total'].sum()
        if not top_product_revenue.empty:
            top_product = top_product_revenue.idxmax()
            st.markdown(f"📦 **Produto Destaque:** O produto **{top_product}** foi o mais lucrativo no período.")

            # Análise de Influenciadores de Produto
            total_revenue_for_narrative = df_filtered['Valor Total'].sum()
            if total_revenue_for_narrative > 0:
                top_3_products = top_product_revenue.nlargest(3)
                top_3_percentage = (top_3_products.sum() / total_revenue_for_narrative) * 100
                top_3_names = ", ".join([f"**{name}**" for name in top_3_products.index])
                st.markdown(f"📊 **Principais Influenciadores:** Os produtos {top_3_names} são os principais motores da receita, representando juntos **{top_3_percentage:.1f}%** do total.")

        # Análise de Tendência Mensal
        monthly_revenue = df_filtered.set_index('Data').resample('M')['Valor Total'].sum()
        monthly_quantity = df_filtered.set_index('Data').resample('M')['Quantidade'].sum()

        if len(monthly_revenue) > 1:
            x = np.arange(len(monthly_revenue))
            y = monthly_revenue.values
            slope, intercept = np.polyfit(x, y, 1)
            
            if slope > 100:
                tendencia_receita = "uma **tendência de crescimento**."
            elif slope < -100:
                tendencia_receita = "uma **tendência de queda**."
            else:
                tendencia_receita = "uma **tendência de estabilidade**."
            st.markdown(f"📈 **Tendência de Receita:** A análise da receita mensal indica {tendencia_receita}")

        if len(monthly_quantity) > 1:
            x_qty = np.arange(len(monthly_quantity))
            y_qty = monthly_quantity.values
            slope_qty, intercept_qty = np.polyfit(x_qty, y_qty, 1)

            if slope_qty > 50: # Limiar diferente para quantidade
                tendencia_qtd = "uma **tendência de crescimento**."
            elif slope_qty < -50:
                tendencia_qtd = "uma **tendência de queda**."
            else:
                tendencia_qtd = "uma **tendência de estabilidade**."
            st.markdown(f"⚖️ **Tendência de Quantidade:** A análise da quantidade mensal indica {tendencia_qtd}")
    except Exception:
        st.warning("Não foi possível gerar algumas análises narrativas com os dados atuais.")

    st.divider()

    # --- Gráficos ---
    st.header("Visualizações Gráficas")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Receita por Regional")
        chart_type_regional = st.radio(
            "Tipo de Gráfico para Regional:",
            ("Pizza", "Barras"),
            horizontal=True,
            label_visibility="collapsed"
        )

        revenue_by_regional = df_filtered.groupby('Regional')['Valor Total'].sum().reset_index()

        if chart_type_regional == "Pizza":
            fig_regional = px.pie(revenue_by_regional, values='Valor Total', names='Regional', hole=.3,
                             color_discrete_sequence=px.colors.sequential.Blues_r)
            fig_regional.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hovertemplate='<b>Regional:</b> %{label}<br><b>Receita:</b> R$ %{value:,.2f}<br><b>Percentual:</b> %{percent}<extra></extra>'
            )
        else: # Barras
            revenue_by_regional = revenue_by_regional.sort_values(by='Valor Total', ascending=True)
            fig_regional = px.bar(revenue_by_regional, x='Valor Total', y='Regional', orientation='h', text=revenue_by_regional['Valor Total'].apply(lambda x: f'R$ {x:,.2f}'))
            fig_regional.update_traces(hovertemplate='<b>Regional:</b> %{y}<br><b>Receita:</b> R$ %{x:,.2f}<extra></extra>',
                                      textposition='outside')
            fig_regional.update_layout(yaxis_title="Regional", xaxis_title="Valor Total (R$)")
        
        st.plotly_chart(fig_regional, use_container_width=True)

        st.subheader("Top 10 Filiais por Receita")
        revenue_by_filial = df_filtered.groupby('Filial Remetente')['Valor Total'].sum().nlargest(10).sort_values(ascending=True)
        fig_bar_h = px.bar(revenue_by_filial, x=revenue_by_filial.values, y=revenue_by_filial.index, orientation='h',
                           text=revenue_by_filial.apply(lambda x: f'R$ {x:,.2f}'))
        fig_bar_h.update_traces(
            hovertemplate='<b>Filial:</b> %{y}<br><b>Receita:</b> R$ %{x:,.2f}<extra></extra>',
            textposition='outside'
        )
        fig_bar_h.update_layout(yaxis_title="Filial Remetente", xaxis_title="Valor Total (R$)")
        st.plotly_chart(fig_bar_h, use_container_width=True)

        st.subheader("Top 10 Destinos por Receita")
        revenue_by_destino = df_filtered.groupby('Destino')['Valor Total'].sum().nlargest(10).sort_values(ascending=True)
        fig_bar_destino = px.bar(revenue_by_destino, x=revenue_by_destino.values, y=revenue_by_destino.index, orientation='h',
                                 text=revenue_by_destino.apply(lambda x: f'R$ {x:,.2f}'))
        fig_bar_destino.update_traces(
            hovertemplate='<b>Destino:</b> %{y}<br><b>Receita:</b> R$ %{x:,.2f}<extra></extra>',
            textposition='outside'
        )
        fig_bar_destino.update_layout(yaxis_title="Destino", xaxis_title="Valor Total (R$)")
        st.plotly_chart(fig_bar_destino, use_container_width=True)

    with col2:
        st.subheader("Análise de Receita por Produto")
        revenue_by_product = df_filtered.groupby('Produto')['Valor Total'].sum()
        if not revenue_by_product.empty:
            product_analysis_df = pd.DataFrame({
                'Valor Total': revenue_by_product,
                'Percentual': (revenue_by_product / total_revenue) * 100 if total_revenue > 0 else 0
            }).nlargest(10, 'Valor Total').sort_values(by='Valor Total', ascending=True)

            fig_prod = px.bar(
                product_analysis_df,
                x='Valor Total',
                y=product_analysis_df.index,
                orientation='h',
                text=product_analysis_df['Valor Total'].apply(lambda x: f'R$ {x:,.2f}'),
                custom_data=[product_analysis_df['Percentual']]
            )
            fig_prod.update_traces(
                hovertemplate='<b>Produto:</b> %{y}<br><b>Receita:</b> R$ %{x:,.2f}<br><b>Percentual do Total:</b> %{customdata[0]:.2f}%<extra></extra>',
                textposition='outside'
            )
            fig_prod.update_layout(
                yaxis_title="Produto",
                xaxis_title="Valor Total (R$)"
            )
            st.plotly_chart(fig_prod, use_container_width=True)

        st.subheader("Top 10 Produtos por Quantidade")
        quantity_by_product = df_filtered.groupby('Produto')['Quantidade'].sum().nlargest(10).sort_values(ascending=True)
        fig_bar_qty = px.bar(quantity_by_product, x=quantity_by_product.values, y=quantity_by_product.index, orientation='h',
                           text=quantity_by_product.apply(lambda x: f'{x:,.2f}'))
        fig_bar_qty.update_traces(
            hovertemplate='<b>Produto:</b> %{y}<br><b>Quantidade Total:</b> %{x:,.2f}<extra></extra>',
            textposition='outside'
        )
        fig_bar_qty.update_layout(yaxis_title="Produto", xaxis_title="Quantidade Total")
        st.plotly_chart(fig_bar_qty, use_container_width=True)

        st.subheader("Receita vs. Quantidade por Produto")
        # Agrupa os dados por produto, somando receita e quantidade
        rev_qty_by_product = df_filtered.groupby('Produto').agg({'Valor Total': 'sum', 'Quantidade': 'sum'}).reset_index()

        if not rev_qty_by_product.empty:
            fig_scatter = px.scatter(
                rev_qty_by_product,
                x='Quantidade',
                y='Valor Total',
                size='Valor Total',      # O tamanho da bolha representa a receita
                color='Produto',         # Cada produto tem uma cor
                hover_name='Produto',
                title="Análise de Portfólio de Produtos",
                labels={'Quantidade': 'Quantidade Total Vendida', 'Valor Total': 'Receita Total (R$)'}
            )
            fig_scatter.update_traces(
                hovertemplate='<b>Produto:</b> %{hovertext}<br>' +
                              '<b>Quantidade:</b> %{x:,.2f}<br>' +
                              '<b>Receita:</b> R$ %{y:,.2f}<extra></extra>'
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        st.subheader("Média de Preço Unitário por Produto")
        avg_price_by_product = df_filtered.groupby('Produto')['Preço Unitário'].mean().reset_index()
        if not avg_price_by_product.empty:
            avg_price_by_product.rename(columns={'Preço Unitário': 'Preço Médio (R$)'}, inplace=True)
            avg_price_by_product = avg_price_by_product.sort_values(by='Preço Médio (R$)', ascending=False)
            st.dataframe(avg_price_by_product.style.format({'Preço Médio (R$)': 'R$ {:,.2f}'}),
                         use_container_width=True,
                         hide_index=True)

    # --- Gráfico de Evolução Mensal (Largura Total) ---
    st.subheader("Evolução da Receita Mensal")
    if 'monthly_revenue' in locals() and len(monthly_revenue) > 1:
        # Converte a Series para DataFrame para facilitar o uso com plotly express
        monthly_revenue_df = monthly_revenue.reset_index()

        fig_line = px.line(monthly_revenue_df, x='Data', y='Valor Total', markers=True, 
                           title="Receita Mensal e Linha de Tendência", text='Valor Total')
        fig_line.update_traces(
            hovertemplate='<b>Mês:</b> %{x|%B de %Y}<br><b>Receita:</b> R$ %{y:,.2f}<extra></extra>',
            texttemplate='R$ %{text:,.2f}',
            textposition='top center'
        )
        trend_line = (slope * np.arange(len(monthly_revenue))) + intercept
        fig_line.add_scatter(x=monthly_revenue_df['Data'], y=trend_line, mode='lines', 
                             name='Linha de Tendência', line=dict(dash='dash'), 
                             hoverinfo='skip')
        # Move a legenda para o topo, ao lado do título
        fig_line.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        st.plotly_chart(fig_line, use_container_width=True)
    elif 'monthly_revenue' in locals():
        st.line_chart(monthly_revenue)

def _create_evolution_chart(df, date_col, value_col, period_code, period_label, title, y_axis_label, y_prefix="", y_suffix=""):
    """
    Função auxiliar para criar um gráfico de evolução temporal (linha com tendência).
    Agrupa os dados pelo período especificado e plota o resultado.
    """
    # 1. Agrupa os dados pelo período (Mensal, Trimestral, Anual)
    data_over_time = df.set_index(date_col).resample(period_code)[value_col].sum()

    if data_over_time.empty:
        # Não exibe nada se não houver dados para o período
        return
    
    # Fallback para um único ponto de dado (não é possível traçar linha de tendência)
    if len(data_over_time) < 2:
        st.line_chart(data_over_time)
        return

    # 2. Prepara o DataFrame para o gráfico
    df_chart = data_over_time.reset_index()
    
    # 3. Define o formato da data para o eixo e o hover do gráfico
    if period_label == "Mensal":
        hover_format = "%B de %Y"
        period_name_for_hover = "Mês"
    elif period_label == "Trimestral":
        # Converte a data para um formato de trimestre (ex: '2024Q1')
        df_chart[date_col] = df_chart[date_col].dt.to_period('Q').astype(str)
        hover_format = None # Usa a string pré-formatada
        period_name_for_hover = "Trimestre"
    else: # Anual
        df_chart[date_col] = df_chart[date_col].dt.year
        hover_format = None # Usa o ano como string
        period_name_for_hover = "Ano"

    # 4. Calcula a linha de tendência
    x_trend = np.arange(len(data_over_time))
    y_trend_data = data_over_time.values
    slope, intercept = np.polyfit(x_trend, y_trend_data, 1)
    trend_line = (slope * x_trend) + intercept

    # 5. Cria a figura do Plotly
    fig = px.line(df_chart, x=date_col, y=value_col, markers=True, 
                  title=f"{title} por Período e Linha de Tendência", text=value_col)
    
    # 6. Formata os templates de hover e texto
    hover_template = f"<b>{period_name_for_hover}:</b> %{{x"
    if hover_format:
        hover_template += f"|{hover_format}"
    hover_template += f"}}<br><b>{y_axis_label}:</b> {y_prefix}%{{y:,.2f}}{y_suffix}<extra></extra>"
    
    text_template = f"{y_prefix}%{{text:,.2f}}{y_suffix}"

    fig.update_traces(
        hovertemplate=hover_template,
        texttemplate=text_template,
        textposition='top center'
    )

    # 7. Adiciona a linha de tendência ao gráfico
    fig.add_scatter(x=df_chart[date_col], y=trend_line, mode='lines', 
                    name='Linha de Tendência', line=dict(dash='dash'), 
                    hoverinfo='skip')
    
    # 8. Atualizações finais de layout
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="Período",
        yaxis_title=y_axis_label,
        title_x=0.5 # Centraliza o título
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # --- Gráfico de Evolução da Quantidade Mensal (Largura Total) ---
    st.subheader("Evolução da Quantidade Mensal")
    if 'monthly_quantity' in locals() and len(monthly_quantity) > 1:
        # Converte a Series para DataFrame para facilitar o uso com plotly express
        monthly_quantity_df = monthly_quantity.reset_index()

        fig_line_qty = px.line(monthly_quantity_df, x='Data', y='Quantidade', markers=True, 
                           title="Quantidade Mensal e Linha de Tendência", text='Quantidade')
        fig_line_qty.update_traces(
            hovertemplate='<b>Mês:</b> %{x|%B de %Y}<br><b>Quantidade:</b> %{y:,.2f}<extra></extra>',
            texttemplate='%{text:,.2f}',
            textposition='top center'
        )
        trend_line_qty = (slope_qty * np.arange(len(monthly_quantity))) + intercept_qty
        fig_line_qty.add_scatter(x=monthly_quantity_df['Data'], y=trend_line_qty, mode='lines', 
                             name='Linha de Tendência', line=dict(dash='dash'), 
                             hoverinfo='skip')
        # Move a legenda para o topo, ao lado do título
        fig_line_qty.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        st.plotly_chart(fig_line_qty, use_container_width=True)
    elif 'monthly_quantity' in locals():
        st.line_chart(monthly_quantity)

    # --- Gráficos de Evolução Temporal (Largura Total) ---
    st.divider()
    st.header("Análise de Evolução Temporal")

    # Seletor de período para os gráficos de evolução
    period_options = {"Mensal": "M", "Trimestral": "Q", "Anual": "Y"}
    selected_period_label = st.radio(
        "Agrupar dados por:",
        options=list(period_options.keys()),
        horizontal=True,
        key="evolution_period"
    )
    period_code = period_options[selected_period_label]

    # Gráfico de Evolução da Receita
    _create_evolution_chart(
        df=df_filtered,
        date_col='Data',
        value_col='Valor Total',
        period_code=period_code,
        period_label=selected_period_label,
        title="Evolução da Receita",
        y_axis_label="Receita (R$)",
        y_prefix="R$ "
    )

    # Gráfico de Evolução da Quantidade
    _create_evolution_chart(
        df=df_filtered,
        date_col='Data',
        value_col='Quantidade',
        period_code=period_code,
        period_label=selected_period_label,
        title="Evolução da Quantidade",
        y_axis_label="Quantidade"
    )

def to_excel(df):
    """Converte um DataFrame para um arquivo Excel em memória."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    processed_data = output.getvalue()
    return processed_data

def get_table_download_link(df, filename, text, logo_path):
    """
    Generates an HTML link to download a data frame as an Excel file,
    styled to look like a button with a logo.
    """
    excel_data = to_excel(df)
    b64_excel = base64.b64encode(excel_data).decode()

    with open(logo_path, "rb") as f:
        logo_data = f.read()
    b64_logo = base64.b64encode(logo_data).decode()

    # CSS to style the link as a button. Using a class to avoid ID conflicts.
    button_css = """
        <style>
        .download-button-custom {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background-color: #F0F2F6;
            color: #3133F;
            padding: 0.4rem 0.75rem;
            border-radius: 0.5rem;
            border: 1px solid rgba(49, 51, 63, 0.2);
            text-decoration: none;
            font-weight: 400;
            font-size: 14px;
            transition: all 0.2s;
            width: 100%;
            box-sizing: border-box;
        }
        .download-button-custom:hover { border-color: #0068C9; color: #0068C9; }
        .download-button-custom:active { background-color: #e0e2e6; }
        </style>
    """
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="{filename}" class="download-button-custom"><img src="data:image/png;base64,{b64_logo}" width="16" style="margin-right: 8px;">{text}</a>'
    return f"{button_css}{href}"

def get_template_excel():
    """Cria e retorna um arquivo Excel modelo para download."""
    # A ordem das colunas foi ajustada para corresponder à estrutura do arquivo do usuário.
    template_data = {
        'Tipo de Operação': ['Venda'],
        'Regional': ['Nome da Regional'],
        'Filial Remetente': ['Nome da Filial'],
        'Data': ['25/01/2024'],
        'Produto': ['Nome do Produto'],
        'Destino': ['Nome do Destino'],
        'Quantidade': [100.50],
        'Unidade': ['KG'],
        'Preço Unitário': [1.25],
        'NFe': ['123456'],
        'Observacoes': ['Exemplo de observação.']
    }
    df_template = pd.DataFrame(template_data)
    return to_excel(df_template)

def process_excel_upload(conn, user_name, uploaded_file):
    """
    Processa o upload de uma planilha Excel e insere os registros no banco de dados.
    Esta versão foi otimizada para performance e robustez, fornecendo feedback detalhado sobre erros.
    """
    if uploaded_file is None:
        st.warning("Por favor, faça o upload de um arquivo Excel.")
        return

    try:
        # 1. Leitura e Normalização de Colunas
        df = pd.read_excel(uploaded_file, dtype=str).fillna('')
        df_original_for_report = df.copy() # Cópia para o relatório de erros

        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.normalize("NFKD")
            .str.encode("ascii", "ignore")
            .str.decode("utf-8")
        )
        df.rename(columns={
            'tipo de operacao': 'tipo_operacao',
            'filial remetente': 'filial_remetente',
            'preco unitario': 'preco_unitario',
            'preço unitario': 'preco_unitario',
            'preço unitário': 'preco_unitario',
            'valor total': 'valor_total',
            'nfe': 'nfe',
            'observacoes': 'observacoes'
        }, inplace=True)

        # 2. Verificação de Colunas Essenciais
        required_columns = [
            "tipo_operacao", "regional", "filial_remetente", "data", "produto", "destino",
            "quantidade", "unidade", "preco_unitario"
        ]
        optional_columns = ["nfe", "observacoes"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"❌ A planilha está com colunas faltando ou com nomes incorretos: {', '.join(missing_columns)}")
            return

        # 3. Limpeza e Conversão de Tipos
        df['tipo_operacao'] = df['tipo_operacao'].str.strip().str.title()
        df['regional'] = df['regional'].str.strip().str.title()
        df['filial_remetente'] = df['filial_remetente'].str.strip().str.title()
        df['destino'] = df['destino'].str.strip().str.title()
        df['produto'] = df['produto'].str.strip().str.title()
        df['unidade'] = df['unidade'].str.strip().str.title()

        # Adiciona colunas opcionais se não existirem
        for col in optional_columns:
            if col not in df.columns: df[col] = ''
        df['nfe'] = df['nfe'].str.strip()
        df['observacoes'] = df['observacoes'].str.strip()

        # Converte tipos de dados, tratando erros e formatos (ex: vírgula decimal)
        df['data'] = pd.to_datetime(df['data'], errors='coerce', dayfirst=True)
        df['quantidade'] = pd.to_numeric(df['quantidade'].str.replace(',', '.', regex=False), errors='coerce')
        df['preco_unitario'] = pd.to_numeric(df['preco_unitario'].str.replace(',', '.', regex=False), errors='coerce')

        # 4. Validação Detalhada e Separação de Dados
        error_conditions = {
            "Data inválida ou em branco": df['data'].isna(),
            "Quantidade inválida, não numérica ou em branco": df['quantidade'].isna(),
            "Preço unitário inválido, não numérico ou em branco": df['preco_unitario'].isna(),
            "Quantidade deve ser maior que zero": df['quantidade'] <= 0,
            "Campo 'Tipo de Operação' obrigatório não preenchido": df['tipo_operacao'] == '',
            "Campo 'Regional' obrigatório não preenchido": df['regional'] == '',
            "Campo 'Produto' obrigatório não preenchido": df['produto'] == '',
            "Campo 'Unidade' obrigatório não preenchido": df['unidade'] == '',
        }

        # Cria uma máscara booleana para identificar todas as linhas inválidas
        invalid_mask = pd.Series(False, index=df.index)
        for condition in error_conditions.values():
            invalid_mask |= condition

        df_valid = df[~invalid_mask].copy()
        df_invalid = df_original_for_report[invalid_mask].copy()

        # Gera a coluna de motivo do erro para o relatório
        if not df_invalid.empty:
            error_messages = pd.Series('', index=df_invalid.index)
            for reason, condition in error_conditions.items():
                # Aplica a condição na máscara de linhas inválidas
                rows_with_this_error = condition[invalid_mask]
                error_messages.loc[rows_with_this_error] = error_messages.loc[rows_with_this_error].apply(lambda x: (x + '; ' if x else '') + reason)
            df_invalid['Motivo do Erro'] = error_messages

        # 5. Processamento dos Dados Válidos
        if df_valid.empty:
            st.error("❌ Nenhum registro válido encontrado na planilha para importação.")
        else:
            # PERFORMANCE: Cálculo vetorizado, muito mais rápido que df.apply
            df_valid['valor_total'] = (df_valid['quantidade'] * df_valid['preco_unitario']).round(2)
            df_valid['data'] = df_valid['data'].dt.strftime('%Y-%m-%d')
            # Adiciona as informações de quem e quando o registro foi adicionado
            df_valid['usuario_lancamento'] = user_name

            # Prepara o DataFrame final para inserção no banco
            final_columns_to_insert = required_columns + optional_columns + ['valor_total', 'usuario_lancamento']
            df_to_insert = df_valid[final_columns_to_insert]

            # Insere o DataFrame diretamente no banco de dados (mais performático)
            # A coluna 'data_lancamento' será preenchida pelo DEFAULT CURRENT_TIMESTAMP do banco.
            df_to_insert.to_sql('registros', conn, if_exists='append', index=False)
            conn.commit()
            
            log_activity(conn, user_name, "Importação de Planilha", f"{len(df_valid)} registros adicionados.")
            st.success(f"✅ Importação concluída! {len(df_valid)} registros adicionados com sucesso.")

        # 6. Feedback Detalhado sobre Erros
        if not df_invalid.empty:
            st.warning(f"⚠️ {len(df_invalid)} linhas foram ignoradas por conterem dados inválidos ou incompletos.")
            with st.expander("Ver detalhes das linhas com erro"):
                st.dataframe(df_invalid, use_container_width=True)
                st.download_button(
                    label="📥 Baixar Relatório de Erros",
                    data=to_excel(df_invalid),
                    file_name=f"relatorio_erros_importacao_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"❌ Ocorreu um erro inesperado ao processar o arquivo Excel: {e}")