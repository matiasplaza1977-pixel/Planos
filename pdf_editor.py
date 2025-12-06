import fitz  # PyMuPDF
import io


class PDFEditor:
    """Clase para manejar la carga, edición y guardado de archivos PDF."""

    def __init__(self, path):
        self.path = path
        self.doc = fitz.open(path)

    def get_page_image(self, page_index, zoom=1.0):
        """
        Obtiene la imagen de una página del PDF.

        Args:
            page_index: Índice de la página (0-indexed)
            zoom: Factor de zoom (default 1.0)

        Returns:
            bytes: Imagen en formato PNG
        """
        page = self.doc.load_page(page_index)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        return img_bytes

    def save_as(self, output_path):
        """
        Guarda el PDF en una nueva ubicación.

        Args:
            output_path: Ruta donde guardar el PDF
        """
        self.doc.save(output_path)

    def save_incremental(self):
        """
        Guarda cambios incrementales en el archivo original.
        """
        self.doc.saveIncr()

    def close(self):
        """Cierra el documento PDF."""
        if self.doc:
            self.doc.close()

    def __del__(self):
        """Destructor para asegurar que el documento se cierre."""
        self.close()
