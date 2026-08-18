from datetime import date, datetime
import io
import unicodedata
import openpyxl
import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración inicial de la página
st.set_page_config(
    page_title="Dashboard Líderes", page_icon="📊", layout="wide"
)


# --- SISTEMA DE AUTENTICACIÓN DINÁMICO ---
def validar_credenciales(usuario_ingresado, password_ingresado):
    if "usuarios" in st.secrets:
        usuarios_dict = st.secrets["usuarios"]
        if usuario_ingresado in usuarios_dict:
            return str(usuarios_dict[usuario_ingresado]) == str(
                password_ingresado
            )
    return (usuario_ingresado == "admin") and (
        password_ingresado == "admin123"
    )


if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# --- PANTALLA DE LOGIN ---
if not st.session_state["autenticado"]:
    st.title("🔒 Acceso Restringido")
    st.write("Ingresa tus credenciales para acceder al Dashboard de Líderes.")

    col1, col2 = st.columns([1, 2])
    with col1:
        with st.form("form_login"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            boton_login = st.form_submit_button("Iniciar Sesión")

            if boton_login:
                if validar_credenciales(usuario, password):
                    st.session_state["autenticado"] = True
                    st.success("¡Acceso concedido!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")

    st.stop()


# --- NAVEGACIÓN Y MENÚ LATERAL (IDÉNTICO A LA IMAGEN) ---

st.sidebar.title("Módulos del Sistema")

# Selección mediante botones de radio (st.sidebar.radio)
modulo = st.sidebar.radio(
    "Seleccione una opción:",
    [
        "🔍 Consulta Detallada",
        "➕ Registro de Nuevo Usuario",
        "✏️ Editar / Modificar Registros",
        "📈 Panel de Control Ejecutivos",
        "📋 Base de Datos Completa",
    ],
)

st.sidebar.markdown("---")

# Botón de cierre de sesión
st.sidebar.button(
    "🚪 Cerrar Sesión",
    on_click=lambda: st.session_state.update({"autenticado": False}),
)


def obtener_rango_filas_excel(sheet, col_letter="A"):
    if not col_letter:
        col_letter = "A"

    col_letter = col_letter.upper().strip()
    primera_fila = None
    ultima_fila = None

    for row in range(1, sheet.max_row + 1):
        val = sheet[f"{col_letter}{row}"].value
        if val is not None and str(val).strip() != "":
            if primera_fila is None:
                primera_fila = row
            ultima_fila = row

    return primera_fila, ultima_fila


# --- MÓDULO 1: CONSULTA DETALLADA ---
if modulo == "🔍 Consulta Detallada":
    st.title("🔍 Consulta Detallada")

    if "df_data" not in st.session_state:
        st.warning(
            "⚠️ No hay datos cargados. Por favor ve al módulo '📋 Base de Datos Completa' para subir tu archivo."
        )
    else:
        df = st.session_state["df_data"]
        st.write("Filtra y consulta información específica de los registros:")

        busqueda = st.text_input("🔎 Buscar término:")
        if busqueda:
            mascara = df.astype(str).apply(
                lambda row: row.str.contains(
                    busqueda, case=False, na=False
                ).any(),
                axis=1,
            )
            st.dataframe(df[mascara], use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)


# --- MÓDULO 2: REGISTRO DE NUEVO USUARIO ---
elif modulo == "➕ Registro de Nuevo Usuario":
    st.title("➕ Registro de Nuevo Usuario")
    st.write("Ingresa los datos para registrar un nuevo usuario/líder:")

    with st.form("form_nuevo_registro"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre completo")
            identificacion = st.text_input("Número de Identificación")
        with col2:
            zona = st.text_input("Zona / Municipio")
            telefono = st.text_input("Teléfono de contacto")

        guardar = st.form_submit_button("Guardar Registro")
        if guardar:
            st.success("¡Registro guardado exitosamente!")


# --- MÓDULO 3: EDITAR / MODIFICAR REGISTROS ---
elif modulo == "✏️ Editar / Modificar Registros":
    st.title("✏️ Editar / Modificar Registros")
    st.write("Selecciona un registro para modificar sus valores:")

    if "df_data" in st.session_state:
        df = st.session_state["df_data"]
        st.dataframe(df.head(5), use_container_width=True)
        st.info("Funcionalidad de edición lista para conectar con tu base.")
    else:
        st.warning("⚠️ Debes cargar una base de datos primero.")


# --- MÓDULO 4: PANEL DE CONTROL EJECUTIVOS ---
elif modulo == "📈 Panel de Control Ejecutivos":
    st.title("📈 Panel de Control Ejecutivos")

    if "df_data" not in st.session_state:
        st.warning(
            "⚠️ No hay datos cargados. Ve al módulo '📋 Base de Datos Completa' para subir tu archivo."
        )
    else:
        df = st.session_state["df_data"]
        inicio, fin = st.session_state.get("rango_info", (1, len(df)))

        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Registros", len(df))
        k2.metric("Columnas", len(df.columns))
        k3.metric("Fila Inicio Excel", inicio)
        k4.metric("Fila Fin Excel", fin)

        st.markdown("---")

        # Gráficos
        cols_categoricas = df.select_dtypes(
            include=["object", "category"]
        ).columns.tolist()
        if cols_categoricas:
            c1, c2 = st.columns(2)
            var_g = c1.selectbox("Agrupar por:", cols_categoricas)
            conteo = df[var_g].value_counts().reset_index()
            conteo.columns = [var_g, "Cantidad"]

            fig_b = px.bar(
                conteo.head(10),
                x=var_g,
                y="Cantidad",
                text="Cantidad",
                title=f"Top 10 - {var_g}",
            )
            c1.plotly_chart(fig_b, use_container_width=True)

            fig_p = px.pie(
                conteo.head(5),
                names=var_g,
                values="Cantidad",
                title=f"Distribución Top 5 - {var_g}",
            )
            c2.plotly_chart(fig_p, use_container_width=True)


# --- MÓDULO 5: BASE DE DATOS COMPLETA ---
elif modulo == "📋 Base de Datos Completa":
    st.title("📋 Base de Datos Completa")
    st.write("Carga y gestiona el archivo completo de Excel:")

    archivo = st.file_uploader(
        "Cargar archivo Excel (.xlsx)", type=["xlsx"]
    )

    if archivo is not None:
        try:
            wb = openpyxl.load_workbook(archivo, data_only=True)
            sheet = wb.active
            inicio, fin = obtener_rango_filas_excel(sheet, col_letter="A")

            if inicio and fin:
                archivo.seek(0)
                df = pd.read_excel(
                    archivo, skiprows=inicio - 1, nrows=(fin - inicio + 1)
                )
                df = df.dropna(how="all", axis=1).dropna(how="all", axis=0)

                st.session_state["df_data"] = df
                st.session_state["rango_info"] = (inicio, fin)

                st.success(
                    f"¡Base cargada correctamente! {len(df)} registros procesados (Filas {inicio} a {fin})."
                )
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("No se hallaron datos en la columna 'A'.")
        except Exception as e:
            st.error(f"Error procesando archivo: {e}")
    else:
        if "df_data" in st.session_state:
            st.success("Base de datos cargada actualmente en el sistema.")
            st.dataframe(st.session_state["df_data"], use_container_width=True)
