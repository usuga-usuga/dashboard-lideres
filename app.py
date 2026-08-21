import pandas as pd
import numpy as np
import re
import os
import streamlit as st

class ProcesadorLideresBD:
    def __init__(self, origen_datos):
        """
        origen_datos puede ser una ruta de archivo (str) 
        o un objeto UploadedFile de Streamlit.
        """
        self.origen_datos = origen_datos
        self.df_raw = None
        self.df_clean = None
        self.resumen_dependencia = None
        self.alertas = {}

    def cargar_datos(self):
        """Carga la hoja omitiendo los super-encabezados agrupadores de la fila 0."""
        self.df_raw = pd.read_excel(self.origen_datos, sheet_name=0, header=1)
        
        # Asignar nombre a la última columna de URL si viene vacía
        columnas = list(self.df_raw.columns)
        if len(columnas) >= 27:
            columnas[26] = "URL_PDF"
        self.df_raw.columns = columnas
        return self

    def limpiar_y_transformar(self):
        """Aplica las reglas de saneamiento, formateo y cálculo de negocio."""
        df = self.df_raw.copy()

        # 1. Normalización de valores nulos globales
        df = df.replace(["nan", "NaN", "null", "NULL", "None", "NONE", "", "<NA>"], np.nan)

        # 2. Formateo de Identificación como Entero
        df["No. Identificacion"] = pd.to_numeric(df["No. Identificacion"], errors="coerce").astype("Int64")

        # 3. Limpieza de Números Telefónicos
        def depurar_telefono(val):
            if pd.isna(val):
                return np.nan
            s = re.sub(r"\D", "", str(val).split('.')[0])
            return s if len(s) >= 7 else np.nan

        df["No. Telefono"] = df["No. Telefono"].apply(depurar_telefono)

        # 4. Formateo de Fechas (AAAA-MM-DD)
        df["Fecha de Cumpleanos"] = pd.to_datetime(df["Fecha de Cumpleanos"], errors="coerce").dt.strftime('%Y-%m-%d')

        # 5. Normalización de Textos y Capitalización
        cols_texto = [
            "Dependencia", "Secretaria y/o Dependencia", "Apoyo", "Profesion", 
            "Cargo actual", "Correo Electronico", "Redes Sociales", "Comuna", 
            "Barrio", "MUNICIPIO", "NOTAS", "URL_PDF"
        ]
        for col in cols_texto:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().replace("nan", np.nan)

        if "Nombres" in df.columns:
            df["Nombres"] = df["Nombres"].astype(str).str.strip().str.title().replace("Nan", np.nan)
        if "Apellidos" in df.columns:
            df["Apellidos"] = df["Apellidos"].astype(str).str.strip().str.title().replace("Nan", np.nan)

        # 6. Formateo de Métricas Numéricas / Conteos
        cols_conteo = [
            "Bello", "Otros", "Total", "PROYECCION", "REGISTROS",
            "No. Amigos", "MUNICIPIO DE BELLO", "OTROS MUNICIPIOS - DEPTOS",
            "NO ESTA EN EL CENSO", "CEDULA ERRONEA"
        ]
        for col in cols_conteo:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        # 7. Reglas de Recálculo y Consistencia
        df["Total"] = np.where(
            (df["Total"] == 0) & ((df["Bello"] > 0) | (df["Otros"] > 0)),
            df["Bello"] + df["Otros"],
            df["Total"]
        )

        suma_desglose_amigos = (
            df["MUNICIPIO DE BELLO"] + 
            df["OTROS MUNICIPIOS - DEPTOS"] + 
            df["NO ESTA EN EL CENSO"] + 
            df["CEDULA ERRONEA"]
        )
        df["No. Amigos"] = np.where(
            (df["No. Amigos"] == 0) & (suma_desglose_amigos > 0),
            suma_desglose_amigos,
            df["No. Amigos"]
        )

        # 8. Descarte de filas vacías
        self.df_clean = df.dropna(subset=["No. Identificacion", "Nombres"], how="all").reset_index(drop=True)
        return self

    def auditar_y_resumir(self):
        """Genera tablas agrupadas y detecta inconsistencias de calidad."""
        if self.df_clean is None:
            self.limpiar_y_transformar()

        df = self.df_clean

        self.resumen_dependencia = df.groupby("Dependencia", dropna=False).agg(
            Lideres_Registrados=("No. Identificacion", "count"),
            Total_Proyeccion=("PROYECCION", "sum"),
            Total_Registros=("REGISTROS", "sum"),
            Total_Amigos=("No. Amigos", "sum"),
            Amigos_Bello=("MUNICIPIO DE BELLO", "sum")
        ).reset_index()

        duplicados = df[df["No. Identificacion"].duplicated(keep=False) & df["No. Identificacion"].notna()]
        sin_telefono = df[df["No. Telefono"].isna()]

        self.alertas = {
            "Cedulas_Duplicadas": duplicados,
            "Sin_Telefono": sin_telefono
        }
        return self


# ==============================================================================
# INTERFAZ DE STREAMLIT
# ==============================================================================
st.set_page_config(page_title="Dashboard Líderes", layout="wide")
st.title("📊 Dashboard Base de Datos Líderes")

# Selector de archivo (File Uploader o Archivo por defecto si existe)
archivo_subido = st.sidebar.file_uploader("Subir archivo Excel", type=["xlsx", "xls"])

# Rutas de respaldo por si el usuario subió el archivo al repositorio de GitHub
archivo_default = None
for posible_nombre in ["Base Datos LIDERES_2.xlsx", "Base Datos LIDERES.xlsx"]:
    if os.path.exists(posible_nombre):
        archivo_default = posible_nombre
        break

origen = archivo_subido if archivo_subido is not None else archivo_default

if origen is not None:
    try:
        pipeline = ProcesadorLideresBD(origen)
        pipeline.cargar_datos().limpiar_y_transformar().auditar_y_resumir()

        st.success("✅ Base de datos procesada exitosamente")

        # Mostrar métricas
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Líderes", len(pipeline.df_clean))
        col2.metric("Proyección Total", pipeline.df_clean["PROYECCION"].sum())
        col3.metric("Registros Totales", pipeline.df_clean["REGISTROS"].sum())
        col4.metric("Total Amigos", pipeline.df_clean["No. Amigos"].sum())

        # Pestañas de información
        tab1, tab2, tab3 = st.tabs(["📋 Base de Datos Limpia", "📈 Resumen por Dependencia", "⚠️ Alertas y Calidad"])

        with tab1:
            st.dataframe(pipeline.df_clean, use_container_width=True)

        with tab2:
            st.dataframe(pipeline.resumen_dependencia, use_container_width=True)

        with tab3:
            st.subheader("Cédulas Duplicadas")
            st.dataframe(pipeline.alertas["Cedulas_Duplicadas"], use_container_width=True)
            
            st.subheader("Registros Sin Teléfono")
            st.dataframe(pipeline.alertas["Sin_Telefono"], use_container_width=True)

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
else:
    st.warning("⚠️ No se encontró ningún archivo Excel. Por favor, sube el archivo desde la barra lateral izquierda (`file_uploader`) o asegúrate de que esté subido en el repositorio de GitHub.")
