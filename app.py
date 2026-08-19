import streamlit as st
import pandas as pd
import unicodedata
from datetime import datetime, date
import io
import plotly.express as px
import gspread

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
# ESTILO Y TEMA VISUAL
# ------------------------------------------------------------------------------
st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC !important; }
    .stApp p, .stApp span, .stApp label, .stApp div, .stApp caption, .stMarkdown { color: #1E293B !important; }
    h1, h2, h3, h4, h5, h6 { color: #0F172A !important; font-weight: 700 !important; }
    
    [data-testid="stSidebar"] { background-color: #0F172A !important; }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span { color: #FFFFFF !important; }
    [data-testid="stSidebar"] .stButton > button { background-color: #1E293B !important; color: #FFFFFF !important; border: 1px solid #334155 !important; border-radius: 8px !important; }
    [data-testid="stSidebar"] .stButton > button:hover { background-color: #F59E0B !important; border-color: #D97706 !important; color: #FFFFFF !important; }
    
    [data-testid="stVerticalBlock"] > div[data-testid="stBlock"], div[data-testid="stForm"], .stCard { 
        background-color: #FFFFFF !important; 
        border-radius: 12px !important; 
        padding: 18px !important; 
        border: 1px solid #E2E8F0 !important; 
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.03) !important; 
    }
    
    [data-testid="stMetricValue"] { color: #0F172A !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] p { color: #475569 !important; font-weight: 700 !important; }
    
    div.stDownloadButton > button, 
    div.stButton > button, 
    div[data-testid="stLinkButton"] > a {
        background-color: #1E3A8A !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 8px 16px !important;
        box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.08) !important;
        transition: all 0.2s ease-in-out !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-decoration: none !important;
        width: auto !important;
    }
    
    div.stDownloadButton > button:hover, 
    div.stButton > button:hover, 
    div[data-testid="stLinkButton"] > a:hover {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.12) !important;
        transform: translateY(-1px);
        text-decoration: none !important;
    }
    
    div.stDownloadButton > button p, 
    div.stButton > button p, 
    div[data-testid="stLinkButton"] > a p,
    div[data-testid="stLinkButton"] > a span {
        color: #FFFFFF !important;
        margin: 0 !important;
    }

    input { color: #0F172A !important; background-color: #FFFFFF !important; border: 1px solid #CBD5E1 !important; }
    </style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 1. SISTEMA DE LOGIN Y AUTENTICACIÓN (EVALUADO ANTES DE CUALQUIER CARGA)
# ------------------------------------------------------------------------------
def verificar_login():
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

if not verificar_login():
    st.stop()

# ------------------------------------------------------------------------------
# CONEXIÓN CON GOOGLE SHEETS VÍA GSPREAD
# ------------------------------------------------------------------------------
SHEET_ID = "114059SazWnhrk9vUc12Qdyy4eP6EP6lUI_SLj-inGXA"

@st.cache_resource
def conectar_google_sheets():
    """Conecta con la API de Google Sheets directamente a la pestaña 'Base de datos Lideres'."""
    try:
        credenciales = dict(st.secrets["gcp_service_account"])
        client = gspread.service_account_from_dict(credenciales)
        
        try:
            sheet = client.open_by_key(SHEET_ID).worksheet("Base de datos Lideres")
        except Exception:
            sheet = client.open_by_key(SHEET_ID).get_worksheet(0)
            
        return sheet
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Google Sheets API: {e}")
        return None

def actualizar_hoja_gspread(sheet, range_name, values):
    """Función de compatibilidad para actualizar celdas en gspread v5 y v6+."""
    try:
        sheet.update(range_name=range_name, values=values)
    except TypeError:
        sheet.update(range_name, values)

def cargar_datos():
    """Carga y reestructura las columnas procesando adecuadamente el encabezado."""
    sheet = conectar_google_sheets()
    if sheet:
        try:
            data = sheet.get_all_values()
            if not data or len(data) < 2:
                st.session_state.header_offset = 1
                return pd.DataFrame()
            
            fila_1 = [str(c).strip() for c in data[0]]
            fila_2 = [str(c).strip() for c in data[1]] if len(data) > 1 else []

            tiene_encabezado_doble = any("PROYECCI" in c.upper() or "PLANILLA" in c.upper() for c in fila_1)

            if tiene_encabezado_doble and len(data) >= 2:
                headers_crudos = fila_2
                data_rows = data[2:]
                st.session_state.header_offset = 2  # 2 filas de encabezado
            else:
                headers_crudos = fila_1
                data_rows = data[1:]
                st.session_state.header_offset = 1  # 1 fila de encabezado

            nombres_mapeados = []
            vistos = {}

            for idx, raw_h in enumerate(headers_crudos):
                h_clean = raw_h.strip()
                
                if not h_clean or h_clean.lower().startswith("columna_") or h_clean.lower().startswith("unnamed"):
                    nombres_sugeridos = [
                        "Nombres", "Apellidos", "Cédula / Identificación", "Dependencia", 
                        "Secretaría", "Cargo Actual", "Profesión", "Teléfono / Celular", 
                        "Correo Electrónico", "Comuna", "Barrio", "Día Cumpleaños", 
                        "Mes Cumpleaños", "Proyección", "Registros", "Municipio", 
                        "Notas", "No. Amigos", "Municipio / Bello", "Otros Municipios / Deptos", 
                        "No está en Censo", "Cédula Errónea", "URL Planilla PDF"
                    ]
                    if idx < len(nombres_sugeridos):
                        h_clean = nombres_sugeridos[idx]
                    else:
                        h_clean = f"Campo Adicional {idx + 1}"

                if h_clean in vistos:
                    vistos[h_clean] += 1
                    nombre_final = f"{h_clean} ({vistos[h_clean]})"
                else:
                    vistos[h_clean] = 0
                    nombre_final = h_clean

                nombres_mapeados.append(nombre_final)

            num_cols = len(nombres_mapeados)
            filas_limpias = []
            for row in data_rows:
                if len(row) < num_cols:
                    row = row + [""] * (num_cols - len(row))
                else:
                    row = row[:num_cols]
                filas_limpias.append(row)

            df = pd.DataFrame(filas_limpias, columns=nombres_mapeados).astype(str)
            
            for col in df.columns:
                df[col] = df[col].str.replace(".0", "", regex=False)
                df[col] = df[col].replace(["nan", "None", "<NA>", "null"], "")
                df[col] = df[col].str.strip()

            return df
        except Exception as e:
            st.error(f"Error al procesar y ordenar la estructura de la hoja: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

if "df_lideres" not in st.session_state or st.session_state.df_lideres.empty:
    st.session_state.df_lideres = cargar_datos()

df_lideres = st.session_state.df_lideres

# ------------------------------------------------------------------------------
# FUNCIONES AUXILIARES Y DE EXPORTACIÓN PDF
# ------------------------------------------------------------------------------
NOMBRES_MESES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

def normalizar(texto):
    if not isinstance(texto, str): return ""
    texto = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn').lower().strip()

def obtener_valor_campo(row, df_columns, palabras_clave, default="Sin datos"):
    for key in palabras_clave:
        key_norm = normalizar(key)
        for col in df_columns:
            if key_norm in normalizar(col):
                val = str(row[col]).strip()
                if val and val.lower() not in ["nan", "none", "null", "<na>", ""]:
                    return val
    return default

def obtener_proximos_cumpleanos(df, dias_anticipacion=5):
    if df.empty: return []
    hoy = date.today()
    proximos = []
    col_dia, col_mes = None, None
    
    # Detección precisa de columnas de Día y Mes
    for col in df.columns:
        col_n = normalizar(col)
        if ("dia" in col_n or "day" in col_n) and "mes" not in col_n:
            col_dia = col
        elif ("mes" in col_n or "month" in col_n) and "dia" not in col_n:
            col_mes = col

    # Fallback si no hay nombres específicos
    if not col_dia or not col_mes:
        for col in df.columns:
            col_n = normalizar(col)
            if "cumple" in col_n:
                if not col_dia: col_dia = col
                elif not col_mes: col_mes = col

    if not col_dia or not col_mes:
        return []

    for idx, row in df.iterrows():
        val_dia = str(row[col_dia]).strip()
        val_mes = str(row[col_mes]).strip()
        dia, mes = None, None
        
        if "/" in val_dia or "-" in val_dia:
            partes = val_dia.replace("-", "/").split("/")
            if len(partes) >= 2:
                try: dia, mes = int(partes[0]), int(partes[1])
                except ValueError: continue
        elif val_dia.isdigit() and val_mes.isdigit():
            dia, mes = int(val_dia), int(val_mes)

        if dia and mes and 1 <= dia <= 31 and 1 <= mes <= 12:
            try:
                cumple = date(hoy.year, mes, dia)
                if cumple < hoy: cumple = date(hoy.year + 1, mes, dia)
                diferencia = (cumple - hoy).days
                
                if 0 <= diferencia <= dias_anticipacion:
                    nombres = obtener_valor_campo(row, df.columns, ["nombres", "nombre"], "")
                    apellidos = obtener_valor_campo(row, df.columns, ["apellidos", "apellido"], "")
                    proximos.append({
                        "nombre": f"{nombres} {apellidos}".strip().upper() or "Usuario sin nombre",
                        "dias": diferencia,
                        "fecha_str": f"{dia} de {NOMBRES_MESES.get(mes, '')}",
                        "telefono": obtener_valor_campo(row, df.columns, ["telefono", "celular"]),
                        "dependencia": obtener_valor_campo(row, df.columns, ["dependencia", "secretaria"])
                    })
            except Exception: continue

    proximos.sort(key=lambda x: x["dias"])
    return proximos

def generar_pdf_ficha(row, df_columns):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1E3A8A'), spaceAfter=10)
    subtitle_style = ParagraphStyle('DocSubTitle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#0F172A'), spaceAfter=6)
    
    nombres = obtener_valor_campo(row, df_columns, ["nombres", "nombre"], "")
    apellidos = obtener_valor_campo(row, df_columns, ["apellidos", "apellido"], "")
    nombre_comp = f"{nombres} {apellidos}".strip().upper() or "FICHA DE USUARIO"
    cedula = obtener_valor_campo(row, df_columns, ["identificacion", "cedula", "doc", "id"])
    
    story.append(Paragraph(f"<b>{nombre_comp}</b>", title_style))
    story.append(Paragraph(f"Cédula / ID: <b>{cedula}</b>", subtitle_style))
    story.append(Spacer(1, 12))
    
    data = [[Paragraph("<b>CAMPO</b>", styles['Normal']), Paragraph("<b>DETALLE</b>", styles['Normal'])]]
    for col in df_columns:
        val = str(row[col]).strip()
        data.append([col, val if val and val.lower() not in ["nan", "none", "null", "<na>"] else "Sin datos"])
    
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
# SECCIÓN SUPERIOR: CUMPLEAÑOS
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
                    if c["dias"] == 0: st.markdown("🥳 **¡HOY CUMPLE AÑOS!** 🎉")
                    else: st.markdown(f"🗓️ **En {c['dias']} día(s)** ({c['fecha_str']})")
                    st.markdown(f"**{c['nombre']}**")
                    st.caption(f"🏢 {c['dependencia']}\n\n📞 Tel: {c['telefono']}")
    else:
        st.info("🎈 No hay personas registradas que cumplan años hoy o en los próximos 5 días.")

st.markdown("---")

# ------------------------------------------------------------------------------
# BARRA LATERAL Y MÓDULOS DEL SISTEMA
# ------------------------------------------------------------------------------
st.sidebar.title("Módulos del Sistema")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.rerun()

if st.sidebar.button("🔄 Recargar datos de Google Drive", use_container_width=True):
    st.cache_resource.clear()
    st.session_state.df_lideres = cargar_datos()
    st.sidebar.success("✅ ¡Base de datos recargada desde la nube!")
    st.rerun()

menu = st.sidebar.radio(
    "Seleccione una opción:",
    [
        "🔍 Consulta Detallada",
        "📈 Panel de Control Ejecutivos",
        "➕ Registro de Nuevo Usuario",
        "✏️ Editar / Modificar Registros",
        "📋 Base de Datos Completa (Edición Directa)"
    ]
)

# ==============================================================================
# MÓDULO 1: CONSULTA DETALLADA
# ==============================================================================
if menu == "🔍 Consulta Detallada":
    st.subheader("🔍 Consulta Detallada de Líderes")
    if not df_lideres.empty:
        criterio = st.radio("Buscar por:", ["Todos los campos", "Cédula / Identificación", "Nombre / Apellido"], horizontal=True)
        resultado = pd.DataFrame()
        
        busqueda = st.text_input("Ingrese término de búsqueda:")
        if busqueda.strip():
            term = busqueda.strip().lower()
            
            if criterio == "Cédula / Identificación":
                cols_target = [c for c in df_lideres.columns if any(k in normalizar(c) for k in ["cedula", "identificacion", "doc", "id"])]
            elif criterio == "Nombre / Apellido":
                cols_target = [c for c in df_lideres.columns if any(k in normalizar(c) for k in ["nombre", "apellido"])]
            else:
                cols_target = df_lideres.columns.tolist()

            if not cols_target:
                cols_target = df_lideres.columns.tolist()

            mask = df_lideres[cols_target].astype(str).apply(lambda row: row.str.contains(term, case=False, na=False)).any(axis=1)
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
                    col_header1, col_header2 = st.columns([4, 1.2])
                    with col_header1:
                        st.markdown(f"## **{nombre_completo.upper()}**")
                        st.markdown(f"**Cédula / Identificación:** {cedula} | **Dependencia:** {dependencia}")
                    with col_header2:
                        pdf_file = generar_pdf_ficha(row, df_lideres.columns)
                        st.download_button(
                            label="📄 Descargar Ficha PDF",
                            data=pdf_file,
                            file_name=f"Ficha_{cedula}.pdf",
                            mime="application/pdf",
                            use_container_width=False
                        )

                    st.markdown("<br>", unsafe_allow_html=True)

                    info_laboral = []
                    contacto_directo = []
                    ubicacion_fechas = []
                    url_pdf_encontrado = None

                    kw_laboral = ["dependencia", "secretaria", "cargo", "profesion", "empresa", "puesto", "sector", "labor", "contrato", "area", "proyeccion", "registro", "nota"]
                    kw_contacto = ["telefono", "celular", "correo", "email", "redes", "whatsapp", "contacto", "movil", "amigos", "link", "url"]
                    kw_ubicacion = ["comuna", "barrio", "municipio", "direccion", "fecha", "cumple", "nacimiento", "mes", "dia", "ubicacion", "zona", "bello", "deptos", "censo"]

                    cols_omitir = [
                        col for col in df_lideres.columns 
                        if normalizar(col) in ["nombre", "nombres", "apellido", "apellidos", "cedula", "identificacion", "doc", "id"]
                    ]

                    for col in df_lideres.columns:
                        if col in cols_omitir:
                            continue
                            
                        val = str(row[col]).strip()
                        if not val or val.lower() in ["nan", "none", "null", "<na>"]:
                            val = "Sin datos"

                        col_norm = normalizar(col)

                        if ("pdf" in col_norm or "url" in col_norm or "planilla" in col_norm) and val.startswith("http"):
                            url_pdf_encontrado = val

                        if any(kw in col_norm for kw in kw_laboral):
                            info_laboral.append((col, val))
                        elif any(kw in col_norm for kw in kw_contacto):
                            contacto_directo.append((col, val))
                        elif any(kw in col_norm for kw in kw_ubicacion):
                            ubicacion_fechas.append((col, val))
                        else:
                            lens = [len(info_laboral), len(contacto_directo), len(ubicacion_fechas)]
                            min_idx = lens.index(min(lens))
                            if min_idx == 0: info_laboral.append((col, val))
                            elif min_idx == 1: contacto_directo.append((col, val))
                            else: ubicacion_fechas.append((col, val))

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown("### 📌 **Información Laboral**")
                        for label, val in info_laboral:
                            st.markdown(f"**{label}:** {val}")

                    with col2:
                        st.markdown("### 📞 **Contacto Directo**")
                        for label, val in contacto_directo:
                            if val.startswith("http://") or val.startswith("https://"):
                                st.markdown(f"**{label}:** [{val}]({val})")
                            elif "@" in val and "." in val:
                                st.markdown(f"**{label}:** [{val}](mailto:{val})")
                            else:
                                st.markdown(f"**{label}:** {val}")

                    with col3:
                        st.markdown("### 📍 **Ubicación y Fechas**")
                        for label, val in ubicacion_fechas:
                            st.markdown(f"**{label}:** {val}")

                    if url_pdf_encontrado:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.link_button("🔗 Abrir PDF Planilla", url_pdf_encontrado, use_container_width=False)

                st.markdown("---")
        elif busqueda:
            st.warning("⚠️ No se localizó ningún registro con el término especificado.")

# ==============================================================================
# MÓDULO 2: PANEL DE CONTROL EJECUTIVOS
# ==============================================================================
elif menu == "📈 Panel de Control Ejecutivos":
    st.subheader("📈 Panel de Control Ejecutivo y Métricas Analíticas")
    if not df_lideres.empty:
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        col_amigos = [c for c in df_lideres.columns if "AMIGOS" in c.upper()]
        total_amigos = pd.to_numeric(df_lideres[col_amigos[0]], errors='coerce').fillna(0).sum() if col_amigos else 0
        col_muni = [c for c in df_lideres.columns if "MUNICIPIO" in c.upper()]
        total_municipios = df_lideres[col_muni[0]].nunique() if col_muni else 0

        kpi1.metric("👥 Total Líderes", len(df_lideres))
        kpi2.metric("📊 Total Registros Amigos", int(total_amigos))
        kpi3.metric("📍 Municipios Cubiertos", total_municipios)
        kpi4.metric("🟢 Estado Conexión", "Sincronizado vía API")
        st.markdown("---")

        # Gráficos Analíticos
        col_g1, col_g2 = st.columns(2)
        
        # Gráfico 1: Líderes por Dependencia/Secretaría o Comuna
        col_dep = [c for c in df_lideres.columns if any(k in normalizar(c) for k in ["dependencia", "secretaria", "comuna", "barrio"])]
        if col_dep:
            target_col = col_dep[0]
            conteo_dep = df_lideres[target_col].replace("", "Sin Especificar").value_counts().head(10).reset_index()
            conteo_dep.columns = [target_col, "Cantidad"]
            
            fig1 = px.bar(
                conteo_dep, x=target_col, y="Cantidad",
                title=f"Distribución de Líderes por {target_col}",
                color="Cantidad", color_continuous_scale="Blues"
            )
            fig1.update_layout(xaxis_title="", yaxis_title="Líderes", template="plotly_white")
            col_g1.plotly_chart(fig1, use_container_width=True)

        # Gráfico 2: Top Líderes con más Amigos/Registros
        if col_amigos:
            amigos_col = col_amigos[0]
            col_nombres = [c for c in df_lideres.columns if "NOMBRE" in c.upper()]
            nom_col = col_nombres[0] if col_nombres else df_lideres.columns[0]
            
            df_temp = df_lideres.copy()
            df_temp["Amigos_Num"] = pd.to_numeric(df_temp[amigos_col], errors='coerce').fillna(0)
            top_lideres = df_temp.sort_values(by="Amigos_Num", ascending=False).head(10)
            
            fig2 = px.bar(
                top_lideres, x=nom_col, y="Amigos_Num",
                title="Top 10 Líderes por Número de Registros / Amigos",
                color="Amigos_Num", color_continuous_scale="Oranges"
            )
            fig2.update_layout(xaxis_title="Líder", yaxis_title="N° Amigos", template="plotly_white")
            col_g2.plotly_chart(fig2, use_container_width=True)

# ==============================================================================
# MÓDULO 3: REGISTRO DE NUEVO USUARIO
# ==============================================================================
elif menu == "➕ Registro de Nuevo Usuario":
    st.subheader("➕ Registro de Nuevo Usuario")
    if not df_lideres.empty:
        st.info("Los datos ingresados se guardarán automáticamente en la nube (Google Sheets).")
        with st.form("form_nuevo_usuario", clear_on_submit=True):
            datos_nuevos = {}
            cols = list(df_lideres.columns)
            c_a, c_b = st.columns(2)
            for idx, col_name in enumerate(cols):
                if idx % 2 == 0:
                    datos_nuevos[col_name] = c_a.text_input(f"{col_name}:")
                else:
                    datos_nuevos[col_name] = c_b.text_input(f"{col_name}:")
                    
            guardar = st.form_submit_button("➕ Registrar y Guardar en Nube")
            
            if guardar:
                sheet = conectar_google_sheets()
                if sheet:
                    nueva_fila = [str(datos_nuevos.get(col, "")) for col in cols]
                    sheet.append_row(nueva_fila)
                    
                    nuevo_row = pd.DataFrame([datos_nuevos]).astype(str)
                    st.session_state.df_lideres = pd.concat([st.session_state.df_lideres, nuevo_row], ignore_index=True)
                    
                    st.success("✅ Usuario registrado exitosamente en Google Sheets y sincronizado.")
                    st.rerun()

# ==============================================================================
# MÓDULO 4: EDITAR / MODIFICAR REGISTROS
# ==============================================================================
elif menu == "✏️ Editar / Modificar Registros":
    st.title("✏️ Edición Formulario Individual de Usuarios")
    st.caption("Los cambios guardados reemplazarán directamente la fila correspondiente en Google Sheets.")
    
    if not df_lideres.empty:
        cedula_buscar = st.text_input("Ingrese la Cédula/ID del usuario a editar:", placeholder="Ej: 3474244")
        
        if cedula_buscar.strip():
            mask = df_lideres.astype(str).apply(lambda row: row.str.contains(cedula_buscar.strip(), case=False, na=False)).any(axis=1)
            idx_match = df_lideres[mask].index

            if len(idx_match) > 0:
                user_idx = idx_match[0]
                usuario_data = df_lideres.loc[user_idx]
                
                st.success(f"👤 Usuario localizado (Índice #{user_idx + 1}). Modifique los campos necesarios:")
                
                with st.form("form_editar_usuario"):
                    nuevos_datos = {}
                    cols = list(df_lideres.columns)
                    c_a, c_b = st.columns(2)
                    for idx, col_name in enumerate(cols):
                        val_actual = str(usuario_data[col_name]) if pd.notna(usuario_data[col_name]) else ""
                        if idx % 2 == 0:
                            nuevos_datos[col_name] = c_a.text_input(f"{col_name}:", value=val_actual)
                        else:
                            nuevos_datos[col_name] = c_b.text_input(f"{col_name}:", value=val_actual)
                    
                    btn_guardar_cambios = st.form_submit_button("💾 Guardar Cambios en la Nube")
                    
                    if btn_guardar_cambios:
                        sheet = conectar_google_sheets()
                        if sheet:
                            # Cálculo dinámico de fila según el número de encabezados detectados
                            offset = st.session_state.get("header_offset", 1)
                            num_fila_sheet = user_idx + offset + 1
                            valores_actualizados = [str(nuevos_datos.get(col, "")) for col in cols]
                            
                            actualizar_hoja_gspread(sheet, f"A{num_fila_sheet}", [valores_actualizados])
                            
                            for col_name, val_nuevo in nuevos_datos.items():
                                st.session_state.df_lideres.at[user_idx, col_name] = val_nuevo
                            
                            st.success(f"✅ Fila #{num_fila_sheet} actualizada correctamente en Google Sheets.")
                            st.rerun()
            else:
                st.warning("⚠️ No se encontró ningún registro con la cédula ingresada.")

# ==============================================================================
# MÓDULO 5: BASE DE DATOS COMPLETA
# ==============================================================================
elif menu == "📋 Base de Datos Completa (Edición Directa)":
    st.subheader("📋 Base de Datos Completa (Edición Directa Tipo Excel)")
    st.caption("✏️ Puedes modificar celdas, agregar nuevas filas (+) o eliminar registros directamente en la tabla.")
    
    if not df_lideres.empty:
        filtro_tabla = st.text_input("🔎 Filtrar registros en la vista general:", placeholder="Escriba para buscar...")
        
        df_editable = df_lideres.copy()
        if filtro_tabla.strip():
            mask = df_editable.astype(str).apply(lambda row: row.str.contains(filtro_tabla.strip(), case=False, na=False)).any(axis=1)
            df_editable = df_editable[mask]

        df_modificado = st.data_editor(
            df_editable,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="editor_tabla_lideres"
        )
        
        col_btn1, col_btn2 = st.columns([2, 2])
        
        with col_btn1:
            if st.button("💾 Guardar Cambios en Google Sheets", use_container_width=False):
                with st.spinner("Guardando y actualizando base de datos en Google Sheets..."):
                    sheet = conectar_google_sheets()
                    if sheet:
                        # 1. Aplicar cambios respetando los datos no visibles si había un filtro
                        if filtro_tabla.strip():
                            st.session_state.df_lideres.update(df_modificado)
                            df_para_guardar = st.session_state.df_lideres.fillna("").astype(str)
                        else:
                            st.session_state.df_lideres = df_modificado.fillna("").astype(str)
                            df_para_guardar = st.session_state.df_lideres

                        # 2. Reescritura segura en Google Sheets
                        sheet.clear()
                        encabezados = df_para_guardar.columns.tolist()
                        filas = df_para_guardar.values.tolist()
                        
                        actualizar_hoja_gspread(sheet, "A1", [encabezados] + filas)
                        st.session_state.header_offset = 1 # Estructura unificada a 1 sola fila de encabezado
                        
                        st.success("✅ ¡Todos los cambios se guardaron en Google Sheets sin pérdida de datos!")
                        st.rerun()

        with col_btn2:
            csv_data = df_modificado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Vista Actual en CSV",
                data=csv_data,
                file_name=f"Base_Lideres_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=False
            )
