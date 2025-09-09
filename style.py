# style.py

CSS_STYLE = """
<style>
    /* Estilos Gerais */
    .stApp {
        background-color: #9a9b9c; /* Fundo cinza para o app principal */
    }

    /* Sidebar - Cor de fundo e texto */
    [data-testid="stSidebar"] {
        background-color: #001f3f; /* Azul escuro */
        color: white;
    }
    [data-testid="stSidebar"] .st-emotion-cache-1yaqxis { /* Título do menu */
        color: white;
    }
    [data-testid="stSidebar"] .st-emotion-cache-1we4pck { /* Subtítulo (se houver) */
        color: white;
    }
    /* Mudar a cor do texto "Logado como: Administrador" para branco */
    [data-testid="stSidebar"] [data-testid="stInfo"] p {
        color: white !important;
    }


    /* Botões */
    .stButton > button {
        background-color: #3dadf1; /* Azul padrão para botões */
        color: white;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
    }
    .stButton > button:hover {
        background-color: #3dadf1; /* Tom mais escuro no hover */
    }

    /* Botão Primário (se você usar type="#e0f2f7") */
    .stButton > button.primary {
        background-color: #3dadf1; /* Azul primário */
        color: white;
    }
    .stButton > button.primary:hover {
        background-color: #3dadf1;
    }

    /* Entrada de Texto e Seleção (caixas de input) */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > button,
    .stDateInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 5px;
        border: 1px solid #ccc;
        padding: 0.5rem;
    }

    /* Cabeçalhos */
    h1, h2, h3, h4, h5, h6 {
        color: #001f3f; /* Cor dos cabeçalhos */
    }
    /* Estilo para st.header */
    .st-emotion-cache-j7qwjs { /* Seletor para st.header */
        color: #001f3f; /* Azul escuro */
        border-bottom: 2px solid #e6e6e6; /* Linha sutil abaixo do cabeçalho */
        padding-bottom: 10px;
        margin-bottom: 20px;
    }

    /* Tabela (st.dataframe) - Estilos para compactar a visualização */
    [data-testid="stDataFrame"] {
        font-size: 0.85rem; /* Diminui o tamanho da fonte na tabela */
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    [data-testid="stDataFrame"] thead th {
        padding: 0.5rem; /* Diminui o padding do cabeçalho */
    }
    [data-testid="stDataFrame"] tbody td {
        padding: 0.3rem 0.5rem; /* Diminui o padding das células */
    }

    /* Mensagens de Info, Sucesso, Alerta, Erro */
    .stAlert, .stInfo, .stSuccess, .stWarning, .stError {
        border-radius: 5px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .stInfo {
        background-color: #e0f2f7; /* Azul claro para info */
        border-left: 5px solid #007bff;
        color: #004085;
    }
    .stSuccess {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        color: #155724;
    }
    .stWarning {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        color: #856404;
    }
    .stError {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        color: #721c24;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f8f9fa; /* Fundo claro para o cabeçalho do expander */
        border-radius: 5px;
        padding: 0.8rem;
        margin-bottom: 0.5rem;
        color: #001f3f;
    }
    .streamlit-expanderContent {
        padding: 1rem;
        border: 1px solid #e9ecef;
        border-top: none;
        border-radius: 0 0 5px 5px;
        background-color: white;
    }

    /* Estilo para links em markdown */
    a {
        color: #007bff; /* Azul padrão para links */
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }

    /* Remove padding default do main block container */
    .main > div {
        padding-top: 2rem;
        padding-bottom: 2rem;
        background-color: transparent; /* Garante que o fundo cinza do app seja visível */
        box-shadow: none; /* Remove qualquer sombra do container principal */
    }
</style>
"""