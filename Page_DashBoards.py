# Page_DashBoards.py
import streamlit as st
import pandas as pd
from datetime import datetime
import os.path
import plotly.express as px
import plotly.graph_objects as go

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError



template_3 = dict(
layout=go.Layout(
    font=dict(family="Verdana", size=12, color="#333333"),
    title_font=dict(family="Verdana", size=24, color="#164F2F"),
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f9f9f9",
    xaxis=dict(
        gridcolor="#e0e0e0",
        title_font=dict(size=14, color="#555555"),
        tickfont=dict(color="#666666")
    ),
    yaxis=dict(
        gridcolor="#e0e0e0",
        title_font=dict(size=14, color="#555555"),
        tickfont=dict(color="#666666")
    ),
    legend=dict(
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="#cccccc",
        borderwidth=1,
        font=dict(color="#444444")
    )))





# --- NOME DE USUÁRIO DO ADMINISTRADOR ---
# Defina aqui o nome de usuário exato do seu administrador
# Este nome DEVE corresponder a um usuário no seu secrets.toml
ADM_USERNAME = "admin" # <--- MUDE AQUI SE O SEU ADM TIVER OUTRO NOME

# --- Configurações ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1Lpjc8Zb9_P8vZjt8pjjft66LpGqTE4g7uUy0hlOnUO8"
SHEET_NAME = "Notas"
RANGE_NAME = f"{SHEET_NAME}"
COLUNA_GESTOR_RESP = 'GESTOR_RESP'
COLUNA_ASSINATURA = 'ASSINATURA'
COLUNA_GESTOR_ASSINATURA = 'GESTORASSINATURA'


@st.cache_resource # Cacheia o objeto 'service'
def get_sheets_service():
    """Autentica com a API do Google Sheets usando st.secrets e retorna o objeto 'service'."""
    creds = None
    if "google_token" not in st.secrets:
        st.error("Configuração '[google_token]' não encontrada em st.secrets.")
        return None
    try:
        token_info = st.secrets["google_token"].to_dict()
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    except Exception as e:
        st.error(f"Erro ao carregar credenciais: {e}")
        return None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            #st.info("Token expirado. Tentando atualizar...")
            try:
                creds.refresh(Request())
                st.success("Token atualizado!")
            except Exception as e:
                st.error(f"Erro ao atualizar o token: {e}")
                return None
        else:
            st.error("Credenciais inválidas.")
            return None
    try:
        service = build("sheets", "v4", credentials=creds)
        return service
    except Exception as e:
        st.error(f"Erro ao construir serviço: {e}")
        return None

@st.cache_data(ttl=300) # Cacheia por 5 minutos
def get_tabela_sheets(_service):
    """Busca os dados da planilha e retorna um DataFrame Pandas."""
    if not _service:
        st.error("Serviço Google Sheets não disponível.")
        return None
    try:
        sheet = _service.spreadsheets()
        result = (sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=SHEET_NAME).execute())
        values = result.get("values", [])

        if not values: # Se não houver nada, retorna um DF vazio com colunas
            st.warning(f"Planilha '{SHEET_NAME}' vazia ou não encontrada. Criando DF vazio.")
            # Defina as colunas esperadas aqui, caso a planilha esteja realmente vazia
            expected_cols = ["NF", "FORNECEDOR", "VALOR", "DT VENC", "GESTOR_RESP", "ASSINATURA", "GESTORASSINATURA"]
            return pd.DataFrame(columns=expected_cols)

        header = values[0]
        data = values[1:] if len(values) > 1 else []
        df = pd.DataFrame(data, columns=header)

        # --- Garante Colunas e Conversão de Tipos ---
        if COLUNA_ASSINATURA not in df.columns: df[COLUNA_ASSINATURA] = 'FALSE'
        if COLUNA_GESTOR_ASSINATURA not in df.columns: df[COLUNA_GESTOR_ASSINATURA] = ''
        if COLUNA_GESTOR_RESP not in df.columns: df[COLUNA_GESTOR_RESP] = ''
        
        df[COLUNA_ASSINATURA] = df[COLUNA_ASSINATURA].astype(str).str.upper()
        df[COLUNA_ASSINATURA] = df[COLUNA_ASSINATURA].map({'TRUE': True, 'VERDADEIRO': True}).fillna(False).astype(bool)

        if 'VALOR' in df.columns:
            df['VALOR'] = pd.to_numeric(df['VALOR'].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
        if 'DT VENC' in df.columns:
            df['DT VENC'] = pd.to_datetime(df['DT VENC'], errors='coerce', dayfirst=True)
        if 'ENTREGA GESTOR' in df.columns:
            df['ENTREGA GESTOR'] = pd.to_datetime(df['ENTREGA GESTOR'], errors='coerce', dayfirst=True)

        return df
    except Exception as err:
        st.error(f"Erro ao buscar dados: {err}")

def show_pcm_page():
    """Mostra o conteúdo da página de DashBoard"""
    service = get_sheets_service()
    if not service:
        st.stop()

    if st.button("🔄 Recarregar Dados da Planilha"):
        get_tabela_sheets.clear()
        st.rerun()
    
    df_original = get_tabela_sheets(service)

    if df_original is None:
        st.error("Não foi possível carregar os dados.")
        st.stop()
    
    st.title("DASHBORDS 💹")
    df_sem_data = df_original[df_original['GESTORASSINATURA'].isnull() | (df_original['GESTORASSINATURA'] == '') | (df_original['GESTORASSINATURA'] == pd.NA)]
    

    with st.expander("Tabela de Dados"):
        tab1, tab2 = st.tabs(["SEM ASSINATURA", "GERAL"])

        with tab1:
            option = st.selectbox(
                "SELECIONE O GESTOR",
                ("GERAL","KATIA","DANILO", "HEBERTON","DANILO"))
            if option == 'GERAL':
                df_sem_data
            else:
                df_sem_data[df_sem_data['GESTOR_RESP']==option]

        with tab2:
            option1 = st.selectbox(
                "SELECIONE O GESTOR:",
                ("GERAL","KATIA","DANILO", "HEBERTON","DANILO"))
            if option1 == 'GERAL':
                df_original
            else:
                df_original[df_original['GESTOR_RESP']==option1]


    st.markdown("### :green[Novo Gráficos à caminho  🛺]")

    df_fig1 = df_sem_data.iloc[:,4].value_counts().reset_index()
    df_fig1.columns = ["Gestor","Qtd"]
    
    fig1 = px.bar(data_frame=df_fig1,x="Gestor",y='Qtd',title="Notas não assinadas",template=template_3
                ,color_discrete_sequence=["#164F2F"], text_auto=True)

    fig2 = px.pie(data_frame=df_fig1, values='Qtd',names="Gestor",color_discrete_sequence=["#164F2F","#20864C","#186439","#31CA73"],title="Notas não assinadas")

    pg1, pg2 = st.columns(2)

    pg1.plotly_chart(fig1)
    pg2.plotly_chart(fig2)  


show_pcm_page()


