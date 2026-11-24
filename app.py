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
    .main .block-container { 
        padding-top: 1.5rem; 
        padding-bottom: 2rem; 
    }
    
    /* TARJETA DE MÉTRICAS (st.metric) */
    div[data-testid="stMetric"] {
        background-color: #1f2937 !important;
        border: 1px solid #374151 !important;
        padding: 15px !important;
        border-radius: 10px !important;
    }
    
    div[data-testid="stMetric"] label,
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    
    /* FORMULARIOS Y CAMPOS DE TEXTO */
    div[data-testid="stForm"] { 
        border: 1px solid #374151; 
        padding: 20px; 
        border-radius: 10px; 
        background-color: #1f2937 !important; 
    }
    
    div[data-testid="stForm"] label, 
    div[data-testid="stForm"] .stMarkdown p { 
        color: #f3f4f6 !important; 
        font-weight: 600 !important; 
    }
    
    div[data-testid="stForm"] input,
    div[data-testid="stForm"] textarea { 
        background-color: #111827 !important; 
        color: #ffffff !important; 
        border: 1px solid #4b5563 !important; 
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# ESTRUCTURA EXACTA DE COLUMNAS DE LA HOJA
# ==========================================
COLUMNAS = [
    "No. Identificacion", "Nombres", "Apellidos", "No. Telefono", "Dependencia",
    "Secretaria y/o Dependencia", "Apoyo", "Profesion", "Cargo actual", "Correo Electronico",
    "Redes Sociales", "Fecha de Cumpleanos", "Comuna", "Barrio", "Bello", "Otros",
    "Total", "PROYECCION", "REGISTROS", "MUNICIPIO PROYECTADO", "NOTAS",
    "MUNICIPIO DE BELLO", "OTROS MUNICIPIOS - DEPTOS", "NO ESTA EN EL CENSO",
    "CEDULA ERRONEA", "Total No. Amigos", "URL_PDF"
]

# ==========================================
# AUTENTICACIÓN DE USUARIOS
# ==========================================
def check_password():
    def password_entered():
        user = st.session_state.get("username", "")
        pwd = st.session_state.get("password", "")
        if user in st.secrets.get("usuarios", {}) and hmac.compare_digest(pwd, st.secrets["usuarios"][user]):
            st.session_state["password_correct"] = True
            st.session_state["logged_user"] = user
            if "password" in st.session_state:
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
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_worksheet():
    client = get_gspread_client()
    if "spreadsheet_id" in st.secrets and st.secrets["spreadsheet_id"].strip():
        return client.open_by_key(st.secrets["spreadsheet_id"].strip()).sheet1
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
        return pd.DataFrame(columns=COLUMNAS + ["_sheet_row"])

    start_idx = 1
    for idx, r in enumerate(raw_data[:5]):
        row_str = [str(cell).strip() for cell in r]
        if "No. Identificacion" in row_str:
            start_idx = idx + 1
            break

    rows = raw_data[start_idx:]
    data = []
    for real_idx, r in enumerate(rows, start=start_idx + 1):
        fila = [r[i] if i < len(r) else "" for i in range(len(COLUMNAS))]
        cedula_val = limpiar_valor(fila[0])
        if cedula_val:
            fila.append(real_idx)
            data.append(fila)

    df = pd.DataFrame(data, columns=COLUMNAS + ["_sheet_row"])

    for col in COLUMNAS:
        df[col] = df[col].apply(limpiar_valor)

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
        table_data = [[Paragraph(k, style_label), Paragraph(str(v), style_val)] for k, v in data_dict.items()]
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
# EXPORTADORES EDITABLES (EXCEL / CSV)
# ==========================================
def generar_excel_bytes(df_export):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_export[COLUMNAS].to_excel(writer, index=False, sheet_name="Reporte_Lideres")
    output.seek(0)
    return output

def generar_csv_bytes(df_export):
    return df_export[COLUMNAS].to_csv(index=False).encode("utf-8-sig")

# ==========================================
# MENÚ LATERAL Y NAVEGACIÓN
# ==========================================
with st.sidebar:
    st.title("📌 Menú Principal")
    st.write(f"👤 **Usuario:** {st.session_state.get('logged_user', 'Admin')}")

    menu = st.radio("Navegación", [
        "📊 Dashboard General",
        "🔍 Consulta Detallada",
        "🎂 Cumpleaños Próximos",
        "➕ Crear Nuevo Registro",
        "✏️ Editar por Cédula",
        "📋 Editor de Tabla Directo"
    ])

    st.markdown("---")
    if st.button("🔄 Recargar datos de Google Sheets", use_container_width=True):
        st.cache_resource.clear()
        st.session_state.df_lideres = cargar_datos()
        st.rerun()

    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==========================================
# MÓDULOS DE LA APLICACIÓN
# ==========================================
if menu == "📊 Dashboard General":
    st.title("📊 Dashboard General de Líderes")
    if df_lideres.empty:
        st.info("No hay datos para mostrar.")
    else:
        st.metric("Total Registros", len(df_lideres))

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

elif menu == "🔍 Consulta Detallada":
    st.title("🔍 Consulta Detallada de Líderes")
    if df_lideres.empty:
        st.warning("No hay datos disponibles.")
    else:
        filtro_pdf = st.radio(
            "Estado de Planilla PDF:",
            ["Todos los registros", "❌ Sin PDF Planilla", "✅ Con PDF Planilla"],
            horizontal=True
        )
        criterio = st.radio("Buscar por:", ["Todos los campos", "Cédula / Identificación", "Nombre / Apellido"], horizontal=True)
        busqueda = st.text_input("Ingrese término de búsqueda (opcional si filtra por Sin PDF Planilla):")

        def tiene_pdf_valido(val):
            v = limpiar_valor(val)
            return v.startswith(("http://", "https://"))

        mask_pdf = df_lideres["URL_PDF"].apply(tiene_pdf_valido)
        if filtro_pdf == "❌ Sin PDF Planilla":
            base_df = df_lideres.loc[~mask_pdf]
        elif filtro_pdf == "✅ Con PDF Planilla":
            base_df = df_lideres.loc[mask_pdf]
        else:
            base_df = df_lideres

        if busqueda.strip():
            term = busqueda.strip()
            if criterio == "Cédula / Identificación":
                mask_busq = base_df["No. Identificacion"].map(limpiar_valor).str.contains(re.escape(term), case=False, na=False)
            elif criterio == "Nombre / Apellido":
                a = base_df["Nombres"].map(limpiar_valor)
                b = base_df["Apellidos"].map(limpiar_valor)
                mask_busq = a.str.contains(re.escape(term), case=False, na=False) | b.str.contains(re.escape(term), case=False, na=False)
            else:
                mask_busq = base_df[COLUMNAS].apply(lambda col: col.map(limpiar_valor).str.contains(re.escape(term), case=False, na=False), axis=0).any(axis=1)
            resultado = base_df.loc[mask_busq]
        elif filtro_pdf != "Todos los registros":
            resultado = base_df
        else:
            resultado = pd.DataFrame()

        if busqueda.strip() or filtro_pdf != "Todos los registros":
            if not resultado.empty:
                top_msg, exp_xls, exp_csv = st.columns([3.2, 1.4, 1.4])
                with top_msg:
                    st.success(f"✅ Se encontraron {len(resultado)} registro(s).")
                with exp_xls:
                    try:
                        excel_bytes = generar_excel_bytes(resultado)
                        st.download_button(
                            "📥 Exportar Excel (.xlsx)",
                            data=excel_bytes,
                            file_name="Reporte_Consulta_Detallada.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Error Excel: {e}")
                with exp_csv:
                    st.download_button(
                        "📄 Exportar CSV (.csv)",
                        data=generar_csv_bytes(resultado),
                        file_name="Reporte_Consulta_Detallada.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                for idx, row in resultado.iterrows():
                    nombre = f"{valor(row,'Nombres','')} {valor(row,'Apellidos','')}".strip()
                    cedula = valor(row, "No. Identificacion")
                    dependencia = valor(row, "Dependencia")
                    sheet_row = int(row["_sheet_row"]) if "_sheet_row" in row else (idx + 2)
                    edit_state_key = f"modo_edicion_{sheet_row}_{idx}"

                    with st.container(border=True):
                        h1, h2, h3 = st.columns([3.5, 1.2, 1.3])
                        with h1:
                            st.markdown(f"## **{nombre.upper() or 'NOMBRE NO REGISTRADO'}**")
                            st.markdown(f"**Cédula / Identificación:** {cedula} | **Dependencia:** {dependencia}")
                        with h2:
                            en_edicion = st.session_state.get(edit_state_key, False)
                            btn_label = "❌ Cancelar Edición" if en_edicion else "✏️ Editar Ficha"
                            if st.button(btn_label, key=f"toggle_edit_{sheet_row}_{idx}", use_container_width=True):
                                st.session_state[edit_state_key] = not en_edicion
                                st.rerun()
                        with h3:
                            pdf_file = generar_pdf_ficha(row)
                            safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", cedula)
                            st.download_button("📄 Descargar PDF", data=pdf_file, file_name=f"Ficha_{safe_id or idx}.pdf", mime="application/pdf", key=f"pdf_{idx}", use_container_width=True)

                        st.markdown("---")

                        # MODO EDICIÓN DIRECTA EN LA FICHA
                        if st.session_state.get(edit_state_key, False):
                            with st.form(key=f"form_consulta_edit_{sheet_row}_{idx}"):
                                st.info(f"✏️ Editando registro en fila {sheet_row} de Google Sheets. Modifica los campos necesarios y pulsa Guardar.")
                                
                                st.markdown("#### 📌 Datos Principales y Contacto")
                                ec1, ec2, ec3 = st.columns(3)
                                with ec1:
                                    ed_cedula = st.text_input("No. Identificación *", value=valor(row, "No. Identificacion", ""))
                                    ed_nombres = st.text_input("Nombres *", value=valor(row, "Nombres", ""))
                                    ed_apellidos = st.text_input("Apellidos", value=valor(row, "Apellidos", ""))
                                    ed_telefono = st.text_input("Teléfono", value=valor(row, "No. Telefono", ""))
                                    ed_correo = st.text_input("Correo Electrónico", value=valor(row, "Correo Electronico", ""))
                                with ec2:
                                    ed_dependencia = st.text_input("Dependencia", value=valor(row, "Dependencia", ""))
                                    ed_secretaria = st.text_input("Secretaría y/o Dependencia", value=valor(row, "Secretaria y/o Dependencia", ""))
                                    ed_cargo = st.text_input("Cargo actual", value=valor(row, "Cargo actual", ""))
                                    ed_profesion = st.text_input("Profesión", value=valor(row, "Profesion", ""))
                                    ed_apoyo = st.text_input("Equipo de Apoyo", value=valor(row, "Apoyo", ""))
                                with ec3:
                                    ed_cumple = st.text_input("Fecha de Cumpleaños", value=valor(row, "Fecha de Cumpleanos", ""))
                                    ed_redes = st.text_input("Redes Sociales", value=valor(row, "Redes Sociales", ""))
                                    ed_comuna = st.text_input("Comuna", value=valor(row, "Comuna", ""))
                                    ed_barrio = st.text_input("Barrio", value=valor(row, "Barrio", ""))
                                    ed_mun_proy = st.text_input("Municipio Proyectado", value=valor(row, "MUNICIPIO PROYECTADO", ""))

                                st.markdown("#### 📊 Votantes, Proyección y Planillas")
                                em1, em2, em3 = st.columns(3)
                                with em1:
                                    ed_bello = st.number_input("Votos Bello", value=int(row.get("Bello", 0)), step=1)
                                    ed_otros = st.number_input("Votos Otros", value=int(row.get("Otros", 0)), step=1)
                                    ed_total = st.number_input("Total Votos", value=int(row.get("Total", 0)), step=1)
                                    ed_proyeccion = st.number_input("Proyección", value=int(row.get("PROYECCION", 0)), step=1)
                                with em2:
                                    ed_registros = st.number_input("Registros", value=int(row.get("REGISTROS", 0)), step=1)
                                    ed_mun_bello = st.number_input("Municipio de Bello (Censo)", value=int(row.get("MUNICIPIO DE BELLO", 0)), step=1)
                                    ed_otros_mun = st.number_input("Otros Municipios - Deptos", value=int(row.get("OTROS MUNICIPIOS - DEPTOS", 0)), step=1)
                                    ed_no_censo = st.number_input("No está en el censo", value=int(row.get("NO ESTA EN EL CENSO", 0)), step=1)
                                with em3:
                                    ed_ced_err = st.number_input("Cédula Errónea", value=int(row.get("CEDULA ERRONEA", 0)), step=1)
                                    ed_total_amigos = st.number_input("Total No. Amigos", value=int(row.get("Total No. Amigos", 0)), step=1)
                                    ed_url_pdf = st.text_input("URL PDF Planilla", value=valor(row, "URL_PDF", ""))

                                ed_notas = st.text_area("Notas Adicionales", value=valor(row, "NOTAS", ""))

                                guardar_edicion = st.form_submit_button("💾 Guardar Cambios en Google Sheets", type="primary", use_container_width=True)
                                if guardar_edicion:
                                    if not ed_cedula.strip() or not ed_nombres.strip():
                                        st.error("⚠️ La Cédula y los Nombres son obligatorios.")
                                    else:
                                        fila_actualizada = [
                                            ed_cedula.strip(),
                                            ed_nombres.strip(),
                                            ed_apellidos.strip(),
                                            ed_telefono.strip(),
                                            ed_dependencia.strip(),
                                            ed_secretaria.strip(),
                                            ed_apoyo.strip(),
                                            ed_profesion.strip(),
                                            ed_cargo.strip(),
                                            ed_correo.strip(),
                                            ed_redes.strip(),
                                            ed_cumple.strip(),
                                            ed_comuna.strip(),
                                            ed_barrio.strip(),
                                            int(ed_bello),
                                            int(ed_otros),
                                            int(ed_total),
                                            int(ed_proyeccion),
                                            int(ed_registros),
                                            ed_mun_proy.strip(),
                                            ed_notas.strip(),
                                            int(ed_mun_bello),
                                            int(ed_otros_mun),
                                            int(ed_no_censo),
                                            int(ed_ced_err),
                                            int(ed_total_amigos),
                                            ed_url_pdf.strip()
                                        ]
                                        try:
                                            ws = get_worksheet()
                                            ws.update(range_name=f"A{sheet_row}:AA{sheet_row}", values=[fila_actualizada])
                                            st.session_state[edit_state_key] = False
                                            st.cache_resource.clear()
                                            st.session_state.df_lideres = cargar_datos()
                                            st.success("✅ ¡Cambios grabados correctamente en Google Sheets!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Error al grabar los cambios en Google Sheets: {e}")

                        # MODO LECTURA NORMAL DE LA FICHA
                        else:
                            col_lab, col_con, col_ubi = st.columns(3)
                            with col_lab:
                                st.markdown("### 📌 Datos Principales")
                                st.markdown(f"**Dependencia:** {valor(row, 'Dependencia')}\n\n**Secretaría:** {valor(row, 'Secretaria y/o Dependencia')}\n\n**Cargo actual:** {valor(row, 'Cargo actual')}\n\n**Profesión:** {valor(row, 'Profesion')}\n\n**Equipo Apoyo:** {valor(row, 'Apoyo')}")
                            with col_con:
                                st.markdown("### 📞 Contacto")
                                st.markdown(f"**Teléfono:** {valor(row, 'No. Telefono')}\n\n**Correo:** {valor(row, 'Correo Electronico')}\n\n**Cumpleaños:** {valor(row, 'Fecha de Cumpleanos')}\n\n**Redes Sociales:** {valor(row, 'Redes Sociales')}")
                            with col_ubi:
                                st.markdown("### 📍 Ubicación")
                                st.markdown(f"**Comuna:** {valor(row, 'Comuna')}\n\n**Barrio:** {valor(row, 'Barrio')}")

                            st.markdown("---")
                            col_vot, col_proy, col_plan = st.columns(3)
                            with col_vot:
                                st.markdown("### 🗳️ Votantes")
                                st.markdown(f"**Bello:** {valor(row, 'Bello', '0')}\n\n**Otros:** {valor(row, 'Otros', '0')}\n\n**Total:** {valor(row, 'Total', '0')}")
                            with col_proy:
                                st.markdown("### 📈 Proyección y Notas")
                                st.markdown(f"**Proyección:** {valor(row, 'PROYECCION', '0')}\n\n**Registros:** {valor(row, 'REGISTROS', '0')}\n\n**Municipio Proyectado:** {valor(row, 'MUNICIPIO PROYECTADO')}\n\n**Notas:** {valor(row, 'NOTAS', 'Sin notas')}")
                            with col_plan:
                                st.markdown("### 📋 Planillas y Registros")
                                st.markdown(f"**Municipio de Bello:** {valor(row, 'MUNICIPIO DE BELLO', '0')}\n\n**Otros Municipios:** {valor(row, 'OTROS MUNICIPIOS - DEPTOS', '0')}\n\n**No en Censo:** {valor(row, 'NO ESTA EN EL CENSO', '0')}\n\n**Cédula Errónea:** {valor(row, 'CEDULA ERRONEA', '0')}\n\n**Total Amigos:** {valor(row, 'Total No. Amigos', '0')}")

                            st.markdown("---")
                            url = valor(row, "URL_PDF", "")
                            if url.startswith(("http://", "https://")):
                                st.link_button("🔗 Abrir PDF Planilla", url)
                            else:
                                st.warning("⚠️ Este registro no tiene un enlace de PDF de planilla cargado.")
            else:
                st.info("No se encontraron registros que coincidan con los filtros aplicados.")

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
            def resaltar_hoy(row):
                if row["Días Faltantes"] == "¡HOY! 🎉":
                    return ['background-color: #B45309; color: #FFFFFF; font-weight: bold;'] * len(row)
                return [''] * len(row)
            st.dataframe(df_cumples.style.apply(resaltar_hoy, axis=1), use_container_width=True, hide_index=True)
        else:
            st.success("🎈 No hay cumpleaños registrados para hoy o los próximos 5 días.")

elif menu == "➕ Crear Nuevo Registro":
    st.title("➕ Agregar Nuevo Líder")
    with st.form("form_nuevo_lider"):
        c1, c2 = st.columns(2)
        with c1:
            cedula = st.text_input("No. Identificación *")
            nombres = st.text_input("Nombres *")
            apellidos = st.text_input("Apellidos *")
            telefono = st.text_input("Teléfono")
            dependencia = st.text_input("Dependencia")
            secretaria = st.text_input("Secretaría")
            apoyo = st.text_input("Apoyo")
            profesion = st.text_input("Profesión")
            cargo = st.text_input("Cargo Actual")
        with c2:
            correo = st.text_input("Correo Electrónico")
            redes = st.text_input("Redes Sociales")
            cumple = st.date_input("Fecha de Cumpleaños", value=None)
            comuna = st.text_input("Comuna")
            barrio = st.text_input("Barrio")
            municipio = st.text_input("Municipio Proyectado")
            amigos = st.number_input("Total Amigos", min_value=0, step=1)
            proyeccion = st.number_input("Proyección", min_value=0, step=1)
            url_pdf = st.text_input("URL PDF Planilla")

        submitted = st.form_submit_button("💾 Guardar Líder", type="primary")
        if submitted:
            if not cedula or not nombres:
                st.error("Por favor complete los campos obligatorios (*).")
            else:
                nueva_fila = [
                    cedula, nombres, apellidos, telefono, dependencia, secretaria, apoyo, profesion,
                    cargo, correo, redes, str(cumple) if cumple else "", comuna, barrio, "", "", "",
                    proyeccion, 0, municipio, "", "", "", "", "", amigos, url_pdf
                ]
                try:
                    ws = get_worksheet()
                    ws.append_row(nueva_fila)
                    st.success("✅ ¡Registro agregado con éxito a Google Sheets!")
                    st.cache_resource.clear()
                    st.session_state.df_lideres = cargar_datos()
                except Exception as e:
                    st.error(f"Error al escribir en Google Sheets: {e}")

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
            
            if "_sheet_row" in row_data:
                sheet_row = int(row_data["_sheet_row"])
            else:
                sheet_row = row_idx + 2

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
                    st.cache_resource.clear()
                    st.session_state.df_lideres = cargar_datos()
                    st.rerun()

elif menu == "📋 Editor de Tabla Directo":
    st.title("📋 Editor de Tabla en Tiempo Real")
    st.info("Modifique los campos directamente en la tabla y presione 'Guardar Todo' para sincronizar con Google Sheets.")

    df_display = df_lideres[COLUMNAS]
    edited_df = st.data_editor(df_display, num_rows="dynamic", use_container_width=True)

    if st.button("💾 Guardar Cambios de la Tabla", type="primary"):
        try:
            ws = get_worksheet()
            val_list = [COLUMNAS] + edited_df.astype(str).values.tolist()
            ws.update(range_name='A1', values=val_list)
            st.success("✅ Hoja de cálculo actualizada correctamente.")
            st.cache_resource.clear()
            st.session_state.df_lideres = cargar_datos()
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar la tabla: {e}")
