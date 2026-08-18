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
    """Obtiene la primera y última fila con datos basándose en una columna específica.

    Parámetros:
        sheet: Hoja de cálculo de openpyxl (Worksheet)
        col_letter (str): Letra de la columna a evaluar (ej: 'A', 'B')

    Retorna:
        tuple: (primera_fila, ultima_fila) o (None, None) si la columna está
        vacía.
    """
    if not col_letter:
        col_letter = "A"

    col_letter = col_letter.upper().strip()
    primera_fila = None
    ultima_fila = None

    # Recorrer las filas de la columna especificada
    for row in range(1, sheet.max_row + 1):
        val = sheet[f"{col_letter}{row}"].value

        # Verificar que la celda no sea None ni contenga solo espacios en blanco
        if val is not None and str(val).strip() != "":
            if primera_fila is None:
                primera_fila = row
            ultima_fila = row

    return primera_fila, ultima_fila


# Interfaz de Streamlit
st.title("📊 Dashboard Líderes")
st.write("Sube tu archivo de Excel para analizar la información:")

# Componente para cargar archivos
archivo_subido = st.file_uploader(
    "Selecciona un archivo Excel (.xlsx)", type=["xlsx"]
)

if archivo_subido is not None:
    try:
        # Cargar el libro desde el archivo subido en memoria
        wb = openpyxl.load_workbook(archivo_subido, data_only=True)
        sheet = wb.active

        # Obtener rango de filas
        inicio, fin = obtener_rango_filas_excel(sheet, col_letter="A")

        if inicio and fin:
            st.success(
                f"La información inicia en la fila **{inicio}** y termina en la fila **{fin}**."
            )

            # Ejemplo de lectura adicional con Pandas
            df = pd.read_excel(archivo_subido)
            st.dataframe(df)
        else:
            st.warning("La columna evaluada no contiene datos.")

    except Exception as e:
        st.error(f"Error al procesar el archivo Excel: {e}")
else:
    st.info("Por favor, sube un archivo Excel para continuar.")
