class Borrar:
    """Clase para gestionar la funcionalidad de borrado."""

    def borrar_ultimo_punto(self, puntos):
        """
        Borra el último punto de la lista.

        Args:
            puntos: Lista de puntos
        """
        if puntos:
            puntos.pop()

    def borrar_ultima_linea(self, lineas):
        """
        Borra la última línea de la lista.

        Args:
            lineas: Lista de líneas
        """
        if lineas:
            lineas.pop()

    def borrar_ultima_cota(self, cotas):
        """
        Borra la última cota de la lista.

        Args:
            cotas: Lista de cotas
        """
        if cotas:
            cotas.pop()

    def borrar_ultimo_texto(self, textos):
        """
        Borra el último texto de la lista.

        Args:
            textos: Lista de textos
        """
        if textos:
            textos.pop()
