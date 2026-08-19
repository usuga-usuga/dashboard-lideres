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
# CONEXIÓN CON GOOGLE SHEETS VÍA GSPREAD
# ------------------------------------------------------------------------------
SHEET_ID = "114059SazWnhrk9vUc12Qdyy4eP6EP6lUI_SLj-inGXA"

@st.cache_resource
def conectar_google_sheets():
    """Conecta con la API de Google Sheets usando las credenciales de Streamlit Secrets."""
    try:
        credenciales = dict(st.secrets["gcp_service_account"])
        client = gspread.service_account_from_dict(credenciales)
        sheet = client.open_by_key(SHEET_ID).get_worksheet(0)
        return sheet
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Google Sheets API: {e}")
        return None

def cargar_datos():
    """Lee todos los registros de Google Sheets en un DataFrame."""
    sheet = conectar_google_sheets()
    if sheet:
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data).astype(str)
            df = df.fillna("")
            for col in df.columns:
                df[col] = df[col].str.replace(".0", "", regex=False)
                df[col] = df[col].replace(["nan", "None", "<NA>"], "")
            return df
        except Exception as e:
            st.error(f"Error al procesar los datos de la hoja: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# Guardar o recargar la base de datos en Session State
if "df_lideres" not in st.session_state or st.session_state.df_lideres.empty:
    st.session_state.df_lideres = cargar_datos()

df_lideres = st.session_state.df_lideres

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

if not verificar_login():
    st.stop()

# ------------------------------------------------------------------------------
# ESTILO Y TEMA VISUAL CON ALTO CONTRASTE
# ------------------------------------------------------------------------------
st.markdown("""
    <style>
    .stApp { background-color: #F3F4F8 !important; }
    .stApp p, .stApp span, .stApp label, .stApp div, .stApp caption, .stMarkdown { color: #1E293B !important; }
    h1, h2, h3, h4, h5, h6 { color: #0F172A !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] { background-color: #11223F !important; }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span { color: #FFFFFF !important; }
    [data-testid="stSidebar"] .stButton > button { background-color: #1A365D !important; color: #FFFFFF !important; border: 1px solid #2B6CB0 !important; border-radius: 8px !important; }
    [data-testid="stSidebar"] .stButton > button:hover { background-color: #F59E0B !important; border-color: #D97706 !important; color: #FFFFFF !important; }
    [data-testid="stVerticalBlock"] > div[data-testid="stBlock"], div[data-testid="stForm"], .stCard { background-color: #FFFFFF !important; border-radius: 12px !important; padding: 16px !important; border: 1px solid #E2E8F0 !important; box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.05) !important; }
    [data-testid="stMetricValue"] { color: #0F172A !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] p { color: #334155 !important; font-weight: 700 !important; }
    .stButton > button { background-color: #F59E0B !important; color: #FFFFFF !important; font-weight: 700 !important; border-radius: 8px !important; border: none !important; }
    .stButton > button:hover { background-color: #D97706 !important; color: #FFFFFF !important; }
    .stDownloadButton > button { background-color: #11223F !important; color: #FFFFFF !important; font-weight: 600 !important; border-radius: 8px !important; }
    .stDownloadButton > button:hover { background-color: #F59E0B !important; color: #FFFFFF !important; }
    input { color: #0F172A !important; background-color: #F8FAFC !important; border: 1px solid #CBD5E1 !important; }
    </style>
""", unsafe_allow_html=True)

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

def obtener_fecha_cumpleanos_formateada(row, df_columns):
    col_dia, col_mes = None, None
    for col in df_columns:
        col_n = normalizar(col)
        if "fecha de cumple" in col_n or col_n in ["dia", "day"]: col_dia = col
        elif "unnamed: 12" in col_n or col_n in ["mes", "month"]: col_mes = col
            
    val_dia = str(row[col_dia]).strip() if col_dia and col_dia in row else ""
    val_mes = str(row[col_mes]).strip() if col_mes and col_mes in row else ""
    
    if "/" in val_dia or "-" in val_dia:
        partes = val_dia.replace("-", "/").split("/")
        if len(partes) >= 2:
            try:
                d, m = int(partes[0]), int(partes[1])
                if 1 <= d <= 31 and 1 <= m <= 12:
                    return f"{d} de {NOMBRES_MESES[m]}"
            except ValueError: pass

    if val_dia.isdigit() and val_mes.isdigit():
        d, m = int(val_dia), int(val_mes)
        if 1 <= d <= 31 and 1 <= m <= 12:
            return f"{d} de {NOMBRES_MESES[m]}"
            
    return val_dia or "Sin datos"

def obtener_proximos_cumpleanos(df, dias_anticipacion=5):
    if df.empty: return []
    hoy = date.today()
    proximos = []
    col_dia, col_mes = None, None
    
    for col in df.columns:
        col_n = normalizar(col)
        if "fecha de cumple" in col_n or col_n in ["dia", "day"]: col_dia = col
        elif "unnamed: 12" in col_n or col_n in ["mes", "month"]: col_mes = col

    for idx, row in df.iterrows():
        val_dia = str(row[col_dia]).strip() if col_dia else ""
        val_mes = str(row[col_mes]).strip() if col_mes else ""
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
                        "fecha_str": f"{dia} de {NOMBRES_MESES[mes]}",
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
        ["Fecha Cumpleaños", obtener_fecha_cumpleanos_formateada(row, df_columns)],
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
        criterio = st.radio("Buscar por:", ["Cédula / Identificación", "Nombre / Apellido"], horizontal=True)
        resultado = pd.DataFrame()
        
        busqueda = st.text_input("Ingrese término de búsqueda:")
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
                    # Cabecera con nombre y botón PDF
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

                    # --- Fila 1 de Información ---
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        with st.container(border=True):
                            st.markdown("### 📌 Información Laboral")
                            st.markdown(f"**Dependencia:** {dependencia}")
                            st.markdown(f"**Secretaría:** {obtener_valor_campo(row, df_lideres.columns, ['secretaria', 'sec'])}")
                            st.markdown(f"**Cargo Actual:** {obtener_valor_campo(row, df_lideres.columns, ['cargo', 'puesto'])}")
                            st.markdown(f"**Profesión:** {obtener_valor_campo(row, df_lideres.columns, ['profesion', 'oficio'])}")
                            st.markdown(f"**Líder / Apoyo:** {obtener_valor_campo(row, df_lideres.columns, ['lider', 'apoyo', 'rol'])}")

                    with col2:
                        with st.container(border=True):
                            st.markdown("### 📞 Contacto Directo")
                            st.markdown(f"**Teléfono / Celular:** {obtener_valor_campo(row, df_lideres.columns, ['telefono', 'celular', 'tel'])}")
                            correo = obtener_valor_campo(row, df_lideres.columns, ['correo', 'email', 'mail'])
                            st.markdown(f"**Correo:** [{correo}](mailto:{correo})" if correo != "Sin datos" else "**Correo:** Sin datos")
                            st.markdown(f"**Redes Sociales:** {obtener_valor_campo(row, df_lideres.columns, ['redes', 'redes sociales', 'instagram', 'facebook'])}")

                    with col3:
                        with st.container(border=True):
                            st.markdown("### 📍 Ubicación y Fechas")
                            st.markdown(f"**Municipio:** {obtener_valor_campo(row, df_lideres.columns, ['municipio', 'ciudad'])}")
                            st.markdown(f"**Comuna:** {obtener_valor_campo(row, df_lideres.columns, ['comuna'])}")
                            st.markdown(f"**Barrio:** {obtener_valor_campo(row, df_lideres.columns, ['barrio'])}")
                            st.markdown(f"**Cumpleaños:** {obtener_fecha_cumpleanos_formateada(row, df_lideres.columns)}")

                    # --- Fila 2: Proyección y Votación / Planillas ---
                    col4, col5 = st.columns(2)
                    with col4:
                        with st.container(border=True):
                            st.markdown("### 📌 Proyección y Notas")
                            st.markdown(f"**Proyección:** {obtener_valor_campo(row, df_lideres.columns, ['proyeccion'])}")
                            st.markdown(f"**Registros:** {obtener_valor_campo(row, df_lideres.columns, ['registros'])}")
                            st.markdown(f"**Notas / Observaciones:** {obtener_valor_campo(row, df_lideres.columns, ['notas', 'observaciones', 'observacion'])}")

                    with col5:
                        with st.container(border=True):
                            st.markdown("### 📋 Planillas y Registros")
                            st.markdown(f"**No. Amigos:** {obtener_valor_campo(row, df_lideres.columns, ['amigos', 'no. amigos', 'nro amigos'], '0')}")
                            st.markdown(f"**Municipio de Bello:** {obtener_valor_campo(row, df_lideres.columns, ['bello', 'municipio de bello'])}")
                            st.markdown(f"**Otros Municipios:** {obtener_valor_campo(row, df_lideres.columns, ['otros municipios', 'otros'])}")

                    # Botón de enlace PDF (si existe)
                    url_pdf_val = obtener_valor_campo(row, df_lideres.columns, ['url_pdf', 'pdf', 'link', 'planilla'], "Sin datos")
                    if url_pdf_val != "Sin datos" and url_pdf_val.startswith("http"):
                        st.link_button("🔗 Abrir PDF Planilla", url_pdf_val, use_container_width=True)

                st.markdown("---")
        elif busqueda:
            st.warning("⚠️ No se localizó ningún registro.")

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

# ==============================================================================
# MÓDULO 3: REGISTRO DE NUEVO USUARIO (CON ESCRITURA EN GOOGLE SHEETS)
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
# MÓDULO 4: EDITAR / MODIFICAR REGISTROS (FORMULARIO INDIVIDUAL)
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
                
                st.success(f"👤 Usuario localizado (Fila #{user_idx + 1}). Modifique los campos necesarios:")
                
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
                            num_fila_sheet = user_idx + 2
                            valores_actualizados = [str(nuevos_datos.get(col, "")) for col in cols]
                            
                            sheet.update(range_name=f"A{num_fila_sheet}", values=[valores_actualizados])
                            
                            for col_name, val_nuevo in nuevos_datos.items():
                                st.session_state.df_lideres.at[user_idx, col_name] = val_nuevo
                            
                            st.success(f"✅ Fila #{num_fila_sheet} actualizada correctamente en Google Sheets.")
                            st.rerun()
            else:
                st.warning("⚠️ No se encontró ningún registro con la cédula ingresada.")

# ==============================================================================
# MÓDULO 5: BASE DE DATOS COMPLETA (EDICIÓN DIRECTA TIPO EXCEL + GUARDAR CAMBIOS)
# ==============================================================================
elif menu == "📋 Base de Datos Completa (Edición Directa)":
    st.subheader("📋 Base de Datos Completa (Edición Directa Tipo Excel)")
    st.caption("✏️ Puedes modificar celdas, agregar nuevas filas (+) o eliminar registros directamente en la tabla. Haz clic en 'Guardar Cambios' para sincronizar con Google Sheets.")
    
    if not df_lideres.empty:
        # Filtro rápido
        filtro_tabla = st.text_input("🔎 Filtrar registros en la vista general:", placeholder="Escriba para buscar...")
        
        df_editable = df_lideres.copy()
        if filtro_tabla.strip():
            mask = df_editable.astype(str).apply(lambda row: row.str.contains(filtro_tabla.strip(), case=False, na=False)).any(axis=1)
            df_editable = df_editable[mask]

        # Tabla Interactiva editable
        df_modificado = st.data_editor(
            df_editable,
            num_rows="dynamic",        # Permite agregar (+) y eliminar filas
            use_container_width=True,
            hide_index=True,
            key="editor_tabla_lideres"
        )
        
        col_btn1, col_btn2 = st.columns([2, 2])
        
        with col_btn1:
            # BOTÓN DE GUARDADO MASIVO A GOOGLE SHEETS
            if st.button("💾 Guardar Cambios en Google Sheets", use_container_width=True):
                with st.spinner("Guardando y actualizando base de datos en Google Sheets..."):
                    sheet = conectar_google_sheets()
                    if sheet:
                        df_para_guardar = df_modificado.fillna("").astype(str)
                        
                        # 1. Limpiar hoja en Google Sheets
                        sheet.clear()
                        
                        # 2. Reconstruir lista de datos
                        encabezados = df_para_guardar.columns.tolist()
                        filas = df_para_guardar.values.tolist()
                        
                        # 3. Reescribir tabla completa con parámetros nombrados compatibles
                        sheet.update(range_name="A1", values=[encabezados] + filas)
                        
                        # 4. Actualizar session state local
                        st.session_state.df_lideres = df_para_guardar
                        
                        st.success("✅ ¡Todos los cambios se guardaron exitosamente en Google Sheets!")
                        st.rerun()

        with col_btn2:
            # BOTÓN DE DESCARGA EN CSV
            csv_data = df_modificado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Vista Actual en CSV",
                data=csv_data,
                file_name=f"Base_Lideres_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.info("No hay datos cargados para mostrar.")
