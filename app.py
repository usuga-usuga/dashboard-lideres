import streamlit as st
import pandas as pd
import unicodedata
import io
import os

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS ESTÉTICOS
# ==============================================================================
st.set_page_config(
    page_title="Dashboard de Líderes",
    page_icon="🔍",
    layout="wide"
)

# Estilos CSS para corregir contraste, colores y tamaño de los botones
st.markdown("""
    <style>
    /* Estilo para todos los botones primarios y de descarga en Streamlit */
    div.stDownloadButton > button, div.stButton > button, a.stLinkButton {
        background-color: #1e3a8a !important; /* Azul oscuro elegante */
        color: #ffffff !important;           /* Texto blanco brillante */
        border-radius: 8px !important;
        border: 1px solid #1e40af !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 8px 16px !important;
        box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.1) !important;
        transition: all 0.3s ease !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-decoration: none !important;
        width: auto !important; /* Evita que se estiren de forma fea */
    }

    /* Efecto al pasar el cursor (Hover) */
    div.stDownloadButton > button:hover, div.stButton > button:hover, a.stLinkButton:hover {
        background-color: #2563eb !important; /* Azul más claro al pasar el cursor */
        color: #ffffff !important;
        box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.15) !important;
        transform: translateY(-1px);
    }

    /* Ajuste para que el texto dentro del botón sea 100% visible */
    div.stDownloadButton > button p, div.stButton > button p {
        color: #ffffff !important;
        font-weight: 600 !important;
        margin: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# CARGA AUTOMÁTICA DE DATOS
# ==============================================================================
@st.cache_data(ttl=600)
def cargar_datos_automatico():
    """Busca y carga automáticamente el archivo de datos del proyecto."""
    archivos_posibles = [
        "base_lideres.xlsx", "base_lideres.csv", 
        "lideres.xlsx", "lideres.csv",
        "Lideres.xlsx", "Lideres.csv",
        "datos.xlsx", "datos.csv"
    ]
    
    for nombre in archivos_posibles:
        if os.path.exists(nombre):
            try:
                if nombre.endswith('.csv'):
                    return pd.read_csv(nombre)
                else:
                    return pd.read_excel(nombre)
            except Exception:
                continue

    try:
        archivos_carpeta = os.listdir('.')
        for f in archivos_carpeta:
            if f.endswith('.xlsx') or f.endswith('.xls'):
                return pd.read_excel(f)
            elif f.endswith('.csv'):
                return pd.read_csv(f)
    except Exception:
        pass
        
    return pd.DataFrame()

df_lideres = cargar_datos_automatico()

# ==============================================================================
# BARRA LATERAL (MENÚ Y NAVEGACIÓN)
# ==============================================================================
st.sidebar.title("📌 Menú de Navegación")

if df_lideres.empty:
    st.sidebar.warning("⚠️ No se detectó archivo automático.")
    archivo_subido = st.sidebar.file_uploader("Suba su archivo Excel/CSV:", type=["xlsx", "xls", "csv"])
    if archivo_subido is not None:
        if archivo_subido.name.endswith('.csv'):
            df_lideres = pd.read_csv(archivo_subido)
        else:
            df_lideres = pd.read_excel(archivo_subido)

menu = st.sidebar.radio(
    "Seleccione un módulo:",
    ["🔍 Consulta Detallada", "📊 Resumen General"],
    index=0
)

# ==============================================================================
# FUNCIONES AUXILIARES
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
    buffer.write(b"%PDF-1.4 Ficha Tecnicas")
    buffer.seek(0)
    return buffer.getvalue()

# ==============================================================================
# MÓDULO 1: CONSULTA DETALLADA
# ==============================================================================
if menu == "🔍 Consulta Detallada":
    st.title("🔍 Consulta Detallada de Líderes")

    if not df_lideres.empty:
        ver_todos = st.checkbox("Mostrar todos los registros sin buscar", value=False)
        busqueda = st.text_input("Ingrese término de búsqueda (Nombre, Cédula, Municipio, etc.):")
        
        resultado = pd.DataFrame()
        if ver_todos:
            resultado = df_lideres.copy()
        elif busqueda.strip():
            mask = df_lideres.astype(str).apply(
                lambda row: row.str.contains(busqueda.strip(), case=False, na=False)
            ).any(axis=1)
            resultado = df_lideres[mask]

        if not resultado.empty:
            st.success(f"✅ Se encontraron {len(resultado)} registro(s).")

            for idx, row in resultado.iterrows():
                cols_usadas = set()

                # 1. Datos Clave
                cedula = obtener_valor_inteligente(row, df_lideres.columns, ["cedula", "identificacion", "documento", "id"], "Sin datos", cols_usadas)
                nombres = obtener_valor_inteligente(row, df_lideres.columns, ["nombres", "nombre"], "", cols_usadas)
                apellidos = obtener_valor_inteligente(row, df_lideres.columns, ["apellidos", "apellido"], "", cols_usadas)
                nombre_completo = f"{nombres} {apellidos}".strip() or "NOMBRE NO REGISTRADO"

                # 2. Información Laboral
                dependencia = obtener_valor_inteligente(row, df_lideres.columns, ["dependencia"], "Sin datos", cols_usadas)
                secretaria = obtener_valor_inteligente(row, df_lideres.columns, ["secretaria", "secretaría"], "Sin datos", cols_usadas)
                cargo = obtener_valor_inteligente(row, df_lideres.columns, ["cargo actual", "cargo", "puesto"], "Sin datos", cols_usadas)
                profesion = obtener_valor_inteligente(row, df_lideres.columns, ["profesion", "profesión", "oficio"], "Sin datos", cols_usadas)
                lider_apoyo = obtener_valor_inteligente(row, df_lideres.columns, ["lider / apoyo", "lider/apoyo", "lider", "apoyo"], "Sin datos", cols_usadas)

                # 3. Contacto Directo
                telefono = obtener_valor_inteligente(row, df_lideres.columns, ["telefono / celular", "telefono", "celular", "tel", "movil"], "Sin datos", cols_usadas)
                correo = obtener_valor_inteligente(row, df_lideres.columns, ["correo", "email", "mail"], "Sin datos", cols_usadas)
                redes = obtener_valor_inteligente(row, df_lideres.columns, ["redes sociales", "redes"], "Sin datos", cols_usadas)

                # 4. Ubicación y Fechas
                municipio = obtener_valor_inteligente(row, df_lideres.columns, ["municipio", "ciudad"], "Sin datos", cols_usadas)
                comuna = obtener_valor_inteligente(row, df_lideres.columns, ["comuna"], "Sin datos", cols_usadas)
                barrio = obtener_valor_inteligente(row, df_lideres.columns, ["barrio"], "Sin datos", cols_usadas)
                cumpleanos = obtener_fecha_cumpleanos_formateada(row, df_lideres.columns, cols_usadas)

                # 5. URL o Archivo Planilla
                url_pdf_planilla = obtener_valor_inteligente(row, df_lideres.columns, ["url_pdf", "pdf", "link", "planilla"], None, cols_usadas)

                # --- TARJETA DE LÍDER ---
                with st.container(border=True):
                    # CABECERA CON NOMBRE Y BOTÓN FICHAS PDF
                    col_header1, col_header2 = st.columns([4, 1.2])
                    with col_header1:
                        st.markdown(f"## **{nombre_completo.upper()}**")
                        st.markdown(f"**Cédula / Identificación:** {cedula} | **Dependencia:** {dependencia}")
                    
                    with col_header2:
                        # Botón Descargar PDF Ficha con diseño estético
                        pdf_file = generar_pdf_ficha(row, df_lideres.columns)
                        st.download_button(
                            label="📄 Descargar Ficha PDF",
                            data=pdf_file,
                            file_name=f"Ficha_{cedula}.pdf",
                            mime="application/pdf",
                            use_container_width=False
                        )

                    st.markdown("<br>", unsafe_allow_html=True)

                    # TRES COLUMNAS PRINCIPALES DE DATOS
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("### 📌 Información Laboral")
                        st.markdown(f"**Dependencia:** {dependencia}")
                        st.markdown(f"**Secretaría:** {secretaria}")
                        st.markdown(f"**Cargo Actual:** {cargo}")
                        st.markdown(f"**Profesión:** {profesion}")

                    with col2:
                        st.markdown("### 📞 Contacto Directo")
                        st.markdown(f"**Teléfono:** {telefono}")
                        st.markdown(f"**Correo:** [{correo}](mailto:{correo})" if correo != "Sin datos" else "**Correo:** Sin datos")
                        if redes != "Sin datos":
                            st.markdown(f"**Redes:** {redes}")

                    with col3:
                        st.markdown("### 📍 Ubicación y Fechas")
                        if municipio != "Sin datos":
                            st.markdown(f"**Municipio:** {municipio}")
                        st.markdown(f"**Comuna:** {comuna}")
                        st.markdown(f"**Barrio:** {barrio}")
                        st.markdown(f"**Cumpleaños:** {cumpleanos}")

                    # SECCIÓN INFERIOR: BOTÓN "ABRIR PDF PLANILLA" (SI EXISTE)
                    st.markdown("<br>", unsafe_allow_html=True)
                    if url_pdf_planilla and url_pdf_planilla != "Sin datos":
                        col_btn1, col_btn2 = st.columns([1, 4])
                        with col_btn1:
                            st.link_button("🔗 Abrir PDF Planilla", url_pdf_planilla, use_container_width=False)

                st.markdown("---")
        elif busqueda:
            st.warning("⚠️ No se encontró ningún registro que coincida con la búsqueda.")
        else:
            st.info("💡 Escriba en el buscador o active la opción 'Mostrar todos los registros'.")
    else:
        st.error("❌ No hay datos cargados en la aplicación.")

elif menu == "📊 Resumen General":
    st.title("📊 Resumen General")
    if not df_lideres.empty:
        st.metric("Total de Registros Cargados", len(df_lideres))
        st.dataframe(df_lideres, use_container_width=True)
