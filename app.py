import streamlit as st
import pandas as pd
import gspread
import re
import unicodedata

# 1. Configuración de página
st.set_page_config(page_title="Gestión de Base de Datos", layout="wide")

# Aplica CSS para garantizar visibilidad de textos oscuros
st.markdown("""
    <style>
    .card-title { color: #1E3A8A !important; font-weight: bold; margin-bottom: 10px; }
    .label-text { color: #555555 !important; font-weight: 600; }
    .val-text { color: #111827 !important; font-weight: 500; }
    .stMarkdown p, .stMarkdown span { color: #111827 !important; }
    </style>
""", unsafe_allow_html=True)

# 2. Función auxiliar para normalizar nombres de columnas (quita tildes y pasa a minúsculas)
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.strip().lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = re.sub(r'[\u0300-\u036f]', '', texto)
    return texto

# 3. Conexión con Google Sheets usando Secrets
@st.cache_data(ttl=60)
def cargar_datos():
    try:
        # Autenticación con las credenciales cargadas en Streamlit Secrets
        gc = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
        
        # Reemplaza con tu ID activo de Google Sheets
        SPREADSHEET_ID = "114059SazWnhrk9vUc12Qdyy4eP6EP6lUI_SLj-inGXA" 
        
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.get_worksheet(0)
        
        # Obtiene todos los valores en matriz
        data = worksheet.get_all_values()
        if not data or len(data) < 2:
            return pd.DataFrame()

        # Construye el DataFrame
        raw_columns = [str(col).strip() for col in data[0]]
        df = pd.DataFrame(data[1:], columns=raw_columns)
        
        # Elimina columnas en blanco
        df = df.loc[:, df.columns != '']
        
        return df
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return pd.DataFrame()

# Cargar base de datos
df_raw = cargar_datos()

if df_raw.empty:
    st.warning("No hay datos cargados para mostrar o la tabla está vacía.")
    st.stop()

# 4. Crear mapa de columnas normalizadas
col_map = {normalizar_texto(c): c for c in df_raw.columns}

def obtener_valor(row, *posibles_nombres):
    """Busca en la fila probando distintos nombres posibles de columna."""
    for nombre in posibles_nombres:
        norm = normalizar_texto(nombre)
        if norm in col_map:
            col_real = col_map[norm]
            val = str(row[col_real]).strip()
            if val and val.lower() not in ['nan', 'none', 'null', '0', '']:
                return val
    return "Sin datos"

# 5. Buscador en interfaz
st.title("🔍 Consulta de Registro")
identificacion_busqueda = st.text_input("Ingresa la Cédula o Identificación:", "")

if identificacion_busqueda:
    # Buscar coincidencia
    col_id = None
    for posible in ['cedula', 'identificacion', 'documento', 'id']:
        if posible in col_map:
            col_id = col_map[posible]
            break
            
    if col_id:
        coincidencias = df_raw[df_raw[col_id].astype(str).str.strip() == identificacion_busqueda.strip()]
    else:
        coincidencias = pd.DataFrame()

    if coincidencias.empty:
        st.warning("No se encontraron registros con esa identificación.")
    else:
        st.success(f"Se encontraron {len(coincidencias)} registro(s).")
        row = coincidencias.iloc[0]

        # Extraer variables principales
        nombre = obtener_valor(row, 'nombres', 'nombre', 'nombre completo', 'persona')
        apellido = obtener_valor(row, 'apellidos', 'apellido', '')
        nombre_completo = f"{nombre} {apellido}".replace("Sin datos", "").strip().upper()

        st.markdown(f"# {nombre_completo}")
        st.caption(f"Cédula: {identificacion_busqueda}")

        # Columnas visuales
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("<div class='card-title'>📌 Información Laboral</div>", unsafe_allow_html=True)
            st.markdown(f"**Dependencia:** {obtener_valor(row, 'dependencia')}")
            st.markdown(f"**Secretaría:** {obtener_valor(row, 'secretaria')}")
            st.markdown(f"**Cargo Actual:** {obtener_valor(row, 'cargo', 'cargo actual')}")
            st.markdown(f"**Profesión:** {obtener_valor(row, 'profesion', 'ocupacion')}")
            st.markdown(f"**Líder / Apoyo:** {obtener_valor(row, 'lider', 'lider / apoyo', 'apoyo')}")

        with c2:
            st.markdown("<div class='card-title'>📞 Contacto Directo</div>", unsafe_allow_html=True)
            st.markdown(f"**Teléfono / Celular:** {obtener_valor(row, 'telefono', 'celular')}")
            st.markdown(f"**Correo Electrónico:** {obtener_valor(row, 'correo', 'correo electronico', 'email')}")
            st.markdown(f"**Redes Sociales:** {obtener_valor(row, 'redes', 'redes sociales')}")

        with c3:
            st.markdown("<div class='card-title'>📍 Ubicación y Fechas</div>", unsafe_allow_html=True)
            st.markdown(f"**Comuna:** {obtener_valor(row, 'comuna')}")
            st.markdown(f"**Barrio:** {obtener_valor(row, 'barrio')}")
            st.markdown(f"**Fecha Cumpleaños:** {obtener_valor(row, 'fecha cumpleaños', 'cumpleaños', 'fecha de cumpleaños')}")

        st.divider()
        c4, c5 = st.columns(2)

        with c4:
            st.markdown("<div class='card-title'>📌 Notas de Proyección</div>", unsafe_allow_html=True)
            st.markdown(f"**Proyección:** {obtener_valor(row, 'proyeccion')}")
            st.markdown(f"**Registros:** {obtener_valor(row, 'registros')}")
            st.markdown(f"**Municipio:** {obtener_valor(row, 'municipio')}")
            st.markdown(f"**Notas:** {obtener_valor(row, 'notas', 'observaciones')}")

        with c5:
            st.markdown("<div class='card-title'>📋 Planillas de Votación</div>", unsafe_allow_html=True)
            st.markdown(f"**No. Amigos:** {obtener_valor(row, 'no. amigos', 'amigos', 'nro amigos')}")
            st.markdown(f"**Municipio de Bello:** {obtener_valor(row, 'municipio de bello', 'bello')}")
            st.markdown(f"**Otros Municipios:** {obtener_valor(row, 'otros municipios')}")
