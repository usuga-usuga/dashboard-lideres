import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import hmac
import re
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# CONFIGURACIÓN GENERAL Y ESTILOS DE LA APP
# ==========================================
st.set_page_config(
    page_title="Gestión de Líderes y Contactos",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .stMetric { background-color: #f8f9fa; padding: 12px; border-radius: 8px; border: 1px solid #e9ecef; }
    div[data-testid="stForm"] { border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# ESTRUCTURA EXACTA DE COLUMNAS DE LA HOJA (27)
# ==========================================
COLUMNAS = [
    "No. Identificacion",         # Col 1 (A)
    "Nombres",                    # Col 2 (B)
    "Apellidos",                  # Col 3 (C)
    "No. Telefono",               # Col 4 (D)
    "Dependencia",                # Col 5 (E)
    "Secretaria y/o Dependencia", # Col 6 (F)
    "Apoyo",                      # Col 7 (G)
    "Profesion",                  # Col 8 (H)
    "Cargo actual",               # Col 9 (I)
    "Correo Electronico",         # Col 10 (J)
    "Redes Sociales",             # Col 11 (K)
    "Fecha de Cumpleanos",        # Col 12 (L)
    "Comuna",                     # Col 13 (M)
    "Barrio",                     # Col 14 (N)
    "Bello",                      # Col 15 (O)
    "Otros",                      # Col 16 (P)
    "Total",                      # Col 17 (Q)
    "PROYECCION",                 # Col 18 (R)
    "REGISTROS",                  # Col 19 (S)
    "MUNICIPIO PROYECTADO",       # Col 20 (T)
    "NOTAS",                      # Col 21 (U)
    "MUNICIPIO DE BELLO",         # Col 22 (V)
    "OTROS MUNICIPIOS - DEPTOS",  # Col 23 (W)
    "NO ESTA EN EL CENSO",        # Col 24 (X)
    "CEDULA ERRONEA",             # Col 25 (Y)
    "Total No. Amigos",           # Col 26 (Z)
    "URL_PDF"                     # Col 27 (AA)
]

# ==========================================
# AUTENTICACIÓN DE USUARIOS
# ==========================================
def check_password():
    def password_entered():
        user = st.session_state["username"]
        pwd = st.session_state["password"]
        if user in st.secrets.get("usuarios", {}) and hmac.compare_digest(pwd, st.secrets["usuarios"][user]):
            st.session_state["password_correct"] = True
            st.session_state["logged_user"] = user
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔐 Control de Acceso</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Usuario", key="username")
            st.text_input("Contraseña", type="password", key="password")
            st.button("Iniciar Sesión", on_click=password_entered, type="primary", use_container_width=True)
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("<h2 style='text-align: center;'>🔐 Control de Acceso</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Usuario", key="username")
            st.text_input("Contraseña", type="password", key="password")
            st.button("Iniciar Sesión", on_click=password_entered, type="primary", use_container_width=True)
            st.error("😕 Usuario o contraseña incorrectos.")
        return False
    return True

if not check_password():
    st.stop()

# ==========================================
# CONEXIÓN A GOOGLE SHEETS
# ==========================================
@st.cache_resource(ttl=300)
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_worksheet():
    client = get_gspread_client()
    if "spreadsheet_id" in st.secrets and st.secrets["spreadsheet_id"].strip():
        sheet_id = st.secrets["spreadsheet_id"].strip()
        return client.open_by_key(sheet_id).sheet1

    sheet_name = st.secrets.get("spreadsheet_title", "Base Datos LIDERES")
    return client.open(sheet_name).sheet1

# ==========================================
# LIMPIEZA Y BARRIDO INTEGRAL DE DATOS
# ==========================================
def limpiar_valor(val):
    if pd.isna(val) or val is None:
        return ""
    val_str = str(val).strip()
    if val_str.lower() in ["nan", "none", "null", "<na>"]:
        return ""
    if val_str.endswith(".0"):
        val_str = val_str[:-2]
    return val_str

def valor(row, columna, default="Sin datos"):
    if columna not in row.index:
        return default
    v = limpiar_valor(row[columna])
    return v if v else default

def preparar_df(raw_data):
    if not raw_data or len(raw_data) <= 1:
        return pd.DataFrame(columns=COLUMNAS)

    # Identificar la fila de encabezados reales (busca 'No. Identificacion' en las primeras filas)
    start_idx = 1
    for idx, r in enumerate(raw_data[:5]):
        row_str = [str(cell).strip() for cell in r]
        if "No. Identificacion" in row_str:
            start_idx = idx + 1
            break

    rows = raw_data[start_idx:]
    data = []
    for r in rows:
        # Forzar longitud de 27 columnas
        fila = [r[i] if i < len(r) else "" for i in range(len(COLUMNAS))]
        
        # Descartar filas vacías de cédula
        cedula_val = limpiar_valor(fila[0])
        if cedula_val:
            data.append(fila)

    df = pd.DataFrame(data, columns=COLUMNAS)

    # Limpiar espacios y flotantes
    for col in df.columns:
        df[col] = df[col].apply(limpiar_valor)

    # Convertir métricas numéricas
    cols_num = ["Total No. Amigos", "PROYECCION", "REGISTROS", "Bello", "Otros", "Total", 
                "MUNICIPIO DE BELLO", "OTROS MUNICIPIOS - DEPTOS", "NO ESTA EN EL CENSO", "CEDULA ERRONEA"]
    for col in cols_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    return df

def cargar_datos():
    ws = get_worksheet()
    raw = ws.get_all_values()
    return preparar_df(raw)

if "df_lideres" not in st.session_state:
    with st.spinner("Cargando y procesando la totalidad de los datos de la hoja..."):
        try:
            st.session_state.df_lideres = cargar_datos()
        except Exception as e:
            st.error(f"❌ Error al conectar con Google Sheets: {e}")
            st.stop()

df_lideres = st.session_state.df_lideres

# ==========================================
# GENERADOR DE PDF DE FICHA TÉCNICA
# ==========================================
def generar_pdf_ficha(row):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#1E3A8A'))
    style_subtitle = ParagraphStyle('T2', parent=styles['Normal'], fontSize=10, leading=12, textColor=colors.HexColor('#4B5563'))
    style_sec = ParagraphStyle('Sec', parent=styles['Heading2'], fontSize=12, leading=14, textColor=colors.HexColor('#1E3A8A'), spaceBefore=8, spaceAfter=4)
    style_label = ParagraphStyle('Lbl', parent=styles['Normal'], fontSize=9, leading=11, fontName='Helvetica-Bold')
    style_val = ParagraphStyle('Val', parent=styles['Normal'], fontSize=9, leading=11)

    elements = []
    nombre = f"{valor(row, 'Nombres', '')} {valor(row, 'Apellidos', '')}".strip()
    elements.append(Paragraph(f"<b>{nombre.upper() or 'FICHA TÉCNICA DE LÍDER'}</b>", style_title))
    elements.append(Paragraph(f"Cédula: {valor(row, 'No. Identificacion')} | Dependencia: {valor(row, 'Dependencia')}", style_subtitle))
    elements.append(Spacer(1, 10))

    def make_table(data_dict):
        table_data = []
        for k, v in data_dict.items():
            table_data.append([Paragraph(k, style_label), Paragraph(str(v), style_val)])
        t = Table(table_data, colWidths=[140, 370])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F9FAFB')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        return t

    elements.append(Paragraph("📌 Información Laboral y Profesional", style_sec))
    elements.append(make_table({
        "Dependencia": valor(row, "Dependencia"),
        "Secretaría / Área": valor(row, "Secretaria y/o Dependencia"),
        "Cargo Actual": valor(row, "Cargo actual"),
        "Profesión": valor(row, "Profesion"),
        "Equipo de Apoyo": valor(row, "Apoyo")
    }))

    elements.append(Paragraph("📞 Datos de Contacto y Personales", style_sec))
    elements.append(make_table({
        "Teléfono": valor(row, "No. Telefono"),
        "Correo Electrónico": valor(row, "Correo Electronico"),
        "Fecha Cumpleaños": valor(row, "Fecha de Cumpleanos"),
        "Redes Sociales": valor(row, "Redes Sociales")
    }))

    elements.append(Paragraph("📍 Ubicación y Territorio", style_sec))
    elements.append(make_table({
        "Comuna": valor(row, "Comuna"),
        "Barrio": valor(row, "Barrio"),
        "Municipio Proyectado": valor(row, "MUNICIPIO PROYECTADO")
    }))

    elements.append(Paragraph("📊 Métricas Electoral y Proyección", style_sec))
    elements.append(make_table({
        "Total Amigos / Votos": valor(row, "Total No. Amigos", "0"),
        "Proyección": valor(row, "PROYECCION", "0"),
        "Registros": valor(row, "REGISTROS", "0"),
        "Votos Bello": valor(row, "Bello", "0"),
        "Votos Otros": valor(row, "Otros", "0"),
        "En Censo Bello": valor(row, "MUNICIPIO DE BELLO", "0"),
        "Otros Municipios": valor(row, "OTROS MUNICIPIOS - DEPTOS", "0"),
        "No Censo": valor(row, "NO ESTA EN EL CENSO", "0"),
        "Cédula Errónea": valor(row, "CEDULA ERRONEA", "0"),
        "Notas Adicionales": valor(row, "NOTAS", "Sin notas")
    }))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==========================================
# MENÚ LATERAL Y NAVEGACIÓN
# ==========================================
with st.sidebar:
    st.title("📌 Menú Principal")
    st.write(f"👤 **Usuario:** {st.session_state.get('logged_user', 'Admin')}")

    menu = st.radio(
        "Navegación",
        [
            "📊 Dashboard General",
            "🔍 Consulta Detallada",
            "🎂 Cumpleaños Próximos",
            "➕ Crear Nuevo Registro",
            "✏️ Editar por Cédula",
            "📋 Editor de Tabla Directo"
        ]
    )

    st.markdown("---")
    if st.button("🔄 Recargar datos de Google Sheets", use_container_width=True):
        st.cache_data.clear()
        st.session_state.df_lideres = cargar_datos()
        st.rerun()

    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==========================================
# MÓDULO 1: DASHBOARD GENERAL
# ==========================================
if menu == "📊 Dashboard General":
    st.title("📊 Dashboard General de Líderes")

    if df_lideres.empty:
        st.info("No hay datos para mostrar.")
    else:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Registros", len(df_lideres))
        k2.metric("Total Amigos", int(df_lideres["Total No. Amigos"].sum()))
        k3.metric("Proyección Total", int(df_lideres["PROYECCION"].sum()))
        k4.metric("Total Registrados", int(df_lideres["REGISTROS"].sum()))

        st.markdown("---")
        g1, g2 = st.columns(2)

        with g1:
            st.subheader("Líderes por Dependencia")
            dep_counts = df_lideres["Dependencia"].replace("", "Sin Especificar").value_counts().reset_index()
            dep_counts.columns = ["Dependencia", "Cantidad"]
            fig_dep = px.bar(dep_counts, x="Dependencia", y="Cantidad", text="Cantidad", color="Dependencia")
            st.plotly_chart(fig_dep, use_container_width=True)

        with g2:
            st.subheader("Top 10 Líderes por Red de Amigos")
            df_lideres["Nombre Completo"] = df_lideres["Nombres"] + " " + df_lideres["Apellidos"]
            top_amigos = df_lideres.sort_values(by="Total No. Amigos", ascending=False).head(10)
            fig_top = px.bar(top_amigos, x="Total No. Amigos", y="Nombre Completo", orientation='h', text="Total No. Amigos", color="Total No. Amigos")
            fig_top.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_top, use_container_width=True)

# ==========================================
# MÓDULO 2: CONSULTA DETALLADA
# ==========================================
elif menu == "🔍 Consulta Detallada":
    st.title("🔍 Consulta Detallada de Líderes")
    if df_lideres.empty:
        st.warning("No hay datos disponibles.")
    else:
        criterio = st.radio("Buscar por:", ["Todos los campos", "Cédula / Identificación", "Nombre / Apellido"], horizontal=True)
        busqueda = st.text_input("Ingrese término de búsqueda:")
        resultado = pd.DataFrame()

        if busqueda.strip():
            term = busqueda.strip()
            if criterio == "Cédula / Identificación":
                mask = df_lideres["No. Identificacion"].map(limpiar_valor).str.contains(re.escape(term), case=False, na=False)
            elif criterio == "Nombre / Apellido":
                a = df_lideres["Nombres"].map(limpiar_valor)
                b = df_lideres["Apellidos"].map(limpiar_valor)
                mask = a.str.contains(re.escape(term), case=False, na=False) | b.str.contains(re.escape(term), case=False, na=False)
            else:
                mask = df_lideres.apply(lambda col: col.map(limpiar_valor).str.contains(re.escape(term), case=False, na=False), axis=0).any(axis=1)

            resultado = df_lideres.loc[mask]

        if not resultado.empty:
            st.success(f"✅ Se encontraron {len(resultado)} registro(s).")
            for idx, row in resultado.iterrows():
                nombre = f"{valor(row,'Nombres','')} {valor(row,'Apellidos','')}".strip()
                cedula = valor(row, "No. Identificacion")
                dependencia = valor(row, "Dependencia")

                with st.container(border=True):
                    h1, h2 = st.columns([4, 1.2])
                    with h1:
                        st.markdown(f"## **{nombre.upper() or 'NOMBRE NO REGISTRADO'}**")
                        st.markdown(f"**Cédula / Identificación:** {cedula} | **Dependencia:** {dependencia}")
                    with h2:
                        pdf_file = generar_pdf_ficha(row)
                        safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", cedula)
                        st.download_button("📄 Descargar Ficha PDF", data=pdf_file, file_name=f"Ficha_{safe_id or idx}.pdf", mime="application/pdf", key=f"pdf_{idx}")

                    st.markdown("---")

                    # Fila 1: Datos Principales (Laboral, Contacto, Ubicación)
                    col_lab, col_con, col_ubi = st.columns(3)
                    with col_lab:
                        st.markdown("### 📌 Datos Principales")
                        st.markdown(
                            f"**Dependencia:** {valor(row, 'Dependencia')}\n\n"
                            f"**Secretaría:** {valor(row, 'Secretaria y/o Dependencia')}\n\n"
                            f"**Cargo actual:** {valor(row, 'Cargo actual')}\n\n"
                            f"**Profesión:** {valor(row, 'Profesion')}\n\n"
                            f"**Equipo Apoyo:** {valor(row, 'Apoyo')}"
                        )
                    with col_con:
                        st.markdown("### 📞 Contacto")
                        st.markdown(
                            f"**Teléfono:** {valor(row, 'No. Telefono')}\n\n"
                            f"**Correo:** {valor(row, 'Correo Electronico')}\n\n"
                            f"**Cumpleaños:** {valor(row, 'Fecha de Cumpleanos')}\n\n"
                            f"**Redes Sociales:** {valor(row, 'Redes Sociales')}"
                        )
                    with col_ubi:
                        st.markdown("### 📍 Ubicación")
                        st.markdown(
                            f"**Comuna:** {valor(row, 'Comuna')}\n\n"
                            f"**Barrio:** {valor(row, 'Barrio')}"
                        )

                    st.markdown("---")

                    # Fila 2: Categorías Específicas de la Hoja
                    col_vot, col_proy, col_plan = st.columns(3)
                    
                    with col_vot:
                        st.markdown("### 🗳️ Votantes")
                        st.markdown(
                            f"**Bello:** {valor(row, 'Bello', '0')}\n\n"
                            f"**Otros:** {valor(row, 'Otros', '0')}\n\n"
                            f"**Total:** {valor(row, 'Total', '0')}"
                        )

                    with col_proy:
                        st.markdown("### 📈 Proyección y Notas")
                        st.markdown(
                            f"**Proyección:** {valor(row, 'PROYECCION', '0')}\n\n"
                            f"**Registros:** {valor(row, 'REGISTROS', '0')}\n\n"
                            f"**Municipio Proyectado:** {valor(row, 'MUNICIPIO PROYECTADO')}\n\n"
                            f"**Notas:** {valor(row, 'NOTAS', 'Sin notas')}"
                        )

                    with col_plan:
                        st.markdown("### 📋 Planillas y Registros")
                        st.markdown(
                            f"**Municipio de Bello:** {valor(row, 'MUNICIPIO DE BELLO', '0')}\n\n"
                            f"**Otros Municipios - Deptos:** {valor(row, 'OTROS MUNICIPIOS - DEPTOS', '0')}\n\n"
                            f"**No está en el censo:** {valor(row, 'NO ESTA EN EL CENSO', '0')}\n\n"
                            f"**Cédula Errónea:** {valor(row, 'CEDULA ERRONEA', '0')}\n\n"
                            f"**Total No. Amigos:** {valor(row, 'Total No. Amigos', '0')}"
                        )

                    url = valor(row, "URL_PDF", "")
                    if url.startswith(("http://", "https://")):
                        st.markdown("---")
                        st.link_button("🔗 Abrir PDF Planilla", url)

        elif busqueda.strip():
            st.info("No se encontraron registros que coincidan con la búsqueda.")

# ==========================================
# MÓDULO 3: CUMPLEAÑOS PRÓXIMOS
# ==========================================
elif menu == "🎂 Cumpleaños Próximos":
    st.title("🎂 Cumpleaños Hoy y Próximos 5 Días")
    
    if df_lideres.empty:
        st.info("No hay datos cargados.")
    else:
        hoy = pd.Timestamp.now().date()
        cumples = []

        for idx, row in df_lideres.iterrows():
            f_str = valor(row, "Fecha de Cumpleanos", "")
            if f_str:
                try:
                    dt = pd.to_datetime(f_str, errors='coerce')
                    if pd.notna(dt):
                        cumple_este_ano = dt.date().replace(year=hoy.year)
                        dias_faltantes = (cumple_este_ano - hoy).days
                        if 0 <= dias_faltantes <= 5:
                            cumples.append({
                                "Nombre": f"{valor(row, 'Nombres')} {valor(row, 'Apellidos')}",
                                "Cédula": valor(row, "No. Identificacion"),
                                "Teléfono": valor(row, "No. Telefono"),
                                "Fecha Cumpleaños": dt.strftime('%Y-%m-%d'),
                                "Días Faltantes": "¡HOY! 🎉" if dias_faltantes == 0 else f"En {dias_faltantes} días"
                            })
                except Exception:
                    continue

        if cumples:
            df_cumples = pd.DataFrame(cumples)

            # Función para colorear la fila completa si es ¡HOY! 🎉
            def resaltar_hoy(row):
                if row["Días Faltantes"] == "¡HOY! 🎉":
                    return ['background-color: #B45309; color: #FFFFFF; font-weight: bold;'] * len(row)
                return [''] * len(row)

            # Aplicar estilo a la tabla
            st.dataframe(
                df_cumples.style.apply(resaltar_hoy, axis=1),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("🎈 No hay cumpleaños registrados para hoy o los próximos 5 días.")

# ==========================================
# MÓDULO 4: EDITAR LÍDER
# ==========================================
elif menu == "✏️ Editar Líder":
    st.title("✏️ Editar Información de Líder")
    
    # CSS definitivo para eliminar el contenedor blanco y forzar alto contraste
    st.markdown(
        """
        <style>
        /* 1. Eliminar el fondo blanco forzado del formulario y hacerlo oscuro */
        div[data-testid="stForm"], 
        div[data-testid="stForm"] > div,
        .stForm {
            background-color: #111827 !important;
            border: 1px solid #374151 !important;
            border-radius: 10px !important;
            padding: 20px !important;
        }

        /* 2. Forzar que TODOS los nombres de los campos (labels) sean NEGROS o BLANCOS VISIBLES */
        div[data-testid="stForm"] label,
        div[data-testid="stForm"] label p,
        div[data-testid="stForm"] label span,
        div[data-testid="stForm"] .stWidgetLabel,
        div[data-testid="stForm"] .stWidgetLabel p,
        div[data-testid="stForm"] h3,
        div[data-testid="stForm"] h4,
        div[data-testid="stForm"] strong {
            color: #FFFFFF !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            opacity: 1 !important;
            visibility: visible !important;
        }

        /* 3. Estilo de los campos de entrada */
        div[data-testid="stForm"] input, 
        div[data-testid="stForm"] textarea {
            background-color: #1F2937 !important;
            color: #F9FAFB !important;
            border: 1px solid #4B5563 !important;
            border-radius: 6px !important;
        }

        /* 4. Color del título "Editando..." */
        .stSubheader, div[data-testid="stSubheader"] {
            color: #38BDF8 !important;
            font-weight: bold !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if df_lideres.empty:
        st.warning("No hay datos disponibles para editar.")
    else:
        busqueda_ced = st.text_input("Ingrese la Cédula a Editar:")

        if busqueda_ced.strip():
            term = busqueda_ced.strip()
            idx_match = df_lideres[df_lideres["No. Identificacion"].map(limpiar_valor) == term].index

            if not idx_match.empty:
                idx_row = idx_match[0]
                row = df_lideres.loc[idx_row]

                st.subheader(f"Editando: {valor(row, 'Nombres')} {valor(row, 'Apellidos')}")

                with st.form(key=f"form_edit_{idx_row}"):
                    st.markdown("#### 📌 Datos Personales y Contacto")
                    c1, c2 = st.columns(2)
                    with c1:
                        new_nombres = st.text_input("Nombres", value=valor(row, "Nombres"))
                        new_apellidos = st.text_input("Apellidos", value=valor(row, "Apellidos"))
                        new_tel = st.text_input("Teléfono", value=valor(row, "No. Telefono"))
                        new_correo = st.text_input("Correo", value=valor(row, "Correo Electronico"))
                        new_cumple = st.text_input("Fecha Cumpleaños", value=valor(row, "Fecha de Cumpleanos"))
                        new_redes = st.text_input("Redes Sociales", value=valor(row, "Redes Sociales"))
                    with c2:
                        new_dep = st.text_input("Dependencia", value=valor(row, "Dependencia"))
                        new_sec = st.text_input("Secretaría", value=valor(row, "Secretaria y/o Dependencia"))
                        new_cargo = st.text_input("Cargo Actual", value=valor(row, "Cargo actual"))
                        new_prof = st.text_input("Profesión", value=valor(row, "Profesion"))
                        new_apoyo = st.text_input("Apoyo", value=valor(row, "Apoyo"))
                        new_comuna = st.text_input("Comuna", value=valor(row, "Comuna"))
                        new_barrio = st.text_input("Barrio", value=valor(row, "Barrio"))

                    st.markdown("---")

                    st.markdown("#### 🗳️ Votantes, Proyección y Planillas")
                    c3, c4, c5 = st.columns(3)

                    with c3:
                        st.markdown("**🗳️ Votantes**")
                        new_bello = st.number_input("Bello", value=int(pd.to_numeric(valor(row, "Bello"), errors='coerce') or 0), step=1)
                        new_otros = st.number_input("Otros", value=int(pd.to_numeric(valor(row, "Otros"), errors='coerce') or 0), step=1)
                        new_total = st.number_input("Total Votantes", value=int(pd.to_numeric(valor(row, "Total"), errors='coerce') or 0), step=1)

                    with c4:
                        st.markdown("**📈 Proyección y Notas**")
                        new_proy = st.number_input("Proyección", value=int(pd.to_numeric(valor(row, "PROYECCION"), errors='coerce') or 0), step=1)
                        new_registros = st.number_input("Registros", value=int(pd.to_numeric(valor(row, "REGISTROS"), errors='coerce') or 0), step=1)
                        new_mun_proy = st.text_input("Municipio Proyectado", value=valor(row, "MUNICIPIO PROYECTADO"))
                        new_notas = st.text_area("Notas", value=valor(row, "NOTAS"))

                    with c5:
                        st.markdown("**📋 Planillas y Registros**")
                        new_mun_bello = st.number_input("Municipio de Bello", value=int(pd.to_numeric(valor(row, "MUNICIPIO DE BELLO"), errors='coerce') or 0), step=1)
                        new_otros_mun = st.number_input("Otros Municipios - Deptos", value=int(pd.to_numeric(valor(row, "OTROS MUNICIPIOS - DEPTOS"), errors='coerce') or 0), step=1)
                        new_no_censo = st.number_input("No está en el censo", value=int(pd.to_numeric(valor(row, "NO ESTA EN EL CENSO"), errors='coerce') or 0), step=1)
                        new_ced_erronea = st.number_input("Cédula Errónea", value=int(pd.to_numeric(valor(row, "CEDULA ERRONEA"), errors='coerce') or 0), step=1)
                        new_tot_amigos = st.number_input("Total No. Amigos", value=int(pd.to_numeric(valor(row, "Total No. Amigos"), errors='coerce') or 0), step=1)

                    new_url_pdf = st.text_input("URL PDF Planilla", value=valor(row, "URL_PDF"))

                    st.markdown("---")
                    btn_guardar = st.form_submit_button("💾 Guardar Cambios")

                    if btn_guardar:
                        df_lideres.loc[idx_row, "Nombres"] = new_nombres
                        df_lideres.loc[idx_row, "Apellidos"] = new_apellidos
                        df_lideres.loc[idx_row, "No. Telefono"] = new_tel
                        df_lideres.loc[idx_row, "Correo Electronico"] = new_correo
                        df_lideres.loc[idx_row, "Fecha de Cumpleanos"] = new_cumple
                        df_lideres.loc[idx_row, "Redes Sociales"] = new_redes
                        df_lideres.loc[idx_row, "Dependencia"] = new_dep
                        df_lideres.loc[idx_row, "Secretaria y/o Dependencia"] = new_sec
                        df_lideres.loc[idx_row, "Cargo actual"] = new_cargo
                        df_lideres.loc[idx_row, "Profesion"] = new_prof
                        df_lideres.loc[idx_row, "Apoyo"] = new_apoyo
                        df_lideres.loc[idx_row, "Comuna"] = new_comuna
                        df_lideres.loc[idx_row, "Barrio"] = new_barrio

                        df_lideres.loc[idx_row, "Bello"] = new_bello
                        df_lideres.loc[idx_row, "Otros"] = new_otros
                        df_lideres.loc[idx_row, "Total"] = new_total
                        df_lideres.loc[idx_row, "PROYECCION"] = new_proy
                        df_lideres.loc[idx_row, "REGISTROS"] = new_registros
                        df_lideres.loc[idx_row, "MUNICIPIO PROYECTADO"] = new_mun_proy
                        df_lideres.loc[idx_row, "NOTAS"] = new_notas

                        df_lideres.loc[idx_row, "MUNICIPIO DE BELLO"] = new_mun_bello
                        df_lideres.loc[idx_row, "OTROS MUNICIPIOS - DEPTOS"] = new_otros_mun
                        df_lideres.loc[idx_row, "NO ESTA EN EL CENSO"] = new_no_censo
                        df_lideres.loc[idx_row, "CEDULA ERRONEA"] = new_ced_erronea
                        df_lideres.loc[idx_row, "Total No. Amigos"] = new_tot_amigos
                        df_lideres.loc[idx_row, "URL_PDF"] = new_url_pdf

                        st.success("✅ Cambios guardados exitosamente.")
                        st.rerun()
            else:
                st.info("No se encontró ningún registro con esa cédula.")
# ==========================================
# MÓDULO 5: EDITAR POR CÉDULA
# ==========================================
elif menu == "✏️ Editar por Cédula":
    st.title("✏️ Editar Líder por Cédula")
    
    ced_buscar = st.text_input("Ingrese la Cédula a Editar:")
    if ced_buscar:
        match = df_lideres[df_lideres["No. Identificacion"] == ced_buscar.strip()]
        if match.empty:
            st.warning("No se encontró ningún registro con esta cédula.")
        else:
            row_idx = match.index[0]
            row_data = match.iloc[0]
            
            with st.form("form_editar_lider"):
                st.subheader(f"Editando: {row_data['Nombres']} {row_data['Apellidos']}")
                c1, c2 = st.columns(2)
                
                with c1:
                    nombres = st.text_input("Nombres", value=valor(row_data, "Nombres", ""))
                    apellidos = st.text_input("Apellidos", value=valor(row_data, "Apellidos", ""))
                    telefono = st.text_input("Teléfono", value=valor(row_data, "No. Telefono", ""))
                    dependencia = st.text_input("Dependencia", value=valor(row_data, "Dependencia", ""))
                    secretaria = st.text_input("Secretaría", value=valor(row_data, "Secretaria y/o Dependencia", ""))
                    cargo = st.text_input("Cargo Actual", value=valor(row_data, "Cargo actual", ""))
                
                with c2:
                    correo = st.text_input("Correo", value=valor(row_data, "Correo Electronico", ""))
                    comuna = st.text_input("Comuna", value=valor(row_data, "Comuna", ""))
                    barrio = st.text_input("Barrio", value=valor(row_data, "Barrio", ""))
                    municipio = st.text_input("Municipio Proyectado", value=valor(row_data, "MUNICIPIO PROYECTADO", ""))
                    amigos = st.number_input("Total No. Amigos", value=int(row_data.get("Total No. Amigos", 0)))
                    proyeccion = st.number_input("Proyección", value=int(row_data.get("PROYECCION", 0)))
                    url_pdf = st.text_input("URL PDF Planilla", value=valor(row_data, "URL_PDF", ""))

                if st.form_submit_button("💾 Guardar Cambios"):
                    ws = get_worksheet()
                    sheet_row = row_idx + 3  # Ajustado considerando los 2 encabezados superiores
                    
                    ws.update_cell(sheet_row, 2, nombres)
                    ws.update_cell(sheet_row, 3, apellidos)
                    ws.update_cell(sheet_row, 4, telefono)
                    ws.update_cell(sheet_row, 5, dependencia)
                    ws.update_cell(sheet_row, 6, secretaria)
                    ws.update_cell(sheet_row, 9, cargo)
                    ws.update_cell(sheet_row, 10, correo)
                    ws.update_cell(sheet_row, 13, comuna)
                    ws.update_cell(sheet_row, 14, barrio)
                    ws.update_cell(sheet_row, 18, proyeccion)
                    ws.update_cell(sheet_row, 20, municipio)
                    ws.update_cell(sheet_row, 26, amigos)
                    ws.update_cell(sheet_row, 27, url_pdf)
                    
                    st.success("✅ Cambios guardados en Google Sheets.")
                    st.cache_data.clear()
                    st.session_state.df_lideres = cargar_datos()
                    st.rerun()

# ==========================================
# MÓDULO 6: EDITOR DE TABLA DIRECTO
# ==========================================
elif menu == "📋 Editor de Tabla Directo":
    st.title("📋 Editor de Tabla en Tiempo Real")
    st.info("Modifique los campos directamente en la tabla y presione 'Guardar Todo' para sincronizar con Google Sheets.")

    edited_df = st.data_editor(df_lideres, num_rows="dynamic", use_container_width=True)

    if st.button("💾 Guardar Cambios de la Tabla", type="primary"):
        try:
            ws = get_worksheet()
            val_list = [COLUMNAS] + edited_df.astype(str).values.tolist()
            ws.update(val_list)
            st.success("✅ Hoja de cálculo actualizada correctamente.")
            st.session_state.df_lideres = edited_df
        except Exception as e:
            st.error(f"Error al guardar la tabla: {e}")
