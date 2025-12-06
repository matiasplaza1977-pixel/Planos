import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
from streamlit_drawable_canvas import st_canvas
import io

st.set_page_config(layout="wide", page_title="Editor de PDF Streamlit")


def main():
    st.title("Editor de Planos PDF con Streamlit")
    # --- Sidebar: Configura herramientas ---
    st.sidebar.header("Herramientas")

    # Upload PDF
    uploaded_file = st.sidebar.file_uploader("Subir PDF", type=["pdf"])

    if "pdf_doc" not in st.session_state:
        st.session_state.pdf_doc = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = 0
    if uploaded_file is not None:
        # Load PDF only once to session state
        if st.session_state.pdf_doc is None:
            try:
                st.session_state.pdf_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            except Exception as e:
                st.error(f"Error al abrir el PDF: {e}")
                return
        doc = st.session_state.pdf_doc
        total_pages = len(doc)
        # Page Navigation
        st.sidebar.markdown("---")
        col_prev, col_page, col_next = st.sidebar.columns([1, 2, 1])

        if col_prev.button("◀"):
            if st.session_state.current_page > 0:
                st.session_state.current_page -= 1

        if col_next.button("▶"):
            if st.session_state.current_page < total_pages - 1:
                st.session_state.current_page += 1

        col_page.write(f"Pág {st.session_state.current_page + 1} de {total_pages}")
        # Render Current Page
        page = doc.load_page(st.session_state.current_page)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Zoom for better resolution
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))
        # Canvas Configuration
        st.sidebar.markdown("---")
        drawing_mode = st.sidebar.selectbox(
            "Herramienta",
            ("line", "rect", "circle", "transform", "freedraw", "text"),
            format_func=lambda x: {
                "line": "Línea", "rect": "Rectángulo", "circle": "Círculo",
                "transform": "Transformar/Mover", "freedraw": "Lápiz", "text": "Texto"
            }.get(x, x)
        )

        stroke_width = st.sidebar.slider("Grosor de línea", 1, 25, 3)
        stroke_color = st.sidebar.color_picker("Color de trazo", "#FF0000")

        fill_color = "#FFFFFF00"  # Transparent fill by default
        if drawing_mode in ["rect", "circle"]:
            if st.sidebar.checkbox("Relleno sólido?"):
                fill_color = stroke_color

        text_value = ""
        if drawing_mode == "text":
            text_value = st.sidebar.text_input("Texto a insertar", "Texto aquí")
        # Canvas
        canvas_result = st_canvas(
            fill_color=fill_color,
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            background_image=img,
            update_streamlit=True,
            height=img.height,
            width=img.width,
            drawing_mode=drawing_mode if drawing_mode != "text" else "text",
            initial_drawing=None,  # In a real app, you might want to save/load state per page
            key=f"canvas_page_{st.session_state.current_page}",
            display_toolbar=True,
            text_value=text_value if drawing_mode == "text" else "",
        )
        st.sidebar.markdown("---")
        if st.sidebar.button("💾 Guardar Cambios en PDF"):
            # This is where we would burn the canvas JSON into the PyMuPDF document
            # Note: This is complex because coordinate systems match (image vs pdf point).
            # The canvas returns pixels relative to the image size.
            # PyMuPDF uses points (1/72 inch).
            # Transformation is needed: PDF_W / Image_W = Scale

            # Simple proof of concept for downloading the current state
            pass  # Saving annotation logic requires parsing canvas_result.json_data
            # Let's try to implement basic saving for lines and rectangles
            if canvas_result.json_data is not None:
                scale_x = page.rect.width / img.width
                scale_y = page.rect.height / img.height

                objects = canvas_result.json_data["objects"]
                for obj in objects:
                    if obj["type"] == "line":
                        p1 = fitz.Point(obj["x1"] * scale_x, obj["y1"] * scale_y)
                        p2 = fitz.Point(obj["x2"] * scale_x, obj["y2"] * scale_y)
                        annot = page.add_line_annot(p1, p2)
                        annot.set_colors(stroke=hex_to_rgb(obj["stroke"]))
                        annot.set_border(width=obj["strokeWidth"] * scale_x)  # Approx
                        annot.update()
                    elif obj["type"] == "rect":
                        x = obj["left"] * scale_x
                        y = obj["top"] * scale_y
                        w = obj["width"] * scale_x
                        h = obj["height"] * scale_y
                        r = fitz.Rect(x, y, x + w, y + h)
                        annot = page.add_rect_annot(r)
                        annot.set_colors(stroke=hex_to_rgb(obj["stroke"]))
                        annot.set_border(width=obj["strokeWidth"] * scale_x)
                        annot.update()
                    # Add more types...
                # Save buffer
                out_buffer = io.BytesIO()
                doc.save(out_buffer)
                st.sidebar.download_button(
                    label="Descargar PDF Modificado",
                    data=out_buffer.getvalue(),
                    file_name="modificado.pdf",
                    mime="application/pdf"
                )
                st.success("Anotaciones procesadas (Líneas y Rectángulos). Descarga lista.")
    else:
        st.info("Por favor, sube un archivo PDF desde la barra lateral.")


def hex_to_rgb(hex_str):
    if not hex_str: return (0, 0, 0)
    hex_str = hex_str.lstrip('#')
    return (int(hex_str[:2], 16) / 255, int(hex_str[2:4], 16) / 255, int(hex_str[4:], 16) / 255)


if __name__ == "__main__":
    main()
