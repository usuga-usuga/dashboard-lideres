import streamlit as st
import pandas as pd

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN INICIAL DE PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Plataforma de Gestión de Líderes",
    page_icon="📊",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. FIX DEFINITIVO DE ESTILOS CSS GLOBALES
# Soluciona problemas de visibilidad, tarjetas blancas y texto invisible
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Fondo principal de la aplicación */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
    }

    /* FIX PARA TARJETAS DE MÉTRICAS (st.metric) */
    div[data-testid="stMetric"], 
    div[data-testid="metric-container"],
    .stMetric {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.3) !important;
    }

    /* Etiqueta / Título de la métrica */
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] *,
    div[data-testid="stMetricLabel"] * {
        color: #38BDF8 !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }

    /* Valor numérico de la métrica */
    div[data-testid="stMetric"] [data-testid="stMetricValue"] *,
    div[data-testid="stMetricValue"] * {
        color: #FFFFFF !important;
        font-weight: 800 !important;
        font-size: 1.8rem !important;
    }

    /* FIX PARA FORMULARIOS (st.form) Y CONTENEDORES */
    div[data-testid="stForm"], .stForm, form {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 24px !important;
    }

    /* Forzar visibilidad y color en TODOS los textos y etiquetas */
    p, span, label, h1, h2, h3, h4, h5, h6,
    [data-testid="stForm"] label,
    [data-testid="stForm"] .stWidgetLabel p {
        color: #F8FAFC !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }

    /* Títulos destacados dentro de formularios */
    [data-testid="stSubheader"] *, .stSubheader * {
        color: #38BDF8 !important;
        font-weight: 700 !important;
    }

    /* Estilos de inputs, selects y textareas */
    input[type="text"], input[type="number"], textarea, select {
        background-color: #0F172A !important;
        color: #FFFFFF !important;
        border: 1px solid #475569 !important;
        border-radius: 6px !important;
    }

    input:focus, textarea:focus {
        border-color: #38BDF8 !important;
        outline: none !important;
    }

    /* Botones de formulario */
    div[data-testid="stForm"] button[type="submit"] {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
    }

    div[data-testid="stForm"] button[type="submit"]:hover {
        background-color: #1D4ED8 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# 3. FUNCIONES DE APOYO Y CARGA DE DATOS
# -----------------------------------------------------------------------------
def limpiar_valor(val):
    if pd.isna(val):
        return ""
    val_str = str(val).strip()
    if val_str.endswith(".0"):
        val_str = val_str[:-2]
    return val_str

def valor(row, col):
    if col in row and pd.notna(row[col]):
        v = str(row[col]).strip()
        return "" if v == "nan" else v
    return ""

@st.cache_data
def obtener_datos():
    # Sustituir por la carga real de tu CSV o Excel
    # Ejemplo: return pd.read_csv("lideres.csv")
    datos_demo = {
        "No. Identificacion": ["15513554", "98765432"],
        "Nombres": ["WILFREDO", "MARIA"],
        "Apellidos": ["USUGA USUGA", "GOMEZ"],
        "No. Telefono": ["3017732219", "3000000000"],
        "Correo Electronico": ["usuga03@gmail.com", "maria@gmail.com"],
        "Fecha de Cumpleanos": ["1985-05-12", "1990-10-20"],
        "Redes Sociales": ["@wilfredo", "@maria"],
        "Dependencia": ["Municipio", "Salud"],
        "Secretaria y/o Dependencia": ["Edunorte", "Gobierno"],
        "Cargo actual": ["Soporte técnico", "Auxiliar"],
        "Profesion": ["Ingeniero", "Administradora"],
        "Apoyo": ["Si", "No"],
        "Comuna": ["10", "02"],
        "Barrio": ["Machado", "Centro"],
        "Bello": [150, 80],
        "Otros": [20, 10],
        "Total": [170, 90],
        "PROYECCION": [500, 300],
        "REGISTROS": [450, 280],
        "MUNICIPIO PROYECTADO": ["Bello", "Bello"],
        "NOTAS": ["Líder zona norte", "Sin observaciones"],
        "MUNICIPIO DE BELLO": [150, 80],
        "OTROS MUNICIPIOS - DEPTOS": [20, 10],
        "NO ESTA EN EL CENSO": [5, 2],
        "CEDULA ERRONEA": [1, 0],
        "Total No. Amigos": [1600, 800],
        "URL_PDF": ["https://drive.google.com/file/d/15KcdPPY6rVibYppbYKSkQeXC6CpCZJc/view", ""]
    }
    return pd.DataFrame(datos_demo)

# Guardar en Session State para mantener ediciones
if "df_lideres" not in st.session_state:
    st.session_state.df_lideres = obtener_datos()

df_lideres = st.session_state.df_lideres

# -----------------------------------------------------------------------------
# 4. MENÚ NAVEGACIÓN LATERAL
# -----------------------------------------------------------------------------
st.sidebar.title("📌 Menú Principal")
menu = st.sidebar.radio(
    "Seleccione una opción:",
    ["📊 Dashboard General", "📋 Listado de Líderes", "✏️ Editar Líder"]
)

# -----------------------------------------------------------------------------
# 5. MÓDULO 1: DASHBOARD GENERAL
# -----------------------------------------------------------------------------
if menu == "📊 Dashboard General":
    st.title("📊 Dashboard General de Líderes")
    st.markdown("Visión global de registros, proyecciones y votos.")
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    total_registros = len(df_lideres)
    total_amigos = int(pd.to_numeric(df_lideres["Total No. Amigos"], errors='coerce').sum() or 0)
    proyeccion_total = int(pd.to_numeric(df_lideres["PROYECCION"], errors='coerce').sum() or 0)
    total_votantes = int(pd.to_numeric(df_lideres["Total"], errors='coerce').sum() or 0)

    with col1:
        st.metric(label="Total Registros", value=f"{total_registros:,}")
    with col2:
        st.metric(label="Total Amigos", value=f"{total_amigos:,}")
    with col3:
        st.metric(label="Proyección Total", value=f"{proyeccion_total:,}")
    with col4:
        st.metric(label="Total Votantes", value=f"{total_votantes:,}")

    st.markdown("---")
    st.dataframe(df_lideres, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. MÓDULO 2: LISTADO DE LÍDERES
# -----------------------------------------------------------------------------
elif menu == "📋 Listado de Líderes":
    st.title("📋 Listado Consolidado de Líderes")
    st.dataframe(df_lideres, use_container_width=True, height=500)

# -----------------------------------------------------------------------------
# 7. MÓDULO 3: EDITAR LÍDER POR CÉDULA
# -----------------------------------------------------------------------------
elif menu == "✏️ Editar Líder":
    st.title("✏️ Editar Información de Líder")

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
                        st.session_state.df_lideres.loc[idx_row, "Nombres"] = new_nombres
                        st.session_state.df_lideres.loc[idx_row, "Apellidos"] = new_apellidos
                        st.session_state.df_lideres.loc[idx_row, "No. Telefono"] = new_tel
                        st.session_state.df_lideres.loc[idx_row, "Correo Electronico"] = new_correo
                        st.session_state.df_lideres.loc[idx_row, "Fecha de Cumpleanos"] = new_cumple
                        st.session_state.df_lideres.loc[idx_row, "Redes Sociales"] = new_redes
                        st.session_state.df_lideres.loc[idx_row, "Dependencia"] = new_dep
                        st.session_state.df_lideres.loc[idx_row, "Secretaria y/o Dependencia"] = new_sec
                        st.session_state.df_lideres.loc[idx_row, "Cargo actual"] = new_cargo
                        st.session_state.df_lideres.loc[idx_row, "Profesion"] = new_prof
                        st.session_state.df_lideres.loc[idx_row, "Apoyo"] = new_apoyo
                        st.session_state.df_lideres.loc[idx_row, "Comuna"] = new_comuna
                        st.session_state.df_lideres.loc[idx_row, "Barrio"] = new_barrio

                        st.session_state.df_lideres.loc[idx_row, "Bello"] = new_bello
                        st.session_state.df_lideres.loc[idx_row, "Otros"] = new_otros
                        st.session_state.df_lideres.loc[idx_row, "Total"] = new_total
                        st.session_state.df_lideres.loc[idx_row, "PROYECCION"] = new_proy
                        st.session_state.df_lideres.loc[idx_row, "REGISTROS"] = new_registros
                        st.session_state.df_lideres.loc[idx_row, "MUNICIPIO PROYECTADO"] = new_mun_proy
                        st.session_state.df_lideres.loc[idx_row, "NOTAS"] = new_notas

                        st.session_state.df_lideres.loc[idx_row, "MUNICIPIO DE BELLO"] = new_mun_bello
                        st.session_state.df_lideres.loc[idx_row, "OTROS MUNICIPIOS - DEPTOS"] = new_otros_mun
                        st.session_state.df_lideres.loc[idx_row, "NO ESTA EN EL CENSO"] = new_no_censo
                        st.session_state.df_lideres.loc[idx_row, "CEDULA ERRONEA"] = new_ced_erronea
                        st.session_state.df_lideres.loc[idx_row, "Total No. Amigos"] = new_tot_amigos
                        st.session_state.df_lideres.loc[idx_row, "URL_PDF"] = new_url_pdf

                        st.success("✅ Cambios guardados exitosamente.")
                        st.rerun()
            else:
                st.info("No se encontró ningún registro con esa cédula.")
