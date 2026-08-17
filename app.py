import streamlit as st
import sqlitecloud
import pandas as pd
from datetime import date


# ==================================================
# CONFIGURACIÓN DE LA PÁGINA
# ==================================================

st.set_page_config(
    page_title="Sistema Académico Uninorte",
    page_icon="🎓",
    layout="wide"
)


# ==================================================
# CONEXIÓN A SQLITE CLOUD
# ==================================================

@st.cache_resource
def conectar_bd():

    db = st.secrets["database"]

    connection_string = (
        f"sqlitecloud://{db['host']}:{db['port']}/"
        f"{db['database']}?apikey={db['apikey']}"
    )

    return sqlitecloud.connect(connection_string)


# ==================================================
# TABLAS ACADÉMICAS PERMITIDAS
# ==================================================

def obtener_tablas():

    return [
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


# ==================================================
# OBTENER COLUMNAS DE UNA TABLA
# ==================================================

def obtener_columnas(conn, tabla):

    consulta = f'PRAGMA table_info("{tabla}")'

    return pd.read_sql(
        consulta,
        conn
    )


# ==================================================
# CREAR CAMPO SEGÚN EL TIPO DE DATO
# ==================================================

def crear_campo(nombre, tipo, obligatorio=False):

    tipo = str(tipo).upper()

    etiqueta = nombre.replace("_", " ").title()

    if obligatorio:
        etiqueta += " *"

    # ----------------------------------------------
    # NÚMEROS ENTEROS
    # ----------------------------------------------

    if "INT" in tipo:

        return st.number_input(
            etiqueta,
            value=0,
            step=1,
            format="%d"
        )

    # ----------------------------------------------
    # NÚMEROS DECIMALES
    # ----------------------------------------------

    elif (
        "REAL" in tipo
        or "FLOAT" in tipo
        or "DOUBLE" in tipo
        or "DECIMAL" in tipo
        or "NUMERIC" in tipo
    ):

        return st.number_input(
            etiqueta,
            value=0.0
        )

    # ----------------------------------------------
    # FECHAS
    # ----------------------------------------------

    elif "DATE" in tipo:

        return st.date_input(
            etiqueta,
            value=date.today()
        )

    # ----------------------------------------------
    # TEXTO
    # ----------------------------------------------

    else:

        return st.text_input(
            etiqueta
        )


# ==================================================
# CONVERTIR VALORES AL TIPO CORRECTO
# ==================================================

def convertir_valor(valor, tipo):

    tipo = str(tipo).upper()

    # ----------------------------------------------
    # TEXTO VACÍO
    # ----------------------------------------------

    if isinstance(valor, str) and valor.strip() == "":
        return None

    # ----------------------------------------------
    # FECHA
    # ----------------------------------------------

    if "DATE" in tipo:

        if isinstance(valor, date):
            return valor.isoformat()

    return valor


# ==================================================
# INSERTAR REGISTRO
# ==================================================

def insertar_registro(conn, tabla, columnas, valores):

    nombres = []

    datos = []

    for i, columna in columnas.iterrows():

        nombre = columna["name"]
        tipo = columna["type"]

        nombres.append(nombre)

        valor = convertir_valor(
            valores[nombre],
            tipo
        )

        datos.append(valor)

    placeholders = ", ".join(
        ["?"] * len(nombres)
    )

    nombres_sql = ", ".join(
        [f'"{nombre}"' for nombre in nombres]
    )

    consulta = f"""
        INSERT INTO "{tabla}"
        ({nombres_sql})
        VALUES ({placeholders})
    """

    conn.execute(
        consulta,
        tuple(datos)
    )

    conn.commit()


# ==================================================
# MOSTRAR FORMULARIO DE INSERCIÓN
# ==================================================

def mostrar_formulario_insertar(conn, tabla):

    st.subheader(
        f"➕ Agregar registro a `{tabla}`"
    )

    columnas = obtener_columnas(
        conn,
        tabla
    )

    if columnas.empty:

        st.warning(
            "⚠️ No se pudieron encontrar las columnas de esta tabla."
        )

        return

    st.info(
        "Los campos marcados con * son obligatorios."
    )

    valores = {}

    with st.form(
        key=f"form_insertar_{tabla}"
    ):

        # ------------------------------------------
        # CREAR LOS CAMPOS
        # ------------------------------------------

        for _, columna in columnas.iterrows():

            nombre = columna["name"]
            tipo = columna["type"]
            notnull = columna["notnull"]

            valores[nombre] = crear_campo(
                nombre,
                tipo,
                obligatorio=bool(notnull)
            )

        st.write("")

        guardar = st.form_submit_button(
            "💾 Guardar registro",
            use_container_width=True
        )

    # ----------------------------------------------
    # GUARDAR
    # ----------------------------------------------

    if guardar:

        try:

            # --------------------------------------
            # VALIDAR CAMPOS OBLIGATORIOS
            # --------------------------------------

            errores = []

            for _, columna in columnas.iterrows():

                nombre = columna["name"]
                notnull = columna["notnull"]

                valor = valores[nombre]

                if notnull:

                    if valor is None:

                        errores.append(
                            f"El campo `{nombre}` es obligatorio."
                        )

                    elif isinstance(valor, str) and not valor.strip():

                        errores.append(
                            f"El campo `{nombre}` es obligatorio."
                        )

            if errores:

                for error in errores:
                    st.error(f"❌ {error}")

                return

            # --------------------------------------
            # INSERTAR
            # --------------------------------------

            insertar_registro(
                conn,
                tabla,
                columnas,
                valores
            )
            # --------------------------------------
            # ALERTA DE ÉXITO
            # --------------------------------------

            st.success(
                f"✅ ¡Registro agregado correctamente a la tabla `{tabla}`!"
            )


        except Exception as e:

            mensaje = str(e)

            if "UNIQUE constraint failed" in mensaje:

                st.warning(
                    "⚠️ El registro no es válido. "
                    "Uno de los valores ingresados ya existe. "
                    "Verifica que el ID no esté repetido."
                )

            elif "FOREIGN KEY constraint failed" in mensaje:

                st.warning(
                    "⚠️ El registro no es válido. "
                    "Una de las referencias ingresadas no existe."
                )

            elif "NOT NULL constraint failed" in mensaje:

                st.warning(
                    "⚠️ El registro no es válido. "
                    "Debes completar todos los campos obligatorios."
                )

            else:

                st.warning(
                    "⚠️ No se pudo guardar el registro. "
                    "Verifica que los datos ingresados sean válidos."
                )


# ==================================================
# CONSULTAR TABLA
# ==================================================

def consultar_tabla(
    conn,
    tabla,
    columna_filtro=None,
    operador=None,
    valor_filtro=None,
    columna_orden=None,
    direccion="ASC"
):

    consulta = f'SELECT * FROM "{tabla}"'

    parametros = []

    # ----------------------------------------------
    # WHERE
    # ----------------------------------------------

    if (
        columna_filtro
        and operador
        and valor_filtro is not None
        and str(valor_filtro).strip() != ""
    ):

        if operador == "Igual a":
            sql_operador = "="
            parametros.append(valor_filtro)

        elif operador == "Diferente de":
            sql_operador = "!="
            parametros.append(valor_filtro)

        elif operador == "Contiene":
            sql_operador = "LIKE"
            parametros.append(
                f"%{valor_filtro}%"
            )

        elif operador == "Empieza por":
            sql_operador = "LIKE"
            parametros.append(
                f"{valor_filtro}%"
            )

        elif operador == "Termina en":
            sql_operador = "LIKE"
            parametros.append(
                f"%{valor_filtro}"
            )

        elif operador == "Mayor que":
            sql_operador = ">"
            parametros.append(valor_filtro)

        elif operador == "Menor que":
            sql_operador = "<"
            parametros.append(valor_filtro)

        elif operador == "Mayor o igual":
            sql_operador = ">="
            parametros.append(valor_filtro)

        elif operador == "Menor o igual":
            sql_operador = "<="
            parametros.append(valor_filtro)

        else:
            sql_operador = "="
            parametros.append(valor_filtro)

        consulta += (
            f' WHERE "{columna_filtro}" '
            f'{sql_operador} ?'
        )

    # ----------------------------------------------
    # ORDER BY
    # ----------------------------------------------

    if columna_orden:

        if direccion not in ["ASC", "DESC"]:
            direccion = "ASC"

        consulta += (
            f' ORDER BY "{columna_orden}" '
            f'{direccion}'
        )

    return pd.read_sql(
        consulta,
        conn,
        params=parametros
    )


# ==================================================
# INTERFAZ DE CONSULTA
# ==================================================

def mostrar_consulta(conn, tabla):

    st.subheader(
        f"🔎 Consultar `{tabla}`"
    )

    columnas = obtener_columnas(
        conn,
        tabla
    )

    nombres_columnas = columnas[
        "name"
    ].tolist()

    # ==================================================
    # FILTROS
    # ==================================================

    st.markdown("### 🔍 Filtrar registros")

    activar_filtro = st.checkbox(
        "Activar filtro"
    )

    columna_filtro = None
    operador = None
    valor_filtro = None

    if activar_filtro:

        col1, col2, col3 = st.columns(3)

        with col1:

            columna_filtro = st.selectbox(
                "Filtrar por:",
                nombres_columnas
            )

        with col2:

            operador = st.selectbox(
                "Condición:",
                [
                    "Igual a",
                    "Diferente de",
                    "Contiene",
                    "Empieza por",
                    "Termina en",
                    "Mayor que",
                    "Menor que",
                    "Mayor o igual",
                    "Menor o igual"
                ]
            )

        with col3:

            valor_filtro = st.text_input(
                "Valor:"
            )

    # ==================================================
    # ORDENAMIENTO
    # ==================================================

    st.markdown("### ↕️ Ordenar resultados")

    col1, col2 = st.columns(2)

    with col1:

        columna_orden = st.selectbox(
            "Ordenar por:",
            ["Sin ordenar"] + nombres_columnas
        )

    with col2:

        direccion_texto = st.selectbox(
            "Orden:",
            [
                "Ascendente",
                "Descendente"
            ]
        )

    if columna_orden == "Sin ordenar":
        columna_orden_sql = None

    else:
        columna_orden_sql = columna_orden

    if direccion_texto == "Ascendente":
        direccion = "ASC"

    else:
        direccion = "DESC"

    # ==================================================
    # BOTÓN DE CONSULTA
    # ==================================================

    if st.button(
        "🔍 Consultar",
        use_container_width=True
    ):

        try:

            datos = consultar_tabla(
                conn,
                tabla,
                columna_filtro,
                operador,
                valor_filtro,
                columna_orden_sql,
                direccion
            )

            st.markdown(
                "### 📊 Resultados"
            )

            if datos.empty:

                st.warning(
                    "⚠️ No se encontraron registros."
                )

            else:

                st.success(
                    f"✅ Se encontraron "
                    f"{len(datos)} registros."
                )

                st.dataframe(
                    datos,
                    use_container_width=True,
                    hide_index=True
                )

        except Exception as e:

            st.error(
                "❌ Error al realizar la consulta."
            )

            st.exception(e)

    # ==================================================
    # MOSTRAR TODOS LOS REGISTROS
    # ==================================================

    else:

        try:

            datos = pd.read_sql(
                f'SELECT * FROM "{tabla}"',
                conn
            )

            st.markdown(
                "### 📋 Todos los registros"
            )

            st.dataframe(
                datos,
                use_container_width=True,
                hide_index=True
            )

            st.write(
                f"**Total de registros:** {len(datos)}"
            )

        except Exception as e:

            st.error(
                "❌ No se pudieron obtener los registros."
            )

            st.exception(e)


# ==================================================
# PROGRAMA PRINCIPAL
# ==================================================

try:

    conn = conectar_bd()

    tablas = obtener_tablas()

    # ==================================================
    # TÍTULO
    # ==================================================

    st.title(
        "🎓 Sistema Académico - Universidad del Norte"
    )

    st.caption(
        "Sistema de consulta y registro académico"
    )

    st.success(
        "🟢 Conexión exitosa con SQLite Cloud"
    )

    # ==================================================
    # SIDEBAR
    # ==================================================

    st.sidebar.title(
        "🎓 Sistema Académico"
    )

    st.sidebar.divider()

    opcion = st.sidebar.radio(
        "Menú principal",
        [
            "🏠 Inicio",
            "🔎 Consultar registros",
            "➕ Agregar registro"
        ]
    )

    st.sidebar.divider()

    st.sidebar.info(
        "Puedes consultar, filtrar, ordenar "
        "y agregar registros.\n\n"
        "Los registros existentes no pueden "
        "ser modificados ni eliminados."
    )

    # ==================================================
    # INICIO
    # ==================================================

    if opcion == "🏠 Inicio":

        st.header(
            "🏠 Bienvenido al Sistema Académico"
        )

        st.write(
            "Desde este sistema puedes consultar "
            "la información almacenada en la base "
            "de datos y registrar nuevos datos."
        )

        st.divider()

        # ----------------------------------------------
        # MÉTRICAS
        # ----------------------------------------------

        st.subheader(
            "📊 Información de la base de datos"
        )

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "🗂️ Número de tablas",
                len(tablas)
            )

        with col2:

            st.metric(
                "☁️ Base de datos",
                st.secrets["database"]["database"]
            )

        st.divider()

        # ----------------------------------------------
        # TABLAS
        # ----------------------------------------------

        st.subheader(
            "🗂️ Tablas académicas"
        )

        columnas = st.columns(3)

        for i, tabla in enumerate(tablas):

            with columnas[i % 3]:

                try:

                    datos = pd.read_sql(
                        f'SELECT * FROM "{tabla}"',
                        conn
                    )

                    st.metric(
                        tabla.replace(
                            "_",
                            " "
                        ).title(),
                        len(datos)
                    )

                except Exception:

                    st.write(
                        tabla
                    )

    # ==================================================
    # CONSULTAR
    # ==================================================

    elif opcion == "🔎 Consultar registros":

        st.header(
            "🔎 Consultar registros"
        )

        tabla_seleccionada = st.selectbox(
            "Selecciona una tabla:",
            tablas
        )

        st.divider()

        mostrar_consulta(
            conn,
            tabla_seleccionada
        )

    # ==================================================
    # AGREGAR
    # ==================================================

    elif opcion == "➕ Agregar registro":

        st.header(
            "➕ Agregar nuevo registro"
        )

        st.write(
            "Selecciona una tabla y completa "
            "los campos correspondientes."
        )

        st.warning(
            "⚠️ Esta sección solamente permite "
            "crear nuevos registros. "
            "No se pueden modificar ni eliminar "
            "registros existentes."
        )

        tabla_seleccionada = st.selectbox(
            "Selecciona una tabla:",
            tablas
        )

        st.divider()

        mostrar_formulario_insertar(
            conn,
            tabla_seleccionada
        )


# ==================================================
# MANEJO DE ERRORES
# ==================================================

except Exception as e:

    st.error(
        "❌ No se pudo conectar con la base de datos"
    )

    st.exception(e)