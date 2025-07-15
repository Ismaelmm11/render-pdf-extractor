# app.py (versión con logging para depuración)
import os
import fitz  # PyMuPDF
import requests
import base64
import io
import logging
from flask import Flask, request, jsonify

# --- Configuración del Logging ---
# Esto hará que los mensajes se impriman en la consola de logs de Render
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Inicializamos la aplicación Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Servicio de extracción de imágenes de PDF está activo (modo depuración)."

@app.route('/extract', methods=['POST'])
def extract_images():
    logging.info("========================================")
    logging.info("Nueva petición recibida en /extract")
    
    # 1. Obtenemos los datos JSON de la petición
    try:
        data = request.get_json()
        if not data:
            logging.error("El cuerpo de la petición está vacío o no es JSON.")
            return jsonify({"error": "Cuerpo de la petición vacío o no es JSON"}), 400
        
        logging.info(f"Cuerpo JSON recibido: {data}")
        
        pdf_url = data.get('pdf_download_url')
        if not pdf_url:
            logging.error("No se encontró 'pdf_download_url' en el JSON.")
            return jsonify({"error": "Falta el parámetro 'pdf_download_url'"}), 400
        
        logging.info(f"URL del PDF a descargar: {pdf_url}")

    except Exception as e:
        logging.error(f"Error al procesar el JSON de entrada: {e}")
        return jsonify({"error": f"Error al procesar el JSON de entrada: {e}"}), 400

    # 2. Descargamos el PDF desde la URL
    try:
        logging.info("Iniciando descarga del archivo PDF...")
        response = requests.get(pdf_url, timeout=30) # Añadimos un timeout
        
        logging.info(f"Respuesta de Google Drive - Código de estado: {response.status_code}")
        logging.info(f"Respuesta de Google Drive - Cabeceras de contenido: {response.headers.get('Content-Type')}")

        # Si Google nos da un error, lo registramos y paramos
        response.raise_for_status()
        
        pdf_bytes = response.content
        logging.info(f"Descarga completada. Tamaño del archivo: {len(pdf_bytes)} bytes.")
        
        # Verificamos si parece un PDF
        if not pdf_bytes.startswith(b'%PDF-'):
            logging.warning("El archivo descargado NO comienza con '%PDF-'. Podría no ser un PDF válido.")
            # Mostramos los primeros 200 bytes para ver qué es (probablemente una página de error de Google)
            logging.warning(f"Inicio del contenido descargado: {pdf_bytes[:200]}")

    except requests.exceptions.RequestException as e:
        logging.error(f"FALLO en la descarga del PDF: {e}")
        return jsonify({"error": f"Fallo al descargar el archivo desde la URL: {e}"}), 500

    # 3. Procesamos el PDF con PyMuPDF
    try:
        logging.info("Iniciando procesamiento con PyMuPDF...")
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        imagenes_extraidas = []
        for i in range(len(doc)):
            pagina = doc[i]
            for img_index, img_info in enumerate(pagina.get_images(full=True)):
                bbox = pagina.get_image_bbox(img_info)
                pix = pagina.get_pixmap(clip=bbox, alpha=True)
                
                # --- CAMBIO REALIZADO AQUÍ ---
                # Usamos pix.tobytes() que es más directo y robusto
                img_bytes = pix.tobytes(output="png")
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                # --- FIN DEL CAMBIO ---

                imagenes_extraidas.append({
                    "filename": f"pagina_{i+1}_imagen_{img_index+1}.png",
                    "data_base64": img_base64
                })
                pix = None
        
        logging.info(f"Procesamiento completado. Se extrajeron {len(imagenes_extraidas)} imágenes.")
        logging.info("========================================")
        return jsonify({"imagenes": imagenes_extraidas})

    except Exception as e:
        logging.error(f"FALLO durante el procesamiento del PDF con PyMuPDF: {e}")
        logging.info("========================================")
        return jsonify({"error": f"Fallo al procesar el archivo PDF: {e}"}), 500
