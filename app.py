import streamlit as st
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import docx
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="Generador Múltiple de Volovanes", layout="wide")

st.title("Generador Múltiple de Códigos 🥐🏷️")
st.markdown("Ingresa hasta 4 volovanes a la vez. Se generará una sola hoja de Word (lista para imprimir) con los 4 códigos ordenados.")

# Crear las entradas para 4 volovanes usando columnas
volovanes = []
for i in range(4):
    st.markdown(f"### Volován {i + 1}")
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input(f"Nombre del Volován {i+1}:", key=f"nom_{i}", placeholder="Ej. Volován de Jaiba")
    with col2:
        codigo = st.text_input(f"Código / Texto esperado {i+1}:", key=f"cod_{i}", placeholder="Ej. VOL-JAI01")
    
    volovanes.append({"nombre": nombre, "codigo": codigo})

# Separador visual
st.divider()

if st.button("Generar Word con los 4 Códigos", type="primary"):
    # Verificar que al menos uno tenga datos
    datos_ingresados = [v for v in volovanes if v["nombre"] and v["codigo"]]
    
    if datos_ingresados:
        try:
            # 1. Crear el documento de Word
            doc = docx.Document()
            
            # Reducir los márgenes de la hoja para asegurar que quepan los 4
            for section in doc.sections:
                section.top_margin = Inches(0.5)
                section.bottom_margin = Inches(0.5)
                section.left_margin = Inches(0.5)
                section.right_margin = Inches(0.5)

            # Insertar título general (opcional)
            titulo = doc.add_paragraph("ETIQUETAS DE PRODUCTO")
            titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            titulo.runs[0].bold = True

            # 2. Crear una tabla 2x2 para acomodar los 4 códigos en una página
            tabla = doc.add_table(rows=2, cols=2)
            # Para evitar que la tabla se deforme
            tabla.autofit = False 

            clase_codigo = barcode.get_barcode_class("code128")

            # 3. Procesar cada volován y colocarlo en su celda respectiva
            # AQUÍ ESTÁ LA CORRECCIÓN: "in" en lugar de "en"
            for idx, vol in enumerate(datos_ingresados):
                # Calcular en qué fila y columna va (0,0), (0,1), (1,0), (1,1)
                fila = idx // 2
                columna = idx % 2
                celda = tabla.cell(fila, columna)

                # Generar el código de barras (sin el texto por defecto para ponerlo nosotros)
                codigo_obj = clase_codigo(vol["codigo"], writer=ImageWriter())
                buffer_imagen = BytesIO()
                # Opciones: quitamos el texto automático de la imagen para que quede más limpio
                opciones_imagen = {"write_text": False, "module_height": 10.0, "quiet_zone": 1.0}
                codigo_obj.write(buffer_imagen, options=opciones_imagen)
                buffer_imagen.seek(0)

                # -- AGREGAR DATOS A LA CELDA DE WORD --
                
                # A. Nombre del Volován (Arriba)
                p_nombre = celda.paragraphs[0]
                p_nombre.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run_nombre = p_nombre.add_run(vol["nombre"])
                run_nombre.bold = True
                run_nombre.font.size = Pt(14)
                
                # B. Imagen del Código (En medio)
                p_imagen = celda.add_paragraph()
                p_imagen.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run_imagen = p_imagen.add_run()
                # Ajustamos el ancho a 3 pulgadas para que quepan dos columnas perfecto
                run_imagen.add_picture(buffer_imagen, width=Inches(3.0))
                
                # C. Texto esperado / Código (Abajo)
                p_texto = celda.add_paragraph()
                p_texto.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run_texto = p_texto.add_run(vol["codigo"])
                run_texto.font.size = Pt(12)
                
                # Dar un poco de espacio al final de la celda
                p_espacio = celda.add_paragraph()
                p_espacio.paragraph_format.space_after = Pt(20)

            # 4. Guardar Word en memoria
            buffer_word = BytesIO()
            doc.save(buffer_word)
            buffer_word.seek(0)

            st.success("¡Documento generado con éxito!")

            # Botón de descarga
            st.download_button(
                label="📥 Descargar Hoja de Impresión (.docx)",
                data=buffer_word.getvalue(),
                file_name="Etiquetas_4_Volovanes.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        except Exception as e:
            st.error(f"Ocurrió un error al generar el documento: {e}")
    else:
        st.warning("Por favor, llena el nombre y el código de al menos un volován.")
