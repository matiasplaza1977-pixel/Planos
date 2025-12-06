from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import pyqtSignal

class ClickableLabel(QLabel):
    mouse_moved = pyqtSignal(object)  # emitirá el evento mouseMoveEvent
    mouse_pressed = pyqtSignal(object)  # emitirá el evento mousePressEvent

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)  # para recibir mouseMoveEvent sin click

    def mouseMoveEvent(self, event):
        self.mouse_moved.emit(event)

    def mousePressEvent(self, event):
        self.mouse_pressed.emit(event)
