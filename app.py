import streamlit as st
import sqlitecloud
import pandas as pd

# --------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# --------------------------------------------------

st.set_page_config(
    page_title="Sistema Académico Uninorte",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Sistema Académico - Universidad del Norte")
st.write("Sistema conectado a SQLite Cloud")

# --------------------------------------------------
# CONEXIÓN A SQLITE CLOUD
# --------------------------------------------------

@st.cache_resource
def conectar_bd():

    db = st.secrets["database"]

    connection_string = (
        f"sqlitecloud://{db['host']}:{db['port']}/"
        f"{db['database']}?apikey={db['apikey']}"
    )

    return sqlitecloud.connect(connection_string)


# --------------------------------------------------
# OBTENER TABLAS
# --------------------------------------------------

def obtener_tablas():

    tablas_academicas = [
        "asignatura",
        "beca",
        "departamento",
        "estudiante",
        "estudiante_beca",
        "grupo",
        "matricula",
        "periodo",
        "prerrequisito",
        "profesor",
        "profesor_departamento",
        "programa",
        "salon"
    ]

    return tablas_academicas


# --------------------------------------------------
# PROGRAMA PRINCIPAL
# --------------------------------------------------

try:

    conn = conectar_bd()

    st.success("🟢 Conexión exitosa con SQLite Cloud")

    tablas = obtener_tablas()

    # --------------------------------------------------
    # INFORMACIÓN GENERAL
    # --------------------------------------------------

    st.subheader("📊 Resumen de la base de datos")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Número de tablas",
            len(tablas)
        )

    with col2:
        st.metric(
            "Base de datos",
            st.secrets["database"]["database"]
        )

    # --------------------------------------------------
    # LISTA DE TABLAS
    # --------------------------------------------------

    st.subheader("🗂️ Tablas disponibles")

    st.write(tablas)

    # --------------------------------------------------
    # SELECCIONAR TABLA
    # --------------------------------------------------

    st.subheader("🔎 Consultar tabla")

    tabla_seleccionada = st.selectbox(
        "Selecciona una tabla:",
        tablas
    )

    # --------------------------------------------------
    # MOSTRAR TABLA
    # --------------------------------------------------

    if tabla_seleccionada:

        consulta = f'SELECT * FROM "{tabla_seleccionada}"'

        datos = pd.read_sql(
            consulta,
            conn
        )

        st.write(
            f"### 📋 Datos de `{tabla_seleccionada}`"
        )

        st.dataframe(
            datos,
            use_container_width=True,
            hide_index=True
        )

        st.write(
            f"**Registros:** {len(datos)}"
        )

except Exception as e:

    st.error("❌ No se pudo conectar con la base de datos")

    st.exception(e)