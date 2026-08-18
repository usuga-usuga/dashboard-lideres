import os
import io
import pandas as pd
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta-edunorte-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nomina.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# MODELOS DE BASE DE DATOS
# ==========================================

class Empleado(db.Model):
    __tablename__ = 'empleados'
    id = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    cargo = db.Column(db.String(100), nullable=False)
    salario_base = db.Column(db.Float, nullable=False, default=0.0)
    
    # Relación con novedades
    novedades = db.relationship('Novedad', backref='empleado', cascade="all, delete-orphan", lazy=True)

class Novedad(db.Model):
    __tablename__ = 'novedades'
    id = db.Column(db.Integer, primary_key=True)
    empleado_id = db.Column(db.Integer, db.ForeignKey('empleados.id'), nullable=False)
    periodo = db.Column(db.String(7), nullable=False)  # Formato YYYY-MM
    tipo = db.Column(db.String(50), nullable=False)     # Horas Extra, Bonificación, Ausencia, Incapacidad, etc.
    valor = db.Column(db.Float, nullable=False, default=0.0)
    descripcion = db.Column(db.String(200), nullable=True)

# Crear la base de datos si no existe
with app.app_context():
    db.create_all()

# ==========================================
# PLANTILLA HTML ÚNICA (BOOTSTRAP 5)
# ==========================================

HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gestión de Nómina y Novedades - EDUNORTE</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <style>
        body { background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .navbar-custom { background-color: #1e293b; }
        .card { border-radius: 10px; border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .table-responsive { background: #ffffff; border-radius: 8px; }
        .badge-devengado { background-color: #d1e7dd; color: #0f5132; }
        .badge-deduccion { background-color: #f8d7da; color: #842029; }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-dark navbar-custom mb-4 shadow-sm">
    <div class="container-fluid px-4">
        <a class="navbar-brand fw-bold" href="#"><i class="bi bi-calculator me-2"></i>EDUNORTE - Nómina</a>
        <div class="d-flex">
            <span class="navbar-text text-white-50"><i class="bi bi-calendar3 me-1"></i> Período Actual: {{ periodo_actual }}</span>
        </div>
    </div>
</nav>

<div class="container-fluid px-4">

    <!-- Mensajes Flash -->
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
            {{ message }}
            <button type="button" class="btn-Aquí tienes el código completo y actualizado de `app.py`. Incluye la nueva funcionalidad de seleccionar **"Columna Base"** para determinar el rango dinámico de filas con datos, además de mantener el procesamiento de imágenes (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`) y documentos de Office (`.docx`, `.xlsx`, `.pptx`).

```python
import os
import sys
import tempfile
import streamlit as st
import openpyxl
import docx
import pptx
from PIL import Image
from pdf2image import convert_from_path

# ==========================================
# CONFIGURACIÓN DE PÁGINA STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Gestor de Documentos e Imágenes",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Procesador y Convertidor Documental")
st.markdown("Cargue y procese archivos de Excel, Word, PowerPoint o Imágenes con configuraciones personalizadas.")

# ==========================================
# BARRA LATERAL - CONFIGURACIÓN / NOVEDADES
# ==========================================
st.sidebar.header("⚙️ Configuración")

# Novedad: Selección de columna base para el rango de filas
columna_base = st.sidebar.text_input(
    "Columna Base para Lectura (p. ej., A, B, C):",
    value="A",
    help="Indica la columna que determina la última fila con información en la hoja de Excel."
).strip().upper()

opcion_procesamiento = st.sidebar.selectbox(
    "Modo de Procesamiento:",
    ["Estándar", "Extracción Completa", "Vista Previa Rápida"]
)

# ==========================================
# FUNCIONES AUXILIARES DE PROCESAMIENTO
# ==========================================
def obtener_rango_filas_excel(sheet, col_letter):
    """
    Obtiene la primera y última fila con datos basándose en una columna específica.
    """
    if not col_letter:
        col_letter = "A"
    
    # Agrega aquí el resto de tu lógica para obtener las filas...
    
    max_row = sheet.max_row
    min_row = None
    last_row = None

    for row in range(1, max_row + 1):
        cell_val = sheet[f"{col_letter}{row}"].value
        if cell_val is not None and str(cell_val).strip() != "":
            if min_row is None:
                min_row = row
            last_row = row

    return min_row, last_row

def procesar_excel(file, col_base):
    wb = openpyxl.load_workbook(file, data_only=True)
    st.subheader("📊 Análisis de Hoja de Cálculo (Excel)")
    
    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        min_r, max_r = obtener_rango_filas_excel(sheet, col_base)
        
        st.markdown(f"**Hoja:** `{sheet_name}`")
        if min_r and max_r:
            st.info(f"Rango de datos detectado en la **Columna {col_base}**: Filas **{min_r}** a **{max_r}**.")
        else:
            st.warning(f"No se encontraron datos en la **Columna {col_base}** para esta hoja.")

def procesar_word(file):
    doc = docx.Document(file)
    st.subheader("📝 Contenido del Documento Word")
    texto_completo = [p.text for p in doc.paragraphs if p.text.strip()]
    st.write(f"Total de párrafos encontrados: **{len(texto_completo)}**")
    with st.expander("Ver vista previa del texto"):
        st.write("\n".join(texto_completo[:10]))

def procesar_pptx(file):
    prs = pptx.Presentation(file)
    st.subheader("🖥️ Presentación PowerPoint")
    st.write(f"Total de diapositivas: **{len(prs.slides)}**")

def procesar_imagen(file):
    st.subheader("🖼️ Visualización de Imagen")
    img = Image.open(file)
    st.image(img, caption=file.name, use_column_width=True)

# ==========================================
# CARGA Y PROCESAMIENTO DE ARCHIVOS
# ==========================================
archivos_cargados = st.file_uploader(
    "Seleccione o arrastre los archivos a procesar:",
    type=["xlsx", "docx", "pptx", "png", "jpg", "jpeg", "pdf", "tiff", "bmp"],
    accept_multiple_files=True
)

if archivos_cargados:
    for archivo in archivos_cargados:
        st.divider()
        st.markdown(f"### Archivo: `{archivo.name}`")
        ext = archivo.name.split(".")[-1].lower()

        if ext == "xlsx":
            procesar_excel(archivo, columna_base)
        elif ext == "docx":
            procesar_word(archivo)
        elif ext == "pptx":
            procesar_pptx(archivo)
        elif ext in ["png", "jpg", "jpeg", "tiff", "bmp"]:
            procesar_imagen(archivo)
        elif ext == "pdf":
            st.subheader("📄 Documento PDF")
            st.info("Archivo PDF recibido correctamente para su procesamiento.")
        else:
            st.error(f"Formato `.{ext}` no soportado.")
else:
    st.info("Cargue uno o más archivos en el panel superior para comenzar.")
