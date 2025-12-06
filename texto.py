from PyQt5.QtGui import QPen, QColor, QFont
from PyQt5.QtCore import Qt
import math


class Texto:
    """Clase para gestionar anotaciones de texto."""

    def __init__(self):
        self.textos = []  # Lista de tuplas (texto, x, y, color_hex, size)

    def agregar(self, x, y, texto, color_hex, size):
        """
        Agrega una nueva anotación de texto.

        Args:
            x: Coordenada X
            y: Coordenada Y
            texto: Texto a mostrar
            color_hex: Color en formato hexadecimal
            size: Tamaño de la fuente
        """
        self.textos.append((texto, x, y, color_hex, size))

    def dibujar(self, painter, zoom_factor=1.0):
        """
        Dibuja todos los textos en el painter.

        Args:
            painter: QPainter para dibujar
            zoom_factor: Factor de zoom actual
        """
        for texto, x, y, color_hex, size in self.textos:
            color = QColor(color_hex)
            painter.setPen(QPen(color))

            # Configurar fuente con tamaño escalado
            font = QFont("Arial", int(size * zoom_factor))
            painter.setFont(font)

            # Dibujar texto
            painter.drawText(
                int(x * zoom_factor),
                int(y * zoom_factor),
                texto
            )

    def borrar_cerca_de(self, x, y, tolerancia):
        """
        Borra textos cercanos a una posición.

        Args:
            x: Coordenada X
            y: Coordenada Y
            tolerancia: Distancia máxima para considerar un texto cercano
        """
        self.textos = [
            (texto, tx, ty, color, size) for texto, tx, ty, color, size in self.textos
            if math.sqrt((tx - x) ** 2 + (ty - y) ** 2) > tolerancia
        ]
