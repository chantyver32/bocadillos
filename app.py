import streamlit as st
import urllib.parse
import datetime
import io

# Intentar importar la librería para crear el Word
try:
    from docx import Document
except ImportError:
    pass # Manejado en la interfaz

# Configuración inicial de la página
st.set_page_config(page_title="Control de Bocadillos", layout="wide")

# Lista de productos solicitada
productos = [
    "Tuti", "Cubilete Queso", "Hojaldra Jamón", "Chorizo Hojaldrado",
    "Salchicha Hojaldrada", "V. Jamón Queso", "V. Pierna", 
    "V. Picadillo", "V. Cochinita"
]

# 1. Inicializar el inventario en el estado de la sesión (Ahora soporta MÚLTIPLES LOTES)
if 'inv' not in st.session_state:
    st.session_state.inv = {
        p: {
            "pz_caja": 12, # Piezas por caja configurables por producto
            "lotes": []    # Lista de lotes: [{"cajas": c, "sueltas": s, "caducidad": date}]
        } for p in productos
    }

# --- Funciones de Lógica ---

def obtener_total(p):
    """Calcula el total de piezas de un producto sumando todos sus lotes."""
    d = st.session_state.inv[p]
    return sum((lote["cajas"] * d["pz_caja"]) + lote["sueltas"] for lote in d["lotes"])

def hornear(p, cantidad):
    """Descuenta las piezas usando el sistema FIFO (Primeras Entradas, Primeras Salidas basado en caducidad)."""
    d = st.session_state.inv[p]
    total_actual = obtener_total(p)
    
    if cantidad > total_actual:
        st.toast(f"⚠️ No hay suficientes piezas de {p} para hornear.", icon="❌")
        return
    
    # Asegurarnos de que los lotes estén ordenados por caducidad (el más próximo a caducar primero)
    d["lotes"].sort(key=lambda x: x["caducidad"])
    
    restante = cantidad
    for lote in d["lotes"]:
        if restante <= 0:
            break
            
        piezas_lote = (lote["cajas"] * d["pz_caja"]) + lote["sueltas"]
        if piezas_lote == 0:
            continue
            
        if piezas_lote <= restante:
            # Nos acabamos todo este lote
            restante -= piezas_lote
            lote["cajas"] = 0
            lote["sueltas"] = 0
        else:
            # Solo tomamos una parte de este lote
            piezas_lote -= restante
            lote["cajas"] = piezas_lote // d["pz_caja"]
            lote["sueltas"] = piezas_lote % d["pz_caja"]
            restante = 0
            
    # Limpiar la lista: eliminar lotes que se quedaron en 0
    d["lotes"] = [lote for lote in d["lotes"] if (lote["cajas"] * d["pz_caja"]) + lote["sueltas"] > 0]
    
    st.toast(f"✅ Se descontaron {cantidad} piezas de {p} (Se consumió la caducidad más próxima).", icon="🥐")

def agregar_lote(p, c, s, cad, pz_caja):
    """Agrega un nuevo lote de mercancía y actualiza las piezas por caja si cambió."""
    if c == 0 and s == 0:
        st.toast("⚠️ Debes ingresar al menos 1 caja o 1 pieza suelta.", icon="⚠️")
        return
        
    d = st.session_state.inv[p]
    d["pz_caja"] = pz_caja # Actualizar piezas por caja globales para el producto
    
    # Buscar si ya existe un lote con la MISMA fecha de caducidad para agruparlo
    lote_existente = next((l for l in d["lotes"] if l["caducidad"] == cad), None)
    
    if lote_existente:
        total_nuevo = (lote_existente["cajas"] * d["pz_caja"]) + lote_existente["sueltas"] + (c * d["pz_caja"]) + s
        lote_existente["cajas"] = total_nuevo // d["pz_caja"]
        lote_existente["sueltas"] = total_nuevo % d["pz_caja"]
    else:
        # Es una caducidad nueva, crear lote nuevo
        d["lotes"].append({
            "cajas": c,
            "sueltas": s,
            "caducidad": cad
        })
        
    # Re-ordenar siempre por caducidad
    d["lotes"].sort(key=lambda x: x["caducidad"])
    st.toast(f"Lote de {p} registrado con éxito.", icon="💾")

def limpiar_stock(p):
    """Elimina todos los lotes de un producto (poner en cero)."""
    st.session_state.inv[p]["lotes"] = []
    st.toast(f"El inventario de {p} se ha puesto a 0.", icon="🗑️")

def generar_word():
    """Genera un archivo Word con el desglose de lotes y caducidades."""
    doc = Document()
    doc.add_heading('🍞 Reporte de Inventario de Bocadillos', 0)
    doc.add_paragraph(f"Fecha de actualización: {datetime.date.today().strftime('%d/%m/%Y')}")
    
    for p in productos:
        tot = obtener_total(p)
        doc.add_heading(p, level=2)
        p_info = doc.add_paragraph()
        p_info.add_run(f"Total disponible: {tot} pz\n").bold = True
        
        d = st.session_state.inv[p]
        if tot > 0:
            for i, lote in enumerate(d["lotes"]):
                pz_lote = (lote["cajas"] * d["pz_caja"]) + lote["sueltas"]
                p_info.add_run(f"   📦 Lote {i+1}: {pz_lote} pz (Cajas: {lote['cajas']} | Sueltas: {lote['sueltas']}) - Caducidad: {lote['caducidad'].strftime('%d/%m/%Y')}\n")
        else:
            p_info.add_run(f"   ⚠️ Sin stock actualmente.\n")
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- Interfaz de Usuario ---

st.title("🥐 Control de Inventario y Horneado (Múltiples Lotes)")

tab1, tab2, tab3 = st.tabs(["🔥 Área de Horneado", "📦 Ingreso de Lotes", "📱 Reportes (WA / Word)"])

# Pestaña 1: Horneado y vista rápida
with tab1:
    st.subheader("Estado Actual y Despacho")
    st.write("Selecciona cuántas piezas agarras de cada producto. El sistema descontará automáticamente de la fecha más próxima a caducar.")
    
    cols = st.columns(3)
    for idx, p in enumerate(productos):
        with cols[idx % 3]:
            tot = obtener_total(p)
            d = st.session_state.inv[p]
            
            with st.container(border=True):
                st.markdown(f"### {p}")
                st.write(f"**Total disponible:** {tot} pz")
                
                # Mostrar la caducidad más próxima (si hay stock)
                if tot > 0:
                    prox_cad = d["lotes"][0]["caducidad"].strftime('%d/%m/%Y')
                    st.write(f"📅 Próx. a caducar: **{prox_cad}**")
                else:
                    st.write("📅 Sin caducidad (Vacío)")
                
                c1, c2 = st.columns([1, 1])
                cant_hornear = c1.number_input("Cant.", min_value=1, step=1, key=f"h_{p}", label_visibility="collapsed")
                
                if c2.button("Hornear", key=f"btn_h_{p}", use_container_width=True, disabled=(tot==0)):
                    hornear(p, cant_hornear)
                    st.rerun()

# Pestaña 2: Registro de llegada de mercancía
with tab2:
    st.subheader("Registrar Entrada de Nuevos Lotes")
    st.info("Ingresa mercancía nueva asignándole su fecha de caducidad. Si agregas stock con una fecha que ya existe, se sumarán al lote existente.")
    
    for p in productos:
        tot = obtener_total(p)
        with st.expander(f"📦 {p} - Stock actual: {tot} pz"):
            d = st.session_state.inv[p]
            
            # Mostrar lotes actuales si hay
            if len(d["lotes"]) > 0:
                st.write("**Lotes activos actualmente:**")
                for i, lote in enumerate(d["lotes"]):
                    pz_lote = (lote["cajas"] * d["pz_caja"]) + lote["sueltas"]
                    st.caption(f"- Lote {i+1}: {pz_lote} pz (Caducidad: {lote['caducidad'].strftime('%d/%m/%Y')})")
                st.write("---")
            
            # Formulario para agregar nuevo lote
            st.write("**Agregar nuevo lote:**")
            c1, c2, c3, c4, c5 = st.columns(5)
            new_c = c1.number_input("Cajas", min_value=0, value=0, key=f"ec_{p}")
            new_s = c2.number_input("Sueltas", min_value=0, value=0, key=f"es_{p}")
            new_pz = c3.number_input("Pz / Caja", min_value=1, value=d["pz_caja"], key=f"epz_{p}")
            new_cad = c4.date_input("Caducidad Lote", value=datetime.date.today() + datetime.timedelta(days=7), key=f"ecad_{p}")
            
            c5.write("")
            c5.write("")
            if c5.button("➕ Agregar Lote", key=f"save_{p}", use_container_width=True):
                agregar_lote(p, new_c, new_s, new_cad, new_pz)
                st.rerun()
                
            # Botón de emergencia para limpiar el stock
            if st.button(f"🗑️ Poner {p} a 0", key=f"clear_{p}", type="secondary"):
                limpiar_stock(p)
                st.rerun()

# Pestaña 3: Exportar a WhatsApp y Word
with tab3:
    st.subheader("Compartir Reporte de Stock y Lotes")
    
    col_wa, col_word = st.columns(2)
    
    with col_wa:
        st.markdown("#### 📲 Enviar por WhatsApp")
        telefono = st.text_input("Número de WhatsApp destino (ej. 521234567890)")
        
        # Generar texto de reporte con desglose de lotes
        reporte = "🍞 *Reporte de Inventario de Bocadillos* 🍞\n\n"
        for p in productos:
            tot = obtener_total(p)
            reporte += f"*{p}*\n"
            reporte += f"▪️ Total: {tot} pz\n"
            
            d = st.session_state.inv[p]
            if tot > 0:
                for i, lote in enumerate(d["lotes"]):
                    pz_lote = (lote["cajas"] * d["pz_caja"]) + lote["sueltas"]
                    reporte += f"   📦 {pz_lote} pz (Cad: {lote['caducidad'].strftime('%d/%m/%Y')})\n"
            else:
                reporte += "   ⚠️ Agotado\n"
            reporte += "\n"
        
        st.text_area("Vista previa del mensaje:", value=reporte, height=350)
        
        if telefono.strip():
            mensaje_codificado = urllib.parse.quote(reporte)
            link_wa = f"https://wa.me/{telefono.strip()}?text={mensaje_codificado}"
            st.link_button("📲 Abrir WhatsApp y Enviar", link_wa, type="primary", use_container_width=True)
            
    with col_word:
        st.markdown("#### 📄 Descargar en Word")
        st.info("Genera un documento .docx con el inventario detallado por lotes de caducidad.")
        
        if 'Document' in globals() or 'Document' in locals():
            archivo_word = generar_word()
            st.download_button(
                label="📥 Descargar Reporte en Word",
                data=archivo_word,
                file_name=f"Reporte_Bocadillos_{datetime.date.today().strftime('%Y%m%d')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
                use_container_width=True
            )
        else:
            st.error("⚠️ No se puede generar el Word. Instala la librería con: pip install python-docx")
