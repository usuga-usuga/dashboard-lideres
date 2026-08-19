import streamlit as st
import pandas as pd
import unicodedata
import re
from datetime import datetime, date
import io
import gspread

# ReportLab para exportación de PDF
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
# CONEXIÓN Y CARGA DE DATOS DESDE GOOGLE SHEETS
# ------------------------------------------------------------------------------
SHEET_ID = "114059SazWnhrk9vUc12Qdyy4eP6EP6lUI_SLj-inGXA"

@st.cache_resource
def conectar_google_sheets():
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

def cargar_datos():
    sheet = conectar_google_sheets()
    if sheet:
        try:
            data = sheet.get_all_values()
            if not data or len(data) < 2:
                return pd.DataFrame()
            
            fila_1 = [str(c).strip() for c in data[0]]
            fila_2 = [str(c).strip() for c in data[1]] if len(data) > 1 else []

            # Si la fila 1 es un encabezado superior multinivel (ej: PROYECCIÓN Y NOTAS)
            tiene_encabezado_doble = any("PROYECCI" in c.upper() or "PLANILLA" in c.upper() for c in fila_1)

            if tiene_encabezado_doble and len(data) >= 2:
                headers_raw = []
                for i in range(max(len(fila_1), len(fila_2))):
                    h1 = fila_1[i] if i < len(fila_1) else ""
                    h2 = fila_2[i] if i < len(fila_2) else ""
                    # Priorizar el nombre específico de la Fila 2
                    headers_raw.append(h2 if h2 else h1)
                data_rows = data[2:]
            else:
                headers_raw = fila_1
                data_rows = data[1:]

            # Resolver duplicados y celdas vacías
            headers_limpios = []
            vistos = {}
            for i, h in enumerate(headers_raw):
                name = h if h else f"Columna_{i+1}"
                if name in vistos:
                    vistos[name] += 1
                    headers_limpios.append(f"{name}_{vistos[name]}")
                else:
                    vistos[name] = 0
                    headers_limpios.append(name)

            num_cols = len(headers_limpios)
            filas_normalizadas = []
            for row in data_rows:
                if len(row) < num_cols:
                    row = row + [""] * (num_cols - len(row))
                else:
                    row = row[:num_cols]
                filas_normalizadas.append(row)

            df = pd.DataFrame(filas_normalizadas, columns=headers_limpios).astype(str)
            
            for col in df.columns:
                df[col] = df[col].str.replace(".0", "", regex=False)
                df[col] = df[col].replace(["nan", "None", "<NA>", "null"], "")
                df[col] = df[col].str.strip()

            return df
        except Exception as e:
            st.error(f"Error al procesar la hoja: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

if "df_lideres" not in st.session_state or st.session_state.df_lideres.empty:
    st.session_state.df_lideres = cargar_datos()

df_lideres = st.session_state.df_lideres

# ------------------------------------------------------------------------------
# LOGIN
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
                        st.error("❌ Usuario no registrado")
    return False

if not verificar_login():
    st.stop()

# ------------------------------------------------------------------------------
# FUNCIONES BÚSQUEDA EXACTA Y EXTRACTION PATTERNS
# ------------------------------------------------------------------------------
def normalizar(texto):
    if not isinstance(texto, str): return ""
    texto = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn').lower().strip()

def extraer_campo(row, df_cols, patrones, default="Sin datos"):
    """Busca en las columnas del DataFrame la que coincida con patrones regex especificados."""
    for col in df_cols:
        col_norm = normalizar(col)
        for patron in patrones:
            if re.search(r'\b' + re.escape(normalizar(patron)) + r'\b', col_norm):
                val = str(row[col]).strip()
                if val and val.lower() not in ["nan", "none", "null", "<na>", ""]:
                    return val
    return default

NOMBRES_MESES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

def obtener_cumpleanos_formateado(row, df_cols):
    val_dia = extraer_campo(row, df_cols, ["dia", "day", "fecha de cumple"], "")
    val_mes = extraer_campo(row, df_cols, ["mes", "month"], "")
    
    dia, mes = None, None
    if "/" in val_dia or "-" in val_dia:
        partes = val_dia.replace("-", "/").split("/")
        if len(partes) >= 2:
            try: dia, mes = int(partes[0]), int(partes[1])
            except ValueError: pass
    elif val_dia.isdigit() and val_mes.isdigit():
        dia, mes = int(val_dia), int(val_mes)

    if dia and mes and 1 <= mes <= 12:
        return f"{dia} de {NOMBRES_MESES[mes]}"
    return "Sin datos"

# ------------------------------------------------------------------------------
# MÓDULOS DE NAVEGACIÓN
# ------------------------------------------------------------------------------
st.sidebar.title("Módulos del Sistema")
if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.rerun()

if st.sidebar.button("🔄 Recargar datos", use_container_width=True):
    st.cache_resource.clear()
    st.session_state.df_lideres = cargar_datos()
    st.sidebar.success("✅ Base de datos actualizada")
    st.rerun()

menu = st.sidebar.radio("Seleccione una opción:", ["🔍 Consulta Detallada", "📋 Base de Datos Completa"])

# ==============================================================================
# VISTA MÓDULO: CONSULTA DETALLADA (DISEÑO EXACTO A LA IMAGEN)
# ==============================================================================
if menu == "🔍 Consulta Detallada":
    st.subheader("🔍 Consulta Detallada de Líderes")
    if not df_lideres.empty:
        busqueda = st.text_input("Ingrese Cédula o Nombre para buscar:")
        
        if busqueda.strip():
            mask = df_lideres.astype(str).apply(lambda row: row.str.contains(busqueda.strip(), case=False, na=False)).any(axis=1)
            resultado = df_lideres[mask]

            if not resultado.empty:
                for idx, row in resultado.iterrows():
                    cols = df_lideres.columns

                    # Obtención estructurada de campos
                    nombres = extraer_campo(row, cols, ["nombres", "nombre"], "")
                    apellidos = extraer_campo(row, cols, ["apellidos", "apellido"], "")
                    nombre_completo = f"{nombres} {apellidos}".strip().upper() or "NOMBRE NO REGISTRADO"
                    cedula = extraer_campo(row, cols, ["identificacion", "cedula", "doc", "id"])
                    
                    st.markdown(f"## **{nombre_completo}**")
                    st.markdown(f"**Cédula / Identificación:** {cedula}")
                    st.markdown("---")

                    # CONTENEDOR PRINCIPAL TIPO TARJETA
                    with st.container(border=True):
                        # FILA 1: 3 COLUMNAS
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.markdown("### 📌 **Información Laboral**")
                            st.markdown(f"**Dependencia:** {extraer_campo(row, cols, ['dependencia'])}")
                            st.markdown(f"**Secretaría:** {extraer_campo(row, cols, ['secretaria', 'secretaria/entidad'])}")
                            st.markdown(f"**Cargo Actual:** {extraer_campo(row, cols, ['cargo actual', 'cargo'])}")
                            st.markdown(f"**Profesión:** {extraer_campo(row, cols, ['profesion'])}")
                            st.markdown(f"**Líder / Apoyo:** {extraer_campo(row, cols, ['lider / apoyo', 'lider', 'apoyo'])}")

                        with col2:
                            st.markdown("### 📞 **Contacto Directo**")
                            tel = extraer_campo(row, cols, ['telefono / celular', 'telefono', 'celular'])
                            st.markdown(f"**Teléfono / Celular:** {tel}")
                            
                            correo = extraer_campo(row, cols, ['correo', 'email'])
                            if correo != "Sin datos":
                                st.markdown(f"**Correo:** [{correo}](mailto:{correo})")
                            else:
                                st.markdown(f"**Correo:** {correo}")
                                
                            st.markdown(f"**Redes Sociales:** {extraer_campo(row, cols, ['redes sociales', 'redes'])}")

                        with col3:
                            st.markdown("### 📍 **Ubicación y Fechas**")
                            st.markdown(f"**Municipio:** {extraer_campo(row, cols, ['municipio'])}")
                            st.markdown(f"**Comuna:** {extraer_campo(row, cols, ['comuna'])}")
                            st.markdown(f"**Barrio:** {extraer_campo(row, cols, ['barrio'])}")
                            cumple_str = obtener_cumpleanos_formateado(row, cols)
                            st.markdown(f"**Cumpleaños:** {cumple_str}")

                        st.markdown("<br>", unsafe_allow_html=True)

                        # FILA 2: 2 COLUMNAS (PROYECCIÓN Y PLANILLAS)
                        col4, col5 = st.columns([1, 1])

                        with col4:
                            st.markdown("### 📌 **Proyección y Notas**")
                            st.markdown(f"**Proyección:** {extraer_campo(row, cols, ['proyeccion'])}")
                            st.markdown(f"**Registros:** {extraer_campo(row, cols, ['registros'])}")
                            st.markdown(f"**Notas / Observaciones:** {extraer_campo(row, cols, ['notas', 'observaciones'])}")

                        with col5:
                            st.markdown("### 📋 **Planillas y Registros**")
                            st.markdown(f"**No. Amigos:** {extraer_campo(row, cols, ['no. amigos', 'amigos'])}")
                            st.markdown(f"**Municipio de Bello:** {extraer_campo(row, cols, ['municipio o de bello', 'bello'])}")
                            st.markdown(f"**Otros Municipios:** {extraer_campo(row, cols, ['otros municipios - deptos', 'otros municipios'])}")
                            st.markdown(f"**No está en Censo:** {extraer_campo(row, cols, ['no esta en el censo', 'censo'])}")
                            st.markdown(f"**Cédula Errónea:** {extraer_campo(row, cols, ['cedula erronea'])}")

                    st.markdown("<br>", unsafe_allow_html=True)

            else:
                st.warning("⚠️ No se encontró ningún registro coincidente.")

# ==============================================================================
# VISTA MÓDULO: BASE DE DATOS COMPLETA
# ==============================================================================
elif menu == "📋 Base de Datos Completa":
    st.subheader("📋 Vista General de Registros")
    st.dataframe(df_lideres, use_container_width=True)
