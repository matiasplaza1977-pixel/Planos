from PyQt5.QtGui import QPen, QBrush, QColor
from PyQt5.QtCore import Qt
import math


class Punto:
    """Clase para gestionar puntos de anotación."""

    def __init__(self):
        self.puntos = []  # Lista de tuplas (x, y, color_hex)

    def agregar(self, x, y, color_hex):
        """
        Agrega un nuevo punto.

        Args:
            x: Coordenada X
            y: Coordenada Y
            color_hex: Color en formato hexadecimal (#RRGGBB)
        """
        self.puntos.append((x, y, color_hex))

    def dibujar(self, painter, zoom_factor=1.0):
        """
        Dibuja todos los puntos en el painter.

        Args:
            painter: QPainter para dibujar
            zoom_factor: Factor de zoom actual
        """
        for x, y, color_hex in self.puntos:
            color = QColor(color_hex)
            painter.setPen(QPen(color, 2))
            painter.setBrush(QBrush(color))

            # Dibujar círculo centrado exactamente en (x, y)
            radius = 5 * zoom_factor
            # El centro del círculo debe estar en (x * zoom_factor, y * zoom_factor)
            # drawEllipse toma la esquina superior izquierda del rectángulo que contiene el círculo
            center_x = x * zoom_factor
            center_y = y * zoom_factor
            painter.drawEllipse(
                int(center_x - radius),
                int(center_y - radius),
                int(radius * 2),
                int(radius * 2)
            )

    def borrar_cerca_de(self, x, y, tolerancia):
        """
        Borra puntos cercanos a una posición.

        Args:
            x: Coordenada X
            y: Coordenada Y
            tolerancia: Distancia máxima para considerar un punto cercano
        """
        self.puntos = [
            (px, py, color) for px, py, color in self.puntos
            if math.sqrt((px - x) ** 2 + (py - y) ** 2) > tolerancia
        ]
