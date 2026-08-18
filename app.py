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


# Título principal
st.title("📊 Dashboard Analítico de Líderes")
st.write(
    "Carga tu base de datos en Excel para visualizar indicadores, gráficos y tablas dinámicas."
)

# Cargar archivo
archivo_subido = st.file_uploader(
    "Selecciona tu archivo Excel (.xlsx)", type=["xlsx"]
)

if archivo_subido is not None:
    try:
        # Lectura con openpyxl para detectar el rango
        wb = openpyxl.load_workbook(archivo_subido, data_only=True)
        sheet = wb.active
        inicio, fin = obtener_rango_filas_excel(sheet, col_letter="A")

        if inicio and fin:
            # Lectura del rango exacto con pandas
            archivo_subido.seek(0)
            df = pd.read_excel(
                archivo_subido,
                skiprows=inicio - 1,
                nrows=(fin - inicio + 1),
            )

            # Limpieza básica: eliminar columnas/filas totalmente vacías
            df = df.dropna(how="all", axis=1).dropna(how="all", axis=0)

            # --- BARRA LATERAL: FILTROS DINÁMICOS ---
            st.sidebar.header("🔍 Filtros de Información")

            df_filtrado = df.copy()

            # Detectar automáticamente columnas con texto o categorías para los filtros
            cols_categoricas = df.select_dtypes(
                include=["object", "category"]
            ).columns.tolist()

            if cols_categoricas:
                # Seleccionar la primera columna categórica como filtro principal
                col_filtro_1 = st.sidebar.selectbox(
                    "Filtrar por campo primario:",
                    options=["Todos"] + cols_categoricas,
                )

                if col_filtro_1 != "Todos":
                    opciones_1 = (
                        df[col_filtro_1].dropna().unique().tolist()
                    )
                    seleccion_1 = st.sidebar.multiselect(
                        f"Selecciona valores de '{col_filtro_1}':",
                        options=opciones_1,
                        default=opciones_1,
                    )
                    if seleccion_1:
                        df_filtrado = df_filtrado[
                            df_filtrado[col_filtro_1].isin(seleccion_1)
                        ]

            # Buscador global
            busqueda_texto = st.sidebar.text_input(
                "Búsqueda por palabra clave:"
            )
            if busqueda_texto:
                mascara = df_filtrado.astype(str).apply(
                    lambda row: row.str.contains(
                        busqueda_texto, case=False, na=False
                    ).any(),
                    axis=1,
                )
                df_filtrado = df_filtrado[mascara]

            # --- SECCIÓN 1: METRICAS Y KPIS ---
            st.subheader("📌 Resumen General")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)

            kpi1.metric("Total Registros Base", len(df))
            kpi2.metric("Registros Filtrados", len(df_filtrado))
            kpi3.metric("Columnas Analizadas", len(df.columns))
            kpi4.metric(
                "Rango Filas Excel", f"{inicio} - {fin}"
            )

            st.markdown("---")

            # --- SECCIÓN 2: GRÁFICOS INTERACTIVOS ---
            if cols_categoricas and len(df_filtrado) > 0:
                st.subheader("📈 Análisis Gráfico")
                col_g1, col_g2 = st.columns(2)

                col_grafico = col_g1.selectbox(
                    "Selecciona columna para agrupar:",
                    options=cols_categoricas,
                    index=0,
                )

                # Conteo de datos
                conteo_df = (
                    df_filtrado[col_grafico]
                    .value_counts()
                    .reset_index()
                )
                conteo_df.columns = [col_grafico, "Cantidad"]

                # Gráfico de Barras
                fig_barras = px.bar(
                    conteo_df.head(10),
                    x=col_grafico,
                    y="Cantidad",
                    text="Cantidad",
                    title=f"Top 10 - Distribución por {col_grafico}",
                    color="Cantidad",
                    color_continuous_scale="Blues",
                )
                col_g1.plotly_chart(
                    fig_barras, use_container_width=True
                )

                # Gráfico de Pastel
                fig_pie = px.pie(
                    conteo_df.head(5),
                    names=col_grafico,
                    values="Cantidad",
                    title=f"Proporción Top 5 - {col_grafico}",
                    hole=0.4,
                )
                col_g2.plotly_chart(
                    fig_pie, use_container_width=True
                )

                st.markdown("---")

            # --- SECCIÓN 3: TABLA DE DATOS Y DESCARGA ---
            st.subheader("📋 Detalle de Datos Filtrados")
            st.dataframe(
                df_filtrado, use_container_width=True, height=350
            )

            # Botón para descargar los datos filtrados en Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_filtrado.to_excel(writer, index=False, sheet_name="Datos")

            st.download_button(
                label="📥 Descargar datos filtrados en Excel",
                data=buffer.getvalue(),
                file_name=f"reporte_lideres_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        else:
            st.warning(
                "No se detectaron datos válidos en la columna 'A'."
            )

    except Exception as e:
        st.error(f"Error procesando la información: {e}")
else:
    st.info("Carga un archivo de Excel para habilitar el tablero analítico.")
