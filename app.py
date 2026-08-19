import streamlit as st
import pandas as pd
import numpy as np
import unicodedata
import re
from datetime import datetime, date
import gspread

# ------------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Ejecutivo de Líderes",
    page_icon="📊",
    layout="wide"
)

# ------------------------------------------------------------------------------
# CONEXIÓN Y CARGA ROBUSTA DE DATOS DESDE GOOGLE SHEETS
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
            if not data or len(data) < 3:
                return pd.DataFrame()
            
            # Encabezados exactos combinando Fila 0 y Fila 1 según la estructura real del archivo
            headers_fijo = [
                "No. Identificación", "Nombres", "Apellidos", "No. Teléfono", 
                "Dependencia", "Secretaría y/o Dependencia", "Apoyo", "Profesión", 
                "Cargo actual", "Correo Electrónico", "Redes Sociales", "Fecha de Cumpleaños", 
                "Total", "Bello", "Otros", "Comuna", "Barrio", 
                "PROYECCIÓN", "REGISTROS", "MUNICIPIO", "NOTAS", 
                "No. Amigos", "MUNICIPIO DE BELLO", "OTROS MUNICIPIOS - DEPTOS", 
                "NO ESTA EN EL CENSO", "CEDULA ERRONEA", "URL_PDF"
            ]

            # Las filas de datos inician a partir de la Fila 2 en el Excel / Google Sheets
            data_rows = data[2:]

            num_cols = len(headers_fijo)
            filas_normalizadas = []
            for row in data_rows:
                if len(row) < num_cols:
                    row = row + [""] * (num_cols - len(row))
                else:
                    row = row[:num_cols]
                filas_normalizadas.append(row)

            df = pd.DataFrame(filas_normalizadas, columns=headers_fijo).astype(str)
            
            for col in df.columns:
                df[col] = df[col].str.replace(".0", "", regex=False)
                df[col] = df[col].replace(["nan", "None", "<NA>", "null", "NaN"], "")
                df[col] = df[col].str.strip()

            return df
        except Exception as e:
            st.error(f"Error al procesar la hoja de datos: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

if "df_lideres" not in st.session_state or st.session_state.df_lideres.empty:
    st.session_state.df_lideres = cargar_datos()

df_lideres = st.session_state.df_lideres

# ------------------------------------------------------------------------------
# LOGIN DE ACCESO
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
# FUNCIONES DE FORMATEO Y LIMPIEZA
# ------------------------------------------------------------------------------
def obtener_val(row, col_name):
    """Devuelve el valor o 'Sin datos' si está vacío."""
    if col_name in row:
        val = str(row[col_name]).strip()
        if val and val.lower() not in ["nan", "none", "null", "<na>", "", "00:00:00"]:
            return val
    return "Sin datos"

def formatear_cumpleanos(val_fecha):
    if not val_fecha or val_fecha == "Sin datos":
        return "Sin datos"
    
    # Tratamiento de fecha tipo string o timestamp
    val_clean = val_fecha.split(" ")[0].replace("-", "/").strip()
    partes = val_clean.split("/")
    
    meses_nombre = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    if len(partes) == 3:
        try:
            # Formato YYYY/MM/DD
            if len(partes[0]) == 4:
                mes = int(partes[1])
                dia = int(partes[2])
            # Formato DD/MM/YYYY
            else:
                dia = int(partes[0])
                mes = int(partes[1])
            if 1 <= mes <= 12:
                return f"{dia} de {meses_nombre[mes]}"
        except ValueError:
            pass
    return val_fecha

# ------------------------------------------------------------------------------
# MENÚ LATERAL Y MÓDULOS
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
# VISTA: CONSULTA DETALLADA (ESTRUCTURA IDÉNTICA A LA PLANTILLA)
# ==============================================================================
if menu == "🔍 Consulta Detallada":
    st.subheader("🔍 Consulta Detallada de Líderes")
    if not df_lideres.empty:
        busqueda = st.text_input("Ingrese Cédula o Nombre para buscar:")
        
        if busqueda.strip():
            mask = df_lideres.astype(str).apply(
                lambda row: row.str.contains(busqueda.strip(), case=False, na=False)
            ).any(axis=1)
            resultado = df_lideres[mask]

            if not resultado.empty:
                for idx, row in resultado.iterrows():
                    nombre = f"{obtener_val(row, 'Nombres')} {obtener_val(row, 'Apellidos')}".replace("Sin datos", "").strip().upper()
                    cedula = obtener_val(row, "No. Identificación")

                    st.markdown(f"## **{nombre or 'NOMBRE NO REGISTRADO'}**")
                    st.markdown(f"**Cédula / Identificación:** {cedula}")
                    st.markdown("---")

                    # CONTENEDOR CON DISEÑO DE LA IMAGEN
                    with st.container(border=True):
                        # FILA SUPERIOR: 3 COLUMNAS
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.markdown("### 📌 **Información Laboral**")
                            st.markdown(f"**Dependencia:** {obtener_val(row, 'Dependencia')}")
                            st.markdown(f"**Secretaría:** {obtener_val(row, 'Secretaría y/o Dependencia')}")
                            st.markdown(f"**Cargo Actual:** {obtener_val(row, 'Cargo actual')}")
                            st.markdown(f"**Profesión:** {obtener_val(row, 'Profesión')}")
                            st.markdown(f"**Líder / Apoyo:** {obtener_val(row, 'Apoyo')}")

                        with col2:
                            st.markdown("### 📞 **Contacto Directo**")
                            st.markdown(f"**Teléfono / Celular:** {obtener_val(row, 'No. Teléfono')}")
                            
                            correo = obtener_val(row, 'Correo Electrónico')
                            if correo != "Sin datos":
                                st.markdown(f"**Correo:** [{correo}](mailto:{correo})")
                            else:
                                st.markdown(f"**Correo:** {correo}")
                                
                            st.markdown(f"**Redes Sociales:** {obtener_val(row, 'Redes Sociales')}")

                        with col3:
                            st.markdown("### 📍 **Ubicación y Fechas**")
                            st.markdown(f"**Municipio:** {obtener_val(row, 'MUNICIPIO')}")
                            st.markdown(f"**Comuna:** {obtener_val(row, 'Comuna')}")
                            st.markdown(f"**Barrio:** {obtener_val(row, 'Barrio')}")
                            cumple_formatted = formatear_cumpleanos(obtener_val(row, 'Fecha de Cumpleaños'))
                            st.markdown(f"**Cumpleaños:** {cumple_formatted}")

                        st.markdown("<br>", unsafe_allow_html=True)

                        # FILA INFERIOR: 2 COLUMNAS
                        col4, col5 = st.columns(2)

                        with col4:
                            st.markdown("### 📌 **Proyección y Notas**")
                            st.markdown(f"**Proyección:** {obtener_val(row, 'PROYECCIÓN')}")
                            st.markdown(f"**Registros:** {obtener_val(row, 'REGISTROS')}")
                            st.markdown(f"**Notas / Observaciones:** {obtener_val(row, 'NOTAS')}")

                        with col5:
                            st.markdown("### 📋 **Planillas y Registros**")
                            st.markdown(f"**No. Amigos:** {obtener_val(row, 'No. Amigos')}")
                            st.markdown(f"**Municipio de Bello:** {obtener_val(row, 'MUNICIPIO DE BELLO')}")
                            st.markdown(f"**Otros Municipios:** {obtener_val(row, 'OTROS MUNICIPIOS - DEPTOS')}")

                    st.markdown("<br>", unsafe_allow_html=True)

            else:
                st.warning("⚠️ No se encontró ningún registro coincidente.")

# ==============================================================================
# VISTA: BASE DE DATOS COMPLETA
# ==============================================================================
elif menu == "📋 Base de Datos Completa":
    st.subheader("📋 Vista General de la Base de Datos")
    st.dataframe(df_lideres, use_container_width=True)
