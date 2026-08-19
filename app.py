import streamlit as st
import pandas as pd
import unicodedata
import re

# ==============================================================================
# FUNCIONES DE UTILIDAD Y NORMALIZACIÓN
# ==============================================================================
def normalizar(texto):
    """Normaliza texto eliminando tildes, mayúsculas y caracteres especiales."""
    if not isinstance(texto, str):
        texto = str(texto)
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.lower().strip()

def buscar_columna_df(df_cols, alias_list):
    """Encuentra la columna real dentro del DataFrame buscando alias."""
    for alias in alias_list:
        alias_norm = normalizar(alias)
        for col in df_cols:
            col_norm = normalizar(str(col))
            if alias_norm == col_norm or alias_norm in col_norm:
                return col
    return None

def obtener_valor_inteligente(row, df_cols, alias_list, default="Sin datos", cols_usadas=None):
    """Obtiene el valor de una columna según sus alias y evita repetir columnas."""
    col_encontrada = buscar_columna_df(df_cols, alias_list)
    if col_encontrada:
        if cols_usadas is not None:
            cols_usadas.add(col_encontrada)
        val = str(row[col_encontrada]).strip()
        if val and val.lower() not in ["nan", "none", "null", "<na>", ""]:
            return val
    return default

def obtener_fecha_cumpleanos_formateada(row, df_cols, cols_usadas=None):
    """Busca la columna de cumpleaños y le da un formato legible."""
    val = obtener_valor_inteligente(row, df_cols, ["cumpleanos", "cumpleaños", "fecha nacimiento", "nacimiento"], "Sin datos", cols_usadas)
    if val != "Sin datos":
        try:
            fecha_dt = pd.to_datetime(val)
            return fecha_dt.strftime("%d de %B")
        except Exception:
            return val
    return val

def generar_pdf_ficha(row, df_cols):
    """Función stub para la generación de PDF Ficha."""
    # Reemplaza con la lógica de generación PDF de tu sistema si aplica
    return b"PDF_DUMMY_DATA"


# ==============================================================================
# MÓDULO 1: CONSULTA DETALLADA
# ==============================================================================
if menu == "🔍 Consulta Detallada":
    st.subheader("🔍 Consulta Detallada de Líderes")
    if not df_lideres.empty:
        criterio = st.radio("Buscar por:", ["Cédula / Identificación", "Nombre / Apellido"], horizontal=True)
        resultado = pd.DataFrame()
        
        busqueda = st.text_input("Ingrese término de búsqueda:")
        if busqueda.strip():
            mask = df_lideres.astype(str).apply(
                lambda row: row.str.contains(busqueda.strip(), case=False, na=False)
            ).any(axis=1)
            resultado = df_lideres[mask]

        if not resultado.empty:
            st.success(f"✅ Se encontraron {len(resultado)} registro(s).")

            for idx, row in resultado.iterrows():
                cols_usadas = set()

                # --- 1. Identificación y Nombre ---
                cedula = obtener_valor_inteligente(
                    row, df_lideres.columns, ["cedula", "identificacion", "documento", "id"], "Sin datos", cols_usadas
                )
                nombres = obtener_valor_inteligente(
                    row, df_lideres.columns, ["nombres", "nombre"], "", cols_usadas
                )
                apellidos = obtener_valor_inteligente(
                    row, df_lideres.columns, ["apellidos", "apellido"], "", cols_usadas
                )
                nombre_completo = f"{nombres} {apellidos}".strip() or "NOMBRE NO REGISTRADO"

                # --- 2. Datos Bloque Laboral ---
                dependencia = obtener_valor_inteligente(
                    row, df_lideres.columns, ["dependencia"], "Sin datos", cols_usadas
                )
                secretaria = obtener_valor_inteligente(
                    row, df_lideres.columns, ["secretaria", "secretaría"], "Sin datos", cols_usadas
                )
                cargo = obtener_valor_inteligente(
                    row, df_lideres.columns, ["cargo actual", "cargo", "puesto"], "Sin datos", cols_usadas
                )
                profesion = obtener_valor_inteligente(
                    row, df_lideres.columns, ["profesion", "profesión", "oficio"], "Sin datos", cols_usadas
                )
                lider_apoyo = obtener_valor_inteligente(
                    row, df_lideres.columns, ["lider / apoyo", "lider/apoyo", "lider", "apoyo"], "Sin datos", cols_usadas
                )

                # --- 3. Datos Contacto Directo ---
                telefono = obtener_valor_inteligente(
                    row, df_lideres.columns, ["telefono / celular", "telefono", "celular", "tel", "movil"], "Sin datos", cols_usadas
                )
                correo = obtener_valor_inteligente(
                    row, df_lideres.columns, ["correo", "email", "mail"], "Sin datos", cols_usadas
                )
                redes = obtener_valor_inteligente(
                    row, df_lideres.columns, ["redes sociales", "redes"], "Sin datos", cols_usadas
                )

                # --- 4. Datos Ubicación y Fechas ---
                municipio = obtener_valor_inteligente(
                    row, df_lideres.columns, ["municipio", "ciudad"], "Sin datos", cols_usadas
                )
                comuna = obtener_valor_inteligente(
                    row, df_lideres.columns, ["comuna"], "Sin datos", cols_usadas
                )
                barrio = obtener_valor_inteligente(
                    row, df_lideres.columns, ["barrio"], "Sin datos", cols_usadas
                )
                cumpleanos = obtener_fecha_cumpleanos_formateada(row, df_lideres.columns, cols_usadas)

                # --- 5. Datos Proyección y Notas ---
                proyeccion = obtener_valor_inteligente(
                    row, df_lideres.columns, ["proyeccion", "proyección"], "Sin datos", cols_usadas
                )
                registros = obtener_valor_inteligente(
                    row, df_lideres.columns, ["registros", "registro"], "Sin datos", cols_usadas
                )
                notas = obtener_valor_inteligente(
                    row, df_lideres.columns, ["notas / observaciones", "notas", "observaciones", "comentarios"], "Sin datos", cols_usadas
                )

                # --- 6. Datos Planillas y Registros (INCLUYE CENSO) ---
                amigos = obtener_valor_inteligente(
                    row, df_lideres.columns, ["no. amigos", "nro amigos", "amigos"], "0", cols_usadas
                )
                bello = obtener_valor_inteligente(
                    row, df_lideres.columns, ["municipio de bello", "bello"], "Sin datos", cols_usadas
                )
                otros_muni = obtener_valor_inteligente(
                    row, df_lideres.columns, ["otros municipios"], "Sin datos", cols_usadas
                )
                censo = obtener_valor_inteligente(
                    row, df_lideres.columns, ["no esta en el censo", "censo", "no censo"], "Sin datos", cols_usadas
                )

                # --- RENDERIZADO VISUAL EN TARJETAS ---
                with st.container(border=True):
                    # Cabecera Principal
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

                    # --- Fila 1: Laboral, Contacto y Ubicación ---
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
                            st.markdown(
                                f"**Correo:** [{correo}](mailto:{correo})" if correo != "Sin datos" else "**Correo:** Sin datos"
                            )
                            st.markdown(f"**Redes Sociales:** {redes}")

                    with col3:
                        with st.container(border=True):
                            st.markdown("### 📍 Ubicación y Fechas")
                            st.markdown(f"**Municipio:** {municipio}")
                            st.markdown(f"**Comuna:** {comuna}")
                            st.markdown(f"**Barrio:** {barrio}")
                            st.markdown(f"**Cumpleaños:** {cumpleanos}")

                    # --- Fila 2: Proyección y Planillas ---
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

                    # --- Fila 3: Captura de cualquier columna sobrante no mapeada ---
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
