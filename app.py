import streamlit as st
import fitz  # PyMuPDF
import io
import os
import math
import numpy as np
from PIL import Image, ImageOps
import tempfile
import warnings

# Importar explícitamente st_canvas
try:
    from streamlit_drawable_canvas import st_canvas
except ImportError:
    st.error(
        "No se pudo importar streamlit-drawable-canvas. Por favor, instálalo con: pip install streamlit-drawable-canvas")
    st.stop()

# Ignorar advertencias de descompresión de imágenes
warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)

# Configuración de la página
st.set_page_config(layout="wide", page_title="Editor de Planos PDF")

# Aumentar el límite de píxeles para imágenes grandes
Image.MAX_IMAGE_PIXELS = None  # Eliminar límite
Image.LOAD_TRUNCATED_IMAGES = True


# Clases para manejar las anotaciones
class Punto:
    def __init__(self):
        self.puntos = []

    def agregar(self, x, y, color):
        self.puntos.append((x, y, color))

    def borrar_cerca_de(self, x, y, tolerancia):
        self.puntos = [(px, py, c) for px, py, c in self.puntos
                       if math.sqrt((px - x) ** 2 + (py - y) ** 2) > tolerancia]


class Linea:
    def __init__(self):
        self.lineas = []
        self.punto_inicial = None
        self.punto_actual = None
        self.grosor = 5

    def set_grosor(self, grosor):
        self.grosor = grosor

    def agregar(self, x, y, color):
        if self.punto_inicial is None:
            self.punto_inicial = (x, y)
        else:
            self.lineas.append((self.punto_inicial, (x, y), color, self.grosor))
            self.punto_inicial = None

    def actualizar_punto_actual(self, x, y):
        if self.punto_inicial is not None:
            self.punto_actual = (x, y)

    def borrar_cerca_de(self, x, y, tolerancia):
        nuevas_lineas = []
        for (x1, y1), (x2, y2), color, grosor in self.lineas:
            distancia = self.punto_a_linea_distancia(x, y, x1, y1, x2, y2)
            if distancia > tolerancia:
                nuevas_lineas.append(((x1, y1), (x2, y2), color, grosor))
        self.lineas = nuevas_lineas

    def punto_a_linea_distancia(self, px, py, x1, y1, x2, y2):
        longitud = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if longitud == 0:
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
        t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / longitud ** 2))
        projection_x = x1 + t * (x2 - x1)
        projection_y = y1 + t * (y2 - y1)
        return math.sqrt((px - projection_x) ** 2 + (py - projection_y) ** 2)


class Cota:
    def __init__(self):
        self.cotas = []
        self.punto_inicial = None
        self.punto_actual = None

    def agregar(self, x, y, color):
        if self.punto_inicial is None:
            self.punto_inicial = (x, y)
        else:
            self.cotas.append((self.punto_inicial, (x, y), color))
            self.punto_inicial = None

    def actualizar_punto_actual(self, x, y):
        if self.punto_inicial is not None:
            self.punto_actual = (x, y)

    def borrar_cerca_de(self, x, y, tolerancia):
        nuevas_cotas = []
        for (x1, y1), (x2, y2), color in self.cotas:
            distancia = self.punto_a_linea_distancia(x, y, x1, y1, x2, y2)
            if distancia > tolerancia:
                nuevas_cotas.append(((x1, y1), (x2, y2), color))
        self.cotas = nuevas_cotas

    def punto_a_linea_distancia(self, px, py, x1, y1, x2, y2):
        longitud = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if longitud == 0:
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
        t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / longitud ** 2))
        projection_x = x1 + t * (x2 - x1)
        projection_y = y1 + t * (y2 - y1)
        return math.sqrt((px - projection_x) ** 2 + (py - projection_y) ** 2)


class Texto:
    def __init__(self):
        self.textos = []

    def agregar(self, x, y, texto, color, tamaño):
        self.textos.append((texto, x, y, color, tamaño))

    def borrar_cerca_de(self, x, y, tolerancia):
        nuevos_textos = []
        for texto, tx, ty, color, tamaño in self.textos:
            if math.sqrt((tx - x) ** 2 + (ty - y) ** 2) > tolerancia:
                nuevos_textos.append((texto, tx, ty, color, tamaño))
        self.textos = nuevos_textos


class Medir:
    def __init__(self):
        self.medidas = []
        self.punto_inicial = None
        self.punto_actual = None
        self.escala_pixeles_por_metro = 100

    def agregar(self, x, y, color):
        if self.punto_inicial is None:
            self.punto_inicial = (x, y)
        else:
            dist_px = math.sqrt((x - self.punto_inicial[0]) ** 2 + (y - self.punto_inicial[1]) ** 2)
            dist_m = dist_px / self.escala_pixeles_por_metro
            self.medidas.append((self.punto_inicial, (x, y), dist_m, color))
            self.punto_inicial = None

    def actualizar_punto_actual(self, x, y):
        if self.punto_inicial is not None:
            self.punto_actual = (x, y)

    def borrar_cerca_de(self, x, y, tolerancia):
        nuevas_medidas = []
        for (x1, y1), (x2, y2), dist, color in self.medidas:
            distancia = self.punto_a_linea_distancia(x, y, x1, y1, x2, y2)
            if distancia > tolerancia:
                nuevas_medidas.append(((x1, y1), (x2, y2), dist, color))
        self.medidas = nuevas_medidas

    def punto_a_linea_distancia(self, px, py, x1, y1, x2, y2):
        longitud = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if longitud == 0:
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
        t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / longitud ** 2))
        projection_x = x1 + t * (x2 - x1)
        projection_y = y1 + t * (y2 - y1)
        return math.sqrt((px - projection_x) ** 2 + (py - projection_y) ** 2)


class Borrar:
    def __init__(self):
        pass


# Funciones de utilidad
def hex_to_rgb(hex_str):
    if not hex_str:
        return (0, 0, 0)
    hex_str = hex_str.lstrip('#')
    if len(hex_str) != 6:
        return (0, 0, 0)
    try:
        return (int(hex_str[:2], 16) / 255, int(hex_str[2:4], 16) / 255, int(hex_str[4:], 16) / 255)
    except:
        return (0, 0, 0)


def pdf_to_image(pdf_file, page_num=0, zoom=1):
    """Convierte una página de PDF a una imagen PIL."""
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    page = doc.load_page(page_num)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return img


# Función principal
def main():
    st.title("Editor de Planos PDF con Streamlit")

    # Inicializar variables de sesión
    if "pdf_doc" not in st.session_state:
        st.session_state.pdf_doc = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = 0
    if "zoom_factor" not in st.session_state:
        st.session_state.zoom_factor = 1.0
    if "herramienta_activa" not in st.session_state:
        st.session_state.herramienta_activa = None
    if "punto_herramienta" not in st.session_state:
        st.session_state.punto_herramienta = Punto()
    if "linea_herramienta" not in st.session_state:
        st.session_state.linea_herramienta = Linea()
    if "cota_herramienta" not in st.session_state:
        st.session_state.cota_herramienta = Cota()
    if "texto_herramienta" not in st.session_state:
        st.session_state.texto_herramienta = Texto()
    if "medir_herramienta" not in st.session_state:
        st.session_state.medir_herramienta = Medir()
    if "borrar_herramienta" not in st.session_state:
        st.session_state.borrar_herramienta = Borrar()
    if "color_punto" not in st.session_state:
        st.session_state.color_punto = "#ff0000"
    if "color_linea" not in st.session_state:
        st.session_state.color_linea = "#0066ff"
    if "color_cota" not in st.session_state:
        st.session_state.color_cota = "#00cc66"
    if "color_texto" not in st.session_state:
        st.session_state.color_texto = "#333333"
    if "color_medir" not in st.session_state:
        st.session_state.color_medir = "#ff9933"
    if "tamanio_texto" not in st.session_state:
        st.session_state.tamanio_texto = 12
    if "grosor_linea_actual" not in st.session_state:
        st.session_state.grosor_linea_actual = 5

    # Barra lateral para herramientas
    st.sidebar.header("Herramientas")

    # Subir archivo PDF
    uploaded_file = st.sidebar.file_uploader("Subir PDF", type=["pdf"])

    if uploaded_file is not None:
        # Cargar PDF
        if st.session_state.pdf_doc is None:
            try:
                st.session_state.pdf_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                st.success(f"PDF cargado: {len(st.session_state.pdf_doc)} páginas")
            except Exception as e:
                st.error(f"Error al abrir el PDF: {e}")
                return

        doc = st.session_state.pdf_doc
        total_pages = len(doc)

        # Navegación de páginas
        st.sidebar.markdown("---")
        col_prev, col_page, col_next = st.sidebar.columns([1, 2, 1])

        with col_prev:
            if st.button("◀"):
                if st.session_state.current_page > 0:
                    st.session_state.current_page -= 1
                    st.rerun()

        with col_next:
            if st.button("▶"):
                if st.session_state.current_page < total_pages - 1:
                    st.session_state.current_page += 1
                    st.rerun()

        col_page.write(f"Pág {st.session_state.current_page + 1} de {total_pages}")

        # Zoom - Limitado para evitar imágenes demasiado grandes
        st.sidebar.markdown("---")
        zoom_level = st.sidebar.slider("Zoom", 0.5, 2.0, st.session_state.zoom_factor, 0.1)
        if zoom_level != st.session_state.zoom_factor:
            st.session_state.zoom_factor = zoom_level
            st.rerun()

        # Herramientas de dibujo
        st.sidebar.markdown("---")
        herramienta = st.sidebar.selectbox(
            "Herramienta",
            ["Ninguna", "Punto", "Línea", "Cota", "Texto", "Medir", "Borrar"],
            format_func=lambda x: {
                "Ninguna": "Ninguna",
                "Punto": "Punto",
                "Línea": "Línea",
                "Cota": "Cota",
                "Texto": "Texto",
                "Medir": "Medir",
                "Borrar": "Borrar"
            }.get(x, x)
        )

        if herramienta != "Ninguna":
            st.session_state.herramienta_activa = herramienta.lower()
        else:
            st.session_state.herramienta_activa = None

        # Configuración de colores según la herramienta
        if st.session_state.herramienta_activa == "punto":
            st.session_state.color_punto = st.sidebar.color_picker("Color del punto", st.session_state.color_punto)
        elif st.session_state.herramienta_activa == "línea":
            st.session_state.color_linea = st.sidebar.color_picker("Color de la línea", st.session_state.color_linea)
            st.session_state.grosor_linea_actual = st.sidebar.slider("Grosor de línea", 1, 20,
                                                                     st.session_state.grosor_linea_actual)
            st.session_state.linea_herramienta.set_grosor(st.session_state.grosor_linea_actual)
        elif st.session_state.herramienta_activa == "cota":
            st.session_state.color_cota = st.sidebar.color_picker("Color de la cota", st.session_state.color_cota)
        elif st.session_state.herramienta_activa == "texto":
            st.session_state.color_texto = st.sidebar.color_picker("Color del texto", st.session_state.color_texto)
            st.session_state.tamanio_texto = st.sidebar.slider("Tamaño del texto", 8, 72,
                                                               st.session_state.tamanio_texto)
        elif st.session_state.herramienta_activa == "medir":
            st.session_state.color_medir = st.sidebar.color_picker("Color de la medida", st.session_state.color_medir)
            st.session_state.medir_herramienta.escala_pixeles_por_metro = st.sidebar.number_input(
                "Escala (píxeles por metro)",
                min_value=1,
                value=st.session_state.medir_herramienta.escala_pixeles_por_metro
            )

        # Convertir página actual a imagen con un zoom base menor
        try:
            # Guardar el PDF en un temporal para leerlo
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_path = tmp_file.name
                doc.save(tmp_path)

            # Leer el archivo temporal
            with open(tmp_path, "rb") as f:
                pdf_data = f.read()

            # Convertir a imagen
            img = pdf_to_image(io.BytesIO(pdf_data), st.session_state.current_page, zoom=1.5)

            # Redimensionar imagen según el zoom
            if st.session_state.zoom_factor != 1.0:
                new_width = int(img.width * st.session_state.zoom_factor)
                new_height = int(img.height * st.session_state.zoom_factor)
                img = img.resize((new_width, new_height), Image.LANCZOS)

            # Limitar el tamaño máximo de la imagen para evitar problemas
            max_size = 2000  # Máximo 2000 píxeles en cualquier dimensión
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_width = int(img.width * ratio)
                new_height = int(img.height * ratio)
                img = img.resize((new_width, new_height), Image.LANCZOS)
                st.warning(
                    f"La imagen ha sido reducida a {new_width}x{new_height} píxeles para mejorar el rendimiento.")

            # Mostrar la imagen
            st.image(img, caption=f"Página {st.session_state.current_page + 1}")

            # Canvas para dibujar
            st.subheader("Área de Dibujo")

            # Configuración del canvas según la herramienta activa
            drawing_mode = "transform"  # Por defecto

            if st.session_state.herramienta_activa == "punto":
                drawing_mode = "point"
                stroke_color = st.session_state.color_punto
            elif st.session_state.herramienta_activa == "línea":
                drawing_mode = "line"
                stroke_color = st.session_state.color_linea
            elif st.session_state.herramienta_activa == "cota":
                drawing_mode = "line"
                stroke_color = st.session_state.color_cota
            elif st.session_state.herramienta_activa == "texto":
                drawing_mode = "text"
                stroke_color = st.session_state.color_texto
            elif st.session_state.herramienta_activa == "medir":
                drawing_mode = "line"
                stroke_color = st.session_state.color_medir
            elif st.session_state.herramienta_activa == "borrar":
                drawing_mode = "transform"
            else:
                drawing_mode = "transform"
                stroke_color = "#000000"

            # Crear el canvas con manejo de errores
            try:
                canvas_result = st_canvas(
                    fill_color="rgba(255, 165, 0, 0.3)",
                    stroke_width=st.session_state.grosor_linea_actual if st.session_state.herramienta_activa == "línea" else 3,
                    stroke_color=stroke_color,
                    background_image=img,
                    update_streamlit=True,
                    height=img.height,
                    width=img.width,
                    drawing_mode=drawing_mode,
                    initial_drawing=None,
                    key=f"canvas_page_{st.session_state.current_page}",
                    display_toolbar=True,
                )

                # Procesar los resultados del canvas
                if canvas_result.json_data is not None:
                    objects = canvas_result.json_data["objects"]

                    for obj in objects:
                        if obj["type"] == "path" and st.session_state.herramienta_activa == "línea":
                            if len(obj["path"]) >= 2:
                                x1, y1 = obj["path"][0]
                                x2, y2 = obj["path"][1]
                                x1 /= st.session_state.zoom_factor
                                y1 /= st.session_state.zoom_factor
                                x2 /= st.session_state.zoom_factor
                                y2 /= st.session_state.zoom_factor
                                st.session_state.linea_herramienta.lineas.append(
                                    ((x1, y1), (x2, y2), st.session_state.color_linea,
                                     st.session_state.grosor_linea_actual)
                                )
                        elif obj["type"] == "path" and st.session_state.herramienta_activa == "cota":
                            if len(obj["path"]) >= 2:
                                x1, y1 = obj["path"][0]
                                x2, y2 = obj["path"][1]
                                x1 /= st.session_state.zoom_factor
                                y1 /= st.session_state.zoom_factor
                                x2 /= st.session_state.zoom_factor
                                y2 /= st.session_state.zoom_factor
                                st.session_state.cota_herramienta.cotas.append(
                                    ((x1, y1), (x2, y2), st.session_state.color_cota)
                                )
                        elif obj["type"] == "path" and st.session_state.herramienta_activa == "medir":
                            if len(obj["path"]) >= 2:
                                x1, y1 = obj["path"][0]
                                x2, y2 = obj["path"][1]
                                x1 /= st.session_state.zoom_factor
                                y1 /= st.session_state.zoom_factor
                                x2 /= st.session_state.zoom_factor
                                y2 /= st.session_state.zoom_factor
                                dist_px = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                                dist_m = dist_px / st.session_state.medir_herramienta.escala_pixeles_por_metro
                                st.session_state.medir_herramienta.medidas.append(
                                    ((x1, y1), (x2, y2), dist_m, st.session_state.color_medir)
                                )
                        elif obj["type"] == "point" and st.session_state.herramienta_activa == "punto":
                            x = obj["left"]
                            y = obj["top"]
                            x /= st.session_state.zoom_factor
                            y /= st.session_state.zoom_factor
                            st.session_state.punto_herramienta.puntos.append(
                                (x, y, st.session_state.color_punto)
                            )
                        elif obj["type"] == "text" and st.session_state.herramienta_activa == "texto":
                            x = obj["left"]
                            y = obj["top"]
                            texto = obj.get("text", "Texto")
                            x /= st.session_state.zoom_factor
                            y /= st.session_state.zoom_factor
                            st.session_state.texto_herramienta.textos.append(
                                (texto, x, y, st.session_state.color_texto, st.session_state.tamanio_texto)
                            )
                        elif obj["type"] == "rect" and st.session_state.herramienta_activa == "borrar":
                            x = obj["left"]
                            y = obj["top"]
                            w = obj["width"]
                            h = obj["height"]
                            x /= st.session_state.zoom_factor
                            y /= st.session_state.zoom_factor
                            w /= st.session_state.zoom_factor
                            h /= st.session_state.zoom_factor

                            # Borrar anotaciones en el área
                            st.session_state.punto_herramienta.puntos = [
                                (px, py, c) for px, py, c in st.session_state.punto_herramienta.puntos
                                if not (x <= px <= x + w and y <= py <= y + h)
                            ]

                            nuevas_lineas = []
                            for (x1, y1), (x2, y2), color, grosor in st.session_state.linea_herramienta.lineas:
                                if not (x <= x1 <= x + w and y <= y1 <= y + h) and not (
                                        x <= x2 <= x + w and y <= y2 <= y + h):
                                    nuevas_lineas.append(((x1, y1), (x2, y2), color, grosor))
                            st.session_state.linea_herramienta.lineas = nuevas_lineas

                            nuevas_cotas = []
                            for (x1, y1), (x2, y2), color in st.session_state.cota_herramienta.cotas:
                                if not (x <= x1 <= x + w and y <= y1 <= y + h) and not (
                                        x <= x2 <= x + w and y <= y2 <= y + h):
                                    nuevas_cotas.append(((x1, y1), (x2, y2), color))
                            st.session_state.cota_herramienta.cotas = nuevas_cotas

                            st.session_state.texto_herramienta.textos = [
                                (texto, tx, ty, color, tamaño) for texto, tx, ty, color, tamaño in
                                st.session_state.texto_herramienta.textos
                                if not (x <= tx <= x + w and y <= ty <= y + h)
                            ]

                            nuevas_medidas = []
                            for (x1, y1), (x2, y2), dist, color in st.session_state.medir_herramienta.medidas:
                                if not (x <= x1 <= x + w and y <= y1 <= y + h) and not (
                                        x <= x2 <= x + w and y <= y2 <= y + h):
                                    nuevas_medidas.append(((x1, y1), (x2, y2), dist, color))
                            st.session_state.medir_herramienta.medidas = nuevas_medidas

                    # Actualizar la vista
                    st.rerun()

            except Exception as e:
                st.error(f"Error al crear el canvas: {e}")
                st.info("Intenta reducir el zoom o usar un PDF con páginas más pequeñas.")

            # Botón para guardar el PDF
            st.sidebar.markdown("---")
            if st.sidebar.button("💾 Guardar Cambios en PDF"):
                try:
                    # Crear un archivo temporal para guardar el PDF modificado
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        temp_path = tmp_file.name

                    # Guardar el PDF original en el archivo temporal
                    doc.save(temp_path)

                    # Abrir el PDF temporal para modificarlo
                    doc_modificado = fitz.open(temp_path)
                    page = doc_modificado.load_page(st.session_state.current_page)

                    # Aplicar anotaciones al PDF
                    # Puntos
                    for x, y, color in st.session_state.punto_herramienta.puntos:
                        size = 5
                        r = fitz.Rect(x, y, x + size, y + size)
                        annot = page.add_rect_annot(r)
                        color_rgb = hex_to_rgb(color)
                        annot.set_colors(stroke=color_rgb, fill=color_rgb)
                        annot.set_info(subject="punto")
                        annot.update()

                    # Líneas
                    for (x1, y1), (x2, y2), color, grosor in st.session_state.linea_herramienta.lineas:
                        p1 = fitz.Point(x1, y1)
                        p2 = fitz.Point(x2, y2)
                        annot = page.add_line_annot(p1, p2)
                        color_rgb = hex_to_rgb(color)
                        annot.set_colors(stroke=color_rgb)
                        annot.set_border(width=grosor)
                        annot.set_info(subject="trazo")
                        annot.update()

                    # Cotas
                    for (x1, y1), (x2, y2), color in st.session_state.cota_herramienta.cotas:
                        p1 = fitz.Point(x1, y1)
                        p2 = fitz.Point(x2, y2)
                        annot = page.add_line_annot(p1, p2)
                        color_rgb = hex_to_rgb(color)
                        annot.set_colors(stroke=color_rgb)
                        annot.set_border(width=2)
                        annot.set_info(subject="cota")
                        annot.update()

                    # Textos
                    for texto, x, y, color, tamaño in st.session_state.texto_herramienta.textos:
                        point = fitz.Point(x, y)
                        color_rgb = hex_to_rgb(color)
                        page.insert_text(
                            point,
                            texto,
                            fontsize=tamaño,
                            fontname="helv",
                            color=color_rgb
                        )

                    # Medidas
                    for (x1, y1), (x2, y2), dist, color in st.session_state.medir_herramienta.medidas:
                        p1 = fitz.Point(x1, y1)
                        p2 = fitz.Point(x2, y2)
                        annot = page.add_line_annot(p1, p2)
                        color_rgb = hex_to_rgb(color)
                        annot.set_colors(stroke=color_rgb)
                        annot.set_border(width=3)
                        annot.set_info(subject="medir")
                        annot.update()

                    # Guardar el PDF modificado
                    doc_modificado.save(temp_path)

                    # Leer el PDF modificado para descargar
                    with open(temp_path, "rb") as f:
                        pdf_data = f.read()

                    # Botón de descarga
                    st.sidebar.download_button(
                        label="Descargar PDF Modificado",
                        data=pdf_data,
                        file_name="modificado.pdf",
                        mime="application/pdf"
                    )

                    st.success("PDF guardado correctamente. Descarga lista.")
                except Exception as e:
                    st.error(f"Error al guardar el PDF: {e}")
                finally:
                    # Eliminar el archivo temporal
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
        except Exception as e:
            st.error(f"Error al procesar la imagen: {e}")
            st.info("El PDF puede tener páginas demasiado grandes. Intenta con un archivo más pequeño.")
    else:
        st.info("Por favor, sube un archivo PDF desde la barra lateral.")


if __name__ == "__main__":
    main()