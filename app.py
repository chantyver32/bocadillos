import streamlit as st
import urllib.parse
import datetime

# Configuración inicial de la página
st.set_page_config(page_title="Control de Bocadillos", layout="wide")

# Lista de productos solicitada
productos = [
    "Tuti", "Cubilete Queso", "Hojaldra Jamón", "Chorizo Hojaldrado",
    "Salchicha Hojaldrada", "V. Jamón Queso", "V. Pierna", 
    "V. Picadillo", "V. Cochinita"
]

# 1. Inicializar el inventario en el estado de la sesión
if 'inv' not in st.session_state:
    st.session_state.inv = {
        p: {
            "cajas": 0, 
            "sueltas": 0, 
            "pz_caja": 12, # Por defecto asumo 12, pero se puede editar
            "caducidad": datetime.date.today()
        } for p in productos
    }

# --- Funciones de Lógica ---

def hornear(p, cantidad):
    """Descuenta las piezas seleccionadas para hornear del total."""
    d = st.session_state.inv[p]
    total_actual = (d["cajas"] * d["pz_caja"]) + d["sueltas"]
    
    if cantidad > total_actual:
        st.toast(f"⚠️ No hay suficientes piezas de {p} para hornear.", icon="❌")
        return
    
    # Restar y recalcular cajas y sueltas
    nuevo_total = total_actual - cantidad
    st.session_state.inv[p]["cajas"] = nuevo_total // d["pz_caja"]
    st.session_state.inv[p]["sueltas"] = nuevo_total % d["pz_caja"]
    st.toast(f"✅ Se descontaron {cantidad} piezas de {p}.", icon="🥐")

def guardar_edicion(p, c, s, pz, cad):
    """Guarda los ajustes manuales de inventario que ingresa el usuario."""
    st.session_state.inv[p]["cajas"] = c
    st.session_state.inv[p]["sueltas"] = s
    st.session_state.inv[p]["pz_caja"] = pz
    st.session_state.inv[p]["caducidad"] = cad
    st.toast(f"Inventario de {p} actualizado.", icon="💾")

# --- Interfaz de Usuario ---

st.title("🥐 Control de Inventario y Horneado")

# Dividimos la app en tres pestañas para mantenerla limpia
tab1, tab2, tab3 = st.tabs(["🔥 Área de Horneado (Dashboard)", "📦 Ingreso de Inventario", "📱 Reporte WhatsApp"])

# Pestaña 1: Horneado y vista rápida
with tab1:
    st.subheader("Estado Actual y Despacho")
    st.write("Selecciona cuántas piezas agarras de cada producto para hornear.")
    
    cols = st.columns(3) # Cuadrícula de 3 columnas
    for idx, p in enumerate(productos):
        with cols[idx % 3]:
            d = st.session_state.inv[p]
            tot = (d["cajas"] * d["pz_caja"]) + d["sueltas"]
            
            with st.container(border=True):
                st.markdown(f"### {p}")
                st.write(f"**Total disponible:** {tot} pz")
                st.write(f"📦 Cajas: {d['cajas']} | 🥐 Sueltas: {d['sueltas']}")
                st.write(f"📅 Caducidad: {d['caducidad'].strftime('%d/%m/%Y')}")
                
                # Botón y selección para hornear
                c1, c2 = st.columns([1, 1])
                cant_hornear = c1.number_input("Cant.", min_value=1, step=1, key=f"h_{p}", label_visibility="collapsed")
                
                if c2.button("Hornear", key=f"btn_h_{p}", use_container_width=True):
                    hornear(p, cant_hornear)
                    st.rerun()

# Pestaña 2: Registro de llegada de mercancía
with tab2:
    st.subheader("Ajuste Manual de Inventario")
    st.info("Utiliza esta sección cuando llegue nueva mercancía para registrar tus cajas, piezas y vigencia.")
    
    for p in productos:
        with st.expander(f"Actualizar {p}"):
            d = st.session_state.inv[p]
            c1, c2, c3, c4, c5 = st.columns(5)
            new_c = c1.number_input("Cajas", min_value=0, value=d["cajas"], key=f"ec_{p}")
            new_s = c2.number_input("Sueltas", min_value=0, value=d["sueltas"], key=f"es_{p}")
            new_pz = c3.number_input("Pz / Caja", min_value=1, value=d["pz_caja"], key=f"epz_{p}")
            new_cad = c4.date_input("Caducidad", value=d["caducidad"], key=f"ecad_{p}")
            
            # Un pequeño espacio para alinear el botón
            c5.write("")
            c5.write("")
            if c5.button("Guardar", key=f"save_{p}", use_container_width=True):
                guardar_edicion(p, new_c, new_s, new_pz, new_cad)
                st.rerun()

# Pestaña 3: Exportar a WhatsApp
with tab3:
    st.subheader("Compartir Reporte de Stock")
    
    telefono = st.text_input("Número de WhatsApp destino (incluye código de país, ej. 52 para México: 521234567890)")
    
    # Generar el texto del reporte automáticamente
    reporte = "🍞 *Reporte de Inventario de Bocadillos* 🍞\n\n"
    for p in productos:
        d = st.session_state.inv[p]
        tot = (d["cajas"] * d["pz_caja"]) + d["sueltas"]
        reporte += f"*{p}*\n"
        reporte += f"▪️ Total: {tot} pz (Cajas: {d['cajas']}, Sueltas: {d['sueltas']})\n"
        reporte += f"▪️ Caducidad: {d['caducidad'].strftime('%d/%m/%Y')}\n\n"
    
    st.text_area("Vista previa del mensaje:", value=reporte, height=350)
    
    if telefono.strip():
        # Codificar el texto para que los espacios y saltos de línea se envíen bien en la URL
        mensaje_codificado = urllib.parse.quote(reporte)
        link_wa = f"https://wa.me/{telefono.strip()}?text={mensaje_codificado}"
        
        # Usamos link_button (disponible en versiones recientes de Streamlit)
        st.link_button("📲 Abrir WhatsApp y Enviar", link_wa, type="primary")
    else:
        st.warning("⚠️ Ingresa un número de teléfono válido arriba para habilitar el botón de envío.")
