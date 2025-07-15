# app.py
import os
import fitz  # PyMuPDF
import requests
import base64
import io
from flask import Flask, request, jsonify

# Inicializamos la aplicación Flask
app = Flask(__name__)

@app.route('/')
def home():
    # Una ruta simple para saber que el servicio está funcionando
    return "Servicio de extracción de imágenes de PDF está activo."

@app.route('/extract', methods=['POST'])
def extract_images():
    """
    Este es el endpoint principal. Recibe una URL de un PDF,
    extrae las imágenes y las devuelve en formato Base64.
    """
    # 1. Obtenemos los datos JSON de la petición
    data = request.get_json()
    if not data or 'pdf_download_url' not in data:
        return jsonify({"error": "Falta el parámetro 'pdf_download_url' en el cuerpo de la petición"}), 400

    pdf_url = data['pdf_download_url']

    # 2. Descargamos el PDF desde la URL
    try:
        response = requests.get(pdf_url)
        response.raise_for_status()  # Lanza un error si la descarga falla (ej. 404)
        pdf_bytes = response.content
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error al descargar el PDF: {e}"}), 500

    # 3. Procesamos el PDF con PyMuPDF
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        imagenes_extraidas = []
        
        # Lógica de extracción que ya perfeccionamos
        for i in range(len(doc)):
            pagina = doc[i]
            for img_index, img_info in enumerate(pagina.get_images(full=True)):
                try:
                    bbox = pagina.get_image_bbox(img_info)
                    pix = pagina.get_pixmap(clip=bbox, alpha=True)
                    
                    img_buffer = io.BytesIO()
                    pix.save(img_buffer, "png")
                    img_buffer.seek(0)
                    
                    img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
                    
                    imagenes_extraidas.append({
                        "filename": f"pagina_{i+1}_imagen_{img_index+1}.png",
                        "data_base64": img_base64
                    })
                    pix = None
                except Exception as e_inner:
                    print(f"Omitiendo una imagen en la página {i+1} por error: {e_inner}")
                    continue
        
        # 4. Devolvemos la lista de imágenes en formato JSON
        return jsonify({"imagenes": imagenes_extraidas})

    except Exception as e:
        return jsonify({"error": f"Error al procesar el archivo PDF: {e}"}), 500

# Esta parte es para ejecutar la app localmente si quisiéramos probarla
if __name__ == '__main__':
    # Render usará un servidor de producción como Gunicorn, no esto.
    app.run(debug=True, port=os.getenv("PORT", default=5000))
