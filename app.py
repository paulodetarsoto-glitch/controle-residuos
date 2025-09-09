# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import operations
import database
from datetime import datetime
from PIL import Image
from streamlit_option_menu import option_menu
import base64
import time
import os
from style import CSS_STYLE

# --- Funções Cacheadas para Performance ---
@st.cache_data
def get_cached_logo():
    """Carrega a imagem do logo, cacheando o resultado."""
    return Image.open("logo.png")

@st.cache_data
def get_cached_setting_options(_conn, setting_name):
    """Busca opções de configuração do DB, cacheando o resultado."""
    return operations.get_setting_options(_conn, setting_name)

@st.cache_data
def get_cached_distinct_options(_conn, field_name):
    """Busca opções distintas da tabela de registros, cacheando o resultado."""
    return operations.get_distinct_field_options(_conn, field_name)

# --- Configurações da Página ---
logo_icon = get_cached_logo()
st.set_page_config(
    page_title="Controle de Resíduos",
    page_icon=logo_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Aplica o CSS global em todas as páginas ---
st.markdown(f'<style>{CSS_STYLE}</style>', unsafe_allow_html=True)

# --- Força a cor azul em todos os botões ---
FORCE_BUTTON_BLUE_CSS = """
<style>
    /* Força a cor de todos os botões para o azul especificado */
    div[data-testid="stButton"] > button,
    div[data-testid="stDownloadButton"] > button,
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #3dadf1 !important;
        color: white !important;
        border: 1px solid #3dadf1 !important;
    }

    /* Efeito hover para os botões */
    div[data-testid="stButton"] > button:hover,
    div[data-testid="stDownloadButton"] > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #2c8ac8 !important; /* Um tom de azul um pouco mais escuro */
        border: 1px solid #2c8ac8 !important;
        color: white !important;
    }

    /* Estilo para botões desabilitados para manter a consistência */
    div[data-testid="stButton"] > button:disabled,
    div[data-testid="stDownloadButton"] > button:disabled,
    div[data-testid="stFormSubmitButton"] > button:disabled {
        background-color: #cccccc !important;
        color: #666666 !important;
        border: 1px solid #cccccc !important;
    }
</style>
"""
st.markdown(FORCE_BUTTON_BLUE_CSS, unsafe_allow_html=True)

def show_success_animation():
    """Exibe uma animação de sucesso (checkmark) em tela cheia."""
    success_html = """
        <div id="success-container-fullscreen">
            <div id="success-animation-container">
                <svg class="checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
                    <circle class="checkmark__circle" cx="26" cy="26" r="25" fill="none"/>
                    <path class="checkmark__check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
                </svg>
                <div id="success-message">Registro Adicionado!</div>
            </div>
        </div>
        <style>
            #success-container-fullscreen {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                display: flex;
                justify-content: center;
                align-items: center;
                background-color: rgba(0, 0, 0, 0.4);
                z-index: 9999;
                pointer-events: none;
                animation: fadeOutContainerSuccess 2s forwards;
                animation-delay: 1.5s;
            }
            #success-animation-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 2rem;
                background-color: #fff;
                border-radius: 15px;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                animation: popInSuccess 0.5s ease-out forwards;
            }
            #success-message { font-size: 1.5rem; font-weight: bold; color: #001f3f; margin-top: 1rem; }
            .checkmark { width: 100px; height: 100px; }
            .checkmark__circle { stroke-dasharray: 166; stroke-dashoffset: 166; stroke-width: 3; stroke-miterlimit: 10; stroke: #4CAF50; fill: none; animation: stroke 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards; }
            .checkmark__check { transform-origin: 50% 50%; stroke-dasharray: 48; stroke-dashoffset: 48; stroke-width: 3; stroke: #4CAF50; fill: none; animation: stroke 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.8s forwards; }
            @keyframes stroke { 100% { stroke-dashoffset: 0; } }
            @keyframes popInSuccess { from { transform: scale(0.5); opacity: 0; } to { transform: scale(1); opacity: 1; } }
            @keyframes fadeOutContainerSuccess { from { opacity: 1; } to { opacity: 0; } }
        </style>
        <script>
            setTimeout(() => { const el = document.getElementById('success-container-fullscreen'); if (el) { el.remove(); } }, 3500);
        </script>
    """
    st.markdown(success_html, unsafe_allow_html=True)
    st.session_state.show_add_success_animation = False

def parse_brl_to_float(value_str: str) -> float:
    """
    Converte uma string de moeda no formato brasileiro (ex: '1.234,56') para float.
    Levanta um ValueError se a string não for um número válido.
    """
    if not isinstance(value_str, str):
        if isinstance(value_str, (int, float)):
            return float(value_str)
        value_str = str(value_str)

    cleaned_str = value_str.strip()
    if not cleaned_str:
        return 0.0

    # Remove o separador de milhar (.) e substitui a vírgula decimal (,) por ponto.
    return float(cleaned_str.replace('.', '').replace(',', '.'))

@st.cache_data
def get_image_as_base64(path):
    """Codifica uma imagem em base64 para embutir em CSS."""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# --- Conexão com o Banco de Dados e Inicialização ---
conn = database.connect_db()
if conn:
    database.create_table(conn)
    database.create_settings_tables(conn)
    database.create_users_table(conn)
    database.run_migrations(conn)
    operations.run_user_role_migration(conn)
    database.create_log_table(conn)
else:
    st.error("Falha crítica na conexão com o banco de dados. O aplicativo não pode continuar.")
    st.stop()

# --- Lógica de Autenticação e UI de Login ---
def show_login_page():
    """Exibe a página de login e popula o banco com usuários iniciais, se necessário."""
    # Centraliza o conteúdo principal da página de login.
    _, center_col, _ = st.columns([1, 1.2, 1])
    with center_col:
        
        st.markdown("<h3 style='text-align: center; color: white; font-size: 1.2rem; margin-bottom: 1rem; white-space: nowrap;'>Sistema de controle de vendas e transferência de resíduos</h3>", unsafe_allow_html=True)
        # --- SOLUÇÃO APLICADA AQUI: Adiciona um div customizado para estilização confiável ---
        st.markdown('<div class="login-container-custom">', unsafe_allow_html=True)
        st.image("logobranca.png", use_container_width=True)

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            st.info("⚙️ Configurando usuários iniciais pela primeira vez...")
            operations.add_user(conn, "Administrador", "admpaulo", role="Admin")
            operations.add_user(conn, "Gilberto", "gilberto01", role="User")
            st.info("Usuários iniciais criados. Por favor, faça o login.")
            st.rerun()

        with st.form("login_form"):
            username = st.text_input("Usuário", placeholder="Usuário", label_visibility="collapsed")
            password = st.text_input("Senha", type="password", placeholder="Senha", label_visibility="collapsed")
            submitted = st.form_submit_button("Entrar", use_container_width=True, type="primary")

            if submitted:
                with st.spinner("Entrando no sistema de controle de resíduos..."):
                    user = operations.get_user(conn, username)
                    if user and operations.verify_password(user['password_hash'], password):
                        st.session_state.authenticated = True
                        st.session_state.username = user['username']
                        st.session_state.role = user['role']
                        st.session_state.show_welcome_animation = True
                        st.rerun()
                    else:
                        st.error("Usuário ou senha inválidos.")
        st.markdown('</div>', unsafe_allow_html=True) # Feche o div customizado

# --- Lógica Principal do Aplicativo ---
if not st.session_state.get("authenticated"):
    logo_base64 = get_image_as_base64("logobranca.png")
    login_overrides_css = f"""
        <style>
            .stApp {{
                background-color: #31333f; /* Cor de fundo para a tela de login */
            }}
            /* Imagem de fundo opaca */
            [data-testid="stAppViewContainer"]::before {{
                content: "";
                position: fixed;
                left: 0;
                top: 0;
                width: 100vw;
                height: 100vh;
                background-image: url("data:image/png;base64,{logo_base64}");
                background-size: 40%;
                background-position: center;
                background-repeat: no-repeat;
                opacity: 0.05;
                z-index: -1;
            }}
            /* Estilo da caixa de login - AGORA COM CLASSE CUSTOMIZADA */
            .login-container-custom {{
                background-color: transparent !important;
                border-radius: 15px;
                padding: 2rem;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                border: 1px solid rgba(255, 255, 255, 0.18);
            }}
            /* Estiliza o popover de ajuda "Algo está errado" */
            [data-testid="stPopover"] {{
                display: flex;
                justify-content: center;
                margin-top: 1rem;
            }}
            [data-testid="stPopover"] > button {{
                background-color: transparent !important;
                color: white !important; /* Cor do texto para ser visível no fundo escuro */
                border: none !important;
                padding: 0 !important;
                font-size: 0.7rem; /* Tamanho da fonte ainda menor */
                text-decoration: none; /* Remove sublinhado padrão */
                box-shadow: none !important;
            }}
            [data-testid="stPopover"] > button:hover {{
                text-decoration: underline !important;
            }}

            /* Remove a borda da imagem do logo, já que agora está na caixa */
            .stImage > img {{
                border: none;
                box-shadow: none;
                /* Adiciona um contorno branco que segue a arte da logo */
                filter: drop-shadow(2px 0 0 white) 
                        drop-shadow(-2px 0 0 white) 
                        drop-shadow(0 2px 0 white) 
                        drop-shadow(0 -2px 0 white);
            }}
            /* Garante que o container principal não tenha fundo, para não sobrepor a caixa */
            .main > .block-container {{
                background-color: transparent !important;
                box-shadow: none;
                border: none;
                padding-top: 0;
            }}
        </style>
    """
    if logo_base64:
        st.markdown(login_overrides_css, unsafe_allow_html=True)

    show_login_page()
else:
    # --- Recupera informações do usuário da sessão ---
    user_name = st.session_state.get('username')
    user_role = st.session_state.get('role')

    if st.session_state.get("show_welcome_animation"):
        welcome_message = f'♻️ Seja bem-vindo, {st.session_state.username}!'
        
        # --- CORREÇÃO AQUI: Escapa a chave do JavaScript com {{ e }} ---
        animation_html = f"""
            <div id="welcome-container-fullscreen">
                <div id="welcome-message-animated">{welcome_message}</div>
            </div>
            <style>
                #welcome-container-fullscreen {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 9999;
                    pointer-events: none;
                    animation: fadeOutContainer 4s forwards;
                    animation-delay: 2s;
                }}

                #welcome-message-animated {{
                    font-size: 2.5rem;
                    font-weight: bold;
                    color: white;
                    padding: 20px 40px;
                    background-color: #001f3f;
                    border-radius: 10px;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
                    text-align: center;
                    animation: popIn 0.5s ease-out forwards;
                }}

                @keyframes popIn {{ from {{ transform: scale(0.5); opacity: 0; }} to {{ transform: scale(1); opacity: 1; }} }}
                @keyframes fadeOutContainer {{ from {{ opacity: 1; }} to {{ opacity: 0; }} }}
            </style>
            <script>
                setTimeout(() => {{ const el = document.getElementById('welcome-container-fullscreen'); if (el) {{ el.remove(); }} }}, 6000);
            </script>
        """
        st.markdown(animation_html, unsafe_allow_html=True)
        st.session_state.show_welcome_animation = False

    # --- ANIMAÇÃO DE SUCESSO AO ADICIONAR REGISTRO ---
    if st.session_state.get("show_add_success_animation"):
        show_success_animation()

    # --- Barra Lateral e Menu de Navegação ---
    with st.sidebar:
        st.image("logo.png", use_container_width=True)
        st.markdown(f"<p style='text-align: center; color: white; font-size: 0.8rem;'>Usuário logado: {user_name}</p>", unsafe_allow_html=True)
        st.title("") 
        PAGES = {
            "Dashboard": "📊 Dashboard",
            "Visualizar Registros": "📋 Visualizar Registros",
            "Configurações": "⚙️ Configurações",
        }
        if user_role == "Admin":
            PAGES["Log de Atividades"] = "📜 Log de Atividades"
            PAGES["Upload de Planilha"] = "⬆️ Upload de Planilha"
            PAGES["Gerenciamento de Usuários"] = "👥 Gerenciamento de Usuários"
        
        PAGES["Ajuda"] = "❓ Ajuda"

        selected_page_key = option_menu(
            menu_title=None,
            options=list(PAGES.keys()),
            icons=[v.split(" ")[0] for v in PAGES.values()],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#001f3f"},
                "icon": {"color": "white", "font-size": "18px"},
                "nav-link": {"color": "white", "font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#004c7a"},
                "nav-link-selected": {"background-color": "##6d5381"},
            }
        )
        
        st.divider()
        if st.button("Sair", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    previous_page_key = st.session_state.get('previous_page_key', None)

    # --- Função Reutilizável para o Formulário de Adição ---
    def display_add_record_form(conn, user_name, regionais_options, remetentes_options, destinos_options, produtos_options, unidades_options, on_close_callback=None):
        """Exibe o formulário completo para adicionar um novo registro."""
        
        st.header("Adicionar Novo Registro")

        with st.form("add_record_form"):
            col1, col2 = st.columns(2)
            with col1:
                data = st.date_input("Data")
                tipo_operacao = st.selectbox("Tipo de Operação", ["Venda", "Transferência"], index=None, placeholder="Selecione o tipo de operação...")

                regional = st.selectbox("Regional", regionais_options, index=None, placeholder="Selecione a regional...")
                remetente = st.selectbox("Filial Remetente", remetentes_options, index=None, placeholder="Selecione a filial...")
                
                add_new_destino_str = "➕ Adicionar Novo Destino..."
                destino_options_with_add = destinos_options + [add_new_destino_str]
                destino_selection = st.selectbox("Destino", destino_options_with_add, index=None, placeholder="Selecione ou adicione um destino...")
                destino = st.text_input("Digite o Novo Destino", key="new_destino_input") if destino_selection == add_new_destino_str else destino_selection
                    
                produto = st.selectbox("Produto", produtos_options, index=None, placeholder="Selecione o produto...")
            
            with col2:
                quantidade = st.number_input("Quantidade", min_value=0.0, format="%.2f")

                unidade = st.selectbox("Unidade", unidades_options, index=None, placeholder="Selecione a unidade...")

                preco_unitario_str = st.text_input("Preço Unitário (R$)", "0,00")
                valor_total_str = st.text_input("Valor Total (R$)", "0,00")
                nfe = st.text_input("NFe")
                observacoes = st.text_area("Observações")

            submit_col, close_col, _ = st.columns([1, 1, 4])
            submitted = submit_col.form_submit_button("Adicionar Registro", use_container_width=True, type="primary")
            
            if on_close_callback:
                if close_col.form_submit_button("Fechar", use_container_width=True):
                    on_close_callback()
                    st.rerun()

            if submitted:
                if not all([tipo_operacao, regional, remetente, destino, produto, unidade]):
                    st.error("❌ Por favor, preencha todos os campos obrigatórios.")
                else:
                    try:
                        preco_unitario = parse_brl_to_float(preco_unitario_str)
                        valor_total = parse_brl_to_float(valor_total_str)
                    except ValueError:
                        st.error("❌ Por favor, insira valores numéricos válidos para Preço Unitário e Valor Total.")
                    else:
                        success = operations.add_record(conn, user_name, data.strftime('%Y-%m-%d'), tipo_operacao, regional, remetente, destino, produto, quantidade, unidade, preco_unitario, valor_total, nfe, observacoes)
                        if success:
                            # Limpa o cache de opções para que o novo valor apareça na próxima vez
                            get_cached_distinct_options.clear()
                            st.session_state.show_add_success_animation = True
                            if on_close_callback: on_close_callback()
                            st.rerun()

    if selected_page_key != previous_page_key and selected_page_key == "Dashboard":
        operations.log_activity(conn, user_name, "Visualizar Dashboard", "Usuário acessou a página do dashboard.")
    st.session_state['previous_page_key'] = selected_page_key

    # Busca as opções das listas a partir dos dados já existentes nos registros.
    regionais_options = get_cached_distinct_options(conn, "regional")
    remetentes_options = get_cached_distinct_options(conn, "filial_remetente")
    destinos_options = get_cached_distinct_options(conn, "destino")
    produtos_options = get_cached_distinct_options(conn, "produto")
    unidades_options = get_cached_distinct_options(conn, "unidade")

    if selected_page_key == "Dashboard":
        operations.display_dashboard(conn)

    elif selected_page_key == "Visualizar Registros":
        st.header("Registros Atuais")

        # --- Funções de Callback para a página "Visualizar Registros" ---
        def open_inline_form():
            st.session_state.show_add_form_inline = True

        def close_inline_form():
            st.session_state.show_add_form_inline = False

        def go_to_next_page(total_pages):
            """Callback para ir para a próxima página."""
            if st.session_state.page_number < total_pages - 1:
                st.session_state.page_number += 1

        def go_to_previous_page():
            """Callback para ir para a página anterior."""
            if st.session_state.page_number > 0:
                st.session_state.page_number -= 1

        def handle_selection_change():
            """Callback para lidar com a seleção de linha no dataframe."""
            selection = st.session_state.get("registros_df", {}).get("selection", {})
            selected_indices = selection.get("rows", [])
            
            # O 'on_select' retorna os ÍNDICES da linha na tabela exibida (ex: 0, 1, 2).
            # Precisamos mapear esses índices para os IDs reais do banco de dados.
            # Usamos o DataFrame da página atual, que está no escopo quando o callback é executado.
            if selected_indices and not df_to_display.empty:
                st.session_state.selected_record_ids = df_to_display.iloc[selected_indices]['ID'].tolist()
            else:
                st.session_state.selected_record_ids = []
            
            # Limpa os estados de exclusão se a seleção mudar
            if 'record_to_delete' in st.session_state:
                del st.session_state.record_to_delete
            if 'records_to_delete_bulk' in st.session_state:
                del st.session_state.records_to_delete_bulk

        def prompt_for_delete():
            """Callback para iniciar o processo de exclusão."""
            if st.session_state.get('selected_record_ids') and len(st.session_state.selected_record_ids) == 1:
                st.session_state.record_to_delete = st.session_state.selected_record_ids[0]

        def confirm_delete():
            """Callback para confirmar e executar a exclusão."""
            operations.delete_record(conn, user_name, st.session_state.record_to_delete)
            del st.session_state.record_to_delete
            st.session_state.selected_record_ids = []
            st.session_state.registros_df['selection'] = {'rows': [], 'columns': []} # Limpa a seleção visualmente

        def cancel_delete():
            """Callback para cancelar a exclusão."""
            del st.session_state.record_to_delete

        def prompt_for_bulk_delete():
            """Callback para iniciar o processo de exclusão em massa."""
            st.session_state.records_to_delete_bulk = st.session_state.selected_record_ids

        def confirm_bulk_delete():
            """Callback para confirmar e executar a exclusão em massa."""
            operations.delete_records_bulk(conn, user_name, st.session_state.records_to_delete_bulk)
            del st.session_state.records_to_delete_bulk
            st.session_state.selected_record_ids = []
            st.session_state.registros_df['selection'] = {'rows': [], 'columns': []}

        def cancel_bulk_delete():
            """Callback para cancelar a exclusão em massa."""
            del st.session_state.records_to_delete_bulk

        if 'page_number' not in st.session_state:
            st.session_state.page_number = 0
        
        # --- Botão para Adicionar Registro Inline ---
        if 'show_add_form_inline' not in st.session_state:
            st.session_state.show_add_form_inline = False

        add_form_placeholder = st.empty()
        if not st.session_state.show_add_form_inline:
            st.button("➕ Adicionar Novo Registro", on_click=open_inline_form, type="primary")
        
        if st.session_state.show_add_form_inline:
            with add_form_placeholder.container(border=True):
                display_add_record_form(
                    conn, user_name, regionais_options, remetentes_options, 
                    destinos_options, produtos_options, unidades_options,
                    on_close_callback=close_inline_form
                )

        RECORDS_PER_PAGE = 25
        search_query = st.text_input("Pesquisar em todos os campos de texto", placeholder="Digite para pesquisar...")
        total_records = operations.get_records_count(conn, search_query)
        total_pages = (total_records + RECORDS_PER_PAGE - 1) // RECORDS_PER_PAGE if total_records > 0 else 1
        st.session_state.page_number = max(0, min(st.session_state.page_number, total_pages - 1))
        offset = st.session_state.page_number * RECORDS_PER_PAGE
        df_to_display = operations.get_paginated_records(
            conn, 
            limit=RECORDS_PER_PAGE, 
            offset=offset, 
            search_query=search_query
        )

        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        with nav_col1:
            st.button("⬅️ Anterior", 
                      use_container_width=True, 
                      disabled=(st.session_state.page_number <= 0),
                      on_click=go_to_previous_page)
        with nav_col2:
            st.markdown(f"<p style='text-align: center; color: white; margin-top: 0.5rem;'>Página {st.session_state.page_number + 1} de {total_pages}</p>", unsafe_allow_html=True)
        with nav_col3:
            st.button("Próximo ➡️", 
                      use_container_width=True, 
                      disabled=(st.session_state.page_number >= total_pages - 1),
                      on_click=go_to_next_page,
                      args=(total_pages,))
        
        # Placeholder para o diálogo de confirmação, para que ele possa ser renderizado no topo se necessário
        confirmation_placeholder = st.empty()

        selected_ids = st.session_state.get("selected_record_ids", [])

        # --- Botões de Ação em Massa (Aparecem quando há seleção) ---
        if selected_ids and user_role == 'Admin':
            num_selected = len(selected_ids)
            st.info(f"**{num_selected} registro(s) selecionado(s).**")
            
            # Desabilita botões se um diálogo de confirmação já estiver ativo
            is_confirmation_active = 'record_to_delete' in st.session_state or 'records_to_delete_bulk' in st.session_state
            
            action_col1, _ = st.columns([1, 5])
            with action_col1:
                st.button(f"🗑️ Excluir {num_selected} Registro(s)", key="delete_bulk_prompt",
                          on_click=prompt_for_bulk_delete, type="primary", use_container_width=True,
                          disabled=is_confirmation_active)

        if not df_to_display.empty:
            df_display = df_to_display.copy()
            df_display["Data"] = df_display["Data"].dt.strftime("%d/%m/%Y")

            column_order = [
                "Data de Lançamento", "Usuário", "Data", "Tipo de Operação",
                "Regional", "Filial Remetente", "Destino", "Produto",
                "Quantidade", "Unidade", "Preço Unitário", "Valor Total", 
                "NFe", "Observacoes"
            ]
            existing_columns_in_df = [col for col in column_order if col in df_display.columns]

            st.dataframe(
                df_display.set_index('ID'),
                on_select=handle_selection_change,
                selection_mode="multi-row",
                key="registros_df",
                use_container_width=True,
                column_order=existing_columns_in_df,
                column_config={
                    "Data de Lançamento": st.column_config.DatetimeColumn("Lançamento", format="DD/MM/YYYY HH:mm"),
                    "Preço Unitário": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Valor Total": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Quantidade": st.column_config.NumberColumn(format="%.2f")
                }
            )
        else:
            st.info("Nenhum registro encontrado.")

        # --- Formulário de Edição (Aparece apenas se 1 registro for selecionado) ---
        if len(selected_ids) == 1 and 'record_to_delete' not in st.session_state and 'records_to_delete_bulk' not in st.session_state:
            selected_id = selected_ids[0]
            if user_role == 'Admin': # Apenas admin pode ver o formulário de edição
                record_data = operations.get_record_by_id(conn, selected_id)

                if record_data:
                    with st.container(border=True):
                        with st.form(f"edit_form_{selected_id}"):
                            st.subheader(f"Editar Registro Selecionado (ID: {selected_id})")
                            record_date = datetime.strptime(record_data['Data'], '%Y-%m-%d').date()

                            col1_edit, col2_edit = st.columns(2)
                            with col1_edit:
                                data_edit = st.date_input("Data", value=record_date, key=f"date_{selected_id}")
                                
                                operacao_options = ["Venda", "Transferência"]
                                try:
                                    operacao_idx = operacao_options.index(record_data.get('Tipo de Operação'))
                                except (ValueError, AttributeError): operacao_idx = 0
                                tipo_operacao_edit = st.selectbox("Tipo de Operação", options=operacao_options, index=operacao_idx, key=f"op_{selected_id}")

                                try:
                                    regional_idx = regionais_options.index(record_data['Regional'])
                                except (ValueError, AttributeError): regional_idx = 0
                                regional_edit = st.selectbox("Regional", options=regionais_options, index=regional_idx, key=f"reg_{selected_id}")

                                try:
                                    remetente_idx = remetentes_options.index(record_data['Filial Remetente'])
                                except (ValueError, AttributeError): remetente_idx = 0
                                remetente_edit = st.selectbox("Filial Remetente", options=remetentes_options, index=remetente_idx, key=f"rem_{selected_id}")

                                try:
                                    destino_idx = destinos_options.index(record_data['Destino'])
                                except (ValueError, AttributeError): destino_idx = 0
                                destino_edit = st.selectbox("Destino", options=destinos_options, index=destino_idx, key=f"dest_{selected_id}")

                                try:
                                    produto_idx = produtos_options.index(record_data['Produto'])
                                except (ValueError, AttributeError): produto_idx = 0
                                produto_edit = st.selectbox("Produto", options=produtos_options, index=produto_idx, key=f"prod_{selected_id}")
                            
                            with col2_edit:
                                quantidade_edit = st.number_input("Quantidade", min_value=0.0, format="%.2f", value=record_data['Quantidade'], key=f"qtd_{selected_id}")
                                try:
                                    unidade_idx = unidades_options.index(record_data['Unidade'])
                                except (ValueError, AttributeError): unidade_idx = 0
                                unidade_edit = st.selectbox("Unidade", options=unidades_options, index=unidade_idx, key=f"un_{selected_id}")
                                preco_unitario_str_edit = st.text_input("Preço Unitário (R$)", value=f"{record_data['Preço Unitário']:.2f}".replace('.',','), key=f"price_{selected_id}")
                                valor_total_str_edit = st.text_input("Valor Total (R$)", value=f"{record_data['Valor Total']:.2f}".replace('.',','), key=f"total_{selected_id}")
                                nfe_edit = st.text_input("NFe", value=record_data.get('NFe', ''), key=f"nfe_{selected_id}")
                                observacoes_edit = st.text_area("Observações", value=record_data.get('Observacoes', ''), key=f"obs_{selected_id}")

                            update_submitted = st.form_submit_button("Salvar Alterações", type="primary", use_container_width=True)

                            if update_submitted:
                                try:
                                    preco_unitario_edit = parse_brl_to_float(preco_unitario_str_edit)
                                    valor_total_edit = parse_brl_to_float(valor_total_str_edit)
                                except ValueError:
                                    st.error("❌ Por favor, insira valores numéricos válidos para Preço Unitário e Valor Total (use vírgula para decimais).")
                                else:
                                    operations.update_record(
                                        conn, user_name, selected_id, data_edit.strftime('%Y-%m-%d'), tipo_operacao_edit, regional_edit,
                                        remetente_edit, destino_edit, produto_edit, quantidade_edit, unidade_edit,
                                        preco_unitario_edit, valor_total_edit, nfe_edit, observacoes_edit
                                    )
                                    # O formulário já causa um rerun, não é necessário chamar st.rerun()

                        # Botão de exclusão fora do formulário para usar on_click
                        st.button(
                            "Excluir Registro", 
                            key=f"delete_prompt_{selected_id}", 
                            on_click=prompt_for_delete,
                            type="secondary",
                            use_container_width=True
                        )
            else:
                st.info(f"Registro ID {selected_ids[0]} selecionado. Apenas administradores podem editar ou excluir.")
                
        # --- Diálogo de Confirmação de Exclusão (ÚNICO) ---
        if 'record_to_delete' in st.session_state and st.session_state.record_to_delete:
            with confirmation_placeholder.container():
                record_id = st.session_state.record_to_delete
                st.warning(f"⚠️ **Atenção!** Tem certeza que deseja excluir permanentemente o registro ID **{record_id}**? Esta ação não pode ser desfeita.")
                
                confirm_col1, confirm_col2, _ = st.columns([1, 1, 5])
                confirm_col1.button("Sim, excluir registro", type="primary", on_click=confirm_delete)
                confirm_col2.button("Cancelar", on_click=cancel_delete)

        # --- Diálogo de Confirmação de Exclusão (EM MASSA) ---
        if 'records_to_delete_bulk' in st.session_state and st.session_state.records_to_delete_bulk:
            with confirmation_placeholder.container():
                num_records = len(st.session_state.records_to_delete_bulk)
                st.warning(f"⚠️ **Atenção!** Tem certeza que deseja excluir permanentemente os **{num_records}** registros selecionados? Esta ação não pode ser desfeita.")
                confirm_col1, confirm_col2, _ = st.columns([1, 1, 5])
                confirm_col1.button("Sim, excluir selecionados", type="primary", on_click=confirm_bulk_delete)
                confirm_col2.button("Cancelar", on_click=cancel_bulk_delete)

        st.divider()
        if st.session_state.get('role') == 'Admin':
            with st.expander("⚠️ Zona de Perigo - Ações Irreversíveis"):
                st.warning("A ação abaixo excluirá **TODOS** os registros do banco de dados permanentemente.")
                
                confirm_delete = st.checkbox("Eu confirmo que desejo excluir todos os registros.")
                
                if confirm_delete:
                    if st.button("Excluir Todos os Registros Agora", type="primary"):
                        operations.delete_all_records(conn, user_name)
                        st.rerun()

    elif selected_page_key == "Gerenciamento de Usuários" and st.session_state.get('role') == "Admin":
        st.header("Gerenciamento de Usuários")

        with st.expander("➕ Adicionar Novo Usuário"):
            with st.form("add_user_form", clear_on_submit=True):
                new_username = st.text_input("Nome do Novo Usuário")
                new_password = st.text_input("Senha Temporária", type="password")
                new_role = st.selectbox("Função do Usuário", ["User", "Admin"])
                if st.form_submit_button("Criar Usuário", type="primary"):
                    if operations.add_user(conn, new_username, new_password, new_role):
                        operations.log_activity(conn, user_name, "Criar Usuário", f"Usuário '{new_username}' criado.")
                        st.rerun()

        st.divider()

        st.subheader("Usuários Existentes")
        all_users = operations.get_all_users(conn)

        if not all_users:
            st.info("Nenhum outro usuário cadastrado.")
        else:
            def handle_role_change(target_user):
                new_role_val = st.session_state[f"role_{target_user}"]
                operations.update_user_role(conn, user_name, target_user, new_role_val)

            for user in all_users:
                user_id = user['username']
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    col1.text_input("user_display", value=user_id, disabled=True, label_visibility="collapsed", key=f"user_{user_id}")
                    
                    with col2:
                        role_options = ["User", "Admin"]
                        current_role_index = role_options.index(user['role']) if user['role'] in role_options else 0
                        st.selectbox("Função", role_options, index=current_role_index, key=f"role_{user_id}", on_change=handle_role_change, args=(user_id,))

                    with col3:
                        with st.popover("Resetar Senha", use_container_width=True):
                            with st.form(f"reset_pass_form_{user_id}"):
                                new_pass = st.text_input("Nova Senha", type="password", key=f"new_pass_{user_id}")
                                if st.form_submit_button("Confirmar Reset", type="primary"):
                                    if operations.update_user_password(conn, user_name, user_id, new_pass):
                                        st.rerun()

                    with col4:
                        if st.button("Excluir", key=f"delete_user_{user_id}", use_container_width=True):
                            st.session_state.user_to_delete = user_id
                            st.rerun()

        if 'user_to_delete' in st.session_state and st.session_state.user_to_delete:
            user_to_del = st.session_state.user_to_delete
            st.warning(f"⚠️ **Atenção!** Tem certeza que deseja excluir o usuário **{user_to_del}**? Esta ação é irreversível.")
            
            confirm_col1, confirm_col2, _ = st.columns([1, 1, 5])
            with confirm_col1:
                if st.button("Sim, excluir usuário", type="primary"):
                    operations.delete_user(conn, user_name, user_to_del)
                    del st.session_state.user_to_delete
                    st.rerun()
            with confirm_col2:
                if st.button("Cancelar Exclusão"):
                    del st.session_state.user_to_delete
                    st.rerun()

    elif selected_page_key == "Upload de Planilha" and st.session_state.get('role') == "Admin":
        st.header("Importar Registros de Planilha Excel")
        st.info("Para garantir a importação correta, use o modelo de planilha abaixo.")
        template_excel = operations.get_template_excel()
        st.download_button(
            label="📥 Baixar Modelo da Planilha",
            data=template_excel,
            file_name="modelo_importacao_residuos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.divider()
        uploaded_file = st.file_uploader("Escolha um arquivo Excel (.xlsx)", type="xlsx")
        if uploaded_file is not None:
            if st.button("Importar Dados da Planilha", type="primary"):
                operations.process_excel_upload(conn, user_name, uploaded_file)
                st.rerun()

    elif selected_page_key == "Configurações":
        st.header("Gerenciar Opções das Listas de Seleção")
        st.info("Adicione ou remova opções que aparecerão nos formulários de adição e edição de registros.")

        setting_configs = {
            "Regionais": "regionais",
            "Filiais Remetentes": "filiais",
            "Destinos": "destinos",
            "Produtos": "produtos",
            "Unidades": "unidades"
        }

        for display_name, table_name in setting_configs.items():
            with st.expander(f"Gerenciar {display_name}"):
                
                options = get_cached_setting_options(conn, table_name)
                
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.subheader("Adicionar Nova Opção")
                    with st.form(f"add_form_{table_name}", clear_on_submit=True):
                        new_option = st.text_input("Nova Opção", placeholder="Digite a nova opção aqui...", label_visibility="collapsed")
                        if st.form_submit_button("➕ Adicionar"):
                            if new_option:
                                # Limpa o cache para esta opção para que a lista seja recarregada com o novo item.
                                get_cached_setting_options.clear()
                                operations.add_setting_option(conn, table_name, new_option)
                                st.rerun()

                with col2:
                    st.subheader("Opções Atuais")
                    if not options:
                        st.caption("Nenhuma opção cadastrada.")
                    else:
                        with st.container(height=250):
                            for option in options:
                                item_col1, item_col2 = st.columns([0.85, 0.15])
                                item_col1.text_input("item", value=option, disabled=True, label_visibility="collapsed", key=f"item_{table_name}_{option}")
                                if item_col2.button("🗑️", key=f"del_{table_name}_{option}", help=f"Remover '{option}'", use_container_width=True):
                                    # Limpa o cache para que a lista seja recarregada sem o item removido.
                                    get_cached_setting_options.clear()
                                    operations.delete_setting_option(conn, table_name, option)
                                    st.rerun()
        
        st.divider()
        with st.expander("🧰 Manutenção de Dados"):
            st.warning(
                "A ação abaixo irá percorrer todos os registros existentes e aplicar as regras de "
                "padronização (ex: 'kg' se tornará 'KG', 'nome produto' se tornará 'Nome Produto'). "
                "É seguro executar esta operação múltiplas vezes."
            )
            
            if st.checkbox("Eu entendo e desejo padronizar os dados antigos."):
                if st.button("Padronizar Dados Antigos Agora", type="primary"):
                    operations.migrate_old_records(conn)
                    st.rerun()

    elif selected_page_key == "Log de Atividades":
        st.header("Log de Atividades Recentes")
        log_df = operations.get_activity_log(conn)
        if not log_df.empty:
            log_df['Data e Hora'] = log_df['Data e Hora'].dt.strftime('%d/%m/%Y %H:%M:%S')
            st.dataframe(log_df, use_container_width=True, hide_index=True)

    elif selected_page_key == "Ajuda":
        st.header("❓ Central de Ajuda")
        st.markdown("Encontre aqui todas as informações que você precisa para utilizar o sistema de Controle de Resíduos.")

        st.image("logo.png", width=150)
        st.subheader("Sobre o Frango Americano e o Aplicativo")
        st.markdown("""
        Bem-vindo ao sistema de Controle de Resíduos do **Frango Americano**. 
        Esta ferramenta foi desenvolvida para otimizar e padronizar o registro de vendas e transferências de resíduos, 
        garantindo maior precisão, rastreabilidade e eficiência em nossos processos.
        
        **Observação Importante:** Este é um sistema de uso interno. Todas as informações aqui inseridas são cruciais para a gestão e devem ser preenchidas com o máximo de atenção e precisão.
        """)
        st.divider()

        st.info("**Dica:** Para encontrar um tópico específico rapidamente, use a função de busca do seu navegador (pressione `Ctrl+F` ou `Cmd+F`).")
        st.divider()

        st.subheader("Tutoriais e Funcionalidades")

        with st.expander("🔐 Autenticação e Login"):
            st.markdown("""
            - **Login:** Para acessar o sistema, você deve utilizar o **Usuário** e **Senha** fornecidos.
            - **Sair:** Para encerrar sua sessão de forma segura, clique no botão **"Sair"** na barra lateral esquerda. Isso garante que mais ninguém use o sistema com seu nome.
            - **Rastreamento:** Todas as ações importantes (adição, edição, exclusão) são registradas com o nome do usuário logado.
            """)

        with st.expander("📊 Dashboard"):
            st.markdown("""
            O Dashboard é a tela inicial do sistema e oferece uma visão geral e analítica dos dados.
            - **Filtros de Análise:** Você pode filtrar os dados por período (Data de Início e Fim), Regional, Filial, Produto e Destino. Clique em "Aplicar Filtros" para atualizar os gráficos.
            - **Exportação:** Após filtrar, você pode exportar os dados para **Excel** ou **CSV** usando os botões na parte superior.
            - **KPIs (Indicadores Chave):** Mostram a Receita Total, Quantidade Total e o número de registros para o período filtrado.
            - **Análises e Narrativas:** Textos automáticos que destacam a regional, filial e produto com maior receita, além de uma análise de tendência mensal.
            - **Gráficos:** Visualizações interativas da receita por regional, filial, produto e destino, além da quantidade por produto e evolução mensal da receita.
            """)

        with st.expander("➕ Adicionar Registro"):
            st.markdown("""
            Esta página é usada para inserir um novo registro de venda ou transferência.
            1.  **Preencha os Campos:** Insira a data, selecione as opções nas listas (Regional, Filial, etc.) e preencha os valores de quantidade e preço.
            2.  **Adicionar Novo Destino:** Se um destino não estiver na lista, você pode adicioná-lo selecionando a opção "➕ Adicionar Novo Destino...".
            3.  **Cálculo Automático:** O sistema pode calcular o *Valor Total* a partir da *Quantidade* e *Preço Unitário*. Se você preencher o *Valor Total* diretamente, o *Preço Unitário* será recalculado.
            4.  **Salvar:** Clique em "Adicionar Registro" para salvar. O botão só funciona se todos os campos de seleção estiverem preenchidos.
            """)

        with st.expander("📋 Visualizar Registros"):
            st.markdown("""
            Aqui você pode ver, pesquisar, editar e excluir todos os registros.
            - **Pesquisa:** Use a barra de busca no topo para encontrar registros específicos. A busca funciona para todos os campos de texto.
            - **Editar:** Clique em uma linha da tabela para selecioná-la. Um formulário de edição aparecerá abaixo com os dados do registro. Altere o que for necessário e clique em "Salvar Alterações".
            - **Excluir:** Após selecionar um registro, clique no botão "Excluir Registro" no formulário de edição. Uma confirmação será solicitada.
            - **⚠️ Zona de Perigo:** Tenha muito cuidado com esta seção. A opção "Excluir Todos os Registros" apaga **permanentemente** todos os dados do sistema. Use apenas se tiver certeza absoluta.
            """)

        with st.expander("⬆️ Upload de Planilha"):
            st.markdown("""
            Permite importar múltiplos registros de uma vez a partir de um arquivo Excel.
            1.  **Baixar Modelo:** É **essencial** usar o modelo padrão. Clique em "📥 Baixar Modelo da Planilha" para obter o arquivo `.xlsx` com as colunas corretas.
            2.  **Preencher a Planilha:** Abra o modelo e preencha com seus dados, seguindo o formato das colunas. A coluna 'Data' deve estar no formato `DD/MM/AAAA`.
            3.  **Fazer Upload:** Selecione o arquivo preenchido no campo "Escolha um arquivo Excel".
            4.  **Importar:** Clique em "Importar Dados da Planilha". O sistema validará os dados e informará quantos registros foram adicionados e quantos foram ignorados por erros.
            """)

        with st.expander("⚙️ Configurações"):
            st.markdown("""
            Nesta página, você pode gerenciar as opções que aparecem nas listas suspensas do aplicativo (como Regionais, Produtos, etc.).
            - **Adicionar Opção:** Em cada categoria, digite a nova opção no campo de texto e clique em "➕ Adicionar".
            - **Remover Opção:** Na lista de "Opções Atuais", clique no ícone de lixeira (🗑️) ao lado do item que deseja remover.
            - **🧰 Manutenção de Dados:** A função "Padronizar Dados Antigos" serve para corrigir e padronizar registros antigos que possam ter sido inseridos com formatação diferente (ex: 'kg' em vez de 'KG'). É seguro executar esta ação.
            """)

        with st.expander("📜 Log de Atividades"):
            st.markdown("""
            Esta tela exibe um histórico de todas as ações importantes realizadas no sistema. As informações incluem a data/hora, o usuário, o tipo de ação (ex: Adicionar, Editar) e detalhes relevantes, servindo para auditoria e rastreamento.
            """)
        
        st.divider()

        st.subheader("Solução de Problemas e Erros Comuns")
        st.markdown("""
        - **"Usuário ou senha inválidos"**: Verifique se digitou seu nome de usuário e senha corretamente, respeitando letras maiúsculas e minúsculas.
        - **"Falha ao adicionar/editar registro"**: Geralmente ocorre por dados inválidos. Verifique se a 'Quantidade' é maior que zero e se os campos de preço contêm números válidos.
        - **"A planilha está com colunas faltando"**: Certifique-se de que está usando o modelo baixado do sistema e que não renomeou ou removeu nenhuma coluna.
        - **Registros da planilha foram ignorados**: Isso acontece se linhas da sua planilha tiverem dados essenciais faltando (como data, quantidade) ou em formato incorreto (ex: texto no campo de quantidade).
        
        **Se um erro persistir:**
        1.  Tente atualizar a página (pressione `F5`).
        2.  Verifique sua conexão com a internet.
        3.  Se o problema continuar, entre em contato com o suporte de TI responsável pelo aplicativo.
        """)
