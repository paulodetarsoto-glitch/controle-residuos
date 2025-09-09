import streamlit as st
import pandas as pd
import database
import io
from datetime import datetime

def to_excel(df: pd.DataFrame) -> bytes:
    """
    Converte um DataFrame do Pandas para um arquivo Excel em memória.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Registros')
    # O método .close() é chamado automaticamente pelo 'with'
    processed_data = output.getvalue()
    return processed_data

# --- Configuração da Página ---
# st.set_page_config é chamado no app.py principal

# --- Título da Página ---
st.title("📋 Visualizar Registros")
st.markdown("Filtre e visualize todos os registros de vendas e transferências de resíduos.")

# --- Conexão com o Banco de Dados ---
conn = database.connect_db()
if not conn:
    st.error("Falha na conexão com o banco de dados.")
    st.stop()

# --- Carregar Dados ---
try:
    # Supondo que a função get_all_records exista em database.py e retorne um DataFrame
    df_registros = database.get_all_records(conn)
except Exception as e:
    st.error(f"Ocorreu um erro ao buscar os registros: {e}")
    st.stop()
finally:
    conn.close()

if df_registros.empty:
    st.warning("Nenhum registro encontrado no banco de dados.")
    st.stop()

# --- UI de Filtros na Barra Lateral ---
st.sidebar.header("Filtros de Visualização")

# Garante que as colunas existem antes de criar os filtros
remetente_options = sorted(df_registros['Filial Remetente'].unique()) if 'Filial Remetente' in df_registros.columns else []
produto_options = sorted(df_registros['Produto'].unique()) if 'Produto' in df_registros.columns else []

selected_remetentes = st.sidebar.multiselect("Filtrar por Remetente:", options=remetente_options, default=[])
selected_produtos = st.sidebar.multiselect("Filtrar por Produto:", options=produto_options, default=[])

# Aplica os filtros
df_filtered = df_registros
if selected_remetentes:
    df_filtered = df_filtered[df_filtered['Filial Remetente'].isin(selected_remetentes)]
if selected_produtos:
    df_filtered = df_filtered[df_filtered['Produto'].isin(selected_produtos)]

# --- Exibição dos Dados ---
st.dataframe(df_filtered, use_container_width=True, hide_index=True)

st.markdown("---")

# --- Botão de Exportação ---
if not df_filtered.empty:
    excel_data = to_excel(df_filtered)
    
    st.download_button(
        label="📥 Exportar Dados Filtrados para Excel",
        data=excel_data,
        file_name=f"registros_residuos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary"
    )