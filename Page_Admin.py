# Page_Admin.py
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

# --- NOME DE USUÁRIO DO ADMINISTRADOR ---
# Defina aqui o nome de usuário exato do seu administrador
# Este nome DEVE corresponder a um usuário no seu secrets.toml
ADM_USERNAME = "admin" # <--- MUDE AQUI SE O SEU ADM TIVER OUTRO NOME

# --- Configurações ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1Lpjc8Zb9_P8vZjt8pjjft66LpGqTE4g7uUy0hlOnUO8"
SHEET_NAME = "Devolução"
RANGE_NAME = f"{SHEET_NAME}"
COLUNA_GESTOR_RESP = 'GESTOR_RESP'
COLUNA_ASSINATURA = 'ASSINATURA'
COLUNA_GESTOR_ASSINATURA = 'GESTORASSINATURA'
COLUNA_DEVOLUCAO = 'DEVOLUCAO'
# Para o ADM, talvez você queira permitir editar tudo,
# então COLUNAS_DESABILITADAS pode ser uma tupla vazia ()
# ou você pode remover o 'disabled' do data_editor.
# COLUNAS_DESABILITADAS = () # Exemplo: ADM pode editar tudo
COLUNAS_DESABILITADAS = ("GESTORASSINATURA",) # Exemplo: ADM pode editar quase tudo


# --- Funções de API do Google Sheets (Corrigindo indentação e cache) ---

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
        if COLUNA_DEVOLUCAO not in df.columns: df[COLUNA_DEVOLUCAO] = 'FALSE'
        if COLUNA_GESTOR_ASSINATURA not in df.columns: df[COLUNA_GESTOR_ASSINATURA] = ''
        if COLUNA_GESTOR_RESP not in df.columns: df[COLUNA_GESTOR_RESP] = ''
        
        df[COLUNA_ASSINATURA] = df[COLUNA_ASSINATURA].astype(str).str.upper()
        df[COLUNA_ASSINATURA] = df[COLUNA_ASSINATURA].map({'TRUE': True, 'VERDADEIRO': True}).fillna(False).astype(bool)
        df[COLUNA_DEVOLUCAO] = df[COLUNA_DEVOLUCAO].map({'TRUE': True, 'VERDADEIRO': True}).fillna(False).astype(bool)

        if 'VALOR' in df.columns:
            df['VALOR'] = pd.to_numeric(df['VALOR'].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
        if 'DT VENC' in df.columns:
            df['DT VENC'] = pd.to_datetime(df['DT VENC'], errors='coerce', dayfirst=True)
        if 'DATA DEVOLUCAO' in df.columns:
            df['DATA DEVOLUCAO'] = pd.to_datetime(df['DATA DEVOLUCAO'], errors='coerce', dayfirst=True)
        if 'ENTREGA GESTOR' in df.columns:
            df['ENTREGA GESTOR'] = pd.to_datetime(df['ENTREGA GESTOR'], errors='coerce', dayfirst=True)

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
        if COLUNA_ASSINATURA in df_to_save.columns:
             df_to_save[COLUNA_ASSINATURA] = df_to_save[COLUNA_ASSINATURA].apply(lambda x: 'TRUE' if x else 'FALSE')
        if COLUNA_DEVOLUCAO in df_to_save.columns:
             df_to_save[COLUNA_DEVOLUCAO] = df_to_save[COLUNA_DEVOLUCAO].apply(lambda x: 'TRUE' if x else 'FALSE')
        if 'DT VENC' in df_to_save.columns:
             df_to_save['DT VENC'] = pd.to_datetime(df_to_save['DT VENC']).dt.strftime('%d/%m/%Y').fillna('')
        if 'DATA DEVOLUCAO' in df_to_save.columns:
             df_to_save['DATA DEVOLUCAO'] = pd.to_datetime(df_to_save['DATA DEVOLUCAO']).dt.strftime('%d/%m/%Y').fillna('')
        if 'ENTREGA GESTOR' in df_to_save.columns:
             df_to_save['ENTREGA GESTOR'] = pd.to_datetime(df_to_save['ENTREGA GESTOR']).dt.strftime('%d/%m/%Y').fillna('')

        # Garante que todas as colunas sejam string para evitar erros de tipo na API
        df_to_save = df_to_save.astype(str).replace({'NaT': '', 'nan': '', 'None': ''})
        data_to_write = [df_to_save.columns.tolist()] + df_to_save.values.tolist()
        body = {"values": data_to_write}

        # Limpa a aba antes de escrever (MAIS SEGURO com num_rows="dynamic")
        st.warning("Limpando a aba antes de reescrever...")
        sheet.values().clear(spreadsheetId=SPREADSHEET_ID, range=SHEET_NAME).execute()

        result = (sheet.values().update(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}", valueInputOption="USER_ENTERED", body=body).execute())
        st.info(f"{result.get('updatedCells')} células atualizadas.")
        return True
    except Exception as error:
        st.error(f"Erro ao atualizar planilha: {error}")
        return False

# --- Lógica da Página PCM ---

def show_pcm_page_1():
    """Mostra o conteúdo da página de Controle de Notas para o ADM."""
    service = get_sheets_service()
    if not service:
        st.stop()

    st.title("PAINEL DO ADMINISTRADOR - CONTROLE DE NOTAS ⚙️📝")
    st.sidebar.success("Logado como: Administrador!")
    add_logout_button()

    if st.button("🔄 Recarregar Dados da Planilha"):
        get_tabela_sheets.clear()
        st.rerun()

    df_original = get_tabela_sheets(service)

    if df_original is None:
        st.error("Não foi possível carregar os dados.")
        st.stop()

    st.subheader("Visão Geral - Todas as Notas")

    # O ADM vê e edita o DataFrame COMPLETO
    edited_df = st.data_editor(
        df_original, # Mostra o DF original completo
        disabled=COLUNAS_DESABILITADAS, # Permite editar (ou não)
        num_rows="dynamic",
        use_container_width=True,
        key="editor_adm", # Chave única para o editor do ADM
        column_config={
            COLUNA_ASSINATURA: st.column_config.CheckboxColumn("Assinar?", default=False),
            COLUNA_DEVOLUCAO: st.column_config.CheckboxColumn("Assinar?", default=False),
            "VALOR": st.column_config.NumberColumn("Valor (R$)", format="%.2f"),
            "DT VENC": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
            "ENTREGA GESTOR": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
            COLUNA_GESTOR_RESP: st.column_config.SelectboxColumn( # Ou TextColumn
                "Gestor",
                options=df_original[COLUNA_GESTOR_RESP].unique().tolist(), # Pega gestores existentes
                required=True, # Garante que o ADM preencha
            )
        }
    )

    if st.button("Salvar Alterações", type="primary"):
        try:
            # Para o ADM, o edited_df É o novo estado da planilha.
            # A lógica de GESTORASSINATURA ainda pode ser útil.
            indices_comuns = df_original.index.intersection(edited_df.index)
            df_original_comum = df_original.loc[indices_comuns]
            edited_comum = edited_df.loc[indices_comuns]

            mudancas_mask = (edited_comum[COLUNA_ASSINATURA] == True) & \
                            (df_original_comum[COLUNA_ASSINATURA] == False)

            indices_para_atualizar = indices_comuns[mudancas_mask]
            now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            edited_df.loc[indices_para_atualizar, COLUNA_GESTOR_ASSINATURA] = now_str

            # O ADM salva o DataFrame editado inteiro.
            # É CRUCIAL que o ADM preencha GESTOR_RESP em novas linhas.
            # Adicionar validação aqui seria bom.
            if edited_df[COLUNA_GESTOR_RESP].isnull().any() or (edited_df[COLUNA_GESTOR_RESP] == '').any():
                st.error("ERRO: Existem linhas sem 'GESTOR_RESP' definido. Preencha antes de salvar.")
            else:
                if update_tabela_sheets(service, edited_df):
                    st.success("As alterações foram salvas com sucesso!")
                    st.balloons()
                    get_tabela_sheets.clear()
                    st.rerun()
                else:
                    st.error("Falha ao salvar as alterações.")

        except Exception as e:
            st.error(f"Ocorreu um erro ao salvar: {e}")
            st.exception(e)

def show_pcm_page_2():
    """Mostra o conteúdo da página de Assinatura"""
    service = get_sheets_service()
    if not service:
        st.stop()

    st.title("CONTROLE DE NOTAS :lower_left_fountain_pen:")
    #add_logout_button() # Adiciona botão de sair na sidebar

    if st.button("🔄 Recarregar Dados da Planilha!"):
        get_tabela_sheets.clear()
        st.rerun()

    df_original = get_tabela_sheets(service)

    if df_original is None:
        st.error("Não foi possível carregar os dados.")
        st.stop()

    # Filtra pelo usuário logado AQUI
    if COLUNA_GESTOR_RESP in df_original.columns:
        df_filtrado_usuario = df_original.copy()

        edited_df = st.data_editor(
            df_filtrado_usuario, # Usa o DF filtrado pelo usuário
            disabled=COLUNAS_DESABILITADAS,
            use_container_width=True,
            column_config={
                COLUNA_ASSINATURA: st.column_config.CheckboxColumn("Assinar?", default=False),
                COLUNA_DEVOLUCAO: st.column_config.CheckboxColumn("Assinar?", default=False),
                "DEVOLUCAO":st.column_config.CheckboxColumn("Devolucão?", default=False),
                "VALOR": st.column_config.NumberColumn("Valor (R$)", format="%.2f"),
                "DT VENC": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                "DATA DEVOLUCAO": st.column_config.DateColumn("Data Devolução", format="DD/MM/YYYY"),
            }
        )

        if st.button("Salvar Alterações!", type="primary"):
            try:

                mudancas = edited_df[COLUNA_DEVOLUCAO] & ~df_filtrado_usuario.loc[edited_df.index, COLUNA_DEVOLUCAO]
                now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                edited_df.loc[mudancas, "DATA DEVOLUCAO"] = now_str
                df_original.update(edited_df)
                
                if update_tabela_sheets(service, df_original): # Salva o DF *COMPLETO*
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
    # Se logado, verifica se é o ADM
    logged_in_user = st.session_state.get("logged_in_user")
    if logged_in_user == ADM_USERNAME:
        # É ADM, mostra a página
        tab1, tab2 = st.tabs(["DEVOLUÇÃO", "GERAL"])
        with tab1:
            show_pcm_page_2()
        with tab2:
            show_pcm_page_1()
            
    else:
        # Não é ADM, mostra erro
        st.error("🚫 Acesso Negado!")
        st.warning(f"O usuário '{logged_in_user}' não tem permissão para acessar esta página.")
        st.info("Esta funcionalidade é restrita aos administradores.")
        add_logout_button() # Permite sair mesmo se negado
else:
    # Se não logado, a função 'check_password' já exibirá o formulário.
    st.warning("Você precisa fazer login como administrador para acessar esta página.")