import streamlit as st
import barcode
from barcode.writer import ImageWriter
from io import BytesIO

st.set_page_config(page_title="Generador de Códigos", page_icon="🏷️")

st.title("🏷️ Generador de Códigos de Barras")
st.write("Ingresa un texto o número para generar tu código. El formato Code 128 soporta caracteres alfanuméricos.")

# Entrada principal
texto_codigo = st.text_input("Datos del código:", placeholder="Ej. 3000100090013")

# Opciones de formato para evitar errores de captura
st.markdown("### Opciones de Formato")
col1, col2 = st.columns(2)
with col1:
    quitar_ceros = st.checkbox("Eliminar ceros iniciales innecesarios", value=True)
with col2:
    validar_16 = st.checkbox("Validar longitud de 16 dígitos", value=False)

if st.button("Generar Código", type="primary"):
    if texto_codigo:
        texto_final = texto_codigo
        
        # Limpieza de ceros a la izquierda
        if quitar_ceros:
            texto_final = texto_final.lstrip('0')
            if not texto_final:  # Por si el usuario solo ingresó ceros
                texto_final = "0"
                
        # Validación de longitud (16 caracteres)
        if validar_16 and len(texto_final) != 16:
            st.warning(f"⚠️ Atención: El código tiene {len(texto_final)} caracteres en lugar de 16.")
            
        try:
            # Usar Code128 para soportar texto y números
            TIPO_CODIGO = barcode.get_barcode_class('code128')
            
            # Configurar el escritor de imagen para generar un PNG
            opciones_imagen = {
                'module_width': 0.3, # Ancho de las barras
                'module_height': 10.0, # Alto de las barras
                'font_size': 10,
                'text_distance': 4.0,
            }
            
            # Generar el código en memoria (BytesIO) para no tener que guardar el archivo localmente
            buffer = BytesIO()
            codigo_generado = TIPO_CODIGO(texto_final, writer=ImageWriter())
            codigo_generado.write(buffer, options=opciones_imagen)
            
            st.success("¡Código generado con éxito!")
            
            # Mostrar la imagen en Streamlit
            st.image(buffer, caption=f"Código: {texto_final}", use_container_width=False)
            
            # Botón para descargar la imagen
            st.download_button(
                label="⬇️ Descargar Código de Barras",
                data=buffer.getvalue(),
                file_name=f"codigo_{texto_final}.png",
                mime="image/png"
            )
            
        except Exception as e:
            st.error(f"Ocurrió un error al generar el código: {e}")
    else:
        st.error("Por favor, ingresa al menos un carácter para generar el código.")
        
