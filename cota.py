from PyQt5.QtGui import QPen, QColor, QPainterPath
from PyQt5.QtCore import Qt, QPointF
import math


class Cota:
    """Clase para gestionar cotas (líneas con flechas en ambos extremos)."""

    def __init__(self):
        self.cotas = []  # Lista de tuplas ((x1, y1), (x2, y2), color_hex)
        self.punto_inicial = None
        self.punto_actual = None
        self.color_actual = "#00aa00"

    def agregar(self, x, y, color_hex):
        """
        Agrega un punto de la cota (inicio o fin).

        Args:
            x: Coordenada X
            y: Coordenada Y
            color_hex: Color en formato hexadecimal
        """
        if self.punto_inicial is None:
            self.punto_inicial = (x, y)
            self.color_actual = color_hex
        else:
            self.cotas.append((self.punto_inicial, (x, y), self.color_actual))
            self.punto_inicial = None
            self.punto_actual = None

    def actualizar_punto_actual(self, x, y):
        """
        Actualiza el punto actual mientras se dibuja la cota.

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
        Dibuja todas las cotas en el painter.

        Args:
            painter: QPainter para dibujar
            zoom_factor: Factor de zoom actual
        """
        # Dibujar cotas completadas
        for (x1, y1), (x2, y2), color_hex in self.cotas:
            color = QColor(color_hex)
            pen = QPen(color, 2 * zoom_factor, Qt.SolidLine)
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

        # Dibujar cota en progreso
        if self.punto_inicial is not None and self.punto_actual is not None:
            x1, y1 = self.punto_inicial
            x2, y2 = self.punto_actual
            color = QColor(self.color_actual)
            pen = QPen(color, 2 * zoom_factor, Qt.DashLine)
            painter.setPen(pen)

            sx1 = x1 * zoom_factor
            sy1 = y1 * zoom_factor
            sx2 = x2 * zoom_factor
            sy2 = y2 * zoom_factor

            painter.drawLine(int(sx1), int(sy1), int(sx2), int(sy2))

    def borrar_cerca_de(self, x, y, tolerancia):
        """
        Borra cotas cercanas a una posición.

        Args:
            x: Coordenada X
            y: Coordenada Y
            tolerancia: Distancia máxima para considerar una cota cercana
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

        self.cotas = [
            ((x1, y1), (x2, y2), color) for (x1, y1), (x2, y2), color in self.cotas
            if distancia_punto_a_linea(x, y, x1, y1, x2, y2) > tolerancia
        ]
