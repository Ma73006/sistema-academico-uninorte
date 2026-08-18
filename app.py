import streamlit as st
import sqlitecloud
import pandas as pd
from datetime import date


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Sistema Académico Uninorte",
    page_icon="🎓",
    layout="wide"
)


# ============================================================
# CONEXIÓN A SQLITE CLOUD
# ============================================================

@st.cache_resource
def conectar_bd():

    db = st.secrets["database"]

    connection_string = (
        f"sqlitecloud://{db['host']}:{db['port']}/"
        f"{db['database']}?apikey={db['apikey']}"
    )

    return sqlitecloud.connect(connection_string)


# ============================================================
# TABLAS ACADÉMICAS
# ============================================================

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


# ============================================================
# OBTENER DATOS
# ============================================================

def obtener_datos(conn, tabla):

    consulta = f'SELECT * FROM "{tabla}"'

    return pd.read_sql(
        consulta,
        conn
    )


# ============================================================
# OBTENER COLUMNAS
# ============================================================

def obtener_columnas(conn, tabla):

    """
    Obtiene las columnas de una tabla.
    No guarda errores en caché.
    """

    try:

        consulta = f'SELECT * FROM "{tabla}" LIMIT 0'

        datos = pd.read_sql(
            consulta,
            conn
        )

        columnas = []

        for nombre in datos.columns:

            columnas.append({
                "name": nombre,
                "type": str(datos[nombre].dtype)
            })

        return pd.DataFrame(columnas)

    except Exception:

        return pd.DataFrame()


# ============================================================
# INFORMACIÓN DE COLUMNAS
# ============================================================

def obtener_info_columnas(conn, tabla):

    """
    Obtiene:

    - nombre
    - tipo
    - NOT NULL
    - PRIMARY KEY
    """

    try:

        cursor = conn.cursor()

        consulta = (
            f'PRAGMA table_info("{tabla}")'
        )

        cursor.execute(
            consulta
        )

        filas = cursor.fetchall()

        cursor.close()

        info = []

        for fila in filas:

            if len(fila) >= 6:

                info.append({

                    "name": fila[1],

                    "type": fila[2],

                    "notnull": bool(
                        fila[3]
                    ),

                    "pk": bool(
                        fila[5]
                    )

                })

        if info:

            return pd.DataFrame(info)

    except Exception:

        pass


    # ========================================================
    # RESPALDO
    # ========================================================

    columnas = obtener_columnas(
        conn,
        tabla
    )

    if not columnas.empty:

        columnas["notnull"] = False

        columnas["pk"] = False

        return columnas

    return pd.DataFrame()


# ============================================================
# DETECTAR FOREIGN KEYS
# ============================================================

def obtener_foreign_keys(
    conn,
    tabla
):

    """
    Detecta automáticamente las Foreign Keys.
    """

    try:

        cursor = conn.cursor()

        consulta = (
            f'PRAGMA foreign_key_list("{tabla}")'
        )

        cursor.execute(
            consulta
        )

        filas = cursor.fetchall()

        cursor.close()

        foreign_keys = {}

        for fila in filas:

            if len(fila) >= 5:

                columna_local = fila[3]

                tabla_referencia = fila[2]

                columna_referencia = fila[4]

                foreign_keys[
                    columna_local
                ] = {

                    "tabla_referencia":
                        tabla_referencia,

                    "columna_referencia":
                        columna_referencia
                }

        return foreign_keys

    except Exception:

        return {}


# ============================================================
# BUSCAR COLUMNA AMIGABLE
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def encontrar_columna_mostrar_cache(
    tabla,
    columna_id
):

    try:

        conn = conectar_bd()

        datos = obtener_datos(
            conn,
            tabla
        )

        if datos.empty:

            return columna_id

        columnas = datos.columns.tolist()

        nombres_preferidos = [

            "nombre",
            "nombres",
            "name",
            "descripcion",
            "description",
            "titulo",
            "nombre_programa",
            "nombre_asignatura",
            "nombre_profesor",
            "nombre_departamento",
            "nombre_salon"

        ]

        for preferida in nombres_preferidos:

            if preferida in columnas:

                return preferida

        # ----------------------------------------------------
        # Buscar columna que no sea ID
        # ----------------------------------------------------

        columnas_no_id = [

            columna

            for columna in columnas

            if columna != columna_id

            and "id_" not in columna.lower()

            and not columna.lower().endswith("_id")

        ]

        if columnas_no_id:

            return columnas_no_id[0]

        return columna_id

    except Exception:

        return columna_id


# ============================================================
# OBTENER OPCIONES FOREIGN KEY
# ============================================================

@st.cache_data(ttl=60, show_spinner=False)
def obtener_opciones_fk_cache(
    tabla_referencia,
    columna_id
):

    try:

        conn = conectar_bd()

        datos = obtener_datos(
            conn,
            tabla_referencia
        )

        if datos.empty:

            return []

        if columna_id not in datos.columns:

            return []

        columna_mostrar = (
            encontrar_columna_mostrar_cache(
                tabla_referencia,
                columna_id
            )
        )

        if columna_mostrar not in datos.columns:

            columna_mostrar = columna_id

        opciones = []

        for _, fila in datos.iterrows():

            valor_id = fila[
                columna_id
            ]

            valor_mostrar = fila[
                columna_mostrar
            ]

            opciones.append(
                (
                    valor_id,
                    valor_mostrar
                )
            )

        return opciones

    except Exception:

        return []


# ============================================================
# CREAR CAMPO NORMAL
# ============================================================

def crear_campo_normal(
    nombre,
    tipo,
    obligatorio=False
):

    etiqueta = nombre.replace(
        "_",
        " "
    ).title()

    if obligatorio:

        etiqueta += " *"

    tipo = str(tipo).upper()

    # --------------------------------------------------------
    # ENTEROS
    # --------------------------------------------------------

    if (
        "INT" in tipo
        or "INTEGER" in tipo
    ):

        return st.number_input(
            etiqueta,
            value=0,
            step=1,
            format="%d"
        )

    # --------------------------------------------------------
    # DECIMALES
    # --------------------------------------------------------

    elif (
        "FLOAT" in tipo
        or "DOUBLE" in tipo
        or "REAL" in tipo
        or "DECIMAL" in tipo
        or "NUMERIC" in tipo
    ):

        return st.number_input(
            etiqueta,
            value=0.0
        )

    # --------------------------------------------------------
    # FECHAS
    # --------------------------------------------------------

    elif "DATE" in tipo:

        return st.date_input(
            etiqueta,
            value=date.today()
        )

    # --------------------------------------------------------
    # TEXTO
    # --------------------------------------------------------

    else:

        return st.text_input(
            etiqueta
        )


# ============================================================
# CREAR FOREIGN KEY
# ============================================================

def crear_campo_foreign_key(
    nombre,
    relacion,
    obligatorio=False
):

    tabla_referencia = relacion[
        "tabla_referencia"
    ]

    columna_referencia = relacion[
        "columna_referencia"
    ]

    opciones = obtener_opciones_fk_cache(
        tabla_referencia,
        columna_referencia
    )

    etiqueta = nombre.replace(
        "_",
        " "
    ).title()

    if obligatorio:

        etiqueta += " *"

    # --------------------------------------------------------
    # NO HAY OPCIONES
    # --------------------------------------------------------

    if not opciones:

        st.warning(
            f"⚠️ No existen opciones disponibles "
            f"para {etiqueta}."
        )

        return None


    # --------------------------------------------------------
    # CREAR OPCIONES VISUALES
    # --------------------------------------------------------

    opciones_visuales = []

    mapa_valores = {}

    for valor_id, valor_mostrar in opciones:

        texto = (
            f"{valor_mostrar} "
            f"(ID: {valor_id})"
        )

        opciones_visuales.append(
            texto
        )

        mapa_valores[
            texto
        ] = valor_id


    # --------------------------------------------------------
    # SELECTBOX
    # --------------------------------------------------------

    seleccion = st.selectbox(
        etiqueta,
        opciones_visuales,
        key=(
            f"fk_{nombre}_"
            f"{tabla_referencia}"
        )
    )

    return mapa_valores[
        seleccion
    ]


# ============================================================
# CONVERTIR VALORES
# ============================================================

def convertir_valor(valor):

    if isinstance(
        valor,
        date
    ):

        return valor.isoformat()

    if isinstance(
        valor,
        str
    ):

        if valor.strip() == "":

            return None

        return valor.strip()

    return valor


# ============================================================
# INSERTAR REGISTRO
# ============================================================

def insertar_registro(
    conn,
    tabla,
    valores
):

    nombres = list(
        valores.keys()
    )

    datos = []

    for nombre in nombres:

        datos.append(
            convertir_valor(
                valores[nombre]
            )
        )

    nombres_sql = ", ".join(
        [
            f'"{nombre}"'
            for nombre in nombres
        ]
    )

    placeholders = ", ".join(
        ["?"] * len(nombres)
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


# ============================================================
# FORMULARIO DE INSERTAR
# ============================================================

def mostrar_formulario_insertar(
    conn,
    tabla
):

    st.subheader(
        f"➕ Agregar registro a `{tabla}`"
    )

    # --------------------------------------------------------
    # INFORMACIÓN DE COLUMNAS
    # --------------------------------------------------------

    columnas = obtener_info_columnas(
        conn,
        tabla
    )

    if columnas.empty:

        st.info(
            "La información de la tabla está "
            "cargando. Intenta nuevamente."
        )

        return


    # --------------------------------------------------------
    # FOREIGN KEYS
    # --------------------------------------------------------

    foreign_keys = obtener_foreign_keys(
        conn,
        tabla
    )

    st.info(
        "Completa los campos y presiona "
        "**Guardar registro**.\n\n"
        "Los campos marcados con * son obligatorios. "
        "Las llaves foráneas se seleccionan "
        "automáticamente."
    )

    valores = {}

    formulario_valido = True


    # ========================================================
    # FORMULARIO
    # ========================================================

    with st.form(
        key=f"form_insertar_{tabla}"
    ):

        for _, columna in columnas.iterrows():

            nombre = columna[
                "name"
            ]

            tipo = columna[
                "type"
            ]

            obligatorio = bool(
                columna.get(
                    "notnull",
                    False
                )
            )


            # =================================================
            # FOREIGN KEY
            # =================================================

            if nombre in foreign_keys:

                valor = crear_campo_foreign_key(
                    nombre,
                    foreign_keys[nombre],
                    obligatorio
                )

                if valor is None:

                    formulario_valido = False

                valores[
                    nombre
                ] = valor


            # =================================================
            # CAMPO NORMAL
            # =================================================

            else:

                valores[
                    nombre
                ] = crear_campo_normal(
                    nombre,
                    tipo,
                    obligatorio
                )


        st.write("")

        guardar = st.form_submit_button(
            "💾 Guardar registro",
            use_container_width=True
        )


    # ========================================================
    # GUARDAR
    # ========================================================

    if guardar:

        if not formulario_valido:

            st.warning(
                "⚠️ No se puede guardar el registro "
                "porque una de las llaves foráneas "
                "no tiene opciones disponibles."
            )

            return

        try:

            insertar_registro(
                conn,
                tabla,
                valores
            )

            # ------------------------------------------------
            # LIMPIAR CACHÉ DE LAS OPCIONES FK
            # ------------------------------------------------

            obtener_opciones_fk_cache.clear()

            st.success(
                f"✅ ¡Registro agregado correctamente "
                f"a la tabla `{tabla}`!"
            )

            st.rerun()


        except Exception as e:

            mensaje = str(e)


            # ------------------------------------------------
            # UNIQUE
            # ------------------------------------------------

            if (
                "UNIQUE constraint failed"
                in mensaje
            ):

                st.warning(
                    "⚠️ El registro no es válido. "
                    "Uno de los valores ingresados "
                    "ya existe. Verifica que el ID "
                    "no esté repetido."
                )


            # ------------------------------------------------
            # FOREIGN KEY
            # ------------------------------------------------

            elif (
                "FOREIGN KEY constraint failed"
                in mensaje
            ):

                st.warning(
                    "⚠️ El registro no es válido. "
                    "Una de las referencias ingresadas "
                    "no existe."
                )


            # ------------------------------------------------
            # NOT NULL
            # ------------------------------------------------

            elif (
                "NOT NULL constraint failed"
                in mensaje
            ):

                st.warning(
                    "⚠️ El registro no es válido. "
                    "Debes completar todos los "
                    "campos obligatorios."
                )


            # ------------------------------------------------
            # OTRO ERROR
            # ------------------------------------------------

            else:

                st.warning(
                    "⚠️ No se pudo guardar el registro. "
                    "Verifica que los datos ingresados "
                    "sean válidos."
                )


# ============================================================
# CONSULTAR TABLA
# ============================================================

def consultar_tabla(
    conn,
    tabla,
    columna_filtro=None,
    operador=None,
    valor_filtro=None,
    columna_orden=None,
    direccion="ASC"
):

    consulta = (
        f'SELECT * FROM "{tabla}"'
    )

    parametros = []


    # ========================================================
    # WHERE
    # ========================================================

    if (
        columna_filtro
        and operador
        and valor_filtro is not None
        and str(valor_filtro).strip() != ""
    ):

        if operador == "Igual a":

            sql_operador = "="

            parametros.append(
                valor_filtro
            )

        elif operador == "Diferente de":

            sql_operador = "!="

            parametros.append(
                valor_filtro
            )

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

            parametros.append(
                valor_filtro
            )

        elif operador == "Menor que":

            sql_operador = "<"

            parametros.append(
                valor_filtro
            )

        elif operador == "Mayor o igual":

            sql_operador = ">="

            parametros.append(
                valor_filtro
            )

        elif operador == "Menor o igual":

            sql_operador = "<="

            parametros.append(
                valor_filtro
            )

        else:

            sql_operador = "="

            parametros.append(
                valor_filtro
            )


        consulta += (
            f' WHERE "{columna_filtro}" '
            f'{sql_operador} ?'
        )


    # ========================================================
    # ORDER BY
    # ========================================================

    if columna_orden:

        if direccion not in [
            "ASC",
            "DESC"
        ]:

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


# ============================================================
# INTERFAZ DE CONSULTA
# ============================================================

def mostrar_consulta(
    conn,
    tabla
):

    st.subheader(
        f"🔎 Consultar `{tabla}`"
    )

    columnas = obtener_columnas(
        conn,
        tabla
    )

    if columnas.empty:

        st.info(
            "La información de la tabla está "
            "cargando. Intenta nuevamente."
        )

        return


    nombres_columnas = columnas[
        "name"
    ].tolist()

    if not nombres_columnas:

        st.info(
            "La información de la tabla está "
            "cargando. Intenta nuevamente."
        )

        return


    # ========================================================
    # FILTRO
    # ========================================================

    st.markdown(
        "### 🔍 Filtrar registros"
    )

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


    # ========================================================
    # ORDENAR
    # ========================================================

    st.markdown(
        "### ↕️ Ordenar resultados"
    )

    col1, col2 = st.columns(2)

    with col1:

        columna_orden = st.selectbox(
            "Ordenar por:",
            [
                "Sin ordenar"
            ] + nombres_columnas
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


    # ========================================================
    # BOTÓN CONSULTAR
    # ========================================================

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

        except Exception:

            st.warning(
                "⚠️ No se pudo realizar la consulta. "
                "Verifica los datos ingresados."
            )


    # ========================================================
    # TABLA INICIAL
    # ========================================================

    else:

        try:

            datos = obtener_datos(
                conn,
                tabla
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
                f"**Total de registros:** "
                f"{len(datos)}"
            )

        except Exception:

            st.info(
                "No se pudieron cargar los registros "
                "en este momento."
            )


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

try:

    conn = conectar_bd()

    tablas = obtener_tablas()


    # ========================================================
    # TÍTULO
    # ========================================================

    st.title(
        "🎓 Sistema Académico - Universidad del Norte"
    )

    st.caption(
        "Sistema de consulta y registro académico"
    )

    st.success(
        "🟢 Conexión exitosa con SQLite Cloud"
    )


    # ========================================================
    # SIDEBAR
    # ========================================================

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


    # ========================================================
    # BOTÓN ACTUALIZAR
    # ========================================================

    if st.sidebar.button(
        "🔄 Actualizar información",
        use_container_width=True
    ):

        st.rerun()


    # ========================================================
    # INICIO
    # ========================================================

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
                st.secrets[
                    "database"
                ][
                    "database"
                ]
            )

        st.divider()

        st.subheader(
            "🗂️ Tablas académicas"
        )

        columnas_metricas = st.columns(3)

        for i, tabla in enumerate(tablas):

            with columnas_metricas[
                i % 3
            ]:

                try:

                    datos = obtener_datos(
                        conn,
                        tabla
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


    # ========================================================
    # CONSULTAR
    # ========================================================

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


    # ========================================================
    # AGREGAR
    # ========================================================

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


# ============================================================
# ERROR GENERAL
# ============================================================

except Exception:

    st.error(
        "❌ No se pudo conectar con la base de datos."
    )

    st.warning(
        "Verifica la configuración de conexión "
        "con SQLite Cloud e inténtalo nuevamente."
    )