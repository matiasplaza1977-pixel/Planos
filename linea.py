from PyQt5.QtGui import QPen, QColor
from PyQt5.QtCore import Qt
import math


class Linea:
    """Clase para gestionar líneas/trazos de anotación con grosor variable."""

    def __init__(self):
        self.lineas = []  # Lista de tuplas ((x1, y1), (x2, y2), color_hex, grosor)
        self.punto_inicial = None
        self.punto_actual = None
        self.color_actual = "#0000ff"
        self.grosor_actual = 5  # Grosor por defecto aumentado

    def set_grosor(self, grosor):
        """
        Establece el grosor de línea actual.

        Args:
            grosor: Grosor de línea (sin límite máximo)
        """
        # Eliminamos el límite máximo para permitir grosores mayores
        self.grosor_actual = max(1, grosor)  # Solo aseguramos que sea al menos 1


    def agregar(self, x, y, color_hex):
        """
        Agrega un punto de la línea (inicio o fin).
        Args:
            x: Coordenada X
            y: Coordenada Y
            color_hex: Color en formato hexadecimal
        """
        if self.punto_inicial is None:
            self.punto_inicial = (x, y)
            self.color_actual = color_hex

        else:
            # Guardar con grosor actual
            self.lineas.append((self.punto_inicial, (x, y), self.color_actual, self.grosor_actual))

            self.punto_inicial = None
            self.punto_actual = None

    def actualizar_punto_actual(self, x, y):
        """
        Actualiza el punto actual mientras se dibuja la línea.
        Args:
            x: Coordenada X
            y: Coordenada Y
        """
        self.punto_actual = (x, y)

    def dibujar(self, painter, zoom_factor=1.0):
        """
        Dibuja todas las líneas en el painter.
        Args:
            painter: QPainter para dibujar
            zoom_factor: Factor de zoom actual
        """
        # Dibujar líneas completadas
        for item in self.lineas:
            # Compatibilidad con formato antiguo (sin grosor)
            if len(item) == 3:
                (x1, y1), (x2, y2), color_hex = item
                grosor = 5  # Grosor por defecto aumentado
            else:
                (x1, y1), (x2, y2), color_hex, grosor = item

            color = QColor(color_hex)
            # Aplicamos una fórmula de zoom más agresiva para el grosor
            grosor_zoom = grosor * (1 + (zoom_factor - 1) * 0.5)
            pen = QPen(color, grosor_zoom, Qt.SolidLine)
            pen.setCapStyle(Qt.RoundCap)  # Mejor apariencia para líneas gruesas
            painter.setPen(pen)
            painter.drawLine(
                int(x1 * zoom_factor),
                int(y1 * zoom_factor),
                int(x2 * zoom_factor),
                int(y2 * zoom_factor)
            )

        # Dibujar línea en progreso
        if self.punto_inicial is not None and self.punto_actual is not None:
            x1, y1 = self.punto_inicial
            x2, y2 = self.punto_actual
            color = QColor(self.color_actual)
            # Aplicamos la misma fórmula de zoom para la línea en progreso
            grosor_zoom = self.grosor_actual * (1 + (zoom_factor - 1) * 0.5)
            pen = QPen(color, grosor_zoom, Qt.DashLine)
            pen.setCapStyle(Qt.RoundCap)  # Mejor apariencia para líneas gruesas
            painter.setPen(pen)
            painter.drawLine(
                int(x1 * zoom_factor),
                int(y1 * zoom_factor),
                int(x2 * zoom_factor),
                int(y2 * zoom_factor)
            )

    def borrar_cerca_de(self, x, y, tolerancia):
        """
        Borra líneas cercanas a una posición.
        Args:
            x: Coordenada X
            y: Coordenada Y
            tolerancia: Distancia máxima para considerar una línea cercana
        """

        def distancia_punto_a_linea(px, py, x1, y1, x2, y2):
            """Calcula la distancia de un punto a una línea."""
            dx = x2 - x1
            dy = y2 - y1
            len_sq = dx * dx + dy * dy
            if len_sq == 0:
                return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
            t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / len_sq))
            closest_x = x1 + t * dx
            closest_y = y1 + t * dy
            return math.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)

        nuevas_lineas = []
        for item in self.lineas:
            if len(item) == 3:
                (x1, y1), (x2, y2), color = item
                grosor = 5  # Grosor por defecto aumentado
            else:
                (x1, y1), (x2, y2), color, grosor = item

            if distancia_punto_a_linea(x, y, x1, y1, x2, y2) > tolerancia:
                nuevas_lineas.append(((x1, y1), (x2, y2), color, grosor))

        self.lineas = nuevas_lineas