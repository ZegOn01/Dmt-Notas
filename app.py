# app.py
import streamlit as st

# Garante que as configurações da página sejam definidas apenas uma vez
# e de preferência no script principal, embora com st.Page possa não ser
# estritamente necessário se cada página definir a sua.
# Para consistência, podemos definir um padrão aqui.
st.set_page_config(page_title="App de Controle", layout="wide", initial_sidebar_state="auto")
sidebar_logo = "R.png"
main_logo = "Imagem1.jpg"
st.logo(sidebar_logo,icon_image=main_logo,size="large")

# Define as páginas usando st.Page
login_page = st.Page("Page_Assinatura.py", title="ASSINATURAS", icon="🔐")
pcm_page = st.Page("Page_Admin.py", title="CONTROLE DE NOTAS", icon="📝")
dash_page = st.Page("Page_DashBoards.py", title="DASHBOARDS", icon="📈")
test = st.Page("page_test.py", title="Developing", icon="🚜")

# Configura a navegação na barra lateral
pg = st.navigation([login_page, dash_page, pcm_page])

# Adiciona algo à barra lateral que aparecerá em todas as páginas (opcional)

#st.sidebar.info("Navegue entre as páginas acima.")

# Executa a página selecionada
pg.run()