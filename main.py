import sys
import os
import math
import fitz  # PyMuPDF
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QFileDialog,
    QToolBar, QAction, QMessageBox, QScrollArea, QColorDialog, QInputDialog,
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QWidget
)
from PyQt5.QtGui import QPixmap, QImage, QIcon, QColor, QPainter, QPen
from PyQt5.QtCore import Qt, pyqtSignal
from pdf_editor import PDFEditor
from punto import Punto
from linea import Linea
from cota import Cota
from texto import Texto
from borrar import Borrar
from medir import Medir


class LineaPreview(QWidget):
    """Widget para mostrar una línea con un grosor específico"""

    def __init__(self, grosor, color, parent=None):
        super().__init__(parent)
        self.grosor = grosor
        self.color = color
        self.setFixedSize(200, 80)
        self.setMouseTracking(True)
        self.hover = False
        self.selected = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Fondo con efecto hover/selección
        if self.selected:
            painter.fillRect(self.rect(), QColor(0, 212, 255, 80))
        elif self.hover:
            painter.fillRect(self.rect(), QColor(0, 212, 255, 40))

        # Dibujar línea de ejemplo
        pen = QPen(QColor(self.color))
        pen.setWidth(self.grosor)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        # Línea horizontal en el centro
        y = self.height() // 2
        painter.drawLine(20, y, self.width() - 20, y)

        # Texto con el grosor
        painter.setPen(QColor("#e8e8e8"))
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(10, 25, f"Grosor: {self.grosor}")

    def enterEvent(self, event):
        self.hover = True
        self.update()
        self.setCursor(Qt.PointingHandCursor)

    def leaveEvent(self, event):
        self.hover = False
        self.update()
        self.setCursor(Qt.ArrowCursor)

    def setSelected(self, selected):
        self.selected = selected
        self.update()


class GrosorDialog(QDialog):
    """Diálogo para seleccionar el grosor de línea con vista previa"""

    def __init__(self, color_actual, grosor_actual, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.color_actual = color_actual
        self.grosor_actual = grosor_actual
        self.grosor_seleccionado = grosor_actual
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Seleccionar grosor de línea")
        self.setMinimumWidth(300)
        self.setMinimumHeight(450)

        layout = QVBoxLayout()

        # Mensaje
        label = QLabel("Seleccione el grosor de la línea:")
        label.setStyleSheet("font-size: 14px; font-weight: bold; margin: 10px; color: white;")
        layout.addWidget(label)

        # Contenedor para las vistas previas
        preview_container = QWidget()
        preview_layout = QVBoxLayout()
        preview_container.setLayout(preview_layout)

        # Opciones de grosor
        grosores = [2, 5, 8, 12, 16]
        self.previews = []

        for grosor in grosores:
            preview = LineaPreview(grosor, self.color_actual)
            preview.setObjectName(f"preview_{grosor}")
            preview_layout.addWidget(preview)
            preview.mousePressEvent = lambda event, g=grosor: self.seleccionar_grosor(g)
            self.previews.append((preview, grosor))

            if grosor == self.grosor_actual:
                preview.setSelected(True)

        layout.addWidget(preview_container)

        # Botones
        button_layout = QHBoxLayout()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #16213e;
                color: #e8e8e8;
                border: 2px solid #00d4ff;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0f3460;
            }
        """)

        btn_aceptar = QPushButton("Aceptar")
        btn_aceptar.clicked.connect(self.accept)
        btn_aceptar.setStyleSheet("""
            QPushButton {
                background-color: #00d4ff;
                color: #0f3460;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00ffaa;
            }
        """)

        button_layout.addWidget(btn_cancelar)
        button_layout.addWidget(btn_aceptar)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def seleccionar_grosor(self, grosor):
        self.grosor_seleccionado = grosor
        for preview, g in self.previews:
            preview.setSelected(g == grosor)

    def get_grosor(self):
        return self.grosor_seleccionado


class ClickableLabel(QLabel):
    """Label personalizado que emite señales de mouse."""
    mouse_moved = pyqtSignal(object)
    mouse_pressed = pyqtSignal(object)
    mouse_released = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        self.mouse_moved.emit(event)

    def mousePressEvent(self, event):
        self.mouse_pressed.emit(event)

    def mouseReleaseEvent(self, event):
        self.mouse_released.emit(event)


class MainWindow(QMainWindow):
    """Ventana principal del editor de PDFs con diseño moderno."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editor de Planos PDF")
        self.setMinimumSize(1200, 800)

        # Variables de estado
        self.editor = None
        self.page_index = 0
        self.zoom_factor = 1.0
        self.herramienta_activa = None
        self.current_rotation = 0

        # Colores por defecto
        self.color_punto = "#ff0000"
        self.color_linea = "#0066ff"
        self.color_cota = "#00cc66"
        self.color_texto = "#333333"
        self.color_medir = "#ff9933"
        self.tamanio_texto = 12

        # Grosor de línea actual
        self.grosor_linea_actual = 5

        # Herramientas de dibujo
        self.punto_herramienta = Punto()
        self.linea_herramienta = Linea()
        self.cota_herramienta = Cota()
        self.texto_herramienta = Texto()
        self.medir_herramienta = Medir()
        self.borrar_herramienta = Borrar()
        self.borrando = False
        self.session_annotations = []

        # Caché para optimizar rendimiento
        self.cached_page_pixmap = None
        self.cached_page_index = -1
        self.cached_zoom = 1.0
        self.cached_rotation = 0
        self.annotations_changed = True

        # Aplicar estilos y configurar UI
        self.aplicar_estilos()
        self.configurar_ui()
        self.setWindowFlags(Qt.FramelessWindowHint)

    def aplicar_estilos(self):
        """Aplica estilos CSS modernos a la aplicación."""
        estilo = """
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
            }
            QMenuBar {
                background-color: #0f3460;
                color: #e8e8e8;
                border: none;
                padding: 5px;
                font-size: 13px;
                font-weight: 500;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #16537e;
            }
            QMenuBar::item:pressed {
                background-color: #00d4ff;
                color: #0f3460;
            }
            QMenu {
                background-color: #16213e;
                color: #e8e8e8;
                border: none;
                border-radius: 6px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 30px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0f3460;
                color: #00d4ff;
            }
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0f3460, stop:1 #16213e);
                border: none;
                border-bottom: 2px solid #00d4ff;
                spacing: 8px;
                padding: 8px;
            }
            QToolButton {
                background-color: rgba(0, 212, 255, 0.1);
                border: 2px solid transparent;
                border-radius: 8px;
                padding: 8px;
                margin: 2px;
                min-width: 40px;
                min-height: 40px;
            }
            QToolButton:hover {
                background-color: rgba(0, 212, 255, 0.2);
                border: 2px solid #00d4ff;
            }
            QToolButton:pressed {
                background-color: rgba(0, 212, 255, 0.3);
                border: 2px solid #00ffaa;
            }
            QToolButton:checked {
                background-color: #00d4ff;
                border: 2px solid #00ffaa;
            }
            QScrollArea {
                background-color: #1a1a2e;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #16213e;
                width: 14px;
                border-radius: 7px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #00d4ff;
                border-radius: 7px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #00ffaa;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #16213e;
                height: 14px;
                border-radius: 7px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: #00d4ff;
                border-radius: 7px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #00ffaa;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QStatusBar {
                background-color: #0f3460;
                color: #00d4ff;
                border-top: 2px solid #00d4ff;
                font-size: 12px;
                font-weight: 500;
                padding: 5px;
            }
            QMessageBox {
                background-color: #16213e;
                color: #e8e8e8;
            }
            QMessageBox QPushButton {
                background-color: #00d4ff;
                color: #0f3460;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #00ffaa;
            }
            QMessageBox QPushButton:pressed {
                background-color: #0099cc;
            }
            QInputDialog {
                background-color: #16213e;
                color: #e8e8e8;
            }
            QInputDialog QLineEdit, QInputDialog QSpinBox {
                background-color: #0f3460;
                color: #e8e8e8;
                border: 2px solid #00d4ff;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QInputDialog QLineEdit:focus, QInputDialog QSpinBox:focus {
                border: 2px solid #00ffaa;
            }
            QColorDialog {
                background-color: #16213e;
            }
            QDialog {
                background-color: #16213e;
                color: #e8e8e8;
            }
            QDialog QLabel {
                color: #ffffff;
            }
            QComboBox {
                background-color: #0f3460;
                color: #e8e8e8;
                border: none;
                border-radius: 6px;
                padding: 5px;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 12px;
                height: 12px;
                background-color: #00d4ff;
            }
            QComboBox QAbstractItemView {
                background-color: #16213e;
                color: #e8e8e8;
                border: none;
                selection-background-color: #0f3460;
                selection-color: #00d4ff;
            }
        """
        self.setStyleSheet(estilo)

    def configurar_ui(self):
        """Configura la interfaz de usuario."""
        self.label = ClickableLabel()
        self.label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label.setStyleSheet("background-color: #2a2a3e; border-radius: 8px;")
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.label)
        self.scroll_area.setWidgetResizable(False)
        self.setCentralWidget(self.scroll_area)
        self.label.mouse_pressed.connect(self.on_label_mouse_press)
        self.label.mouse_moved.connect(self.on_label_mouse_move)
        self.label.mouse_released.connect(self.on_label_mouse_release)
        self.crear_menu()
        self.crear_toolbar()
        self.statusBar().showMessage("Listo - Abra un archivo PDF para comenzar")

    def crear_menu(self):
        """Crea el menú de la aplicación."""
        menu_bar = self.menuBar()
        archivo_menu = menu_bar.addMenu("📁 Archivo")
        accion_nuevo = QAction("Abrir PDF", self)
        accion_guardar = QAction("Guardar PDF", self)
        accion_cerrar = QAction("Cerrar PDF", self)
        accion_acerca_de = QAction("Acerca de", self)
        accion_salir = QAction("Salir", self)
        archivo_menu.addAction(accion_nuevo)
        archivo_menu.addAction(accion_guardar)
        archivo_menu.addSeparator()
        archivo_menu.addAction(accion_cerrar)
        archivo_menu.addSeparator()
        archivo_menu.addAction(accion_acerca_de)
        archivo_menu.addSeparator()
        archivo_menu.addAction(accion_salir)
        accion_nuevo.triggered.connect(self.abrir_pdf)
        accion_guardar.triggered.connect(self.guardar_pdf)
        accion_cerrar.triggered.connect(self.cerrar_pdf)
        accion_acerca_de.triggered.connect(self.mostrar_acerca_de)
        accion_salir.triggered.connect(self.close)

    def crear_toolbar(self):
        """Crea la barra de herramientas."""
        toolbar = QToolBar("Herramientas de edición")
        toolbar.setMovable(False)
        toolbar.setIconSize(QtCore.QSize(32, 32))
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        def icon(name):
            icon_path = os.path.join("icons", f"{name}.png")
            if os.path.exists(icon_path):
                return QIcon(icon_path)
            return QIcon()

        self.action_punto = QAction(icon("punto"), "Punto", self)
        self.action_punto.setToolTip("Agregar puntos")
        self.action_punto.setCheckable(True)
        self.action_trazo = QAction(icon("trazo"), "Trazo", self)
        self.action_trazo.setToolTip("Dibujar líneas")
        self.action_trazo.setCheckable(True)
        self.action_cota = QAction(icon("cota"), "Cota", self)
        self.action_cota.setToolTip("Agregar cotas")
        self.action_cota.setCheckable(True)
        self.action_texto = QAction(icon("texto"), "Texto", self)
        self.action_texto.setToolTip("Agregar texto")
        self.action_texto.setCheckable(True)
        self.action_borrar = QAction(icon("borrar"), "Borrar", self)
        self.action_borrar.setToolTip("Borrar")
        self.action_borrar.setCheckable(True)
        self.action_girar = QAction(icon("girar"), "Girar", self)
        self.action_girar.setToolTip("Rotar página 90°")
        self.action_medir = QAction(icon("medir"), "Medir", self)
        self.action_medir.setToolTip("Herramienta de medición")
        self.action_medir.setCheckable(True)
        self.action_foto = QAction(icon("foto"), "Capturar", self)
        self.action_foto.setToolTip("Capturar imagen de la página")
        self.action_aumentar = QAction(icon("aumentar"), "Zoom +", self)
        self.action_aumentar.setToolTip("Aumentar zoom")
        self.action_disminuir = QAction(icon("disminuir"), "Zoom -", self)
        self.action_disminuir.setToolTip("Disminuir zoom")
        toolbar.addAction(self.action_punto)
        toolbar.addAction(self.action_trazo)
        toolbar.addAction(self.action_cota)
        toolbar.addAction(self.action_texto)
        toolbar.addSeparator()
        toolbar.addAction(self.action_borrar)
        toolbar.addSeparator()
        toolbar.addAction(self.action_medir)
        toolbar.addAction(self.action_girar)
        toolbar.addAction(self.action_foto)
        toolbar.addSeparator()
        toolbar.addAction(self.action_aumentar)
        toolbar.addAction(self.action_disminuir)
        self.action_punto.triggered.connect(lambda: self.activar_herramienta("punto"))
        self.action_trazo.triggered.connect(lambda: self.activar_herramienta("trazo"))
        self.action_cota.triggered.connect(lambda: self.activar_herramienta("cota"))
        self.action_texto.triggered.connect(lambda: self.activar_herramienta("texto"))
        self.action_borrar.triggered.connect(lambda: self.activar_herramienta("borrar"))
        self.action_girar.triggered.connect(self.girar_pagina)
        self.action_medir.triggered.connect(lambda: self.activar_herramienta("medir"))
        self.action_foto.triggered.connect(self.capturar_imagen)
        self.action_aumentar.triggered.connect(self.zoom_in)
        self.action_disminuir.triggered.connect(self.zoom_out)

    def desactivar_todas_herramientas(self):
        """Desactiva todas las herramientas checkables."""
        for action in [self.action_punto, self.action_trazo, self.action_cota,
                       self.action_texto, self.action_borrar, self.action_medir]:
            action.setChecked(False)

    def calcular_grosor_real(self, grosor):
        """Calcula el grosor real aplicando un multiplicador."""
        if grosor < 3:
            return grosor
        elif grosor < 6:
            return grosor * 1.5
        elif grosor < 10:
            return grosor * 2
        else:
            return grosor * 3

    def activar_herramienta(self, herramienta):
        """Activa una herramienta específica."""
        self.desactivar_todas_herramientas()
        self.herramienta_activa = herramienta
        acciones = {
            "punto": self.action_punto,
            "trazo": self.action_trazo,
            "cota": self.action_cota,
            "texto": self.action_texto,
            "borrar": self.action_borrar,
            "medir": self.action_medir
        }
        if herramienta in acciones:
            acciones[herramienta].setChecked(True)
        self.statusBar().showMessage(f"✨ Herramienta activa: {herramienta.capitalize()}")

        if herramienta == "punto":
            color_dialog = QColorDialog(self)
            color_dialog.setCurrentColor(QColor(self.color_punto))
            color_dialog.setWindowTitle("Seleccionar color del punto")
            color_dialog.setWindowFlags(Qt.FramelessWindowHint)
            if color_dialog.exec_() == QDialog.Accepted:
                self.color_punto = color_dialog.selectedColor().name()
        elif herramienta == "trazo":
            color_dialog = QColorDialog(self)
            color_dialog.setCurrentColor(QColor(self.color_linea))
            color_dialog.setWindowTitle("Seleccionar color de la línea")
            color_dialog.setWindowFlags(Qt.FramelessWindowHint)
            if color_dialog.exec_() == QDialog.Accepted:
                self.color_linea = color_dialog.selectedColor().name()

            dialog = GrosorDialog(self.color_linea, self.grosor_linea_actual, self)
            if dialog.exec_() == QDialog.Accepted:
                grosor = dialog.get_grosor()
                if grosor is not None:
                    self.grosor_linea_actual = grosor
                    grosor_real = self.calcular_grosor_real(grosor)
                    self.linea_herramienta.set_grosor(grosor_real)
            self.linea_herramienta.punto_inicial = None
        elif herramienta == "cota":
            color_dialog = QColorDialog(self)
            color_dialog.setCurrentColor(QColor(self.color_cota))
            color_dialog.setWindowTitle("Seleccionar color de la cota")
            color_dialog.setWindowFlags(Qt.FramelessWindowHint)
            if color_dialog.exec_() == QDialog.Accepted:
                self.color_cota = color_dialog.selectedColor().name()
            self.cota_herramienta.punto_inicial = None
        elif herramienta == "texto":
            color_dialog = QColorDialog(self)
            color_dialog.setCurrentColor(QColor(self.color_texto))
            color_dialog.setWindowTitle("Seleccionar color del texto")
            color_dialog.setWindowFlags(Qt.FramelessWindowHint)
            if color_dialog.exec_() == QDialog.Accepted:
                self.color_texto = color_dialog.selectedColor().name()

            input_dialog = QInputDialog(self)
            input_dialog.setWindowTitle("Tamaño de texto")
            input_dialog.setLabelText("Ingrese el tamaño de letra:")
            input_dialog.setIntValue(self.tamanio_texto)
            input_dialog.setIntRange(6, 72)
            input_dialog.setWindowFlags(Qt.FramelessWindowHint)
            if input_dialog.exec_() == QDialog.Accepted:
                self.tamanio_texto = input_dialog.intValue()
        elif herramienta == "borrar":
            self.borrando = True
        elif herramienta == "medir":
            self.medir_herramienta.punto_inicial = None

    def rgb_to_hex(self, rgb_tuple):
        """Convierte un color RGB (0-1) a formato hexadecimal."""
        if rgb_tuple is None or len(rgb_tuple) < 3:
            return "#000000"
        r = int(rgb_tuple[0] * 255)
        g = int(rgb_tuple[1] * 255)
        b = int(rgb_tuple[2] * 255)
        return f"#{r:02x}{g:02x}{b:02x}"

    def cargar_anotaciones(self):
        """Carga las anotaciones existentes del PDF."""
        if not self.editor:
            return
        try:
            page = self.editor.doc.load_page(self.page_index)
            self.current_rotation = page.rotation
            rotation = page.rotation
            rect = page.rect
            width = rect.width
            height = rect.height

            def transform_point_to_visual(px, py):
                if rotation == 0:
                    return px, py
                elif rotation == 90:
                    return width - py, px
                elif rotation == 180:
                    return width - px, height - py
                elif rotation == 270:
                    return py, height - px
                return px, py

            for annot in page.annots():
                annot_type = annot.type[0]
                info = annot.info
                subject = info.get("subject", "")
                colors = annot.colors
                stroke_color = colors.get("stroke", (0, 0, 0))
                color_hex = self.rgb_to_hex(stroke_color)

                if annot_type == fitz.PDF_ANNOT_SQUARE or subject == "punto":
                    r = annot.rect
                    cx = (r.x0 + r.x1) / 2
                    cy = (r.y0 + r.y1) / 2
                    vx, vy = transform_point_to_visual(cx, cy)
                    self.punto_herramienta.puntos.append((vx, vy, color_hex))
                elif annot_type == fitz.PDF_ANNOT_LINE:
                    vertices = annot.vertices
                    if vertices and len(vertices) >= 2:
                        p1 = vertices[0]
                        p2 = vertices[1]
                        x1, y1 = transform_point_to_visual(p1[0], p1[1])
                        x2, y2 = transform_point_to_visual(p2[0], p2[1])
                        if subject == "cota":
                            self.cota_herramienta.cotas.append(((x1, y1), (x2, y2), color_hex))
                        elif subject == "medir":
                            dist_px = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                            dist_m = dist_px / self.medir_herramienta.escala_pixeles_por_metro
                            self.medir_herramienta.medidas.append(((x1, y1), (x2, y2), dist_m, color_hex))
                        else:
                            border = annot.border
                            grosor = int(border.get("width", 5)) if border else 5
                            self.linea_herramienta.lineas.append(((x1, y1), (x2, y2), color_hex, grosor))

            self.annotations_changed = True
        except Exception as e:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"No se pudieron cargar las anotaciones:\n{e}")
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowFlags(Qt.FramelessWindowHint)
            msg_box.exec_()

    def abrir_pdf(self):
        """Abre un archivo PDF."""
        path, _ = QFileDialog.getOpenFileName(self, "Abrir PDF", "", "PDF Files (*.pdf)")
        if path:
            try:
                self.editor = PDFEditor(path)
                self.page_index = 0
                self.zoom_factor = 1.0
                self.current_rotation = 0
                self.punto_herramienta = Punto()
                self.linea_herramienta = Linea()
                self.cota_herramienta = Cota()
                self.texto_herramienta = Texto()
                self.medir_herramienta = Medir()
                self.session_annotations = []
                self.cargar_anotaciones()
                self.mostrar_pagina()
                self.centrar_documento()
                self.statusBar().showMessage(f"📄 Archivo abierto: {os.path.basename(path)} | Zoom: 100%")
            except Exception as e:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Error")
                msg_box.setText(f"No se pudo abrir el PDF:\n{e}")
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowFlags(Qt.FramelessWindowHint)
                msg_box.exec_()

    def centrar_documento(self):
        """Centra el documento en el scroll area."""
        if self.label.pixmap():
            scroll_width = self.scroll_area.viewport().width()
            scroll_height = self.scroll_area.viewport().height()
            label_width = self.label.width()
            label_height = self.label.height()
            x = max(0, (label_width - scroll_width) // 2)
            y = max(0, (label_height - scroll_height) // 2)
            self.scroll_area.horizontalScrollBar().setValue(x)
            self.scroll_area.verticalScrollBar().setValue(y)

    def mostrar_pagina(self):
        """Muestra la página actual del PDF con las anotaciones."""
        if not self.editor:
            return

        try:
            # Verificar si necesitamos recargar la página
            page_changed = (self.cached_page_index != self.page_index or
                            self.cached_zoom != self.zoom_factor or
                            self.cached_rotation != self.current_rotation)

            if page_changed or self.cached_page_pixmap is None:
                # Recargar la imagen del PDF
                img_bytes = self.editor.get_page_image(self.page_index)
                image = QImage.fromData(img_bytes)
                pixmap = QPixmap.fromImage(image)
                if self.zoom_factor != 1.0:
                    width = int(pixmap.width() * self.zoom_factor)
                    height = int(pixmap.height() * self.zoom_factor)
                    pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.cached_page_pixmap = pixmap
                self.cached_page_index = self.page_index
                self.cached_zoom = self.zoom_factor
                self.cached_rotation = self.current_rotation
                self.annotations_changed = True

            # Solo redibujar anotaciones si han cambiado
            if self.annotations_changed or self.herramienta_activa in ["trazo", "cota", "medir"]:
                canvas = self.cached_page_pixmap.copy()
                painter = QPainter(canvas)

                # Dibujar todas las anotaciones
                self.punto_herramienta.dibujar(painter, self.zoom_factor)
                self.linea_herramienta.dibujar(painter, self.zoom_factor)
                self.cota_herramienta.dibujar(painter, self.zoom_factor)
                self.texto_herramienta.dibujar(painter, self.zoom_factor)
                self.medir_herramienta.dibujar(painter, self.zoom_factor)

                painter.end()
                self.label.setPixmap(canvas)
                self.label.resize(canvas.size())

                # Si no estamos en medio de un dibujo, marcar anotaciones como no cambiadas
                if self.herramienta_activa not in ["trazo", "cota", "medir"]:
                    self.annotations_changed = False
        except Exception as e:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"No se pudo mostrar la página:\n{e}")
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowFlags(Qt.FramelessWindowHint)
            msg_box.exec_()

    def capturar_imagen(self):
        """Captura la página actual como imagen."""
        if self.label.pixmap() is None:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Sin imagen")
            msg_box.setText("No hay contenido para capturar.")
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowFlags(Qt.FramelessWindowHint)
            msg_box.exec_()
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Imagen", "",
                                              "PNG Files (*.png);;JPEG Files (*.jpg);;Todos los archivos (*)")
        if not path:
            return
        try:
            self.label.pixmap().save(path)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("✅ Imagen guardada")
            msg_box.setText(f"La imagen se guardó exitosamente en:\n{path}")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowFlags(Qt.FramelessWindowHint)
            msg_box.exec_()
            self.statusBar().showMessage(f"📸 Imagen guardada: {os.path.basename(path)}")
        except Exception as e:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"No se pudo guardar la imagen:\n{e}")
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowFlags(Qt.FramelessWindowHint)
            msg_box.exec_()

    def on_label_mouse_press(self, event):
        """Maneja el evento de clic del mouse."""
        if not self.editor:
            return
        pos = event.pos()
        x = pos.x() / self.zoom_factor
        y = pos.y() / self.zoom_factor

        if self.herramienta_activa == "punto":
            self.punto_herramienta.agregar(x, y, self.color_punto)
            self.annotations_changed = True
        elif self.herramienta_activa == "trazo":
            grosor_real = self.calcular_grosor_real(self.grosor_linea_actual)
            self.linea_herramienta.set_grosor(grosor_real)
            self.linea_herramienta.agregar(x, y, self.color_linea)
        elif self.herramienta_activa == "cota":
            self.cota_herramienta.agregar(x, y, self.color_cota)
        elif self.herramienta_activa == "texto":
            input_dialog = QInputDialog(self)
            input_dialog.setWindowTitle("Agregar Texto")
            input_dialog.setLabelText("Ingrese el texto:")
            input_dialog.setWindowFlags(Qt.FramelessWindowHint)
            if input_dialog.exec_() == QDialog.Accepted:
                texto = input_dialog.textValue()
                if texto:
                    self.texto_herramienta.agregar(x, y, texto, self.color_texto, self.tamanio_texto)
                    self.annotations_changed = True
        elif self.herramienta_activa == "medir":
            self.medir_herramienta.agregar(x, y, self.color_medir)
        elif self.herramienta_activa == "borrar":
            self.borrando = True
            self.borrar_en_posicion(x, y)
            self.annotations_changed = True

        self.mostrar_pagina()

    def on_label_mouse_move(self, event):
        """Maneja el movimiento del mouse."""
        if not self.editor:
            return
        pos = event.pos()
        x = pos.x() / self.zoom_factor
        y = pos.y() / self.zoom_factor
        self.statusBar().showMessage(
            f"✨ Herramienta: {self.herramienta_activa or 'Ninguna'} | "
            f"📍 Posición: ({int(x)}, {int(y)}) | "
            f"🔍 Zoom: {int(self.zoom_factor * 100)}%"
        )

        if self.herramienta_activa == "borrar" and self.borrando:
            self.borrar_en_posicion(x, y)
            self.annotations_changed = True
            self.mostrar_pagina()
            return

        if self.herramienta_activa == "trazo" and self.linea_herramienta.punto_inicial is not None:
            grosor_real = self.calcular_grosor_real(self.grosor_linea_actual)
            self.linea_herramienta.set_grosor(grosor_real)
            self.linea_herramienta.actualizar_punto_actual(x, y)
            self.mostrar_pagina()
        elif self.herramienta_activa == "cota" and self.cota_herramienta.punto_inicial is not None:
            self.cota_herramienta.actualizar_punto_actual(x, y)
            self.mostrar_pagina()
        elif self.herramienta_activa == "medir" and self.medir_herramienta.punto_inicial is not None:
            self.medir_herramienta.actualizar_punto_actual(x, y)
            self.mostrar_pagina()

    def on_label_mouse_release(self, event):
        """Maneja el evento de soltar el botón del mouse."""
        if self.herramienta_activa == "borrar":
            self.borrando = False
        elif self.herramienta_activa in ["trazo", "cota", "medir"]:
            self.annotations_changed = True
            self.mostrar_pagina()

    def borrar_en_posicion(self, x, y):
        """Borra anotaciones cercanas a una posición."""
        tolerancia = 10
        self.punto_herramienta.borrar_cerca_de(x, y, tolerancia)
        self.linea_herramienta.borrar_cerca_de(x, y, tolerancia)
        self.cota_herramienta.borrar_cerca_de(x, y, tolerancia)
        self.texto_herramienta.borrar_cerca_de(x, y, tolerancia)
        self.medir_herramienta.borrar_cerca_de(x, y, tolerancia)

    def hex_to_rgb(self, color_hex):
        """Convierte un color hexadecimal a RGB en formato 0-1 para PyMuPDF."""
        color_hex = color_hex.lstrip('#')
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
        return (r / 255.0, g / 255.0, b / 255.0)

    def aplicar_cambios(self):
        """Aplica las anotaciones al PDF."""
        if not self.editor:
            return
        try:
            page = self.editor.doc.load_page(self.page_index)
            rotation = page.rotation
            rect = page.rect
            width = rect.width
            height = rect.height

            def transform_point(x, y):
                if rotation == 0:
                    return fitz.Point(x, y)
                elif rotation == 90:
                    return fitz.Point(y, width - x)
                elif rotation == 180:
                    return fitz.Point(width - x, height - y)
                elif rotation == 270:
                    return fitz.Point(height - y, x)
                return fitz.Point(x, y)

            # Borrar todas las anotaciones previas
            annot = page.first_annot
            while annot:
                next_annot = annot.next
                page.delete_annot(annot)
                annot = next_annot

            # Puntos
            for x, y, color_hex in self.punto_herramienta.puntos:
                size = 5
                p = transform_point(x, y)
                r = fitz.Rect(p.x, p.y, p.x + size, p.y + size)
                annot = page.add_rect_annot(r)
                color_rgb = self.hex_to_rgb(color_hex)
                annot.set_colors(stroke=color_rgb, fill=color_rgb)
                annot.set_info(subject="punto")
                annot.update()

            # Líneas
            for item in self.linea_herramienta.lineas:
                if len(item) == 3:
                    (x1, y1), (x2, y2), color_hex = item
                    grosor = self.calcular_grosor_real(self.grosor_linea_actual)
                else:
                    (x1, y1), (x2, y2), color_hex, grosor = item

                p1 = transform_point(x1, y1)
                p2 = transform_point(x2, y2)
                annot = page.add_line_annot(p1, p2)
                color_rgb = self.hex_to_rgb(color_hex)
                annot.set_colors(stroke=color_rgb)
                annot.set_border(width=grosor)
                annot.set_info(subject="trazo")
                annot.update()

            # Cotas
            for (x1, y1), (x2, y2), color_hex in self.cota_herramienta.cotas:
                p1 = transform_point(x1, y1)
                p2 = transform_point(x2, y2)
                annot = page.add_line_annot(p1, p2)
                color_rgb = self.hex_to_rgb(color_hex)
                annot.set_colors(stroke=color_rgb)
                annot.set_border(width=2)
                annot.set_info(subject="cota")
                annot.update()

            # Textos
            for texto, x, y, color_hex, size in self.texto_herramienta.textos:
                point = transform_point(x, y)
                color_rgb = self.hex_to_rgb(color_hex)
                page.insert_text(
                    point,
                    texto,
                    fontsize=size,
                    fontname="helv",
                    color=color_rgb,
                    rotate=rotation
                )

            # Medidas
            for (x1, y1), (x2, y2), distancia_metros, color_hex in self.medir_herramienta.medidas:
                p1 = transform_point(x1, y1)
                p2 = transform_point(x2, y2)
                annot = page.add_line_annot(p1, p2)
                color_rgb = self.hex_to_rgb(color_hex)
                annot.set_colors(stroke=color_rgb)
                annot.set_border(width=3)
                annot.set_info(subject="medir")
                annot.update()
        except Exception as e:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error al guardar")
            msg_box.setText(f"No se pudo guardar anotaciones:\n{e}")
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowFlags(Qt.FramelessWindowHint)
            msg_box.exec_()

    def guardar_pdf(self):
        """Guarda el PDF con las anotaciones."""
        if self.editor:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", "", "PDF Files (*.pdf)")
            if path:
                try:
                    self.aplicar_cambios()
                    if path == self.editor.path:
                        self.editor.save_incremental()
                    else:
                        self.editor.save_as(path)
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("✅ Guardado")
                    msg_box.setText("PDF guardado correctamente.")
                    msg_box.setIcon(QMessageBox.Information)
                    msg_box.setWindowFlags(Qt.FramelessWindowHint)
                    msg_box.exec_()
                    self.statusBar().showMessage(f"💾 PDF guardado: {os.path.basename(path)}")
                except Exception as e:
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("Error")
                    msg_box.setText(f"No se pudo guardar el PDF:\n{e}")
                    msg_box.setIcon(QMessageBox.Critical)
                    msg_box.setWindowFlags(Qt.FramelessWindowHint)
                    msg_box.exec_()

    def cerrar_pdf(self):
        """Cierra el PDF actual."""
        if self.editor:
            self.editor = None
            self.label.setPixmap(QPixmap())
            self.statusBar().showMessage("📄 Documento cerrado")
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Cerrado")
            msg_box.setText("Se cerró el documento.")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowFlags(Qt.FramelessWindowHint)
            msg_box.exec_()

    def mostrar_acerca_de(self):
        """Muestra el diálogo Acerca de."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Acerca de")
        dialog.setWindowFlags(Qt.FramelessWindowHint)
        dialog.setMinimumSize(350, 200)
        dialog.setModal(True)

        layout = QVBoxLayout()

        label_desarrollador = QLabel("Desarrollado por Matias Plaza")
        label_desarrollador.setAlignment(Qt.AlignCenter)
        label_desarrollador.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px; color: #e8e8e8;")
        layout.addWidget(label_desarrollador)

        label_email = QLabel("Contacto: matias.plaza1977@gmail.com")
        label_email.setAlignment(Qt.AlignCenter)
        label_email.setStyleSheet("font-size: 14px; margin: 5px; color: #00d4ff;")
        layout.addWidget(label_email)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dialog.accept)
        btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: #00d4ff;
                color: #0f3460;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #00ffaa;
            }
        """)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(btn_cerrar)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        dialog.setLayout(layout)
        dialog.resize(300, 150)
        dialog.exec_()

    def zoom_in(self):
        """Aumenta el zoom."""
        if self.editor:
            self.zoom_factor *= 1.2
            self.mostrar_pagina()
            self.statusBar().showMessage(f"🔍 Zoom: {int(self.zoom_factor * 100)}%")

    def zoom_out(self):
        """Disminuye el zoom."""
        if self.editor:
            self.zoom_factor /= 1.2
            self.mostrar_pagina()
            self.statusBar().showMessage(f"🔍 Zoom: {int(self.zoom_factor * 100)}%")

    def girar_pagina(self):
        """Rota la página 90 grados y transforma las coordenadas de las anotaciones."""
        if self.editor:
            try:
                page = self.editor.doc.load_page(self.page_index)
                rect = page.rect
                width = rect.width
                height = rect.height
                page.set_rotation((page.rotation + 90) % 360)
                self.current_rotation = (self.current_rotation + 90) % 360

                def rotar_coordenadas(x, y, w, h):
                    return h - y, x

                # Rotar puntos
                puntos_rotados = []
                for x, y, color in self.punto_herramienta.puntos:
                    nuevo_x, nuevo_y = rotar_coordenadas(x, y, width, height)
                    puntos_rotados.append((nuevo_x, nuevo_y, color))
                self.punto_herramienta.puntos = puntos_rotados

                # Rotar líneas
                lineas_rotadas = []
                for item in self.linea_herramienta.lineas:
                    if len(item) == 3:
                        (x1, y1), (x2, y2), color = item
                        grosor = self.calcular_grosor_real(self.grosor_linea_actual)
                    else:
                        (x1, y1), (x2, y2), color, grosor = item

                    nuevo_x1, nuevo_y1 = rotar_coordenadas(x1, y1, width, height)
                    nuevo_x2, nuevo_y2 = rotar_coordenadas(x2, y2, width, height)
                    lineas_rotadas.append(((nuevo_x1, nuevo_y1), (nuevo_x2, nuevo_y2), color, grosor))
                self.linea_herramienta.lineas = lineas_rotadas

                # Rotar cotas
                cotas_rotadas = []
                for (x1, y1), (x2, y2), color in self.cota_herramienta.cotas:
                    nuevo_x1, nuevo_y1 = rotar_coordenadas(x1, y1, width, height)
                    nuevo_x2, nuevo_y2 = rotar_coordenadas(x2, y2, width, height)
                    cotas_rotadas.append(((nuevo_x1, nuevo_y1), (nuevo_x2, nuevo_y2), color))
                self.cota_herramienta.cotas = cotas_rotadas

                # Rotar textos
                textos_rotados = []
                for texto, x, y, color, size in self.texto_herramienta.textos:
                    nuevo_x, nuevo_y = rotar_coordenadas(x, y, width, height)
                    textos_rotados.append((texto, nuevo_x, nuevo_y, color, size))
                self.texto_herramienta.textos = textos_rotados

                # Rotar medidas
                medidas_rotadas = []
                for (x1, y1), (x2, y2), dist, color in self.medir_herramienta.medidas:
                    nuevo_x1, nuevo_y1 = rotar_coordenadas(x1, y1, width, height)
                    nuevo_x2, nuevo_y2 = rotar_coordenadas(x2, y2, width, height)
                    medidas_rotadas.append(((nuevo_x1, nuevo_y1), (nuevo_x2, nuevo_y2), dist, color))
                self.medir_herramienta.medidas = medidas_rotadas

                self.annotations_changed = True
                self.mostrar_pagina()
                self.statusBar().showMessage("🔄 Página rotada 90°")
            except Exception as e:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Error")
                msg_box.setText(f"No se pudo rotar la página:\n{e}")
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowFlags(Qt.FramelessWindowHint)
                msg_box.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QtGui.QFont("Segoe UI", 10)
    app.setFont(font)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec_())