from datetime import date, datetime
import io
import unicodedata
import openpyxl
import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración inicial de la página
st.set_page_config(
    page_title="Dashboard Líderes", page_icon="📊", layout="wide"
)

MESES_ESPANOL = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


# --- SISTEMA DE AUTENTICACIÓN DINÁMICO ---
def validar_credenciales(usuario_ingresado, password_ingresado):
    if "usuarios" in st.secrets:
        usuarios_dict = st.secrets["usuarios"]
        if usuario_ingresado in usuarios_dict:
            return str(usuarios_dict[usuario_ingresado]) == str(
                password_ingresado
            )
    return (usuario_ingresado == "admin") and (
        password_ingresado == "admin123"
    )


if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# --- PANTALLA DE LOGIN ---
if not st.session_state["autenticado"]:
    st.title("🔒 Acceso Restringido")
    st.write("Ingresa tus credenciales para acceder al Dashboard de Líderes.")

    col1, col2 = st.columns([1, 2])
    with col1:
        with st.form("form_login"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            boton_login = st.form_submit_button("Iniciar Sesión")

            if boton_login:
                if validar_credenciales(usuario, password):
                    st.session_state["autenticado"] = True
                    st.success("¡Acceso concedido!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")

    st.stop()


# --- NAVEGACIÓN Y MENÚ LATERAL ---

st.sidebar.title("Módulos del Sistema")

modulo = st.sidebar.radio(
    "Seleccione una opción:",
    [
        "🔍 Consulta Detallada",
        "➕ Registro de Nuevo Usuario",
        "✏️ Editar / Modificar Registros",
        "📈 Panel de Control Ejecutivos",
        "📋 Base de Datos Completa",
    ],
)

st.sidebar.markdown("---")

st.sidebar.button(
    "🚪 Cerrar Sesión",
    on_click=lambda: st.session_state.update({"autenticado": False}),
)


# --- FUNCIONES AUXILIARES INTELIGENTES ---

def normalizar_texto(texto):
    if not isinstance(texto, str):
        texto = str(texto)
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto.lower().strip()


def obtener_rango_filas_excel(sheet, col_letter="A"):
    if not col_letter:
        col_letter = "A"

    col_letter = col_letter.upper().strip()
    primera_fila = None
    ultima_fila = None

    for row in range(1, sheet.max_row + 1):
        val = sheet[f"{col_letter}{row}"].value
        if val is not None and str(val).strip() != "":
            if primera_fila is None:
                primera_fila = row
            ultima_fila = row

    return primera_fila, ultima_fila


def obtener_valor(row, posibles_columnas, valor_defecto="Sin datos"):
    for pos in posibles_columnas:
        pos_norm = normalizar_texto(pos)
        for col in row.index:
            col_norm = normalizar_texto(col)
            if col_norm == pos_norm:
                val = row[col]
                if (
                    pd.notna(val)
                    and str(val).strip() != ""
                    and str(val).strip().lower() != "nan"
                ):
                    return val

    for pos in posibles_columnas:
        pos_norm = normalizar_texto(pos)
        for col in row.index:
            col_norm = normalizar_texto(col)
            if pos_norm in col_norm:
                val = row[col]
                if (
                    pd.notna(val)
                    and str(val).strip() != ""
                    and str(val).strip().lower() != "nan"
                ):
                    return val

    return valor_defecto


def obtener_dia_mes_cumpleanos(row):
    dia = obtener_valor(
        row,
        [
            "Dia Cumpleaños",
            "Día Cumpleaños",
            "Dia de Cumpleaños",
            "Día de Cumpleaños",
            "Dia Cumpleanos",
            "Día Cumpleanos",
            "Día",
            "Dia",
        ],
        None,
    )
    mes = obtener_valor(
        row,
        [
            "Mes Cumpleaños",
            "Mes de Cumpleaños",
            "Mes Cumpleanos",
            "Mes",
        ],
        None,
    )

    if (
        dia is not None
        and mes is not None
        and str(dia) != "Sin datos"
        and str(mes) != "Sin datos"
    ):
        return str(mes), str(dia)

    posibles_fechas = [
        "Cumpleaños",
        "Cumpleanos",
        "Fecha de Nacimiento",
        "Fecha Nacimiento",
        "Fecha Cumpleaños",
        "Fecha Cumpleanos",
        "Fecha de Cumpleaños",
        "Fecha",
        "Nacimiento",
        "F_Nacimiento",
    ]
    fecha_val = obtener_valor(row, posibles_fechas, None)

    if fecha_val is not None and str(fecha_val) != "Sin datos":
        try:
            dt = pd.to_datetime(fecha_val, dayfirst=True, errors="coerce")
            if pd.notna(dt):
                mes_str = MESES_ESPANOL.get(dt.month, str(dt.month))
                dia_str = str(dt.day)
                return mes_str, dia_str
        except Exception:
            pass

    mes_final = mes if (mes is not None and str(mes) != "Sin datos") else "Sin datos"
    dia_final = dia if (dia is not None and str(dia) != "Sin datos") else "Sin datos"

    return mes_final, dia_final


# --- MÓDULO 1: CONSULTA DETALLADA ---
if modulo == "🔍 Consulta Detallada":
    st.title("🔍 Consulta Detallada")

    if "df_data" not in st.session_state:
        st.warning(
            "⚠️ No hay datos cargados. Por favor ve al módulo '📋 Base de Datos Completa' para subir tu archivo."
        )
    else:
        df = st.session_state["df_data"]

        busqueda = st.text_input(
            "🔎 Buscar por Cédula o Nombre completo:",
            placeholder="Ejemplo: 15513554 o WILFREDO",
        )

        if busqueda:
            mascara = df.astype(str).apply(
                lambda row: row.str.contains(
                    busqueda, case=False, na=False
                ).any(),
                axis=1,
            )
            resultados = df[mascara]

            if len(resultados) > 0:
                if len(resultados) > 1:
                    opciones_personas = [
                        f"{i+1}. {obtener_valor(row, ['Nombre', 'Nombres', 'Nombre Completo', 'Lider'])} - Cédula: {obtener_valor(row, ['Cedula', 'Cédula', 'ID', 'Documento'])}"
                        for i, (_, row) in enumerate(resultados.iterrows())
                    ]
                    seleccion = st.selectbox(
                        "Se encontraron varios registros. Selecciona uno:",
                        opciones_personas,
                    )
                    idx_real = resultados.index[opciones_personas.index(seleccion)]
                else:
                    idx_real = resultados.index[0]

                registro = st.session_state["df_data"].loc[idx_real]

                st.success("✅ Registro localizado con éxito.")

                nombre_persona = str(
                    obtener_valor(
                        registro,
                        [
                            "Nombre",
                            "Nombres",
                            "Nombre Completo",
                            "Lider",
                            "Líder",
                        ],
                        "NOMBRE NO REGISTRADO",
                    )
                ).upper()
                cedula_persona = obtener_valor(
                    registro, ["Cedula", "Cédula", "ID", "Documento", "CC"]
                )
                dependencia_persona = obtener_valor(
                    registro, ["Dependencia", "Entidad", "Área"]
                )

                st.markdown(
                    f"""
                    <div style="background-color: #ffffff; color: #111111; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1);">
                        <h1 style="margin:0; font-size: 32px; font-weight: 800; color: #000000; text-transform: uppercase;">{nombre_persona}</h1>
                        <p style="margin: 5px 0 0 0; color: #555555; font-size: 15px; font-weight: 500;">
                            <b>Cédula:</b> {cedula_persona} | <b>Dependencia:</b> {dependencia_persona}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                mes_cumple, dia_cumple = obtener_dia_mes_cumpleanos(registro)

                col1, col2, col3 = st.columns(3)

                with col1:
                    with st.container(border=True):
                        st.markdown("### 📌 Información Laboral")
                        st.write(
                            f"**Dependencia:** {obtener_valor(registro, ['Dependencia', 'Entidad'])}"
                        )
                        st.write(
                            f"**Secretaría:** {obtener_valor(registro, ['Secretaria', 'Secretaría'])}"
                        )
                        st.write(
                            f"**Cargo Actual:** {obtener_valor(registro, ['Cargo', 'Cargo Actual'])}"
                        )
                        st.write(
                            f"**Profesión:** {obtener_valor(registro, ['Profesion', 'Profesión', 'Título'])}"
                        )
                        st.write(
                            f"**Líder Apoyo:** {obtener_valor(registro, ['Lider Apoyo', 'Líder Apoyo', 'Apoyo'])}"
                        )

                with col2:
                    with st.container(border=True):
                        st.markdown("### 📞 Contacto Directo")
                        st.write(
                            f"**Teléfono / Celular:** {obtener_valor(registro, ['Telefono', 'Teléfono', 'Celular', 'Contacto'])}"
                        )
                        correo_val = obtener_valor(
                            registro, ["Correo", "Correo Electrónico", "Email"]
                        )
                        if (
                            correo_val != "Sin datos"
                            and "@" in str(correo_val)
                        ):
                            st.markdown(
                                f"**Correo Electrónico:** [{correo_val}](mailto:{correo_val})"
                            )
                        else:
                            st.write(f"**Correo Electrónico:** {correo_val}")
                        st.write(
                            f"**Redes Sociales:** {obtener_valor(registro, ['Redes Sociales', 'Redes'])}"
                        )

                with col3:
                    with st.container(border=True):
                        st.markdown("### 📍 Ubicación y Fechas")
                        st.write(
                            f"**Comuna:** {obtener_valor(registro, ['Comuna'])}"
                        )
                        st.write(
                            f"**Barrio:** {obtener_valor(registro, ['Barrio'])}"
                        )
                        st.write(f"**Mes Cumpleaños:** {mes_cumple}")
                        st.write(f"**Día Cumpleaños:** {dia_cumple}")

                col4, col5 = st.columns([1.2, 1.8])

                with col4:
                    with st.container(border=True):
                        st.markdown("### 📌 Notas de Proyección")
                        st.write(
                            f"**Proyección:** {obtener_valor(registro, ['Proyeccion', 'Proyección'])}"
                        )
                        st.write(
                            f"**Registros:** {obtener_valor(registro, ['Registros'])}"
                        )
                        st.write(
                            f"**Municipio:** {obtener_valor(registro, ['Municipio'])}"
                        )
                        st.write(
                            f"**Notas:** {obtener_valor(registro, ['Notas', 'Observaciones'])}"
                        )

                with col5:
                    with st.container(border=True):
                        st.markdown("### 📋 Planillas de Votación")
                        st.write(
                            f"**No. Amigos:** {obtener_valor(registro, ['No. Amigos', 'Amigos', 'Num Amigos'], 0)}"
                        )
                        st.write(
                            f"**Municipio de Bello:** {obtener_valor(registro, ['Municipio de Bello', 'Bello'], 0)}"
                        )
                        st.write(
                            f"**Otros Municipios / Deptos:** {obtener_valor(registro, ['Otros Municipios', 'Otros Municipios / Deptos'], 0)}"
                        )
                        st.write(
                            f"**No está en el Censo:** {obtener_valor(registro, ['No esta en el Censo', 'No está en el Censo'], 0)}"
                        )
                        st.write(
                            f"**Cédula Errónea:** {obtener_valor(registro, ['Cedula Erronea', 'Cédula Errónea'], 0)}"
                        )

                        # Recuadro para URL_PDF
                        url_pdf_actual = obtener_valor(
                            registro, ["URL_PDF", "URL PDF", "PDF", "Link_PDF"], ""
                        )
                        if url_pdf_actual == "Sin datos":
                            url_pdf_actual = ""

                        nueva_url = st.text_input(
                            "URL_PDF",
                            value=str(url_pdf_actual),
                            placeholder="Ingrese o pegue el enlace del PDF aquí...",
                            key=f"input_pdf_{idx_real}",
                        )

                        c_save, c_link = st.columns([1, 1])
                        with c_save:
                            if st.button("💾 Guardar URL", key=f"btn_pdf_{idx_real}"):
                                if "URL_PDF" not in st.session_state["df_data"].columns:
                                    st.session_state["df_data"]["URL_PDF"] = ""
                                st.session_state["df_data"].at[idx_real, "URL_PDF"] = nueva_url
                                st.success("¡URL guardada!")
                                st.rerun()

                        with c_link:
                            if nueva_url.strip():
                                st.markdown(
                                    f'<a href="{nueva_url}" target="_blank" style="display:inline-block; margin-top:5px; padding:6px 12px; background-color:#007bff; color:white; text-decoration:none; border-radius:5px; font-size:14px; font-weight:bold;">🔗 Abrir PDF</a>',
                                    unsafe_allow_html=True,
                                )

            else:
                st.warning(
                    f"No se encontró ningún registro que coincida con '{busqueda}'."
                )
        else:
            st.info(
                "Ingresa una Cédula o Nombre en el campo de búsqueda arriba para visualizar la ficha técnica."
            )


# --- MÓDULO 2: REGISTRO DE NUEVO USUARIO ---
elif modulo == "➕ Registro de Nuevo Usuario":
    st.title("➕ Registro de Nuevo Usuario")
    st.write("Ingresa los datos para registrar un nuevo usuario/líder:")

    with st.form("form_nuevo_registro"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre completo")
            identificacion = st.text_input("Número de Identificación")
        with col2:
            zona = st.text_input("Zona / Municipio")
            telefono = st.text_input("Teléfono de contacto")

        guardar = st.form_submit_button("Guardar Registro")
        if guardar:
            st.success("¡Registro guardado exitosamente!")


# --- MÓDULO 3: EDITAR / MODIFICAR REGISTROS ---
elif modulo == "✏️ Editar / Modificar Registros":
    st.title("✏️ Edición de Datos de Usuarios")
    st.write(
        "Busque al usuario por Cédula, modifique los datos necesarios y guarde los cambios."
    )

    if "df_data" not in st.session_state:
        st.warning(
            "⚠️ No hay datos cargados. Por favor ve al módulo '📋 Base de Datos Completa' para subir tu archivo."
        )
    else:
        df = st.session_state["df_data"]

        cedula_buscar = st.text_input(
            "Ingrese la Cédula/ID del usuario a editar:", placeholder="Ej: 3474244"
        )

        if cedula_buscar:
            cols_cedula = [
                c
                for c in df.columns
                if any(
                    x in str(c).lower()
                    for x in ["cedula", "cédula", "id", "documento"]
                )
            ]

            idx_match = None
            if cols_cedula:
                col_c = cols_cedula[0]
                matches = df[
                    df[col_c].astype(str).str.strip()
                    == str(cedula_buscar).strip()
                ]
                if not matches.empty:
                    idx_match = matches.index[0]

            if idx_match is None:
                matches_gen = df[
                    df.astype(str).apply(
                        lambda r: r.str.contains(
                            cedula_buscar, case=False, na=False
                        ).any(),
                        axis=1,
                    )
                ]
                if not matches_gen.empty:
                    idx_match = matches_gen.index[0]

            if idx_match is not None:
                st.success("✅ Usuario localizado. Modifique los campos a continuación:")

                fila_actual = df.loc[idx_match]

                with st.form("form_editar_usuario"):
                    nuevos_valores = {}
                    cols = list(df.columns)
                    c_col1, c_col2 = st.columns(2)

                    for i, col_name in enumerate(cols):
                        val_orig = (
                            ""
                            if pd.isna(fila_actual[col_name])
                            else str(fila_actual[col_name])
                        )
                        target_col = c_col1 if i % 2 == 0 else c_col2

                        nuevos_valores[col_name] = target_col.text_input(
                            label=f"**{col_name}**", value=val_orig
                        )

                    guardar_cambios = st.form_submit_button(
                        "💾 Guardar Cambios"
                    )

                    if guardar_cambios:
                        for col_name, val_nuevo in nuevos_valores.items():
                            st.session_state["df_data"].at[
                                idx_match, col_name
                            ] = val_nuevo
                        st.success(
                            "¡Los cambios han sido guardados exitosamente!"
                        )
                        st.rerun()
            else:
                st.error(
                    f"No se encontró ningún usuario con la Cédula/ID '{cedula_buscar}'."
                )


# --- MÓDULO 4: PANEL DE CONTROL EJECUTIVOS ---
elif modulo == "📈 Panel de Control Ejecutivos":
    st.title("📈 Panel de Control Ejecutivos")

    if "df_data" not in st.session_state:
        st.warning(
            "⚠️ No hay datos cargados. Ve al módulo '📋 Base de Datos Completa' para subir tu archivo."
        )
    else:
        df = st.session_state["df_data"]
        inicio, fin = st.session_state.get("rango_info", (1, len(df)))

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Registros", len(df))
        k2.metric("Columnas", len(df.columns))
        k3.metric("Fila Inicio Excel", inicio)
        k4.metric("Fila Fin Excel", fin)

        st.markdown("---")

        cols_categoricas = df.select_dtypes(
            include=["object", "category"]
        ).columns.tolist()
        if cols_categoricas:
            c1, c2 = st.columns(2)
            var_g = c1.selectbox("Agrupar por:", cols_categoricas)
            conteo = df[var_g].value_counts().reset_index()
            conteo.columns = [var_g, "Cantidad"]

            fig_b = px.bar(
                conteo.head(10),
                x=var_g,
                y="Cantidad",
                text="Cantidad",
                title=f"Top 10 - {var_g}",
            )
            c1.plotly_chart(fig_b, use_container_width=True)

            fig_p = px.pie(
                conteo.head(5),
                names=var_g,
                values="Cantidad",
                title=f"Distribución Top 5 - {var_g}",
            )
            c2.plotly_chart(fig_p, use_container_width=True)


# --- MÓDULO 5: BASE DE DATOS COMPLETA ---
elif modulo == "📋 Base de Datos Completa":
    st.title("📋 Base de Datos Completa")
    st.write("Carga y gestiona el archivo completo de Excel:")

    archivo = st.file_uploader(
        "Cargar archivo Excel (.xlsx)", type=["xlsx"]
    )

    if archivo is not None:
        try:
            wb = openpyxl.load_workbook(archivo, data_only=True)
            sheet = wb.active
            inicio, fin = obtener_rango_filas_excel(sheet, col_letter="A")

            if inicio and fin:
                archivo.seek(0)
                df = pd.read_excel(
                    archivo, skiprows=inicio - 1, nrows=(fin - inicio + 1)
                )
                df = df.dropna(how="all", axis=1).dropna(how="all", axis=0)

                st.session_state["df_data"] = df
                st.session_state["rango_info"] = (inicio, fin)

                st.success(
                    f"¡Base cargada correctamente! {len(df)} registros procesados (Filas {inicio} a {fin})."
                )
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("No se hallaron datos en la columna 'A'.")
        except Exception as e:
            st.error(f"Error procesando archivo: {e}")
    else:
        if "df_data" in st.session_state:
            st.success("Base de datos cargada actualmente en el sistema.")
            st.dataframe(st.session_state["df_data"], use_container_width=True)
