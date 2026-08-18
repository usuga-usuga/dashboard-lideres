import openpyxl


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


def obtener_rango_filas_rapido(sheet, col_letter="A"):
    """Versión optimizada para archivos grandes.

    Retorna la primera y última fila con datos en la columna indicada.
    """
    col_letter = col_letter.upper().strip() if col_letter else "A"

    # Obtiene solo las celdas de la columna deseada
    celdas = sheet[col_letter]

    # Filtra las celdas que contienen datos reales
    filas_con_datos = [
        cell.row
        for cell in celdas
        if cell.value is not None and str(cell.value).strip() != ""
    ]

    if not filas_con_datos:
        return None, None

    return filas_con_datos[0], filas_con_datos[-1]


# Ejemplo de uso:
if __name__ == "__main__":
    # Cargar el libro de trabajo
    wb = openpyxl.load_workbook("tu_archivo.xlsx", data_only=True)
    sheet = wb.active

    # Obtener el rango
    inicio, fin = obtener_rango_filas_excel(sheet, col_letter="A")

    if inicio and fin:
        print(f"La información inicia en la fila {inicio} y termina en la {fin}")
    else:
        print("La columna evaluada está vacía.")
