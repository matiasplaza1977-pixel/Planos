from PyQt5.QtGui import QPen, QColor, QFont, QPainterPath
from PyQt5.QtCore import Qt, QPointF
import math
class Medir:
    """Clase para gestionar mediciones en metros entre dos puntos."""
    def __init__(self):
        self.medidas = []  # Lista de tuplas ((x1, y1), (x2, y2), distancia_metros, color_hex)
        self.punto_inicial = None
        self.punto_actual = None
        self.color_actual = "#ff9933"
        # CALIBRADO: Escala fija basada en medición conocida (100m reales)
        self.escala_pixeles_por_metro = 3.45
    def set_escala(self, pixeles_por_metro):
        """
        Establece la escala de conversión de píxeles a metros.
        Args:
            pixeles_por_metro: Cantidad de píxeles que equivalen a 1 metro
        """
        self.escala_pixeles_por_metro = pixeles_por_metro
    def agregar(self, x, y, color_hex):
        """
        Agrega un punto de la medida (inicio o fin).
        Args:
            x: Coordenada X
            y: Coordenada Y
            color_hex: Color en formato hexadecimal
        """
        if self.punto_inicial is None:
            self.punto_inicial = (x, y)
            self.color_actual = color_hex
        else:
            # Calcular distancia en píxeles
            dx = x - self.punto_inicial[0]
            dy = y - self.punto_inicial[1]
            distancia_pixeles = math.sqrt(dx * dx + dy * dy)
            # Convertir a metros
            distancia_metros = distancia_pixeles / self.escala_pixeles_por_metro
            self.medidas.append((self.punto_inicial, (x, y), distancia_metros, self.color_actual))
            self.punto_inicial = None
            self.punto_actual = None
    def actualizar_punto_actual(self, x, y):
        """
        Actualiza el punto actual mientras se dibuja la medida.
        Args:
            x: Coordenada X
            y: Coordenada Y
        """
        self.punto_actual = (x, y)
    def dibujar_flecha(self, painter, x1, y1, x2, y2, zoom_factor):
        """
        Dibuja una flecha desde (x1, y1) hacia (x2, y2).
        Args:
            painter: QPainter para dibujar
            x1, y1: Coordenadas del inicio
            x2, y2: Coordenadas del fin
            zoom_factor: Factor de zoom actual
        """
        # Calcular ángulo de la línea
        dx = x2 - x1
        dy = y2 - y1
        angle = math.atan2(dy, dx)
        # Tamaño de la flecha
        arrow_size = 10 * zoom_factor
        # Puntos de la flecha
        arrow_p1 = QPointF(
            x2 - arrow_size * math.cos(angle - math.pi / 6),
            y2 - arrow_size * math.sin(angle - math.pi / 6)
        )
        arrow_p2 = QPointF(
            x2 - arrow_size * math.cos(angle + math.pi / 6),
            y2 - arrow_size * math.sin(angle + math.pi / 6)
        )
        # Dibujar la flecha
        path = QPainterPath()
        path.moveTo(x2, y2)
        path.lineTo(arrow_p1)
        path.moveTo(x2, y2)
        path.lineTo(arrow_p2)
        painter.drawPath(path)
    def dibujar(self, painter, zoom_factor=1.0):
        """
        Dibuja todas las medidas en el painter.
        Args:
            painter: QPainter para dibujar
            zoom_factor: Factor de zoom actual
        """
        # Dibujar medidas completadas
        for (x1, y1), (x2, y2), distancia_metros, color_hex in self.medidas:
            color = QColor(color_hex)
            pen = QPen(color, 3 * zoom_factor, Qt.SolidLine)
            painter.setPen(pen)
            # Coordenadas escaladas
            sx1 = x1 * zoom_factor
            sy1 = y1 * zoom_factor
            sx2 = x2 * zoom_factor
            sy2 = y2 * zoom_factor
            # Dibujar línea principal
            painter.drawLine(int(sx1), int(sy1), int(sx2), int(sy2))
            # Dibujar flechas en ambos extremos
            self.dibujar_flecha(painter, sx2, sy2, sx1, sy1, zoom_factor)
            self.dibujar_flecha(painter, sx1, sy1, sx2, sy2, zoom_factor)
            # Posición del texto (punto medio, 20px arriba)
            mid_x = (sx1 + sx2) / 2
            mid_y = (sy1 + sy2) / 2 - 20 * zoom_factor  # 20px arriba
            # Configurar fuente
            font = QFont("Arial", int(12 * zoom_factor), QFont.Bold)
            painter.setFont(font)
            # Texto de la medida
            texto = f"{distancia_metros:.2f} m"
            metrics = painter.fontMetrics()
            text_rect = metrics.boundingRect(texto)
            text_width = text_rect.width()
            # Dibujar texto en negro, centrado
            painter.setPen(QPen(QColor("#000000")))
            painter.drawText(
                int(mid_x - text_width / 2),
                int(mid_y),
                texto
            )
        # Dibujar medida en progreso
        if self.punto_inicial is not None and self.punto_actual is not None:
            x1, y1 = self.punto_inicial
            x2, y2 = self.punto_actual
            color = QColor(self.color_actual)
            pen = QPen(color, 3 * zoom_factor, Qt.DashLine)
            painter.setPen(pen)
            sx1 = x1 * zoom_factor
            sy1 = y1 * zoom_factor
            sx2 = x2 * zoom_factor
            sy2 = y2 * zoom_factor
            painter.drawLine(int(sx1), int(sy1), int(sx2), int(sy2))
            # Calcular y mostrar distancia temporal
            dx = x2 - x1
            dy = y2 - y1
            distancia_pixeles = math.sqrt(dx * dx + dy * dy)
            distancia_metros = distancia_pixeles / self.escala_pixeles_por_metro
            mid_x = (sx1 + sx2) / 2
            mid_y = (sy1 + sy2) / 2 - 20 * zoom_factor  # 20px arriba
            font = QFont("Arial", int(12 * zoom_factor), QFont.Bold)
            painter.setFont(font)
            texto = f"{distancia_metros:.2f} m"
            metrics = painter.fontMetrics()
            text_rect = metrics.boundingRect(texto)
            text_width = text_rect.width()
            # Texto en negro, centrado
            painter.setPen(QPen(QColor("#000000")))
            painter.drawText(int(mid_x - text_width / 2), int(mid_y), texto)
    def borrar_cerca_de(self, x, y, tolerancia):
        """
        Borra medidas cercanas a una posición.
        Args:
            x: Coordenada X
            y: Coordenada Y
            tolerancia: Distancia máxima para considerar una medida cercana
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
        self.medidas = [
            ((x1, y1), (x2, y2), dist, color) for (x1, y1), (x2, y2), dist, color in self.medidas
            if distancia_punto_a_linea(x, y, x1, y1, x2, y2) > tolerancia
        ]
