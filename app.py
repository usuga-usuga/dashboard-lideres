import streamlit as st
import pandas as pd
import unicodedata
from datetime import datetime, date
import io
import plotly.express as px

# ReportLab para la exportación de PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ------------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Ejecutivo de Líderes",
    page_icon="📊",
    layout="wide"
)

# ------------------------------------------------------------------------------
# 1. SISTEMA DE LOGIN Y AUTENTICACIÓN
# ------------------------------------------------------------------------------
def verificar_login():
    """Muestra la pantalla de inicio de sesión si el usuario no se ha autenticado."""
    if st.session_state.get("autenticado", False):
        return True

    st.markdown("<h2 style='text-align: center; color: #0F172A;'>🔒 Sistema de Control de Acceso</h2>", unsafe_allow_html=True)
    
    col_c1, col_c2, col_c3 = st.columns([1, 1.2, 1])
    with col_c2:
        with st.container(border=True):
            st.subheader("Iniciar Sesión")
            with st.form("form_login"):
                usuario = st.text_input("Usuario:")
                password = st.text_input("Contraseña:", type="password")
                boton_login = st.form_submit_button("Ingresar", use_container_width=True)

                if boton_login:
                    if "usuarios" in st.secrets and usuario in st.secrets["usuarios"]:
                        if str(password) == str(st.secrets["usuarios"][usuario]):
                            st.session_state.autenticado = True
                            st.success("✅ Acceso concedido")
                            st.rerun()
                        else:
                            st.error("❌ Contraseña incorrecta")
                    else:
                        st.error("❌ Usuario no registrado o secretos no configurados")

    return False

# Detiene la ejecución si no ha iniciado sesión
if not verificar_login():
    st.stop()

# ------------------------------------------------------------------------------
# ESTILO Y TEMA VISUAL CON ALTO CONTRASTE Y LEGIBILIDAD
# ------------------------------------------------------------------------------
st.markdown("""
    <style>
    /* 1. Fondo general de la app */
    .stApp {
        background-color: #F3F4F8 !important;
    }
    
    /* 2. Regla global de contraste para textos */
    .stApp p, .stApp span, .stApp label, .stApp div, .stApp caption, .stMarkdown {
        color: #1E293B !important;
    }
    
    /* Encabezados oscuros legibles */
    h1, h2, h3, h4, h5, h6 {
        color: #0F172A !important;
        font-weight: 700 !important;
    }
    
    /* 3. Barra lateral */
    [data-testid="stSidebar"] {
        background-color: #11223F !important;
    }
    
    /* Textos dentro de la barra lateral */
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
        color: #FFFFFF !important;
    }
    
    /* Botones en la barra lateral */
    [data-testid="stSidebar"] .stButton > button {
        background-color: #1A365D !important;
        color: #FFFFFF !important;
        border: 1px solid #2B6CB0 !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #F59E0B !important;
        border-color: #D97706 !important;
        color: #FFFFFF !important;
    }
    
    /* 4. Tarjetas y Contenedores Blancos con alto contraste */
    [data-testid="stVerticalBlock"] > div[data-testid="stBlock"], 
    div[data-testid="stForm"],
    .stCard {
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        padding: 16px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.05) !important;
    }

    /* Modificación de métricas KPIs */
    [data-testid="stMetricValue"] {
        color: #0F172A !important;
        font-weight: 800 !important;
    }
    [data-testid="stMetricLabel"] p {
        color: #334155 !important;
        font-weight: 700 !important;
    }
    
    /* Botones primarios */
    .stButton > button {
        background-color: #F59E0B !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        border: none !important;
    }
    .stButton > button:hover {
        background-color: #D97706 !important;
        color: #FFFFFF !important;
    }
    
    /* Botones de descarga */
    .stDownloadButton > button {
        background-color: #11223F !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }
    .stDownloadButton > button:hover {
        background-color: #F59E0B !important;
        color: #FFFFFF !important;
    }

    /* Inputs de texto */
    input {
        color: #0F172A !important;
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------------------------------
def normalizar(texto):
    """Quita tildes, mayúsculas y espacios para comparaciones flexibles."""
    if not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.lower().strip()

def obtener_valor_campo(row, df_columns, palabras_clave, default="Sin datos"):
    """Busca en la fila el valor utilizando una lista de posibles nombres de columna."""
    for key in palabras_clave:
        key_norm = normalizar(key)
        for col in df_columns:
            col_norm = normalizar(col)
            if key_norm in col_norm:
                val = str(row[col]).strip()
                if val and val.lower() not in ["nan", "none", "null", "<na>", ""]:
                    return val
    return default

def obtener_proximos_cumpleanos(df, dias_anticipacion=5):
    """Calcula las personas que cumplen años hoy o en los próximos N días."""
    if df.empty:
        return []
    
    hoy = date.today()
    proximos = []
    
    col_dia = None
    col_mes = None
    
    for col in df.columns:
        col_n = normalizar(col)
        if "fecha de cumple" in col_n or col_n in ["dia", "day"]:
            col_dia = col
        elif "unnamed: 12" in col_n or col_n in ["mes", "month"]:
            col_mes = col

    for idx, row in df.iterrows():
        dia_str = str(row[col_dia]).strip() if col_dia else ""
        mes_str = str(row[col_mes]).strip() if col_mes else ""
        
        if not dia_str.isdigit() or not mes_str.isdigit():
            continue
            
        dia = int(dia_str)
        mes = int(mes_str)
        
        if 1 <= dia <= 31 and 1 <= mes <= 12:
            try:
                try:
                    cumple_este_ano = date(hoy.year, mes, dia)
                except ValueError:
                    cumple_este_ano = date(hoy.year, mes, 28)
                
                if cumple_este_ano < hoy:
                    cumple_este_ano = date(hoy.year + 1, mes, dia)
                    
                diferencia = (cumple_este_ano - hoy).days
                
                if 0 <= diferencia <= dias_anticipacion:
                    nombres = obtener_valor_campo(row, df.columns, ["nombres", "nombre"], "")
                    apellidos = obtener_valor_campo(row, df.columns, ["apellidos", "apellido"], "")
                    nombre_comp = f"{nombres} {apellidos}".strip() or "Usuario sin nombre"
                    
                    proximos.append({
                        "nombre": nombre_comp.upper(),
                        "dias": diferencia,
                        "fecha_str": f"{dia:02d}/{mes:02d}",
                        "telefono": obtener_valor_campo(row, df.columns, ["telefono", "celular"]),
                        "dependencia": obtener_valor_campo(row, df.columns, ["dependencia", "secretaria"])
                    })
            except Exception:
                continue

    proximos.sort(key=lambda x: x["dias"])
    return proximos

def generar_pdf_ficha(row, df_columns):
    """Genera un archivo PDF con la ficha completa del usuario."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6
    )
    
    nombres = obtener_valor_campo(row, df_columns, ["nombres", "nombre"], "")
    apellidos = obtener_valor_campo(row, df_columns, ["apellidos", "apellido"], "")
    nombre_comp = f"{nombres} {apellidos}".strip().upper() or "FICHA DE USUARIO"
    cedula = obtener_valor_campo(row, df_columns, ["identificacion", "cedula", "doc", "id"])
    
    story.append(Paragraph(f"<b>{nombre_comp}</b>", title_style))
    story.append(Paragraph(f"Cédula / ID: <b>{cedula}</b>", subtitle_style))
    story.append(Spacer(1, 12))
    
    data = [
        [Paragraph("<b>CAMPO</b>", styles['Normal']), Paragraph("<b>DETALLE</b>", styles['Normal'])],
        ["Dependencia", obtener_valor_campo(row, df_columns, ['dependencia', 'area'])],
        ["Secretaría", obtener_valor_campo(row, df_columns, ['secretaria'])],
        ["Cargo", obtener_valor_campo(row, df_columns, ['cargo'])],
        ["Profesión", obtener_valor_campo(row, df_columns, ['profesion'])],
        ["Teléfono / Celular", obtener_valor_campo(row, df_columns, ['telefono', 'celular'])],
        ["Correo Electrónico", obtener_valor_campo(row, df_columns, ['correo', 'email'])],
        ["Comuna / Barrio", f"{obtener_valor_campo(row, df_columns, ['comuna'])} - {obtener_valor_campo(row, df_columns, ['barrio'])}"],
        ["Municipio", obtener_valor_campo(row, df_columns, ['municipio'])],
        ["No. Amigos", obtener_valor_campo(row, df_columns, ['amigos'], '0')],
        ["Observaciones / Notas", obtener_valor_campo(row, df_columns, ['nota', 'observacion'])]
    ]
    
    table = Table(data, colWidths=[180, 340])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return buffer

# ------------------------------------------------------------------------------
# 2. CONFIGURACIÓN DE CONEXIÓN A GOOGLE DRIVE / GOOGLE SHEETS
# ------------------------------------------------------------------------------
SHEET_ID = "1_ptZSSlI5johqy-OHZlMDfRiHaUmsBWH"
GID = "1965411495"

URL_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

def cargar_datos():
    """Lee la base de datos directamente desde Google Drive forzando formato texto."""
    try:
        df = pd.read_csv(URL_CSV, dtype=str)
        df = df.fillna("")
        df = df.astype(object)
        
        for col in df.columns:
            df[col] = df[col].astype(str).str.replace(".0", "", regex=False)
            df[col] = df[col].replace(["nan", "None", "<NA>"], "")
            
        return df
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Google Sheets: {e}")
        return pd.DataFrame()

if "df_lideres" not in st.session_state:
    st.session_state.df_lideres = cargar_datos()

df_lideres = st.session_state.df_lideres

# ------------------------------------------------------------------------------
# 3. SECCIÓN SUPERIOR: CUMPLEAÑOS
# ------------------------------------------------------------------------------
cumpleanos_lista = obtener_proximos_cumpleanos(df_lideres, dias_anticipacion=5)

with st.container(border=True):
    st.markdown("### 🎂 **Próximos Cumpleaños (Hoy y próximos 5 días)**")
    
    if cumpleanos_lista:
        cols_cumple = st.columns(min(len(cumpleanos_lista), 4))
        for idx, c in enumerate(cumpleanos_lista):
            col_actual = cols_cumple[idx % 4]
            with col_actual:
                with st.container(border=True):
                    if c["dias"] == 0:
                        st.markdown("🥳 **¡HOY CUMPLE AÑOS!** 🎉")
                    else:
                        st.markdown(f"🗓️ **En {c['dias']} día(s)** ({c['fecha_str']})")
                        
                    st.markdown(f"**{c['nombre']}**")
                    st.caption(f"🏢 {c['dependencia']}\n\n📞 Tel: {c['telefono']}")
    else:
        st.info("🎈 No hay personas registradas que cumplan años hoy o en los próximos 5 días.")

st.markdown("---")

# ------------------------------------------------------------------------------
# 4. BARRA LATERAL Y MÓDULOS DEL SISTEMA
# ------------------------------------------------------------------------------
st.sidebar.title("Módulos del Sistema")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.rerun()

if st.sidebar.button("🔄 Recargar datos de Google Drive", use_container_width=True):
    st.cache_data.clear()
    st.session_state.df_lideres = cargar_datos()
    st.sidebar.success("✅ ¡Base de datos actualizada!")
    st.rerun()

menu = st.sidebar.radio(
    "Seleccione una opción:",
    [
        "🔍 Consulta Detallada",
        "📈 Panel de Control Ejecutivos",
        "➕ Registro de Nuevo Usuario",
        "✏️ Editar / Modificar Registros",
        "📋 Base de Datos Completa"
    ]
)

# ==============================================================================
# MÓDULO 1: CONSULTA DETALLADA
# ==============================================================================
if menu == "🔍 Consulta Detallada":
    st.subheader("🔍 Consulta Detallada de Líderes")
    
    if not df_lideres.empty:
        criterio = st.radio("Buscar por:", ["Cédula / Identificación", "Nombre / Apellido"], horizontal=True)
        
        resultado = pd.DataFrame()
        
        if criterio == "Cédula / Identificación":
            busqueda = st.text_input("Ingrese el número de Cédula o Identificación:")
            if busqueda.strip():
                mask = df_lideres.astype(str).apply(lambda row: row.str.contains(busqueda.strip(), case=False, na=False)).any(axis=1)
                resultado = df_lideres[mask]
        else:
            busqueda = st.text_input("Ingrese Nombre o Apellido:")
            if busqueda.strip():
                mask = df_lideres.astype(str).apply(lambda row: row.str.contains(busqueda.strip(), case=False, na=False)).any(axis=1)
                resultado = df_lideres[mask]

        if not resultado.empty:
            st.success(f"✅ Se encontraron {len(resultado)} registro(s).")
            
            for idx, row in resultado.iterrows():
                nombres = obtener_valor_campo(row, df_lideres.columns, ["nombres", "nombre"], "")
                apellidos = obtener_valor_campo(row, df_lideres.columns, ["apellidos", "apellido"], "")
                nombre_completo = f"{nombres} {apellidos}".strip() or "NOMBRE NO REGISTRADO"
                
                cedula = obtener_valor_campo(row, df_lideres.columns, ["identificacion", "cedula", "doc", "id"])
                dependencia = obtener_valor_campo(row, df_lideres.columns, ["dependencia", "area", "sector"])

                with st.container(border=True):
                    col_header1, col_header2 = st.columns([3, 1])
                    with col_header1:
                        st.markdown(f"# **{nombre_completo.upper()}**")
                        st.markdown(f"**Cédula / Identificación:** {cedula} | **Dependencia:** {dependencia}")
                    with col_header2:
                        pdf_file = generar_pdf_ficha(row, df_lideres.columns)
                        st.download_button(
                            label="📄 Descargar Ficha PDF",
                            data=pdf_file,
                            file_name=f"Ficha_{cedula}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )

                col1, col2, col3 = st.columns(3)

                with col1:
                    with st.container(border=True):
                        st.markdown("### 📌 Información Laboral")
                        st.markdown(f"**Dependencia:** {dependencia}")
                        st.markdown(f"**Secretaría:** {obtener_valor_campo(row, df_lideres.columns, ['secretaria'])}")
                        st.markdown(f"**Cargo Actual:** {obtener_valor_campo(row, df_lideres.columns, ['cargo'])}")
                        st.markdown(f"**Profesión:** {obtener_valor_campo(row, df_lideres.columns, ['profesion'])}")
                        st.markdown(f"**Líder / Apoyo:** {obtener_valor_campo(row, df_lideres.columns, ['apoyo', 'lider'])}")

                with col2:
                    with st.container(border=True):
                        st.markdown("### 📞 Contacto Directo")
                        st.markdown(f"**Teléfono / Celular:** {obtener_valor_campo(row, df_lideres.columns, ['telefono', 'celular', 'movil'])}")
                        correo = obtener_valor_campo(row, df_lideres.columns, ['correo', 'email', 'mail'])
                        if correo != "Sin datos":
                            st.markdown(f"**Correo Electrónico:** [{correo}](mailto:{correo})")
                        else:
                            st.markdown("**Correo Electrónico:** Sin datos")
                        st.markdown(f"**Redes Sociales:** {obtener_valor_campo(row, df_lideres.columns, ['redes', 'social'])}")

                with col3:
                    with st.container(border=True):
                        st.markdown("### 📍 Ubicación y Fechas")
                        st.markdown(f"**Comuna:** {obtener_valor_campo(row, df_lideres.columns, ['comuna'])}")
                        st.markdown(f"**Barrio:** {obtener_valor_campo(row, df_lideres.columns, ['barrio'])}")
                        st.markdown(f"**Fecha Cumpleaños:** {obtener_valor_campo(row, df_lideres.columns, ['cumpleaños', 'cumpleanos', 'nacimiento'])}")

                col4, col5 = st.columns(2)

                with col4:
                    with st.container(border=True):
                        st.markdown("### 📌 Notas de Proyección")
                        st.markdown(f"**Proyección:** {obtener_valor_campo(row, df_lideres.columns, ['proyeccion'])}")
                        st.markdown(f"**Registros:** {obtener_valor_campo(row, df_lideres.columns, ['registro'])}")
                        st.markdown(f"**Municipio:** {obtener_valor_campo(row, df_lideres.columns, ['municipio'])}")
                        st.markdown(f"**Notas:** {obtener_valor_campo(row, df_lideres.columns, ['nota', 'observacion'])}")

                with col5:
                    with st.container(border=True):
                        st.markdown("### 📋 Planillas de Votación")
                        st.markdown(f"**No. Amigos:** {obtener_valor_campo(row, df_lideres.columns, ['amigos'], '0')}")
                        st.markdown(f"**Municipio de Bello:** {obtener_valor_campo(row, df_lideres.columns, ['bello'], '0')}")
                        st.markdown(f"**Otros Municipios / Deptos:** {obtener_valor_campo(row, df_lideres.columns, ['otros'], '0')}")
                        st.markdown(f"**No está en el Censo:** {obtener_valor_campo(row, df_lideres.columns, ['censo'], '0')}")
                        st.markdown(f"**Cédula Errónea:** {obtener_valor_campo(row, df_lideres.columns, ['erronea'], '0')}")

                st.markdown("---")
        elif busqueda:
            st.warning("⚠️ No se localizó ningún registro con el parámetro ingresado.")
    else:
        st.info("Cargando la base de datos desde Google Drive...")

# ==============================================================================
# MÓDULO 2: PANEL DE CONTROL EJECUTIVOS
# ==============================================================================
elif menu == "📈 Panel de Control Ejecutivos":
    st.subheader("📈 Panel de Control Ejecutivo y Métricas Analíticas")
    
    if not df_lideres.empty:
        # --- TARJETAS KPI ---
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        col_amigos = [c for c in df_lideres.columns if "AMIGOS" in c.upper()]
        total_amigos = 0
        if col_amigos:
            total_amigos = pd.to_numeric(df_lideres[col_amigos[0]], errors='coerce').fillna(0).sum()
            
        col_muni = [c for c in df_lideres.columns if "MUNICIPIO" in c.upper()]
        total_municipios = df_lideres[col_muni[0]].nunique() if col_muni else 0

        kpi1.metric("👥 Total Líderes", len(df_lideres))
        kpi2.metric("📊 Total Registros Amigos", int(total_amigos))
        kpi3.metric("📍 Municipios Cubiertos", total_municipios)
        kpi4.metric("🟢 Estado Conexión", "Sincronizado")
        
        st.markdown("---")
        
        # --- GRÁFICOS ANALÍTICOS OPTIMIZADOS ---
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("### 🏢 Líderes por Dependencia / Área")
            cols_dep = [col for col in df_lideres.columns if "DEP" in col.upper() or "SECTOR" in col.upper()]
            if cols_dep:
                df_dep = df_lideres[cols_dep[0]].astype(str).str.strip()
                df_dep = df_dep[~df_dep.str.lower().isin(["0", "", "nan", "none", "null", "<na>"])]
                
                conteo_dep = df_dep.value_counts().head(10).reset_index()
                conteo_dep.columns = ["Dependencia", "Cantidad"]
                
                fig_dep = px.bar(
                    conteo_dep, 
                    x="Cantidad", 
                    y="Dependencia", 
                    orientation='h',
                    text="Cantidad",
                    color_discrete_sequence=["#F59E0B"]
                )
                fig_dep.update_layout(
                    font=dict(color="#0F172A", size=12),
                    xaxis=dict(
                        tickfont=dict(color="#0F172A", size=11),
                        title=dict(text="Número de Registros", font=dict(color="#0F172A", size=12))
                    ),
                    yaxis=dict(
                        categoryorder='total ascending',
                        tickfont=dict(color="#0F172A", size=11),
                        title=dict(text="", font=dict(color="#0F172A"))
                    ),
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=380,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                fig_dep.update_traces(
                    textposition='outside',
                    textfont=dict(color="#0F172A", size=11, family="Arial-Bold")
                )
                st.plotly_chart(fig_dep, use_container_width=True)
            else:
                st.caption("No se encontró columna de dependencia.")

        with col_g2:
            st.markdown("### 🗺️ Distribución por Municipio")
            if col_muni:
                df_mun = df_lideres[col_muni[0]].astype(str).str.strip()
                df_mun = df_mun[~df_mun.str.lower().isin(["0", "", "nan", "none", "null", "<na>"])]
                
                conteo_muni = df_mun.value_counts().head(10).reset_index()
                conteo_muni.columns = ["Municipio", "Cantidad"]
                
                fig_muni = px.bar(
                    conteo_muni, 
                    x="Cantidad", 
                    y="Municipio", 
                    orientation='h',
                    text="Cantidad",
                    color_discrete_sequence=["#11223F"]
                )
                fig_muni.update_layout(
                    font=dict(color="#0F172A", size=12),
                    xaxis=dict(
                        tickfont=dict(color="#0F172A", size=11),
                        title=dict(text="Número de Registros", font=dict(color="#0F172A", size=12))
                    ),
                    yaxis=dict(
                        categoryorder='total ascending',
                        tickfont=dict(color="#0F172A", size=11),
                        title=dict(text="", font=dict(color="#0F172A"))
                    ),
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=380,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                fig_muni.update_traces(
                    textposition='outside',
                    textfont=dict(color="#0F172A", size=11, family="Arial-Bold")
                )
                st.plotly_chart(fig_muni, use_container_width=True)
            else:
                st.caption("No se encontró columna de municipios.")

        st.markdown("---")
        
        # --- ANÁLISIS DE PLANILLAS ---
        st.markdown("### 📋 Resumen Métrico de Planillas")
        col_p1, col_p2, col_p3 = st.columns(3)
        
        col_censo = [c for c in df_lideres.columns if "CENSO" in c.upper()]
        col_err = [c for c in df_lideres.columns if "ERRONEA" in c.upper() or "ERROR" in c.upper()]
        
        val_censo = pd.to_numeric(df_lideres[col_censo[0]], errors='coerce').fillna(0).sum() if col_censo else 0
        val_err = pd.to_numeric(df_lideres[col_err[0]], errors='coerce').fillna(0).sum() if col_err else 0
        
        col_p1.metric("👥 Total Amigos Registrados", int(total_amigos))
        col_p2.metric("⚠️ Fuera del Censo", int(val_censo))
        col_p3.metric("❌ Cédulas con Error", int(val_err))
        
    else:
        st.info("No hay información disponible para generar indicadores.")

# ==============================================================================
# MÓDULO 3: REGISTRO DE NUEVO USUARIO
# ==============================================================================
elif menu == "➕ Registro de Nuevo Usuario":
    st.subheader("➕ Registro de Nuevo Usuario")
    
    if not df_lideres.empty:
        st.info("Completa la información requerida para registrar un nuevo perfil.")
        with st.form("form_nuevo_usuario", clear_on_submit=True):
            datos_nuevos = {}
            cols = list(df_lideres.columns)
            
            c_a, c_b = st.columns(2)
            for idx, col_name in enumerate(cols):
                if idx % 2 == 0:
                    datos_nuevos[col_name] = c_a.text_input(f"{col_name}:")
                else:
                    datos_nuevos[col_name] = c_b.text_input(f"{col_name}:")
                    
            guardar = st.form_submit_button("➕ Registrar Usuario")
            
            if guardar:
                nuevo_row = pd.DataFrame([datos_nuevos]).astype(object)
                st.session_state.df_lideres = pd.concat([st.session_state.df_lideres, nuevo_row], ignore_index=True)
                st.success("✅ Usuario registrado en la vista local actual.")
                st.rerun()
    else:
        st.warning("La base de datos aún no se ha cargado.")

# ==============================================================================
# MÓDULO 4: EDITAR / MODIFICAR REGISTROS
# ==============================================================================
elif menu == "✏️ Editar / Modificar Registros":
    st.title("✏️ Edición de Datos de Usuarios")
    st.caption("Busque al usuario por Cédula, modifique los datos necesarios y guarde los cambios.")
    
    if not df_lideres.empty:
        cedula_buscar = st.text_input("Ingrese la Cédula/ID del usuario a editar:", placeholder="Ej: 3474244")
        
        if cedula_buscar.strip():
            mask = df_lideres.astype(str).apply(lambda row: row.str.contains(cedula_buscar.strip(), case=False, na=False)).any(axis=1)
            idx_match = df_lideres[mask].index

            if len(idx_match) > 0:
                user_idx = idx_match[0]
                usuario_data = df_lideres.loc[user_idx]
                
                st.success(f"👤 Usuario localizado (Fila #{user_idx + 1}). Modifique los campos necesarios:")
                
                with st.form("form_editar_usuario"):
                    datos_editados = {}
                    cols = list(df_lideres.columns)
                    c_a, c_b = st.columns(2)
                    
                    for i, col_name in enumerate(cols):
                        val_actual = str(usuario_data[col_name])
                        if val_actual.lower() in ["nan", "none", "null", "<na>"]:
                            val_actual = ""
                            
                        if i % 2 == 0:
                            datos_editados[col_name] = c_a.text_input(f"{col_name}:", value=val_actual)
                        else:
                            datos_editados[col_name] = c_b.text_input(f"{col_name}:", value=val_actual)
                    
                    guardar_cambios = st.form_submit_button("💾 Guardar Cambios")
                    
                    if guardar_cambios:
                        st.session_state.df_lideres = st.session_state.df_lideres.astype(object)
                        for col_name, nuevo_val in datos_editados.items():
                            st.session_state.df_lideres.at[user_idx, col_name] = str(nuevo_val)
                        
                        st.success("✅ Datos del usuario modificados correctamente.")
                        st.rerun()
            else:
                st.warning("⚠️ No se encontró ningún usuario con esa Cédula/ID.")
    else:
        st.warning("La base de datos aún no se ha cargado.")

# ==============================================================================
# MÓDULO 5: BASE DE DATOS COMPLETA
# ==============================================================================
elif menu == "📋 Base de Datos Completa":
    st.subheader("📋 Base de Datos Completa")
    
    if not df_lideres.empty:
        filtro = st.text_input("🔎 Buscar o filtrar registros en la tabla:", placeholder="Escriba un nombre, cédula, dependencia, etc...")
        
        if filtro.strip():
            mask = df_lideres.astype(str).apply(lambda row: row.str.contains(filtro.strip(), case=False, na=False)).any(axis=1)
            df_mostrar = df_lideres[mask]
            st.caption(f"Mostrando **{len(df_mostrar)}** de **{len(df_lideres)}** registros encontrados.")
        else:
            df_mostrar = df_lideres
            st.caption(f"Total de registros: **{len(df_lideres)}**")
            
        st.dataframe(df_mostrar, use_container_width=True)
        
        csv_bytes = df_mostrar.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Vista Actual a CSV",
            data=csv_bytes,
            file_name="Base_Datos_Lideres_Filtrada.csv",
            mime="text/csv"
        )
    else:
        st.warning("La base de datos está vacía o no se ha podido cargar.")
