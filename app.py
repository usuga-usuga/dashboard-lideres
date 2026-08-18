from datetime import date, datetime
import unicodedata
import openpyxl
import pandas as pd
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Líderes", page_icon="📊", layout="wide"
)


def obtener_rango_filas_excel(sheet, col_letter="A"):
    """Obtiene la primera y última fila con datos basándose en una columna específica."""
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


# Encabezado principal
st.title("📊 Dashboard Líderes")
st.write("Sube tu archivo de Excel para analizar la información:")

# Carga de archivo
archivo_subido = st.file_uploader(
    "Selecciona un archivo Excel (.xlsx)", type=["xlsx"]
)

if archivo_subido is not None:
    try:
        # 1. Análisis del rango con openpyxl
        wb = openpyxl.load_workbook(archivo_subido, data_only=True)
        sheet = wb.active

        inicio, fin = obtener_rango_filas_excel(sheet, col_letter="A")

        if inicio and fin:
            st.success(
                f"La información inicia en la fila **{inicio}** y termina en la fila **{fin}**."
            )

            # 2. Lectura y procesamiento de datos con Pandas
            # Se asume que la primera fila detectada (inicio) contiene los nombres de las columnas
            archivo_subido.seek(0)  # Rebobinar puntero del archivo
            df = pd.read_excel(
                archivo_subido,
                skiprows=inicio - 1,
                nrows=(fin - inicio + 1),
            )

            # Eliminar columnas completamente vacías
            df = df.dropna(how="all", axis=1)

            # 3. Vista de Métricas Generales
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    label="Total Registros Procesados", value=len(df)
                )
            with col2:
                st.metric(
                    label="Total Columnas Detectadas", value=len(df.columns)
                )
            with col3:
                st.metric(
                    label="Fila Final Detectada", value=f"Fila {fin}"
                )

            st.markdown("---")

            # 4. Buscador y Filtro interactivo
            st.subheader("🔍 Explorador de Datos")
            busqueda = st.text_input(
                "Filtrar datos en toda la tabla:",
                placeholder="Escribe para buscar...",
            )

            if busqueda:
                # Filtrar filas que contengan el texto buscado en cualquiera de sus columnas
                mascara = df.astype(str).apply(
                    lambda row: row.str.contains(
                        busqueda, case=False, na=False
                    ).any(),
                    axis=1,
                )
                df_filtrado = df[mascara]
            else:
                df_filtrado = df

            # 5. Visualización del DataFrame
            st.dataframe(df_filtrado, use_container_width=True, height=400)

            # 6. Botón de descarga de datos procesados
            buffer_excel = pd.ExcelWriter("datos_procesados.xlsx")
            df_filtrado.to_excel(buffer_excel, index=False)

        else:
            st.warning(
                "La columna 'A' no contiene información válida para delimitar el rango."
            )

    except Exception as e:
        st.error(f"Error al procesar el archivo Excel: {e}")
else:
    st.info("Por favor, sube un archivo Excel para desplegar el panel.")
