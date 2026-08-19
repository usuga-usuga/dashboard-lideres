import streamlit as st
import pandas as pd
import unicodedata
import io

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA DE STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Dashboard de Líderes",
    page_icon="🔍",
    layout="wide"
)

# ==============================================================================
# CARGA DE DATOS (Soporta archivo local, Google Sheets o File Uploader)
# ==============================================================================
st.sidebar.title("📌 Menú y Configuración")

# Opción 1: Subir el archivo directamente desde la interfaz
archivo_subido = st.sidebar.file_uploader(
    "📂 Cargar base de datos (Excel o CSV)", 
    type=["xlsx", "xls", "csv"]
)

@st.cache_data(ttl=600)
def cargar_datos_locales():
    """Intenta cargar un archivo local si existe en el proyecto."""
    for nombre_archivo in ["base_lideres.xlsx", "base_lideres.csv", "datos.xlsx", "datos.csv"]:
        try:
            if nombre_archivo.endswith('.csv'):
                return pd.read_csv(nombre_archivo)
            else:
                return pd.read_excel(nombre_archivo)
        except Exception:
            continue
    return pd.DataFrame()

# Determinación del DataFrame a usar
if archivo_subido is not None:
    try:
        if archivo_subido.name.endswith('.csv'):
            df_lideres = pd.read_csv(archivo_subido)
        else:
            df_lideres = pd.read_excel(archivo_subido)
    except Exception as e:
        st.sidebar.error(f"Error al leer el archivo cargado: {e}")
        df_lideres = pd.DataFrame()
else:
    df_lideres = cargar_datos_locales()

# ==============================================================================
# MENÚ NAVEGACIÓN LATERAL
# ==============================================================================
menu = st.sidebar.radio(
    "Seleccione una opción:",
    ["🔍 Consulta Detallada", "📊 Resumen General"],
    index=0
)

# ==============================================================================
# FUNCIONES AUXILIARES Y NORMALIZACIÓN
# ==============================================================================
def normalizar(texto):
    """Normaliza texto eliminando tildes, mayúsculas y espacios extra."""
    if not isinstance(texto, str):
        texto = str(texto)
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.lower().strip()

def buscar_columna_df(df_cols, alias_list):
    """Encuentra la columna real dentro del DataFrame según alias."""
    for alias in alias_list:
        alias_norm = normalizar(alias)
        for col in df_cols:
            col_norm = normalizar(str(col))
            if alias_norm == col_norm or alias_norm in col_norm:
                return col
    return None

def obtener_valor_inteligente(row, df_cols, alias_list, default="Sin datos", cols_usadas=None):
    """Busca y extrae el valor correcto evitando columnas duplicadas."""
    col_encontrada = buscar_columna_df(df_cols, alias_list)
    if col_encontrada:
        if cols_usadas is not None:
            cols_usadas.add(col_encontrada)
        val = str(row[col_encontrada]).strip()
        if val and val.lower() not in ["nan", "none", "null", "<na>", ""]:
            return val
    return default

def obtener_fecha_cumpleanos_formateada(row, df_cols, cols_usadas=None):
    """Busca y da formato legible al cumpleaños."""
    val = obtener_valor_inteligente(row, df_cols, ["cumpleanos", "cumpleaños", "fecha nacimiento"], "Sin datos", cols_usadas)
    if val != "Sin datos":
        try:
            fecha_dt = pd.to_datetime(val)
            return fecha_dt.strftime("%d de %B")
        except Exception:
            return val
    return val

def generar_pdf_ficha(row, df_cols):
    """Generador de respaldo para la función de descarga en PDF."""
    buffer = io.BytesIO()
    buffer.write(b"%PDF-1.4 Ficha de Registro")
    buffer.seek(0)
    return buffer.getvalue()

# ==============================================================================
# MÓDULO 1: CONSULTA DETALLADA
# ==============================================================================
if menu == "🔍 Consulta Detallada":
    st.title("🔍 Consulta Detallada de Líderes")

    if not df_lideres.empty:
        criterio = st.radio("Buscar por:", ["Cédula / Identificación", "Nombre / Apellido"], horizontal=True)
        busqueda = st.text_input("Ingrese término de búsqueda:")
        
        resultado = pd.DataFrame()
        if busqueda.strip():
            mask = df_lideres.astype(str).apply(
                lambda row: row.str.contains(busqueda.strip(), case=False, na=False)
            ).any(axis=1)
            resultado = df_lideres[mask]

        if not resultado.empty:
            st.success(f"✅ Se encontraron {len(resultado)} registro(s).")

            for idx, row in resultado.iterrows():
                cols_usadas = set()

                # 1. Identificación y Nombres
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

                # 5. Proyección y Notas
                proyeccion = obtener_valor_inteligente(row, df_lideres.columns, ["proyeccion", "proyección"], "Sin datos", cols_usadas)
                registros = obtener_valor_inteligente(row, df_lideres.columns, ["registros", "registro"], "Sin datos", cols_usadas)
                notas = obtener_valor_inteligente(row, df_lideres.columns, ["notas / observaciones", "notas", "observaciones", "comentarios"], "Sin datos", cols_usadas)

                # 6. Planillas y Registros (Incluye Censo)
                amigos = obtener_valor_inteligente(row, df_lideres.columns, ["no. amigos", "nro amigos", "amigos"], "0", cols_usadas)
                bello = obtener_valor_inteligente(row, df_lideres.columns, ["municipio de bello", "bello"], "Sin datos", cols_usadas)
                otros_muni = obtener_valor_inteligente(row, df_lideres.columns, ["otros municipios"], "Sin datos", cols_usadas)
                censo = obtener_valor_inteligente(row, df_lideres.columns, ["no esta en el censo", "censo", "no censo"], "Sin datos", cols_usadas)

                # --- RENDERIZADO TARJETAS ---
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

                    # Fila 1
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        with st.container(border=True):
                            st.markdown("### 📌 Información Laboral")
                            st.markdown(f"**Dependencia:** {dependencia}")
                            st.markdown(f"**Secretaría:** {secretaria}")
                            st.markdown(f"**Cargo Actual:** {cargo}")
                            st.markdown(f"**Profesión:** {profesion}")
                            st.markdown(f"**Líder / Apoyo:** {lider_apoyo}")

                    with col2:
                        with st.container(border=True):
                            st.markdown("### 📞 Contacto Directo")
                            st.markdown(f"**Teléfono / Celular:** {telefono}")
                            st.markdown(f"**Correo:** [{correo}](mailto:{correo})" if correo != "Sin datos" else "**Correo:** Sin datos")
                            st.markdown(f"**Redes Sociales:** {redes}")

                    with col3:
                        with st.container(border=True):
                            st.markdown("### 📍 Ubicación y Fechas")
                            st.markdown(f"**Municipio:** {municipio}")
                            st.markdown(f"**Comuna:** {comuna}")
                            st.markdown(f"**Barrio:** {barrio}")
                            st.markdown(f"**Cumpleaños:** {cumpleanos}")

                    # Fila 2
                    col4, col5 = st.columns(2)
                    with col4:
                        with st.container(border=True):
                            st.markdown("### 📌 Proyección y Notas")
                            st.markdown(f"**Proyección:** {proyeccion}")
                            st.markdown(f"**Registros:** {registros}")
                            st.markdown(f"**Notas / Observaciones:** {notas}")

                    with col5:
                        with st.container(border=True):
                            st.markdown("### 📋 Planillas y Registros")
                            st.markdown(f"**No. Amigos:** {amigos}")
                            st.markdown(f"**Municipio de Bello:** {bello}")
                            st.markdown(f"**Otros Municipios:** {otros_muni}")
                            st.markdown(f"**No está en el censo:** {censo}")

                    # Fila 3: Captura de datos extra no asignados
                    cols_restantes = [
                        c for c in df_lideres.columns 
                        if c not in cols_usadas and normalizar(str(c)) not in ["url_pdf", "pdf", "link", "planilla"]
                    ]
                    
                    extra_data = []
                    for col in cols_restantes:
                        v = str(row[col]).strip()
                        if v and v.lower() not in ["nan", "none", "<na>", "null", ""]:
                            extra_data.append((col, v))
                    
                    if extra_data:
                        mitad = (len(extra_data) + 1) // 2
                        col_add1, col_add2 = st.columns(2)
                        with col_add1:
                            with st.container(border=True):
                                st.markdown("### 📂 Información Complementaria")
                                for k, v in extra_data[:mitad]:
                                    st.markdown(f"**{k}:** {v}")
                        with col_add2:
                            if extra_data[mitad:]:
                                with st.container(border=True):
                                    st.markdown("### 📊 Datos Adicionales")
                                    for k, v in extra_data[mitad:]:
                                        st.markdown(f"**{k}:** {v}")

                st.markdown("---")
        elif busqueda:
            st.warning("⚠️ No se localizó ningún registro.")
    else:
        st.info("👈 **Para comenzar:** Carga tu archivo `.xlsx` o `.csv` desde el menú lateral en el botón **'Cargar base de datos'**, o ubica tu archivo como `base_lideres.xlsx` dentro del directorio del proyecto.")

elif menu == "📊 Resumen General":
    st.title("📊 Resumen General")
    if not df_lideres.empty:
        st.metric("Total Registros", len(df_lideres))
        st.dataframe(df_lideres.head(20), use_container_width=True)
    else:
        st.info("👈 Por favor carga una base de datos en la barra lateral para ver los indicadores.")
