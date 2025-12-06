from PIL import Image, ImageDraw, ImageFont
import os


def create_simple_icon(filename, text, color, bg_color=(0, 0, 0, 0)):
    """Crea un icono simple con texto."""
    size = 64
    img = Image.new('RGBA', (size, size), bg_color)
    draw = ImageDraw.Draw(img)

    # Intentar usar una fuente del sistema
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    # Calcular posición del texto (centrado)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 5

    # Dibujar texto
    draw.text((x, y), text, fill=color, font=font)

    # Guardar
    img.save(filename)


# Crear iconos faltantes
os.makedirs('icons', exist_ok=True)
create_simple_icon('icons/foto.png', '📷', (0, 204, 255, 255))
create_simple_icon('icons/aumentar.png', '+', (0, 204, 102, 255))
create_simple_icon('icons/disminuir.png', '-', (255, 102, 102, 255))
print("Iconos creados exitosamente")
