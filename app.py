import streamlit as st
import pandas as pd
import unicodedata
import io

# ==============================================================================
# 1. CONFIGURACIÓN INICIAL Y ESTILOS
# ==============================================================================
st.set_page_config(
    page_title="Dashboard de Líderes",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo personalizado de CSS para ajustar márgenes y contenedores
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CARGA Y FUENTES DE DATOS
# ==============================================================================
st.sidebar.title("⚙️ Configuración y Datos")

# Método 1: Carga desde Google Sheets o URL remota
url_gsheets = st.sidebar.text_input(
    "🔗 URL Google Sheets (CSV publicado):",
    value="",
    help="Ingresa el enlace CSV público de tu Google Sheet"
)

# Método 2: Selector de archivos interactivo
archivo_subido = st.sidebar.file_uploader(
    "📂 O subir archivo local (Excel / CSV):", 
    type=["xlsx", "xls", "csv"]
)

@st.cache_data(ttl=300)
def cargar_desde_url(url):
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Error al cargar desde la URL: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def cargar_datos_locales():
    for nombre in ["base_lideres.xlsx", "base_lideres.csv", "datos.xlsx", "datos.csv"]:
        try:
            if nombre.endswith('.csv'):
                return pd.read_csv(nombre)
            else:
                return pd.read_excel(nombre)
        except Exception:
            continue
    return pd.DataFrame()

# Determinación de la base de datos principal
if url_gsheets.strip():
    df_lideres = cargar_desde_url(url_gsheets.strip())
elif archivo_subido is not None:
    try:
        if archivo_subido.name.endswith('.csv'):
            df_lideres = pd.read_csv(archivo_subido)
        else:
            df_lideres = pd.read_excel(archivo_subido)
    except Exception as e:
        st.sidebar.error(f"Error al leer el archivo: {e}")
        df_lideres = pd.DataFrame()
else:
    df_lideres = cargar_datos_locales()

# ==============================================================================
# 3. MENÚ DE NAVEGACIÓN
# ==============================================================================
st.sidebar.markdown("---")
st.sidebar.title("📌 Menú Principal")
menu = st.sidebar.radio(
    "Seleccione el módulo:",
    ["🔍 Consulta Detallada", "📊 Resumen General", "⚙️ Configuración de Columnas"],
    index=0
)

# ==============================================================================
# 4. FUNCIONES AUXILIARES Y NORMALIZACIÓN
# ==============================================================================
def normalizar(texto):
    if not isinstance(texto, str):
        texto = str(texto)
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.lower().strip()

def buscar_columna_df(df_cols, alias_list):
    for alias in alias_list:
        alias_norm = normalizar(alias)
        for col in df_cols:
            col_norm = normalizar(str(col))
            if alias_norm == col_norm or alias_norm in col_norm:
                return col
    return None

def obtener_valor_inteligente(row, df_cols, alias_list, default="Sin datos", cols_usadas=None):
    col_encontrada = buscar_columna_df(df_cols, alias_list)
    if col_encontrada:
        if cols_usadas is not None:
            cols_usadas.add(col_encontrada)
        val = str(row[col_encontrada]).strip()
        if val and val.lower() not in ["nan", "none", "null", "<na>", ""]:
            return val
    return default

def obtener_fecha_cumpleanos_formateada(row, df_cols, cols_usadas=None):
    val = obtener_valor_inteligente(row, df_cols, ["cumpleanos", "cumpleaños", "fecha nacimiento"], "Sin datos", cols_usadas)
    if val != "Sin datos":
        try:
            fecha_dt = pd.to_datetime(val)
            return fecha_dt.strftime("%d de %B")
        except Exception:
            return val
    return val

def generar_pdf_ficha(row, df_cols):
    buffer = io.BytesIO()
    buffer.write(b"%PDF-1.4 Ficha Tecnica de Registro")
    buffer.seek(0)
    return buffer.getvalue()

# ==============================================================================
# 5. MÓDULO 1: CONSULTA DETALLADA
# ==============================================================================
if menu == "🔍 Consulta Detallada":
    st.title("🔍 Consulta Detallada de Líderes")

    if not df_lideres.empty:
        col_filtro1, col_filtro2 = st.columns([1, 2])
        with col_filtro1:
            criterio = st.radio("Criterio de Búsqueda:", ["General / Todos los Campos", "Por Cédula", "Por Nombre"], horizontal=True)
        with col_filtro2:
            busqueda = st.text_input("🔍 Ingrese el término o número a buscar:")
        
        resultado = pd.DataFrame()
        if busqueda.strip():
            mask = df_lideres.astype(str).apply(
                lambda row: row.str.contains(busqueda.strip(), case=False, na=False)
            ).any(axis=1)
            resultado = df_lideres[mask]

        if not resultado.empty:
            st.success(f"✅ Se encontraron {len(resultado)} registro(s).")

            for idx, row in resultado.iterrows():
                cols_usadas = set()

                # Identificación y Nombre
                cedula = obtener_valor_inteligente(row, df_lideres.columns, ["cedula", "identificacion", "documento", "id"], "Sin datos", cols_usadas)
                nombres = obtener_valor_inteligente(row, df_lideres.columns, ["nombres", "nombre"], "", cols_usadas)
                apellidos = obtener_valor_inteligente(row, df_lideres.columns, ["apellidos", "apellido"], "", cols_usadas)
                nombre_completo = f"{nombres} {apellidos}".strip() or "NOMBRE NO REGISTRADO"

                # Información Laboral
                dependencia = obtener_valor_inteligente(row, df_lideres.columns, ["dependencia"], "Sin datos", cols_usadas)
                secretaria = obtener_valor_inteligente(row, df_lideres.columns, ["secretaria", "secretaría"], "Sin datos", cols_usadas)
                cargo = obtener_valor_inteligente(row, df_lideres.columns, ["cargo actual", "cargo", "puesto"], "Sin datos", cols_usadas)
                profesion = obtener_valor_inteligente(row, df_lideres.columns, ["profesion", "profesión", "oficio"], "Sin datos", cols_usadas)
                lider_apoyo = obtener_valor_inteligente(row, df_lideres.columns, ["lider / apoyo", "lider/apoyo", "lider", "apoyo"], "Sin datos", cols_usadas)

                # Contacto
                telefono = obtener_valor_inteligente(row, df_lideres.columns, ["telefono / celular", "telefono", "celular", "tel", "movil"], "Sin datos", cols_usadas)
                correo = obtener_valor_inteligente(row, df_lideres.columns, ["correo", "email", "mail"], "Sin datos", cols_usadas)
                redes = obtener_valor_inteligente(row, df_lideres.columns, ["redes sociales", "redes"], "Sin datos", cols_usadas)

                # Ubicación
                municipio = obtener_valor_inteligente(row, df_lideres.columns, ["municipio", "ciudad"], "Sin datos", cols_usadas)
                comuna = obtener_valor_inteligente(row, df_lideres.columns, ["comuna"], "Sin datos", cols_usadas)
                barrio = obtener_valor_inteligente(row, df_lideres.columns, ["barrio"], "Sin datos", cols_usadas)
                cumpleanos = obtener_fecha_cumpleanos_formateada(row, df_lideres.columns, cols_usadas)

                # Proyección y Registros
                proyeccion = obtener_valor_inteligente(row, df_lideres.columns, ["proyeccion", "proyección"], "Sin datos", cols_usadas)
                registros = obtener_valor_inteligente(row, df_lideres.columns, ["registros", "registro"], "Sin datos", cols_usadas)
                notas = obtener_valor_inteligente(row, df_lideres.columns, ["notas / observaciones", "notas", "observaciones"], "Sin datos", cols_usadas)

                # Planillas
                amigos = obtener_valor_inteligente(row, df_lideres.columns, ["no. amigos", "nro amigos", "amigos"], "0", cols_usadas)
                bello = obtener_valor_inteligente(row, df_lideres.columns, ["municipio de bello", "bello"], "Sin datos", cols_usadas)
                otros_muni = obtener_valor_inteligente(row, df_lideres.columns, ["otros municipios"], "Sin datos", cols_usadas)
                censo = obtener_valor_inteligente(row, df_lideres.columns, ["no esta en el censo", "censo", "no censo"], "Sin datos", cols_usadas)

                # TARJETA
                with st.container(border=True):
                    col_h1, col_h2 = st.columns([3, 1])
                    with col_h1:
                        st.markdown(f"# **{nombre_completo.upper()}**")
                        st.markdown(f"**Cédula:** {cedula} | **Dependencia:** {dependencia}")
                    with col_h2:
                        st.download_button(
                            label="📄 Descargar Ficha PDF",
                            data=generar_pdf_ficha(row, df_lideres.columns),
                            file_name=f"Ficha_{cedula}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        with st.container(border=True):
                            st.markdown("### 📌 Información Laboral")
                            st.markdown(f"**Dependencia:** {dependencia}")
                            st.markdown(f"**Secretaría:** {secretaria}")
                            st.markdown(f"**Cargo:** {cargo}")
                            st.markdown(f"**Profesión:** {profesion}")
                            st.markdown(f"**Rol:** {lider_apoyo}")

                    with c2:
                        with st.container(border=True):
                            st.markdown("### 📞 Contacto Directo")
                            st.markdown(f"**Teléfono:** {telefono}")
                            st.markdown(f"**Correo:** [{correo}](mailto:{correo})" if correo != "Sin datos" else "**Correo:** Sin datos")
                            st.markdown(f"**Redes:** {redes}")

                    with c3:
                        with st.container(border=True):
                            st.markdown("### 📍 Ubicación y Fechas")
                            st.markdown(f"**Municipio:** {municipio}")
                            st.markdown(f"**Comuna:** {comuna}")
                            st.markdown(f"**Barrio:** {barrio}")
                            st.markdown(f"**Cumpleaños:** {cumpleanos}")

                    c4, c5 = st.columns(2)
                    with c4:
                        with st.container(border=True):
                            st.markdown("### 📌 Proyección y Notas")
                            st.markdown(f"**Proyección:** {proyeccion}")
                            st.markdown(f"**Registros:** {registros}")
                            st.markdown(f"**Observaciones:** {notas}")

                    with c5:
                        with st.container(border=True):
                            st.markdown("### 📋 Planillas y Registros")
                            st.markdown(f"**No. Amigos:** {amigos}")
                            st.markdown(f"**Bello:** {bello}")
                            st.markdown(f"**Otros Municipios:** {otros_muni}")
                            st.markdown(f"**Censo:** {censo}")

                    # Columnas no mapped
                    cols_restantes = [c for c in df_lideres.columns if c not in cols_usadas]
                    extra_data = [(c, str(row[c]).strip()) for c in cols_restantes if str(row[c]).strip() and str(row[c]).lower() not in ["nan", "none", "<na>", ""]]

                    if extra_data:
                        with st.expander("📂 Ver información complementaria"):
                            for k, v in extra_data:
                                st.write(f"**{k}:** {v}")

                st.markdown("---")
        elif busqueda:
            st.warning("⚠️ No se localizó ningún registro.")
    else:
        st.info("👈 **Carga tus datos** usando la barra lateral izquierda (vía Google Sheets o subiendo el archivo Excel/CSV).")

# ==============================================================================
# 6. MÓDULO 2: RESUMEN GENERAL Y MÉTRICAS
# ==============================================================================
elif menu == "📊 Resumen General":
    st.title("📊 Resumen General de la Base de Datos")
    if not df_lideres.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Registros", len(df_lideres))
        m2.metric("Total Columnas", len(df_lideres.columns))
        
        col_muni = buscar_columna_df(df_lideres.columns, ["municipio", "ciudad"])
        if col_muni:
            m3.metric("Municipios Registrados", df_lideres[col_muni].nunique())

        st.markdown("### Vista Previa de Datos")
        st.dataframe(df_lideres, use_container_width=True)
    else:
        st.info("👈 No hay datos cargados para generar el resumen.")

# ==============================================================================
# 7. MÓDULO 3: CONFIGURACIÓN DE COLUMNAS
# ==============================================================================
elif menu == "⚙️ Configuración de Columnas":
    st.title("⚙️ Configuración y Estructura del Archivo")
    if not df_lideres.empty:
        st.write("A continuación se lista la estructura detectada en tu archivo de datos:")
        st.json(list(df_lideres.columns))
    else:
        st.info("👈 Carga una base de datos para ver sus columnas.")
