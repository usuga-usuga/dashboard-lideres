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


# --- NAVEGACIÓN Y MENÚ LATERAL (SIEMPRE VISIBLE) ---

st.sidebar.title("📌 Menú Principal")

# Selección de módulo
modulo = st.sidebar.selectbox(
    "Selecciona un Módulo:",
    [
        "📂 Carga de Datos",
        "📊 Dashboard Analítico",
        "🔍 Explorador de Registros",
    ],
)

st.sidebar.markdown("---")

# Botón de cierre de sesión al final del menú
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


# --- MÓDULO 1: CARGA DE DATOS ---
if modulo == "📂 Carga de Datos":
    st.title("📂 Carga de Base de Datos")
    st.write("Sube el archivo Excel que contiene la información de los líderes.")

    archivo = st.file_uploader(
        "Selecciona un archivo Excel (.xlsx)", type=["xlsx"]
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

                # Guardar el DataFrame en la sesión global para usarlo en otros módulos
                st.session_state["df_data"] = df
                st.session_state["rango_info"] = (inicio, fin)

                st.success(
                    f"¡Base de datos cargada con éxito! Se procesaron {len(df)} registros (Filas {inicio} a {fin})."
                )
                st.info(
                    "Pasa al módulo '📊 Dashboard Analítico' desde la barra lateral para ver los resultados."
                )

                st.subheader("Vista Previa")
                st.dataframe(df.head(10), use_container_width=True)
            else:
                st.warning("No se detectaron datos en la columna 'A'.")
        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")
    else:
        if "df_data" in st.session_state:
            st.success(
                f"Actualmente hay una base cargada con {len(st.session_state['df_data'])} registros."
            )


# --- MÓDULO 2: DASHBOARD ANALÍTICO ---
elif modulo == "📊 Dashboard Analítico":
    st.title("📊 Dashboard Analítico")

    if "df_data" not in st.session_state:
        st.warning(
            "⚠️ No hay datos cargados. Por favor ve al módulo '📂 Carga de Datos' para subir tu archivo."
        )
    else:
        df = st.session_state["df_data"]
        inicio, fin = st.session_state["rango_info"]

        # Filtros opcionales
        cols_categoricas = df.select_dtypes(
            include=["object", "category"]
        ).columns.tolist()

        df_filtrado = df.copy()

        if cols_categoricas:
            st.sidebar.subheader("🔍 Filtros del Dashboard")
            col_f = st.sidebar.selectbox("Filtrar por:", ["Todos"] + cols_categoricas)
            if col_f != "Todos":
                opciones = df[col_f].dropna().unique().tolist()
                sel = st.sidebar.multiselect(
                    "Selecciona valores:", opciones, default=opciones
                )
                if sel:
                    df_filtrado = df_filtrado[df_filtrado[col_f].isin(sel)]

        # KPIs
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Registros", len(df))
        kpi2.metric("Registros Filtrados", len(df_filtrado))
        kpi3.metric("Columnas", len(df.columns))
        kpi4.metric("Rango Excel", f"{inicio} - {fin}")

        st.markdown("---")

        # Gráficos
        if cols_categoricas and len(df_filtrado) > 0:
            st.subheader("📈 Distribución de Datos")
            c1, c2 = st.columns(2)

            col_g = c1.selectbox(
                "Selecciona variable a graficar:", cols_categoricas
            )
            conteo = (
                df_filtrado[col_g].value_counts().reset_index()
            )
            conteo.columns = [col_g, "Cantidad"]

            fig_barras = px.bar(
                conteo.head(10),
                x=col_g,
                y="Cantidad",
                text="Cantidad",
                title=f"Top 10 - {col_g}",
                color="Cantidad",
                color_continuous_scale="Blues",
            )
            c1.plotly_chart(fig_barras, use_container_width=True)

            fig_pie = px.pie(
                conteo.head(5),
                names=col_g,
                values="Cantidad",
                title=f"Proporción Top 5 - {col_g}",
                hole=0.4,
            )
            c2.plotly_chart(fig_pie, use_container_width=True)


# --- MÓDULO 3: EXPLORADOR DE REGISTROS ---
elif modulo == "🔍 Explorador de Registros":
    st.title("🔍 Exploración y Descarga de Datos")

    if "df_data" not in st.session_state:
        st.warning(
            "⚠️ No hay datos cargados. Por favor ve al módulo '📂 Carga de Datos' para subir tu archivo."
        )
    else:
        df = st.session_state["df_data"]

        busqueda = st.text_input(
            "🔍 Buscar en toda la tabla:", placeholder="Escribe para buscar..."
        )

        if busqueda:
            mascara = df.astype(str).apply(
                lambda row: row.str.contains(
                    busqueda, case=False, na=False
                ).any(),
                axis=1,
            )
            df_mostrar = df[mascara]
        else:
            df_mostrar = df

        st.dataframe(df_mostrar, use_container_width=True, height=400)

        # Botón de descarga
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_mostrar.to_excel(writer, index=False, sheet_name="Datos")

        st.download_button(
            label="📥 Descargar datos en Excel",
            data=buffer.getvalue(),
            file_name=f"reporte_lideres_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
