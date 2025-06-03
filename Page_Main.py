import streamlit as st

# Configuração da página (opcional, mas recomendado)


# Título Principal e Subtítulo
st.title(":streamlit: Bem-vindo ao Controle de Documentos PPCM")
st.markdown("Este aplicativo foi desenvolvido para otimizar o gerenciamento e a assinatura de documentos industriais.")

# Navegação entre Páginas (Popover)
with st.popover("Navegar para:", use_container_width=True): # use_container_width pode ser útil
    st.page_link("Page_Assinatura.py", label="ASSINATURA DE DOCUMENTOS", icon="🔐")
    st.page_link("Page_DashBoards.py", label="PAINEL DE CONTROLE (DASHBOARDS)", icon="📈")
    st.page_link("Page_Admin.py", label="ADMINISTRAÇÃO DE DOCUMENTOS", icon="📝")

st.markdown("---") # Linha divisória para separar seções

# Seção: Objetivo
st.header("🎯 Objetivo do Aplicativo")
st.markdown(
    """
    O processo tradicional exige que documentos sejam assinados fisicamente antes de seu lançamento no sistema,
    conforme ilustrado no fluxo abaixo. Este aplicativo visa simplificar e agilizar esse controle,
    gerenciando documentos assinados e pendentes de assinatura.
    """
)

with st.expander("Visualizar Fluxo de Documentos", expanded=False): # Usar expander pode ser melhor se a imagem for grande
    try:
        st.image("Fluxo.png", caption="Fluxo de Documentos para a área Industrial")
    except FileNotFoundError:
        st.warning("Arquivo 'Fluxo.png' não encontrado. Verifique o caminho do arquivo.")
    except Exception as e:
        st.error(f"Não foi possível carregar a imagem: {e}")


st.markdown(
    """
    Com esta ferramenta, buscamos:
    * Reduzir o uso de papel.
    * Facilitar e agilizar o processo de assinatura.
    * Melhorar o rastreamento e o controle dos documentos.
    """
)

st.markdown("---")

# Seção: Como Funciona
st.header("⚙️ Como Funciona?")
st.markdown(
    """
    O aplicativo está organizado em três seções principais, acessíveis através do menu de navegação
    (localizado na barra lateral ou no botão "Navegar para:" acima):
    """
)

st.subheader("1. ASSINATURA DE DOCUMENTOS 🔐")
st.markdown(
    """
    Destinada aos gestores para a assinatura digital dos documentos.
    * **Acesso:** Requer senha (matrícula do gestor).
    * **Funcionalidade:** Permite visualizar documentos pendentes e assiná-los eletronicamente.
    """
)

st.subheader("2. PAINEL DE CONTROLE (DASHBOARDS) 📈")
st.markdown(
    """
    Oferece uma visão geral do status dos documentos.
    * **Funcionalidade:** Exibe indicadores como a quantidade de documentos assinados, pendentes e o progresso geral.
    """
)

st.subheader("3. ADMINISTRAÇÃO DE DOCUMENTOS 📝")
st.markdown(
    """
    Página de uso restrito ao administrador para gerenciar os documentos no sistema.
    * **Funcionalidade:** Permite inserir novos documentos, confirmar o recebimento das assinaturas pelos gestores e outras tarefas administrativas.
    """
)

st.markdown("---")

# Seção: Suporte/Contato
st.info("ℹ️ Em caso de dúvidas ou necessidade de suporte, entre em contato com o setor de PCM.")
