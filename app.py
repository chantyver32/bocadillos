import streamlit as st
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import docx
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="Generador de Etiquetas de Volovanes", layout="centered")

st.title("Generador de Fichas y Códigos de Barras 🥐🏷️")
st.markdown("Ingresa los datos del producto para generar su código de barras y el documento de Word correspondiente.")

# Formulario de entrada de datos
nombre_volovan = st.text_input("Nombre del Volován:", placeholder="Ej. Volován de Jamón y Queso")
datos_codigo = st.text_input("Texto o Número para el Código de Barras:", placeholder="Ej. VOL-JAM01")

tipo_codigo = st.selectbox(
    "Selecciona el formato del código:", 
    ["code128", "ean13", "upc"],
    help="Code128 es ideal porque acepta letras y números."
)

if st.button("Generar Documento y Código"):
    if nombre_volovan and datos_codigo:
        try:
            # 1. Generar el código de barras en memoria
            clase_codigo = barcode.get_barcode_class(tipo_codigo)
            codigo = clase_codigo(datos_codigo, writer=ImageWriter())
            
            buffer_imagen = BytesIO()
            codigo.write(buffer_imagen)
            buffer_imagen.seek(0) # Reiniciar el puntero del buffer de la imagen

            # Mostrar vista previa del código en la app
            st.image(buffer_imagen, caption=f"Vista previa del código para: {nombre_volovan}", use_container_width=False)

            # 2. Crear el documento de Word (.docx)
            doc = docx.Document()
            
            # Configurar un título en el Word
            titulo = doc.add_paragraph()
            titulo_run = titulo.add_run("FICHA OPERATIVA DE PRODUCTO")
            titulo_run.bold = True
            titulo_run.font.size = Pt(16)
            titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            doc.add_paragraph("-" * 50) # Línea divisoria simple

            # Agregar los datos del producto
            p_nombre = doc.add_paragraph()
            p_nombre.add_run("Producto: ").bold = True
            p_nombre.add_run(nombre_volovan).font.size = Pt(12)

            p_codigo = doc.add_paragraph()
            p_codigo.add_run("Código Identificador: ").bold = True
            p_codigo.add_run(datos_codigo).font.size = Pt(12)

            doc.add_paragraph("Código de Barras generado:").paragraph_format.space_after = Pt(12)

            # Insertar la imagen del código de barras directamente desde el buffer de memoria
            buffer_imagen.seek(0) # Asegurar que está al inicio
            doc.add_picture(buffer_imagen, width=Inches(3.5))
            
            # Guardar el documento de Word en un buffer de memoria para la descarga
            buffer_word = BytesIO()
            doc.save(buffer_word)
            buffer_word.seek(0)

            st.success("¡Todo se ha generado correctamente!")

            # Botón para descargar el archivo de Word
            st.download_button(
                label="📥 Descargar Documento de Word (.docx)",
                data=buffer_word.getvalue(),
                file_name=f"Ficha_{nombre_volovan.replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        except Exception as e:
            st.error(f"Ocurrió un error al procesar los datos. Verifica las restricciones del formato del código elegido.")
    else:
        st.warning("Por favor, rellena tanto el nombre del volován como los datos del código antes de continuar.")
