import openpyxl

def obtener_rango_filas_excel(sheet, col_letter):
    """
    Obtiene la primera y última fila con datos basándose en una columna específica.
    
    Parámetros:
        sheet: Hoja de cálculo de openpyxl
        col_letter (str): Letra de la columna a evaluar (ej: 'A', 'B')
        
    Retorna:
        tuple: (primera_fila, ultima_fila) o (None, None) si la columna está vacía.
    """
    if not col_letter:
        col_letter = "A"
    
    primera_fila = None
    ultima_fila = None
    
    # Recorrer las filas de la hoja para la columna dada
    for row in range(1, sheet.max_row + 1):
        val = sheet[f"{col_letter}{row}"].value
        if val is not None and str(val).strip() != "":
            if primera_fila is None:
                primera_fila = row
            ultima_fila = row
            
    return primera_fila, ultima_fila


# Ejemplo de uso/prueba del script:
if __name__ == "__main__":
    # Si ejecutas app.py directamente, creará un libro de prueba en memoria
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Datos"
    
    # Agregar algunos datos de prueba en la columna A
    ws["A5"] = "Primer dato"
    ws["A10"] = "Dato intermedio"
    ws["A25"] = "Último dato"
    
    min_row, max_row = obtener_rango_filas_excel(ws, "A")
    print(f"Primera fila con datos en columna A: {min_row}")  # Resultado: 5
    print(f"Última fila con datos en columna A: {max_row}")    # Resultado: 25
