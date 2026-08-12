import sqlite3
import urllib.parse
from datetime import datetime, date
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# CONFIGURACIÓN Y BASE DE DATOS
# ==========================================
DB_NAME = "inventario_bocadillos.db"

# Estructura de empaques por producto
EMPAQUES = {
    # Dulce
    "Cubiletes": {"categoria": "Dulce", "piezas_x_paq": 16},
    "Tutis": {"categoria": "Dulce", "piezas_x_paq": 27},
    # Salado
    "Volován de Jamón": {"categoria": "Salado", "piezas_x_paq": 9},
    "Volován de Cochinita": {"categoria": "Salado", "piezas_x_paq": 9},
    "Volován de Picadillo": {"categoria": "Salado", "piezas_x_paq": 9},
    "Volován de Pierna": {"categoria": "Salado", "piezas_x_paq": 9},
    "Chorizo Hojaldrado": {"categoria": "Salado", "piezas_x_paq": 20},
    "Salchicha Hojaldrada": {"categoria": "Salado", "piezas_x_paq": 20},
    # Dulce - Salado
    "Hojaldra Jamón": {"categoria": "Dulce - Salado", "piezas_x_paq": 48},
}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tabla entradas mercancía bocadillos
    c.execute('''CREATE TABLE IF NOT EXISTS entradas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT,
                    paquetes INTEGER,
                    piezas_totales INTEGER,
                    fecha_caducidad TEXT,
                    fecha_registro TEXT
                )''')
    # Tabla horneado
    c.execute('''CREATE TABLE IF NOT EXISTS horneado (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT,
                    paquetes INTEGER,
                    piezas_totales INTEGER,
                    fecha_hora TEXT
                )''')
    # Tabla Coca-Cola
    c.execute('''CREATE TABLE IF NOT EXISTS cocacola (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT,
                    cantidad INTEGER,
                    fecha_caducidad TEXT,
                    fecha_registro TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================
def calcular_stock_actual():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    stock = {}
    for prod in EMPAQUES.keys():
        c.execute("SELECT SUM(paquetes) FROM entradas WHERE producto = ?", (prod,))
        entradas = c.fetchone()[0] or 0
        c.execute("SELECT SUM(paquetes) FROM horneado WHERE producto = ?", (prod,))
        salidas = c.fetchone()[0] or 0
        paq_disp = entradas - salidas
        stock[prod] = {
            "paquetes": paq_disp,
            "piezas": paq_disp * EMPAQUES[prod]["piezas_x_paq"]
        }
    conn.close()
    return stock

def generar_imagen_stock(titulo, lineas_texto):
    # Crear una imagen tipo reporte
    img = Image.new('RGB', (600, 40 + len(lineas_texto) * 35 + 40), color=(245, 247, 250))
    draw = ImageDraw.Draw(img)
    
    # Encabezado
    draw.rectangle([0, 0, 600, 50], fill=(31, 78, 121))
    draw.text((20, 15), titulo, fill=(255, 255, 255))
    
    y = 70
    for linea in lineas_texto:
        draw.text((20, y), linea, fill=(30, 30, 30))
        y += 32
        
    img.save("reporte.png")
    return "reporte.png"

# ==========================================
# INTERFAZ STREAMLIT
# ==========================================
st.set_page_config(page_title="Control de Stock - Bocadillos", layout="centered")
st.title("📦 Control de Stock y Horneado")

tab1, tab2, tab3 = st.tabs([
    "📥 Entradas y Caducidades", 
    "🥐 Registro de Horneado", 
    "🥤 Caducidades Coca-Cola"
])

# ------------------------------------------
# PESTAÑA 1: RECEPCIÓN DE MERCANCÍA
# ------------------------------------------
with tab1:
    st.header("Registrar Nueva Mercancía")
    
    with st.form("form_entrada", clear_on_submit=True):
        prod_sel = st.selectbox("Selecciona Producto", list(EMPAQUES.keys()), index=None, placeholder="Elija un producto...")
        cant_paq = st.number_input("Cantidad de Paquetes recibidos", min_value=1, step=1, value=None, placeholder="0")
        fecha_cad = st.date_input("Fecha de Caducidad", value=None)
        
        btn_guardar = st.form_submit_button("Registrar Entrada")
        
        if btn_guardar:
            if prod_sel and cant_paq and fecha_cad:
                pz_totales = cant_paq * EMPAQUES[prod_sel]["piezas_x_paq"]
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("INSERT INTO entradas (producto, paquetes, piezas_totales, fecha_caducidad, fecha_registro) VALUES (?, ?, ?, ?, ?)",
                          (prod_sel, cant_paq, pz_totales, str(fecha_cad), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                st.success(f"✅ Se registraron {cant_paq} paquete(s) de {prod_sel} ({pz_totales} pzs).")
            else:
                st.error("Por favor completa todos los campos del formulario.")

    st.markdown("---")
    with st.expander("📜 Ver historial de entradas y caducidades anteriores"):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT producto, paquetes, piezas_totales, fecha_caducidad, fecha_registro FROM entradas ORDER BY id DESC")
        registros = c.fetchall()
        conn.close()
        
        if registros:
            st.dataframe(registros, column_config={
                "0": "Producto", "1": "Paquetes", "2": "Piezas Totales", 
                "3": "Caducidad", "4": "Fecha de Registro"
            }, use_container_width=True)
        else:
            st.info("No hay entradas registradas aún.")

# ------------------------------------------
# PESTAÑA 2: REGISTRO DE HORNEADO
# ------------------------------------------
with tab2:
    st.header("Horneado de Mercancía")
    
    with st.form("form_horneado", clear_on_submit=True):
        prod_hornear = st.selectbox("Producto a Hornear", list(EMPAQUES.keys()), index=None, placeholder="Elija un producto...", key="hornear_prod")
        cant_hornear = st.number_input("Paquetes a Hornear", min_value=1, step=1, value=None, placeholder="0", key="hornear_cant")
        
        btn_horneo = st.form_submit_button("Registrar Horneado")
        
        if btn_horneo:
            if prod_hornear and cant_hornear:
                stock_actual = calcular_stock_actual()
                disp = stock_actual[prod_hornear]["paquetes"]
                
                if cant_hornear > disp:
                    st.warning(f"⚠️ Stock insuficiente. Solo hay {disp} paquetes disponibles en nevera.")
                else:
                    pz_totales = cant_hornear * EMPAQUES[prod_hornear]["piezas_x_paq"]
                    hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("INSERT INTO horneado (producto, paquetes, piezas_totales, fecha_hora) VALUES (?, ?, ?, ?)",
                              (prod_hornear, cant_hornear, pz_totales, hora_actual))
                    conn.commit()
                    conn.close()
                    st.success(f"🔥 Registrado horneado de {cant_hornear} paq. de {prod_hornear} a las {hora_actual}.")
            else:
                st.error("Por favor completa los campos para registrar el horneado.")

    st.markdown("---")
    st.subheader("🖼️ Stock Disponible en Nevera")
    
    stock_actual = calcular_stock_actual()
    lineas_reporte = []
    
    for prod, datos in stock_actual.items():
        lineas_reporte.append(f"• {prod}: {datos['paquetes']} paq ({datos['piezas']} pzs)")
        
    path_img = generar_imagen_stock(f"STOCK EN NEVERA - {datetime.now().strftime('%d/%m/%Y %H:%M')}", lineas_reporte)
    
    st.image(path_img, caption="Reporte actual generado automáticamente")
    
    # Preparar mensaje para WhatsApp
    texto_whatsapp = f"Stock en Nevera ({datetime.now().strftime('%d/%m/%Y %H:%M')}):\n" + "\n".join(lineas_reporte)
    url_wa = f"https://wa.me/52291653665?text={urllib.parse.quote(texto_whatsapp)}"
    
    st.markdown(f"[📲 **Enviar reporte por WhatsApp al 2291653665**]({url_wa})", unsafe_allow_html=True)

# ------------------------------------------
# PESTAÑA 3: COCA-COLA
# ------------------------------------------
with tab3:
    st.header("Caducidades de Coca-Cola")
    
    opciones_coca = ["Coca-Cola 3 L", "Coca-Cola 600 ml"]
    
    with st.form("form_coca", clear_on_submit=True):
        prod_coca = st.selectbox("Presentación", opciones_coca, index=None, placeholder="Seleccionar formato...")
        cant_coca = st.number_input("Cantidad de Piezas", min_value=1, step=1, value=None, placeholder="0")
        fecha_coca = st.date_input("Fecha de Caducidad", value=None, key="coca_cad")
        
        btn_coca = st.form_submit_button("Registrar Coca-Cola")
        
        if btn_coca:
            if prod_coca and cant_coca and fecha_coca:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("INSERT INTO cocacola (producto, cantidad, fecha_caducidad, fecha_registro) VALUES (?, ?, ?, ?)",
                          (prod_coca, cant_coca, str(fecha_coca), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                st.success(f"✅ Registrado {cant_coca} de {prod_coca} con caducidad {fecha_coca}.")
            else:
                st.error("Por favor completa todos los campos.")

    st.markdown("---")
    st.subheader("📋 Resumen de Caducidades Coca-Cola")
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT producto, cantidad, fecha_caducidad FROM cocacola ORDER BY fecha_caducidad ASC")
    filas_coca = c.fetchall()
    conn.close()
    
    lineas_coca = []
    if filas_coca:
        for f in filas_coca:
            lineas_coca.append(f"• {f[0]}: {f[1]} pzs - Vence: {f[2]}")
    else:
        lineas_coca = ["No hay registros de Coca-Cola actualmente."]
        
    path_img_coca = generar_imagen_stock(f"CADUCIDADES COCA-COLA - {datetime.now().strftime('%d/%m/%Y')}", lineas_coca)
    st.image(path_img_coca, caption="Imagen de caducidades Coca-Cola")
