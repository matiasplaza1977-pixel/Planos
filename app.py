import streamlit as st
import fitz  # PyMuPDF
import io
import os
import math
import numpy as np
from PIL import Image
import base64
from streamlit_drawable_canvas import st_canvas
import tempfile

# Configuración de la página
st.set_page_config(layout="wide", page_title="Editor de Planos PDF")


# Clases para manejar las anotaciones
class Punto:
    def __init__(self):
        self.puntos = []

    def agregar(self, x, y, color):
        self.puntos.append((x, y, color))

    def borrar_cerca_de(self, x, y, tolerancia):
        self.puntos = [(px, py, c) for px, py, c in self.puntos
                       if math.sqrt((px - x) ** 2 + (py - y) ** 2) > tolerancia]

    def dibujar(self, ctx, zoom_factor):
        for x, y, color in self.puntos:
            ctx.beginPath()
            ctx.arc(x * zoom_factor, y * zoom_factor, 5 * zoom_factor, 0, 2 * math.pi)
            ctx.fillStyle = color
            ctx.fill()


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
            # Calcular distancia del punto a la línea
            distancia = self.punto_a_linea_distancia(x, y, x1, y1, x2, y2)
            if distancia > tolerancia:
                nuevas_lineas.append(((x1, y1), (x2, y2), color, grosor))
        self.lineas = nuevas_lineas

    def punto_a_linea_distancia(self, px, py, x1, y1, x2, y2):
        # Calcular la distancia perpendicular desde un punto a una línea
        longitud = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if longitud == 0:
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
        t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / longitud ** 2))
        projection_x = x1 + t * (x2 - x1)
        projection_y = y1 + t * (y2 - y1)
        return math.sqrt((px - projection_x) ** 2 + (py - projection_y) ** 2)

    def dibujar(self, ctx, zoom_factor):
        for (x1, y1), (x2, y2), color, grosor in self.lineas:
            ctx.beginPath()
            ctx.moveTo(x1 * zoom_factor, y1 * zoom_factor)
            ctx.lineTo(x2 * zoom_factor, y2 * zoom_factor)
            ctx.strokeStyle = color
            ctx.lineWidth = grosor * zoom_factor
            ctx.stroke()

        # Dibujar línea temporal si estamos en medio de un trazo
        if self.punto_inicial is not None and self.punto_actual is not None:
            ctx.beginPath()
            ctx.moveTo(self.punto_inicial[0] * zoom_factor, self.punto_inicial[1] * zoom_factor)
            ctx.lineTo(self.punto_actual[0] * zoom_factor, self.punto_actual[1] * zoom_factor)
            ctx.strokeStyle = color
            ctx.lineWidth = grosor * zoom_factor
            ctx.setLineDash([5, 3])
            ctx.stroke()
            ctx.setLineDash([])


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
            # Calcular distancia del punto a la línea
            distancia = self.punto_a_linea_distancia(x, y, x1, y1, x2, y2)
            if distancia > tolerancia:
                nuevas_cotas.append(((x1, y1), (x2, y2), color))
        self.cotas = nuevas_cotas

    def punto_a_linea_distancia(self, px, py, x1, y1, x2, y2):
        # Calcular la distancia perpendicular desde un punto a una línea
        longitud = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if longitud == 0:
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
        t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / longitud ** 2))
        projection_x = x1 + t * (x2 - x1)
        projection_y = y1 + t * (y2 - y1)
        return math.sqrt((px - projection_x) ** 2 + (py - projection_y) ** 2)

    def dibujar(self, ctx, zoom_factor):
        for (x1, y1), (x2, y2), color in self.cotas:
            # Dibujar línea
            ctx.beginPath()
            ctx.moveTo(x1 * zoom_factor, y1 * zoom_factor)
            ctx.lineTo(x2 * zoom_factor, y2 * zoom_factor)
            ctx.strokeStyle = color
            ctx.lineWidth = 2 * zoom_factor
            ctx.stroke()

            # Dibujar marcas de cota
            longitud = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if longitud > 0:
                # Vector unitario perpendicular a la línea
                nx = -(y2 - y1) / longitud
                ny = (x2 - x1) / longitud

                # Tamaño de las marcas
                marca_size = 5 * zoom_factor

                # Marca en el punto inicial
                ctx.beginPath()
                ctx.moveTo(x1 * zoom_factor, y1 * zoom_factor)
                ctx.lineTo((x1 + nx * marca_size) * zoom_factor, (y1 + ny * marca_size) * zoom_factor)
                ctx.stroke()

                # Marca en el punto final
                ctx.beginPath()
                ctx.moveTo(x2 * zoom_factor, y2 * zoom_factor)
                ctx.lineTo((x2 + nx * marca_size) * zoom_factor, (y2 + ny * marca_size) * zoom_factor)
                ctx.stroke()

                # Texto de la cota
                ctx.font = f"{12 * zoom_factor}px Arial"
                ctx.fillStyle = color
                ctx.textAlign = "center"
                ctx.textBaseline = "middle"
                mid_x = (x1 + x2) / 2
                mid_y = (y1 + y2) / 2
                ctx.fillText(f"{longitud:.1f}", mid_x * zoom_factor, (mid_y + ny * 15) * zoom_factor)

        # Dibujar cota temporal si estamos en medio de un trazo
        if self.punto_inicial is not None and self.punto_actual is not None:
            ctx.beginPath()
            ctx.moveTo(self.punto_inicial[0] * zoom_factor, self.punto_inicial[1] * zoom_factor)
            ctx.lineTo(self.punto_actual[0] * zoom_factor, self.punto_actual[1] * zoom_factor)
            ctx.strokeStyle = color
            ctx.lineWidth = 2 * zoom_factor
            ctx.setLineDash([5, 3])
            ctx.stroke()
            ctx.setLineDash([])


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

    def dibujar(self, ctx, zoom_factor):
        for texto, x, y, color, tamaño in self.textos:
            ctx.font = f"{tamaño * zoom_factor}px Arial"
            ctx.fillStyle = color
            ctx.textAlign = "left"
            ctx.textBaseline = "top"
            ctx.fillText(texto, x * zoom_factor, y * zoom_factor)


class Medir:
    def __init__(self):
        self.medidas = []
        self.punto_inicial = None
        self.punto_actual = None
        self.escala_pixeles_por_metro = 100  # Por defecto, 100 píxeles = 1 metro

    def agregar(self, x, y, color):
        if self.punto_inicial is None:
            self.punto_inicial = (x, y)
        else:
            # Calcular distancia en píxeles
            dist_px = math.sqrt((x - self.punto_inicial[0]) ** 2 + (y - self.punto_inicial[1]) ** 2)
            # Convertir a metros
            dist_m = dist_px / self.escala_pixeles_por_metro
            self.medidas.append((self.punto_inicial, (x, y), dist_m, color))
            self.punto_inicial = None

    def actualizar_punto_actual(self, x, y):
        if self.punto_inicial is not None:
            self.punto_actual = (x, y)

    def borrar_cerca_de(self, x, y, tolerancia):
        nuevas_medidas = []
        for (x1, y1), (x2, y2), dist, color in self.medidas:
            # Calcular distancia del punto a la línea
            distancia = self.punto_a_linea_distancia(x, y, x1, y1, x2, y2)
            if distancia > tolerancia:
                nuevas_medidas.append(((x1, y1), (x2, y2), dist, color))
        self.medidas = nuevas_medidas

    def punto_a_linea_distancia(self, px, py, x1, y1, x2, y2):
        # Calcular la distancia perpendicular desde un punto a una línea
        longitud = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if longitud == 0:
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
        t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / longitud ** 2))
        projection_x = x1 + t * (x2 - x1)
        projection_y = y1 + t * (y2 - y1)
        return math.sqrt((px - projection_x) ** 2 + (py - projection_y) ** 2)

    def dibujar(self, ctx, zoom_factor):
        for (x1, y1), (x2, y2), dist, color in self.medidas:
            # Dibujar línea
            ctx.beginPath()
            ctx.moveTo(x1 * zoom_factor, y1 * zoom_factor)
            ctx.lineTo(x2 * zoom_factor, y2 * zoom_factor)
            ctx.strokeStyle = color
            ctx.lineWidth = 3 * zoom_factor
            ctx.stroke()

            # Texto de la medida
            ctx.font = f"{12 * zoom_factor}px Arial"
            ctx.fillStyle = color
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            ctx.fillText(f"{dist:.2f} m", mid_x * zoom_factor, mid_y * zoom_factor)

        # Dibujar medida temporal si estamos en medio de un trazo
        if self.punto_inicial is not None and self.punto_actual is not None:
            ctx.beginPath()
            ctx.moveTo(self.punto_inicial[0] * zoom_factor, self.punto_inicial[1] * zoom_factor)
            ctx.lineTo(self.punto_actual[0] * zoom_factor, self.punto_actual[1] * zoom_factor)
            ctx.strokeStyle = color
            ctx.lineWidth = 3 * zoom_factor
            ctx.setLineDash([5, 3])
            ctx.stroke()
            ctx.setLineDash([])


class Borrar:
    def __init__(self):
        pass  # No necesita estado interno


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


def rgb_to_hex(rgb_tuple):
    if rgb_tuple is None or len(rgb_tuple) < 3:
        return "#000000"
    r = int(rgb_tuple[0] * 255)
    g = int(rgb_tuple[1] * 255)
    b = int(rgb_tuple[2] * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


def pdf_to_image(pdf_file, page_num=0, zoom=2):
    """Convierte una página de PDF a una imagen PIL."""
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    page = doc.load_page(page_num)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return img


def draw_annotations(image, punto_herramienta, linea_herramienta, cota_herramienta, texto_herramienta,
                     medir_herramienta, zoom_factor):
    """Dibuja las anotaciones sobre la imagen."""
    # Crear un canvas temporal para dibujar las anotaciones
    canvas_image = Image.new('RGBA', image.size, (0, 0, 0, 0))

    # Convertir la imagen a un formato que pueda ser usado por st_canvas
    buffered = io.BytesIO()
    canvas_image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

    return img_str


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

        # Zoom
        st.sidebar.markdown("---")
        zoom_level = st.sidebar.slider("Zoom", 0.5, 3.0, st.session_state.zoom_factor, 0.1)
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

        # Convertir página actual a imagen
        page = doc.load_page(st.session_state.current_page)
        img = pdf_to_image(io.BytesIO(doc.tobytes()), st.session_state.current_page, zoom=2)

        # Redimensionar imagen según el zoom
        if st.session_state.zoom_factor != 1.0:
            new_width = int(img.width * st.session_state.zoom_factor)
            new_height = int(img.height * st.session_state.zoom_factor)
            img = img.resize((new_width, new_height), Image.LANCZOS)

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

        # Crear el canvas
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",  # No se usa para puntos o líneas
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
                    # Procesar líneas
                    if len(obj["path"]) >= 2:
                        x1, y1 = obj["path"][0]
                        x2, y2 = obj["path"][1]
                        # Convertir coordenadas relativas al zoom
                        x1 /= st.session_state.zoom_factor
                        y1 /= st.session_state.zoom_factor
                        x2 /= st.session_state.zoom_factor
                        y2 /= st.session_state.zoom_factor
                        st.session_state.linea_herramienta.lineas.append(
                            ((x1, y1), (x2, y2), st.session_state.color_linea, st.session_state.grosor_linea_actual)
                        )
                elif obj["type"] == "path" and st.session_state.herramienta_activa == "cota":
                    # Procesar cotas
                    if len(obj["path"]) >= 2:
                        x1, y1 = obj["path"][0]
                        x2, y2 = obj["path"][1]
                        # Convertir coordenadas relativas al zoom
                        x1 /= st.session_state.zoom_factor
                        y1 /= st.session_state.zoom_factor
                        x2 /= st.session_state.zoom_factor
                        y2 /= st.session_state.zoom_factor
                        st.session_state.cota_herramienta.cotas.append(
                            ((x1, y1), (x2, y2), st.session_state.color_cota)
                        )
                elif obj["type"] == "path" and st.session_state.herramienta_activa == "medir":
                    # Procesar medidas
                    if len(obj["path"]) >= 2:
                        x1, y1 = obj["path"][0]
                        x2, y2 = obj["path"][1]
                        # Convertir coordenadas relativas al zoom
                        x1 /= st.session_state.zoom_factor
                        y1 /= st.session_state.zoom_factor
                        x2 /= st.session_state.zoom_factor
                        y2 /= st.session_state.zoom_factor
                        # Calcular distancia en píxeles y convertir a metros
                        dist_px = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                        dist_m = dist_px / st.session_state.medir_herramienta.escala_pixeles_por_metro
                        st.session_state.medir_herramienta.medidas.append(
                            ((x1, y1), (x2, y2), dist_m, st.session_state.color_medir)
                        )
                elif obj["type"] == "point" and st.session_state.herramienta_activa == "punto":
                    # Procesar puntos
                    x = obj["left"]
                    y = obj["top"]
                    # Convertir coordenadas relativas al zoom
                    x /= st.session_state.zoom_factor
                    y /= st.session_state.zoom_factor
                    st.session_state.punto_herramienta.puntos.append(
                        (x, y, st.session_state.color_punto)
                    )
                elif obj["type"] == "text" and st.session_state.herramienta_activa == "texto":
                    # Procesar texto
                    x = obj["left"]
                    y = obj["top"]
                    texto = obj.get("text", "Texto")
                    # Convertir coordenadas relativas al zoom
                    x /= st.session_state.zoom_factor
                    y /= st.session_state.zoom_factor
                    st.session_state.texto_herramienta.textos.append(
                        (texto, x, y, st.session_state.color_texto, st.session_state.tamanio_texto)
                    )
                elif obj["type"] == "rect" and st.session_state.herramienta_activa == "borrar":
                    # Procesar borrado (área rectangular)
                    x = obj["left"]
                    y = obj["top"]
                    w = obj["width"]
                    h = obj["height"]
                    # Convertir coordenadas relativas al zoom
                    x /= st.session_state.zoom_factor
                    y /= st.session_state.zoom_factor
                    w /= st.session_state.zoom_factor
                    h /= st.session_state.zoom_factor

                    # Borrar anotaciones en el área
                    # Puntos
                    st.session_state.punto_herramienta.puntos = [
                        (px, py, c) for px, py, c in st.session_state.punto_herramienta.puntos
                        if not (x <= px <= x + w and y <= py <= y + h)
                    ]

                    # Líneas
                    nuevas_lineas = []
                    for (x1, y1), (x2, y2), color, grosor in st.session_state.linea_herramienta.lineas:
                        # Verificar si la línea intersecta con el rectángulo
                        if not (x <= x1 <= x + w and y <= y1 <= y + h) and not (x <= x2 <= x + w and y <= y2 <= y + h):
                            nuevas_lineas.append(((x1, y1), (x2, y2), color, grosor))
                    st.session_state.linea_herramienta.lineas = nuevas_lineas

                    # Cotas
                    nuevas_cotas = []
                    for (x1, y1), (x2, y2), color in st.session_state.cota_herramienta.cotas:
                        # Verificar si la cota intersecta con el rectángulo
                        if not (x <= x1 <= x + w and y <= y1 <= y + h) and not (x <= x2 <= x + w and y <= y2 <= y + h):
                            nuevas_cotas.append(((x1, y1), (x2, y2), color))
                    st.session_state.cota_herramienta.cotas = nuevas_cotas

                    # Textos
                    st.session_state.texto_herramienta.textos = [
                        (texto, tx, ty, color, tamaño) for texto, tx, ty, color, tamaño in
                        st.session_state.texto_herramienta.textos
                        if not (x <= tx <= x + w and y <= ty <= y + h)
                    ]

                    # Medidas
                    nuevas_medidas = []
                    for (x1, y1), (x2, y2), dist, color in st.session_state.medir_herramienta.medidas:
                        # Verificar si la medida intersecta con el rectángulo
                        if not (x <= x1 <= x + w and y <= y1 <= y + h) and not (x <= x2 <= x + w and y <= y2 <= y + h):
                            nuevas_medidas.append(((x1, y1), (x2, y2), dist, color))
                    st.session_state.medir_herramienta.medidas = nuevas_medidas

            # Actualizar la vista
            st.rerun()

        # Botón para guardar el PDF
        st.sidebar.markdown("---")
        if st.sidebar.button("💾 Guardar Cambios en PDF"):
            # Crear un archivo temporal para guardar el PDF modificado
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                temp_path = tmp_file.name

            try:
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
    else:
        st.info("Por favor, sube un archivo PDF desde la barra lateral.")


if __name__ == "__main__":
    main()