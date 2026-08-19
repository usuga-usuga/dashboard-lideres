import streamlit as st
import pandas as pd
import unicodedata
import io
import os

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Dashboard de Líderes",
    page_icon="🔍",
    layout="wide"
)

# ==============================================================================
# CARGA AUTOMÁTICA DE DATOS
# ==============================================================================
@st.cache_data(ttl=600)
def cargar_datos_automatico():
    """Busca y carga automáticamente el archivo de datos del proyecto."""
    archivos_posibles = [
        "base_lideres.xlsx", "base_lideres.csv", 
        "lideres.xlsx", "lideres.csv",
        "Lideres.xlsx", "Lideres.csv",
        "datos.xlsx", "datos.csv"
    ]
    
    # 1. Buscar archivos con nombres conocidos
    for nombre in archivos_posibles:
        if os.path.exists(nombre):
            try:
                if nombre.endswith('.csv'):
                    return pd.read_csv(nombre)
                else:
                    return pd.read_excel(nombre)
            except Exception:
                continue

    # 2. Si no encuentra nombres específicos, busca cualquier .xlsx o .csv en la carpeta
    try:
        archivos_carpeta = os.listdir('.')
        for f in archivos_carpeta:
            if f.endswith('.xlsx') or f.endswith('.xls'):
                return pd.read_excel(f)
            elif f.endswith('.csv'):
                return pd.read_csv(f)
    except Exception:
        pass
        
    return pd.DataFrame()

# Cargar base principal
df_lideres = cargar_datos_automatico()

# Carga manual por si el archivo tiene otro nombre
st.sidebar.title("📌 Menú de Navegación")

if df_lideres.empty:
    st.sidebar.warning("⚠️ No se detectó archivo automático.")
    archivo_subido = st.sidebar.file_uploader("Suba su archivo Excel/CSV:", type=["xlsx", "xls", "csv"])
    if archivo_subido is not None:
        if archivo_subido.name.endswith('.csv'):
            df_lideres = pd.read_csv(archivo_subido)
        else:
            df_lideres = pd.read_excel(archivo_subido)

menu = st.sidebar.radio(
    "Seleccione un módulo:",
    ["🔍 Consulta Detallada", "📊 Resumen General"],
    index=0
)

# ==============================================================================
# FUNCIONES AUXILIARES Y NORMALIZACIÓN
# ==============================================================================
def normalizar(texto):
    if not isinstance(texto, str):
        texto = str(texto)
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.lower().strip()

def buscar_columna_df(df_cols, alias_list):
    for alias in alias_list:
        alias_norm = normalizar(alias)
        for col in df_cols:
            col_norm = normalizar(str(col))
            if alias_norm == col_norm or alias_norm in col_norm:
                return col
    return None

def obtener_valor_inteligente(row, df_cols, alias_list, default="Sin datos", cols_usadas=None):
    col_encontrada = buscar_columna_df(df_cols, alias_list)
    if col_encontrada:
        if cols_usadas is not None:
            cols_usadas.add(col_encontrada)
        val = str(row[col_encontrada]).strip()
        if val and val.lower() not in ["nan", "none", "null", "<na>", ""]:
            return val
    return default

def obtener_fecha_cumpleanos_formateada(row, df_cols, cols_usadas=None):
    val = obtener_valor_inteligente(row, df_cols, ["cumpleanos", "cumpleaños", "fecha nacimiento"], "Sin datos", cols_usadas)
    if val != "Sin datos":
        try:
            fecha_dt = pd.to_datetime(val)
            return fecha_dt.strftime("%d de %B")
        except Exception:
            return val
    return val

def generar_pdf_ficha(row, df_cols):
    buffer = io.BytesIO()
    buffer.write(b"%PDF-1.4 Ficha Tecnicas")
    buffer.seek(0)
    return buffer.getvalue()

# ==============================================================================
# MÓDULO 1: CONSULTA DETALLADA (MOSTRAR TARJETAS)
# ==============================================================================
if menu == "🔍 Consulta Detallada":
    st.title("🔍 Consulta Detallada de Líderes")

    if not df_lideres.empty:
        # Selector para ver todos los registros o realizar búsqueda
        ver_todos = st.checkbox("Mover/Ver todos los registros sin buscar", value=False)
        busqueda = st.text_input("Ingrese término de búsqueda (Nombre, Cédula, Municipio, etc.):")
        
        resultado = pd.DataFrame()
        if ver_todos:
            resultado = df_lideres.copy()
        elif busqueda.strip():
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

                # 6. Planillas y Registros
                amigos = obtener_valor_inteligente(row, df_lideres.columns, ["no. amigos", "nro amigos", "amigos"], "0", cols_usadas)
                bello = obtener_valor_inteligente(row, df_lideres.columns, ["municipio de bello", "bello"], "Sin datos", cols_usadas)
                otros_muni = obtener_valor_inteligente(row, df_lideres.columns, ["otros municipios"], "Sin datos", cols_usadas)
                censo = obtener_valor_inteligente(row, df_lideres.columns, ["no esta en el censo", "censo", "no censo"], "Sin datos", cols_usadas)

                # --- TARJETA PRINCIPAL DE LÍDER ---
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

                    # Bloque 1
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

                    # Bloque 2
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

                    # Bloque 3: Datos no mapeados
                    cols_restantes = [c for c in df_lideres.columns if c not in cols_usadas]
                    extra_data = []
                    for col in cols_restantes:
                        v = str(row[col]).strip()
                        if v and v.lower() not in ["nan", "none", "<na>", "null", ""]:
                            extra_data.append((col, v))
                    
                    if extra_data:
                        with st.expander("📂 Ver otros datos de este registro"):
                            for k, v in extra_data:
                                st.write(f"**{k}:** {v}")

                st.markdown("---")
        elif busqueda:
            st.warning("⚠️ No se encontró ningún registro que coincida con el término buscado.")
        else:
            st.info("💡 Escriba un nombre, cédula o dato en el buscador para consultar o marque la casilla 'Mover/Ver todos los registros'.")
    else:
        st.error("❌ No hay datos cargados. Por favor, suba el archivo de Excel usando el botón de la barra lateral izquierda.")

elif menu == "📊 Resumen General":
    st.title("📊 Resumen General")
    if not df_lideres.empty:
        st.metric("Total de Registros Cargados", len(df_lideres))
        st.dataframe(df_lideres, use_container_width=True)
    else:
        st.warning("No hay datos para mostrar.")
