# Page_Assinatura.py
import streamlit as st
import pandas as pd
from datetime import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Importa as funções de autenticação
from auth import force_relogin_on_navigate, add_logout_button

# --- Configurações ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1Lpjc8Zb9_P8vZjt8pjjft66LpGqTE4g7uUy0hlOnUO8"
SHEET_NAME = "Notas"
RANGE_NAME = f"{SHEET_NAME}" # Pega a aba inteira
COLUNA_GESTOR_RESP = 'GESTOR_RESP'
COLUNA_ASSINATURA = 'ASSINATURA'
COLUNA_GESTOR_ASSINATURA = 'GESTORASSINATURA'
COLUNAS_DESABILITADAS = ("NF", "FORNECEDOR", "VALOR", "DT VENC", COLUNA_GESTOR_RESP, COLUNA_GESTOR_ASSINATURA)

# --- Funções de API do Google Sheets ---

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

        if not values or len(values) < 2: # Precisa de cabeçalho + dados
            st.warning(f"Nenhum dado encontrado na planilha '{SHEET_NAME}'.")
            return None
        else:
            header = values[0]
            data = values[1:]
            df = pd.DataFrame(data, columns=header)
            
            # --- Conversão de Tipos ---
            if COLUNA_ASSINATURA in df.columns:
                df[COLUNA_ASSINATURA] = df[COLUNA_ASSINATURA].astype(str).str.upper()
                df[COLUNA_ASSINATURA] = df[COLUNA_ASSINATURA].map({'TRUE': True, 'VERDADEIRO': True}).infer_objects(copy=False).fillna(False).astype(bool)
            else:
                st.error(f"Coluna '{COLUNA_ASSINATURA}' não encontrada!")
                
            if 'VALOR' in df.columns:
                df['VALOR'] = pd.to_numeric(df['VALOR'].str.replace(',', '.', regex=False), errors='coerce').fillna(0)
            if 'DT VENC' in df.columns:
                df['DT VENC'] = pd.to_datetime(df['DT VENC'], errors='coerce', dayfirst=True)
            if 'ENTREGA GESTOR' in df.columns:
                df['ENTREGA GESTOR'] = pd.to_datetime(df['ENTREGA GESTOR'], errors='coerce', dayfirst=True)
            if 'GESTORASSINATURA' in df.columns:
                df['GESTORASSINATURA'] = pd.to_datetime(df['GESTORASSINATURA'], errors='coerce', dayfirst=True)

            return df
    except Exception as err:
        st.error(f"Erro ao buscar dados: {err}")
        return None

def update_tabela_sheets(_service, df_atualizado):
    """Atualiza os dados na planilha do Google Sheets."""
    if not _service: return False
    try:
        sheet = _service.spreadsheets()
        df_to_save = df_atualizado.copy()
        
        # Converte as colunas de data/hora para string no formato correto
        if 'DT VENC' in df_to_save.columns:
            # Use .dt.strftime para Timestamps e lide com NaT para datas vazias
            df_to_save['DT VENC'] = df_to_save['DT VENC'].dt.strftime('%d/%m/%Y').fillna('')
        
        if 'ENTREGA GESTOR' in df_to_save.columns:
            df_to_save['ENTREGA GESTOR'] = df_to_save['ENTREGA GESTOR'].dt.strftime('%d/%m/%Y').fillna('')

        if COLUNA_GESTOR_ASSINATURA in df_to_save.columns:
            # Para esta coluna, como ela pode ser atualizada com hora, use um formato completo
            df_to_save[COLUNA_GESTOR_ASSINATURA] = df_to_save[COLUNA_GESTOR_ASSINATURA].dt.strftime('%d/%m/%Y %H:%M:%S').fillna('')
            
        # Converte a coluna de assinatura para 'TRUE' ou 'FALSE' string
        if COLUNA_ASSINATURA in df_to_save.columns:
             df_to_save[COLUNA_ASSINATURA] = df_to_save[COLUNA_ASSINATURA].apply(lambda x: 'TRUE' if x else 'FALSE')
        
        df_to_save[COLUNA_ASSINATURA] = 'FALSE'
        df_to_save = df_to_save.astype(str).replace({'NaT': '', 'nan': ''}) 
        
        data_to_write = [df_to_save.columns.tolist()] + df_to_save.values.tolist()
        body = {"values": data_to_write}

        result = (sheet.values().update(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME, valueInputOption="USER_ENTERED", body=body).execute())
        st.info(f"{result.get('updatedCells')} células atualizadas.")
        return True
    except Exception as error:
        st.error(f"Erro ao atualizar planilha: {error}")
        return False

# --- Lógica da Página PCM ---

def show_pcm_page():
    """Mostra o conteúdo da página de Assinatura"""
    service = get_sheets_service()
    if not service:
        st.stop()

    st.title("CONTROLE DE NOTAS :lower_left_fountain_pen:")
    st.markdown("Marque na coluna **Assinar?** e no botão **Salvar Alterações** para Assinar")
    logged_in_user = st.session_state.get("logged_in_user", "Usuário Desconhecido")
    st.sidebar.success(f"Logado como: {logged_in_user}!")
    add_logout_button() # Adiciona botão de sair na sidebar

    if st.button("🔄 Recarregar Dados da Planilha"):
        get_tabela_sheets.clear()
        st.rerun()

    df_original = get_tabela_sheets(service)

    if df_original is None:
        st.error("Não foi possível carregar os dados.")
        st.stop()

    # Filtra pelo usuário logado AQUI
    if COLUNA_GESTOR_RESP in df_original.columns:
        df_filtrado_usuario = df_original[df_original[COLUNA_GESTOR_RESP] == logged_in_user].copy()

        if df_filtrado_usuario.empty:
            st.info(f"Nenhum registro encontrado para o gestor {logged_in_user}.")
            st.stop()

        st.subheader(f"Suas Notas Pendentes ({logged_in_user})")

        edited_df = st.data_editor(
            df_filtrado_usuario, # Usa o DF filtrado pelo usuário
            disabled=COLUNAS_DESABILITADAS, # Desabilita as colunas certas
            key=f"editor_{logged_in_user}",
            use_container_width=True,
            column_config={
                COLUNA_ASSINATURA: st.column_config.CheckboxColumn("Assinar?", default=False),
                "GESTOR_RESP" : st.column_config.TextColumn("Gestor", max_chars=30),
                "FORNECEDOR" : st.column_config.TextColumn("Fornecedor", max_chars=30),
                "N NF" : st.column_config.TextColumn("Nr Nf", max_chars=30),
                "VALOR": st.column_config.NumberColumn("Valor (R$)", format="%.2f"),
                "DT VENC": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                "ENTREGA GESTOR": st.column_config.DateColumn("Entrega", format="DD/MM/YYYY"),
                "GESTORASSINATURA": st.column_config.DatetimeColumn("Assinatura", format="DD/MM/YYYY HH:mm:ss"), # Use DatetimeColumn
            }
        )

        if st.button("Salvar Alterações", type="primary"):
            try:
                # Identifica as mudanças na coluna de assinatura
                # A condição mudancas deve ser aplicada ao df_original antes de ser atualizado
                # para que os valores sejam aplicados apenas onde a assinatura foi marcada
                
                # Crie uma cópia do df_original para atualização
                df_para_salvar = df_original.copy()

                # Itera sobre as linhas do edited_df para aplicar as mudanças ao df_para_salvar
                # Isso é mais robusto do que df_original.update(edited_df) quando há filtros
                for index, row in edited_df.iterrows():
                    # Verifica se a assinatura foi marcada e se a coluna GESTORASSINATURA está vazia
                    if row[COLUNA_ASSINATURA] and pd.isna(df_para_salvar.loc[index, COLUNA_GESTOR_ASSINATURA]):
                        df_para_salvar.loc[index, COLUNA_GESTOR_ASSINATURA] = datetime.now() # Atribui um objeto datetime
                    
                    # Atualiza o valor da coluna ASSINATURA no df_para_salvar
                    df_para_salvar.loc[index, COLUNA_ASSINATURA] = row[COLUNA_ASSINATURA]

                # Agora, passa o DataFrame completo e atualizado para a função de salvamento
                if update_tabela_sheets(service, df_para_salvar): # Salva o DF *COMPLETO*
                    st.success("As alterações foram salvas com sucesso!")
                    st.balloons()
                    get_tabela_sheets.clear()
                    st.rerun()
                else:
                    st.error("Falha ao salvar as alterações.")

            except Exception as e:
                st.error(f"Ocorreu um erro ao salvar: {e}")

    else:
        st.error(f"Coluna '{COLUNA_GESTOR_RESP}' não encontrada na planilha.")

# --- Execução Principal da Página ---

# Chama a função de verificação no início
if force_relogin_on_navigate(__file__):
    # Se logado, mostra o conteúdo da página PCM
    show_pcm_page()
else:
    # Se não logado, a função 'check_password' já exibirá o formulário.
    st.warning("Você precisa fazer login para acessar o Controle de Notas.")