import streamlit as st
import pandas as pd
import unicodedata
from datetime import datetime, date
import io
import re
import html
import hmac
import plotly.express as px
import gspread

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
st.set_page_config(
    page_title="Dashboard Ejecutivo de Líderes",
    page_icon="📊",
    layout="wide"
)

SHEET_ID = "114059SazWnhrk9vUc12Qdyy4eP6EP6lUI_SLj-inGXA"
SHEET_NAME = "BD Cumple"

# IMPORTANTE:
# Estos son los encabezados REALES de la base entregada.
# No se generan nombres por posición ni se adivinan columnas.
COLUMNAS = [
    "No. Identificación",
    "Nombres",
    "Apellidos",
    "No. Teléfono",
    "Dependencia",
    "Secretaría y/o Dependencia",
    "Apoyo",
    "Profesión",
    "Cargo actual",
    "Correo Electrónico",
    "Redes Sociales",
    "Fecha de Cumpleaños",
    "Total",
    "Bello",
    "Otros",
    "Comuna",
    "Barrio",
    "PROYECCIÓN",
    "REGISTROS",
    "MUNICIPIO",
    "NOTAS",
    "No. Amigos",
    "MUNICIPIO DE BELLO",
    "OTROS MUNICIPIOS - DEPTOS",
    "NO ESTA EN EL CENSO",
    "CEDULA ERRONEA",
    "URL_PDF",
]

# Las dos filas superiores de la hoja original contienen encabezados.
# Se conservan exactamente al guardar.
ENCABEZADOS_SUPERIORES = [
    "No. Identificación", "Nombres", "Apellidos", "No. Teléfono",
    "Dependencia", "Secretaría y/o Dependencia", "Apoyo", "Profesión",
    "Cargo actual", "Correo Electrónico", "Redes Sociales",
    "Fecha de Cumpleaños", "Total", "Bello", "Otros", "Comuna", "Barrio",
    "PROYECCIÓN Y NOTAS", "", "", "", "PLANILLAS Y REGISTROS", "", "", "", "",
    "URL_PDF"
]
ENCABEZADOS_INFERIORES = [
    "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
    "PROYECCIÓN", "REGISTROS", "MUNICIPIO", "NOTAS", "No. Amigos",
    "MUNICIPIO DE BELLO", "OTROS MUNICIPIOS - DEPTOS",
    "NO ESTA EN EL CENSO", "CEDULA ERRONEA", ""
]

# ==============================================================================
# ESTILO
# ==============================================================================
st.markdown("""
<style>
.stApp { background-color: #F8FAFC !important; }
.stApp p, .stApp span, .stApp label, .stApp div, .stApp caption, .stMarkdown { color: #1E293B !important; }
h1, h2, h3, h4, h5, h6 { color: #0F172A !important; font-weight: 700 !important; }
[data-testid="stSidebar"] { background-color: #0F172A !important; }
[data-testid="stSidebar"] *, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] span { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stButton > button {
    background-color: #1E293B !important; color: #FFFFFF !important;
    border: 1px solid #334155 !important; border-radius: 8px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #F59E0B !important; border-color: #D97706 !important;
    color: #FFFFFF !important;
}
[data-testid="stVerticalBlock"] > div[data-testid="stBlock"],
div[data-testid="stForm"], .stCard {
    background-color: #FFFFFF !important;
    border-radius: 12px !important;
    padding: 18px !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0px 4px 10px rgba(0,0,0,.03) !important;
}
[data-testid="stMetricValue"] { color: #0F172A !important; font-weight: 800 !important; }
[data-testid="stMetricLabel"] p { color: #475569 !important; font-weight: 700 !important; }
div.stDownloadButton > button, div.stButton > button,
div[data-testid="stLinkButton"] > a {
    background-color: #1E3A8A !important; color: #FFFFFF !important;
    font-weight: 600 !important; font-size: 14px !important;
    border-radius: 8px !important; border: none !important;
    padding: 8px 16px !important;
}
div.stDownloadButton > button:hover, div.stButton > button:hover,
div[data-testid="stLinkButton"] > a:hover {
    background-color: #2563EB !important; color: #FFFFFF !important;
}
div.stDownloadButton > button p, div.stButton > button p,
div[data-testid="stLinkButton"] > a p, div[data-testid="stLinkButton"] > a span {
    color: #FFFFFF !important; margin: 0 !important;
}
input { color: #0F172A !important; background-color: #FFFFFF !important; border: 1px solid #CBD5E1 !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# AUTENTICACIÓN
# ==============================================================================
def verificar_login():
    if st.session_state.get("autenticado", False):
        return True

    st.markdown(
        "<h2 style='text-align:center;color:#0F172A;'>🔒 Sistema de Control de Acceso</h2>",
        unsafe_allow_html=True
    )
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.container(border=True):
            st.subheader("Iniciar Sesión")
            with st.form("form_login"):
                usuario = st.text_input("Usuario:")
                password = st.text_input("Contraseña:", type="password")
                ingresar = st.form_submit_button("Ingresar", use_container_width=True)

                if ingresar:
                    if "usuarios" in st.secrets and usuario in st.secrets["usuarios"]:
                        esperado = str(st.secrets["usuarios"][usuario])
                        if hmac.compare_digest(str(password), esperado):
                            st.session_state.autenticado = True
                            st.rerun()
                        else:
                            st.error("❌ Contraseña incorrecta")
                    else:
                        st.error("❌ Usuario no registrado o secretos no configurados")
    return False

if not verificar_login():
    st.stop()

# ==============================================================================
# UTILIDADES DE NORMALIZACIÓN Y DATOS
# ==============================================================================
def normalizar(texto):
    if texto is None:
        return ""
    texto = str(texto)
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto.lower().strip()

def limpiar_valor(valor):
    """Limpia sin alterar identificadores, teléfonos o textos válidos."""
    if valor is None:
        return ""
    if isinstance(valor, pd.Timestamp):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, float):
        if pd.isna(valor):
            return ""
        if valor.is_integer():
            return str(int(valor))
    texto = str(valor).strip()
    if texto.lower() in {"nan", "none", "null", "<na>"}:
        return ""
    # Solo quitar .0 cuando el valor entero fue convertido como texto.
    if re.fullmatch(r"-?\d+\.0", texto):
        texto = texto[:-2]
    return texto

def preparar_df(data):
    """Lee las filas de datos y las asigna a las columnas REALES, por posición."""
    if not data or len(data) < 2:
        return pd.DataFrame(columns=COLUMNAS)

    # La estructura confirmada del archivo es:
    # fila 1 = encabezados principales/agrupadores
    # fila 2 = subencabezados de las columnas 18-26
    filas = data[2:]

    resultado = []
    for row in filas:
        row = list(row)
        if len(row) < len(COLUMNAS):
            row += [""] * (len(COLUMNAS) - len(row))
        row = row[:len(COLUMNAS)]
        resultado.append([limpiar_valor(v) for v in row])

    return pd.DataFrame(resultado, columns=COLUMNAS)

# ==============================================================================
# GOOGLE SHEETS
# ==============================================================================
@st.cache_resource
def conectar_google_sheets():
    try:
        credenciales = dict(st.secrets["gcp_service_account"])
        client = gspread.service_account_from_dict(credenciales)

        # La hoja REAL del archivo entregado se llama "BD Cumple".
        sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        return sheet
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Google Sheets / pestaña '{SHEET_NAME}': {e}")
        return None

def actualizar_hoja_gspread(sheet, range_name, values):
    try:
        sheet.update(range_name=range_name, values=values)
    except TypeError:
        sheet.update(range_name, values)

def cargar_datos():
    sheet = conectar_google_sheets()
    if sheet is None:
        return pd.DataFrame(columns=COLUMNAS)

    try:
        data = sheet.get_all_values()
        return preparar_df(data)
    except Exception as e:
        st.error(f"❌ Error al leer la base de datos: {e}")
        return pd.DataFrame(columns=COLUMNAS)

if "df_lideres" not in st.session_state:
    st.session_state.df_lideres = cargar_datos()

df_lideres = st.session_state.df_lideres

# ==============================================================================
# BÚSQUEDA EXACTA DE COLUMNAS
# ==============================================================================
def valor(row, columna, default="Sin datos"):
    if columna not in row.index:
        return default
    v = limpiar_valor(row[columna])
    return v if v else default

def indice_por_identificacion(df, identificacion):
    buscado = limpiar_valor(identificacion)
    if not buscado:
        return []

    col = "No. Identificación"
    if col not in df.columns:
        return []

    serie = df[col].map(limpiar_valor)
    return df.index[serie == buscado].tolist()

def fecha_cumpleaños(valor_fecha):
    if not valor_fecha:
        return None
    texto = limpiar_valor(valor_fecha)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto[:10], fmt).date()
        except ValueError:
            pass
    try:
        return pd.to_datetime(texto, dayfirst=True, errors="raise").date()
    except Exception:
        return None

def obtener_proximos_cumpleanos(df, dias_anticipacion=5):
    if df.empty:
        return []

    hoy = date.today()
    proximos = []

    for idx, row in df.iterrows():
        fecha = fecha_cumpleaños(valor(row, "Fecha de Cumpleaños", ""))
        if not fecha:
            continue

        try:
            cumple = date(hoy.year, fecha.month, fecha.day)
        except ValueError:
            # 29 de febrero: se considera 28 de febrero en año no bisiesto.
            if fecha.month == 2 and fecha.day == 29:
                cumple = date(hoy.year, 2, 28)
            else:
                continue

        if cumple < hoy:
            try:
                cumple = date(hoy.year + 1, fecha.month, fecha.day)
            except ValueError:
                cumple = date(hoy.year + 1, 2, 28)

        dias = (cumple - hoy).days
        if 0 <= dias <= dias_anticipacion:
            proximos.append({
                "idx": idx,
                "nombre": f"{valor(row,'Nombres','')} {valor(row,'Apellidos','')}".strip().upper(),
                "dias": dias,
                "fecha": cumple.strftime("%d/%m"),
                "telefono": valor(row, "No. Teléfono"),
                "dependencia": valor(row, "Dependencia")
            })

    proximos.sort(key=lambda x: (x["dias"], x["nombre"]))
    return proximos

# ==============================================================================
# PDF
# ==============================================================================
def generar_pdf_ficha(row):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "DocTitle", parent=styles["Heading1"], fontSize=18,
        textColor=colors.HexColor("#1E3A8A"), spaceAfter=10
    )
    subtitle = ParagraphStyle(
        "DocSubTitle", parent=styles["Heading2"], fontSize=12,
        textColor=colors.HexColor("#0F172A"), spaceAfter=6
    )

    nombre = f"{valor(row,'Nombres','')} {valor(row,'Apellidos','')}".strip().upper()
    cedula = valor(row, "No. Identificación")

    story = [
        Paragraph(html.escape(nombre or "FICHA DE USUARIO"), title),
        Paragraph(f"Cédula / ID: <b>{html.escape(cedula)}</b>", subtitle),
        Spacer(1, 12)
    ]

    data = [[
        Paragraph("<b>CAMPO</b>", styles["Normal"]),
        Paragraph("<b>DETALLE</b>", styles["Normal"])
    ]]

    for col in COLUMNAS:
        v = valor(row, col, "Sin datos")
        data.append([html.escape(col), html.escape(v)])

    table = Table(data, colWidths=[180, 340], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return buffer

# ==============================================================================
# CUMPLEAÑOS
# ==============================================================================
cumpleanos_lista = obtener_proximos_cumpleanos(df_lideres)

with st.container(border=True):
    st.markdown("### 🎂 **Próximos Cumpleaños (Hoy y próximos 5 días)**")
    if cumpleanos_lista:
        cols = st.columns(min(len(cumpleanos_lista), 4))
        for i, c in enumerate(cumpleanos_lista):
            with cols[i % 4]:
                with st.container(border=True):
                    if c["dias"] == 0:
                        st.markdown("🥳 **¡HOY CUMPLE AÑOS!** 🎉")
                    else:
                        st.markdown(f"🗓️ **En {c['dias']} día(s)** ({c['fecha']})")
                    st.markdown(f"**{c['nombre'] or 'USUARIO SIN NOMBRE'}**")
                    st.caption(f"🏢 {c['dependencia']}\n\n📞 Tel: {c['telefono']}")
    else:
        st.info("🎈 No hay personas registradas que cumplan años hoy o en los próximos 5 días.")

st.markdown("---")

# ==============================================================================
# SIDEBAR
# ==============================================================================
st.sidebar.title("Módulos del Sistema")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.rerun()

if st.sidebar.button("🔄 Recargar datos de Google Sheets", use_container_width=True):
    st.session_state.df_lideres = cargar_datos()
    st.sidebar.success("✅ Base de datos recargada.")
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

    if df_lideres.empty:
        st.warning("No hay datos disponibles.")
    else:
        criterio = st.radio(
            "Buscar por:",
            ["Todos los campos", "Cédula / Identificación", "Nombre / Apellido"],
            horizontal=True
        )
        busqueda = st.text_input("Ingrese término de búsqueda:")
        resultado = pd.DataFrame()

        if busqueda.strip():
            term = busqueda.strip()
            if criterio == "Cédula / Identificación":
                serie = df_lideres["No. Identificación"].map(limpiar_valor)
                mask = serie.str.contains(re.escape(term), case=False, na=False)
            elif criterio == "Nombre / Apellido":
                a = df_lideres["Nombres"].map(limpiar_valor)
                b = df_lideres["Apellidos"].map(limpiar_valor)
                mask = a.str.contains(re.escape(term), case=False, na=False) | \
                       b.str.contains(re.escape(term), case=False, na=False)
            else:
                mask = df_lideres.apply(
                    lambda col: col.map(limpiar_valor).str.contains(
                        re.escape(term), case=False, na=False
                    ),
                    axis=0
                ).any(axis=1)

            resultado = df_lideres.loc[mask]

        if not resultado.empty:
            st.success(f"✅ Se encontraron {len(resultado)} registro(s).")

            for idx, row in resultado.iterrows():
                nombre = f"{valor(row,'Nombres','')} {valor(row,'Apellidos','')}".strip()
                cedula = valor(row, "No. Identificación")
                dependencia = valor(row, "Dependencia")

                with st.container(border=True):
                    h1, h2 = st.columns([4, 1.2])
                    with h1:
                        st.markdown(f"## **{nombre.upper() or 'NOMBRE NO REGISTRADO'}**")
                        st.markdown(
                            f"**Cédula / Identificación:** {cedula} | "
                            f"**Dependencia:** {dependencia}"
                        )
                    with h2:
                        pdf_file = generar_pdf_ficha(row)
                        safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", cedula)
                        st.download_button(
                            "📄 Descargar Ficha PDF",
                            data=pdf_file,
                            file_name=f"Ficha_{safe_id or idx}.pdf",
                            mime="application/pdf"
                        )

                    laboral = {
                        "Dependencia": valor(row, "Dependencia"),
                        "Secretaría y/o Dependencia": valor(row, "Secretaría y/o Dependencia"),
                        "Apoyo": valor(row, "Apoyo"),
                        "Profesión": valor(row, "Profesión"),
                        "Cargo actual": valor(row, "Cargo actual"),
                    }
                    contacto = {
                        "No. Teléfono": valor(row, "No. Teléfono"),
                        "Correo Electrónico": valor(row, "Correo Electrónico"),
                        "Redes Sociales": valor(row, "Redes Sociales"),
                    }
                    ubicacion = {
                        "Comuna": valor(row, "Comuna"),
                        "Barrio": valor(row, "Barrio"),
                        "Fecha de Cumpleaños": valor(row, "Fecha de Cumpleaños"),
                        "MUNICIPIO": valor(row, "MUNICIPIO"),
                        "NOTAS": valor(row, "NOTAS"),
                    }
                    proyeccion = {
                        "Total": valor(row, "Total"),
                        "Bello": valor(row, "Bello"),
                        "Otros": valor(row, "Otros"),
                        "PROYECCIÓN": valor(row, "PROYECCIÓN"),
                        "REGISTROS": valor(row, "REGISTROS"),
                        "No. Amigos": valor(row, "No. Amigos"),
                        "MUNICIPIO DE BELLO": valor(row, "MUNICIPIO DE BELLO"),
                        "OTROS MUNICIPIOS - DEPTOS": valor(row, "OTROS MUNICIPIOS - DEPTOS"),
                        "NO ESTA EN EL CENSO": valor(row, "NO ESTA EN EL CENSO"),
                        "CEDULA ERRONEA": valor(row, "CEDULA ERRONEA"),
                    }

                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.markdown("### 📌 Información Laboral")
                        for k, v in laboral.items():
                            st.markdown(f"**{k}:** {v}")
                    with c2:
                        st.markdown("### 📞 Contacto Directo")
                        for k, v in contacto.items():
                            if k == "Correo Electrónico" and v != "Sin datos":
                                st.markdown(f"**{k}:** [{v}](mailto:{v})")
                            elif k == "Redes Sociales" and v.startswith(("http://","https://")):
                                st.markdown(f"**{k}:** [{v}]({v})")
                            else:
                                st.markdown(f"**{k}:** {v}")
                    with c3:
                        st.markdown("### 📍 Ubicación y Fechas")
                        for k, v in ubicacion.items():
                            st.markdown(f"**{k}:** {v}")
                    with c4:
                        st.markdown("### 📊 Proyección y Registros")
                        for k, v in proyeccion.items():
                            st.markdown(f"**{k}:** {v}")

                    url = valor(row, "URL_PDF", "")
                    if url.startswith(("http://","https://")):
                        st.link_button("🔗 Abrir PDF Planilla", url)

                st.markdown("---")
        elif busqueda:
            st.warning("⚠️ No se localizó ningún registro con el término especificado.")

# ==============================================================================
# MÓDULO 2: PANEL
# ==============================================================================
elif menu == "📈 Panel de Control Ejecutivos":
    st.subheader("📈 Panel de Control Ejecutivo y Métricas Analíticas")

    if not df_lideres.empty:
        k1, k2, k3, k4 = st.columns(4)

        amigos = pd.to_numeric(df_lideres["No. Amigos"], errors="coerce").fillna(0).sum()
        municipios = df_lideres["MUNICIPIO"].replace("", pd.NA).dropna().nunique()

        k1.metric("👥 Total Líderes", len(df_lideres))
        k2.metric("📊 Total Registros Amigos", int(amigos))
        k3.metric("📍 Municipios Cubiertos", int(municipios))
        k4.metric("🟢 Estado Conexión", "Sincronizado vía API")

        st.markdown("---")
        g1, g2 = st.columns(2)

        dep = df_lideres["Dependencia"].replace("", "Sin Especificar").value_counts().head(10)
        if not dep.empty:
            fig1 = px.bar(
                dep.reset_index(), x="Dependencia", y="count",
                title="Distribución de Líderes por Dependencia",
                color="count", color_continuous_scale="Blues"
            )
            fig1.update_layout(xaxis_title="", yaxis_title="Líderes", template="plotly_white")
            g1.plotly_chart(fig1, use_container_width=True)

        temp = df_lideres.copy()
        temp["No_Amigos_Num"] = pd.to_numeric(temp["No. Amigos"], errors="coerce").fillna(0)
        temp["Nombre"] = (temp["Nombres"] + " " + temp["Apellidos"]).str.strip()
        top = temp.sort_values("No_Amigos_Num", ascending=False).head(10)

        fig2 = px.bar(
            top, x="Nombre", y="No_Amigos_Num",
            title="Top 10 Líderes por Número de Amigos",
            color="No_Amigos_Num", color_continuous_scale="Oranges"
        )
        fig2.update_layout(xaxis_title="Líder", yaxis_title="N° Amigos", template="plotly_white")
        g2.plotly_chart(fig2, use_container_width=True)

# ==============================================================================
# MÓDULO 3: NUEVO USUARIO
# ==============================================================================
elif menu == "➕ Registro de Nuevo Usuario":
    st.subheader("➕ Registro de Nuevo Usuario")
    st.info("Los datos ingresados se guardarán automáticamente en Google Sheets.")

    with st.form("form_nuevo_usuario", clear_on_submit=True):
        datos = {}
        a, b = st.columns(2)

        for i, col in enumerate(COLUMNAS):
            target = a if i % 2 == 0 else b
            datos[col] = target.text_input(f"{col}:")

        guardar = st.form_submit_button("➕ Registrar y Guardar en Nube")

    if guardar:
        sheet = conectar_google_sheets()
        if sheet:
            nueva = [datos.get(col, "") for col in COLUMNAS]
            try:
                sheet.append_row(nueva, value_input_option="USER_ENTERED")
                st.session_state.df_lideres = cargar_datos()
                st.success("✅ Usuario registrado correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ No fue posible guardar el registro: {e}")

# ==============================================================================
# MÓDULO 4: EDITAR REGISTRO INDIVIDUAL
# ==============================================================================
elif menu == "✏️ Editar / Modificar Registros":
    st.title("✏️ Edición Individual de Usuarios")
    st.caption("La identificación se busca EXCLUSIVAMENTE en 'No. Identificación'.")

    if not df_lideres.empty:
        identificacion = st.text_input(
            "Ingrese la Cédula/ID del usuario a editar:",
            placeholder="Ej: 3474244"
        )

        if identificacion.strip():
            indices = indice_por_identificacion(df_lideres, identificacion)

            if indices:
                if len(indices) > 1:
                    st.warning("⚠️ Hay más de un registro con esa identificación. Seleccione el registro.")
                user_idx = indices[0]
                usuario = df_lideres.loc[user_idx]

                st.success(
                    f"👤 Usuario localizado: "
                    f"{valor(usuario,'Nombres','')} {valor(usuario,'Apellidos','')}"
                )

                with st.form("form_editar_usuario"):
                    nuevos = {}
                    a, b = st.columns(2)

                    for i, col in enumerate(COLUMNAS):
                        actual = limpiar_valor(usuario[col])
                        target = a if i % 2 == 0 else b
                        nuevos[col] = target.text_input(f"{col}:", value=actual)

                    guardar = st.form_submit_button("💾 Guardar Cambios en la Nube")

                if guardar:
                    sheet = conectar_google_sheets()
                    if sheet:
                        try:
                            # La hoja tiene 2 filas de encabezados.
                            # DataFrame índice 0 corresponde a fila 3 de Sheets.
                            fila_sheet = user_idx + 3
                            valores = [nuevos[col] for col in COLUMNAS]
                            actualizar_hoja_gspread(
                                sheet, f"A{fila_sheet}:{chr(64+len(COLUMNAS))}{fila_sheet}",
                                [valores]
                            )
                            st.session_state.df_lideres.loc[user_idx, COLUMNAS] = valores
                            st.success(f"✅ Registro actualizado en la fila {fila_sheet}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al actualizar Google Sheets: {e}")
            else:
                st.warning("⚠️ No se encontró ningún registro con esa identificación.")

# ==============================================================================
# MÓDULO 5: BASE COMPLETA
# ==============================================================================
elif menu == "📋 Base de Datos Completa (Edición Directa)":
    st.subheader("📋 Base de Datos Completa (Edición Directa Tipo Excel)")
    st.caption("La tabla utiliza exactamente las columnas reales de la base.")

    if not df_lideres.empty:
        filtro = st.text_input(
            "🔎 Filtrar registros en la vista general:",
            placeholder="Escriba para buscar..."
        )

        # Mantener el índice original para poder actualizar la fila correcta.
        df_vista = df_lideres.copy()

        if filtro.strip():
            term = filtro.strip()
            mask = df_vista.apply(
                lambda col: col.map(limpiar_valor).str.contains(
                    re.escape(term), case=False, na=False
                ),
                axis=0
            ).any(axis=1)
            df_vista = df_vista.loc[mask]

        df_editable = st.data_editor(
            df_vista,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_tabla_completa",
            hide_index=True
        )

        guardar_col, csv_col = st.columns(2)

        with guardar_col:
            if st.button("💾 Guardar Cambios en Google Sheets", use_container_width=True):
                sheet = conectar_google_sheets()
                if sheet:
                    try:
                        # Si el filtro está activo NO se reescribe toda la base.
                        # Se actualizan solamente las filas originales visibles.
                        if filtro.strip():
                            for original_idx in df_vista.index:
                                if original_idx in df_editable.index:
                                    valores = [
                                        limpiar_valor(df_editable.loc[original_idx, col])
                                        for col in COLUMNAS
                                    ]
                                    fila_sheet = original_idx + 3
                                    actualizar_hoja_gspread(
                                        sheet,
                                        f"A{fila_sheet}:AA{fila_sheet}",
                                        [valores]
                                    )
                            st.session_state.df_lideres = cargar_datos()
                        else:
                            # Sin filtro, se actualizan las filas existentes y
                            # no se tocan las dos filas de encabezados.
                            for original_idx in df_vista.index:
                                if original_idx in df_editable.index:
                                    valores = [
                                        limpiar_valor(df_editable.loc[original_idx, col])
                                        for col in COLUMNAS
                                    ]
                                    fila_sheet = original_idx + 3
                                    actualizar_hoja_gspread(
                                        sheet,
                                        f"A{fila_sheet}:AA{fila_sheet}",
                                        [valores]
                                    )
                            st.session_state.df_lideres = cargar_datos()

                        st.success("✅ Cambios guardados correctamente sin alterar los encabezados.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al guardar cambios: {e}")

        with csv_col:
            csv_data = df_editable.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📥 Descargar Vista Actual (CSV)",
                data=csv_data,
                file_name=f"Base_Datos_Lideres_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
