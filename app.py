import pandas as pd
import numpy as np
import re

class ProcesadorLideresBD:
    def __init__(self, archivo_entrada="Base Datos LIDERES_2.xlsx", archivo_salida="Base_Lideres_Procesada.xlsx"):
        self.archivo_entrada = archivo_entrada
        self.archivo_salida = archivo_salida
        self.df_raw = None
        self.df_clean = None
        self.resumen_dependencia = None
        self.alertas = {}

    def cargar_datos(self):
        """Carga la hoja omitiendo los super-encabezados agrupadores de la fila 0."""
        self.df_raw = pd.read_excel(self.archivo_entrada, sheet_name=0, header=1)
        
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

        # 2. Formateo de Identificación como Entero (vía Int64 para soportar NaNs)
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

        # 7. Reglas de Recálculo y Consistencia Financiera / Votaciones
        # Recalcular Total de Votantes si la celda es 0 y existen desgloses
        df["Total"] = np.where(
            (df["Total"] == 0) & ((df["Bello"] > 0) | (df["Otros"] > 0)),
            df["Bello"] + df["Otros"],
            df["Total"]
        )

        # Recalcular Total de Amigos si el consolidado es 0 y existen desgloses
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

        # 8. Descarte de filas vacías (sin cédula ni nombres)
        self.df_clean = df.dropna(subset=["No. Identificacion", "Nombres"], how="all").reset_index(drop=True)
        return self

    def auditar_y_resumir(self):
        """Genera tablas agrupadas y detecta inconsistencias de calidad."""
        if self.df_clean is None:
            self.limpiar_y_transformar()

        df = self.df_clean

        # Resumen consolidado por Dependencia
        self.resumen_dependencia = df.groupby("Dependencia", dropna=False).agg(
            Lideres_Registrados=("No. Identificacion", "count"),
            Total_Proyeccion=("PROYECCION", "sum"),
            Total_Registros=("REGISTROS", "sum"),
            Total_Amigos=("No. Amigos", "sum"),
            Amigos_Bello=("MUNICIPIO DE BELLO", "sum")
        ).reset_index()

        # Detección de duplicados en Cédula
        duplicados = df[df["No. Identificacion"].duplicated(keep=False) & df["No. Identificacion"].notna()]
        
        # Registros sin número de contacto
        sin_telefono = df[df["No. Telefono"].isna()]

        self.alertas = {
            "Cedulas_Duplicadas": duplicados,
            "Sin_Telefono": sin_telefono
        }
        return self

    def exportar_excel(self):
        """Exporta los datos procesados y los reportes a un archivo Excel estructurado."""
        if self.df_clean is None or self.resumen_dependencia is None:
            self.auditar_y_resumir()

        with pd.ExcelWriter(self.archivo_salida, engine="openpyxl") as writer:
            self.df_clean.to_excel(writer, sheet_name="BD_Limpia", index=False)
            self.resumen_dependencia.to_excel(writer, sheet_name="Resumen_Dependencia", index=False)
            
            if not self.alertas["Cedulas_Duplicadas"].empty:
                self.alertas["Cedulas_Duplicadas"].to_excel(writer, sheet_name="Alertas_Duplicados", index=False)
            
            if not self.alertas["Sin_Telefono"].empty:
                self.alertas["Sin_Telefono"].to_excel(writer, sheet_name="Alertas_Sin_Telefono", index=False)

        print(f"Procesamiento finalizado. Archivo generado: {self.archivo_salida}")


if __name__ == "__main__":
    pipeline = ProcesadorLideresBD("Base Datos LIDERES_2.xlsx")
    pipeline.cargar_datos().limpiar_y_transformar().auditar_y_resumir().exportar_excel()
