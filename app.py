import re
import sqlite3
import urllib.parse
from datetime import datetime
import pytz
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from streamlit_mic_recorder import speech_to_text

# ==========================================
# CONFIGURACIÓN Y BASE DE DATOS
# ==========================================
st.set_page_config(page_title="Control de Stock", page_icon="📦", layout="centered")

DB_NAME = "inventario_bocadillos.db"

EMPAQUES = {
    "Cubiletes": {"categoria": "Dulce", "piezas_x_paq": 16},
    "Tutis": {"categoria": "Dulce", "piezas_x_paq": 27},
    "Volován de Jamón": {"categoria": "Salado", "piezas_x_paq": 9},
    "Volován de Cochinita": {"categoria": "Salado", "piezas_x_paq": 9},
    "Volován de Picadillo": {"categoria": "Salado", "piezas_x_paq": 9},
    "Volován de Pierna": {"categoria": "Salado", "piezas_x_paq": 9},
    "Chorizo Hojaldrado": {"categoria": "Salado", "piezas_x_paq": 20},
    "Salchicha Hojaldrada": {"categoria": "Salado", "piezas_x_paq": 20},
    "Hojaldra Jamón": {"categoria": "Mixta", "piezas_x_paq": 48},
}

def get_hora_mexico():
    tz_mexico = pytz.timezone('America/Mexico_City')
    return datetime.now(tz_mexico)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    username TEXT UNIQUE, 
                    password TEXT
                )''')
    c.execute("INSERT OR IGNORE INTO usuarios (username, password) VALUES ('admin', 'admin')")
    
    c.execute('''CREATE TABLE IF NOT EXISTS entradas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT,
                    paquetes INTEGER,
                    piezas_totales INTEGER,
                    fecha_caducidad TEXT,
                    fecha_registro TEXT,
                    fecha_actualizacion TEXT
                )''')
    try:
        c.execute("ALTER TABLE entradas ADD COLUMN fecha_actualizacion TEXT")
    except sqlite3.OperationalError:
        pass

    c.execute('''CREATE TABLE IF NOT EXISTS horneado (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT,
                    paquetes INTEGER,
                    piezas_totales INTEGER,
                    fecha_hora TEXT,
                    fecha_actualizacion TEXT
                )''')
    try:
        c.execute("ALTER TABLE horneado ADD COLUMN fecha_actualizacion TEXT")
    except sqlite3.OperationalError:
        pass

    c.execute('''CREATE TABLE IF NOT EXISTS cocacola (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT,
                    cantidad INTEGER,
                    fecha_caducidad TEXT,
                    fecha_registro TEXT,
                    fecha_actualizacion TEXT
                )''')
    try:
        c.execute("ALTER TABLE cocacola ADD COLUMN fecha_actualizacion TEXT")
    except sqlite3.OperationalError:
        pass

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
        c.execute("SELECT SUM(piezas_totales) FROM entradas WHERE producto = ?", (prod,))
        entradas_pz = c.fetchone()[0] or 0
        
        c.execute("SELECT SUM(piezas_totales) FROM horneado WHERE producto = ?", (prod,))
        salidas_pz = c.fetchone()[0] or 0
        
        piezas_disp = entradas_pz - salidas_pz
        pz_x_paq = EMPAQUES[prod]["piezas_x_paq"]
        
        paq_disp = piezas_disp // pz_x_paq
        pz_sueltas = piezas_disp % pz_x_paq
        
        stock[prod] = {
            "paquetes": paq_disp,
            "piezas_sueltas": pz_sueltas,
            "piezas_totales": piezas_disp
        }
    conn.close()
    return stock

def insertar_logo(img, width):
    try:
        logo = Image.open("1786574841279.jpg")
        ancho_logo = 300
        alto_logo = int((ancho_logo / logo.width) * logo.height)
        logo = logo.resize((ancho_logo, alto_logo))
        x_logo = (width - ancho_logo) // 2
        img.paste(logo, (x_logo, 20))
    except Exception:
        pass

def get_font(names, size):
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except:
            continue
    return ImageFont.load_default()

def generar_plantilla_bocadillos(datos, fecha_str):
    width = 900
    espacio_logo = 220
    header_height = 130
    table_header_height = 45
    row_height = 55
    total_height = espacio_logo + header_height + table_header_height + (len(datos) * row_height) + 40

    img = Image.new('RGB', (width, total_height), color=(255, 253, 251))
    draw = ImageDraw.Draw(img)

    WINE = (128, 21, 43)        
    WINE_LIGHT = (160, 40, 70)  
    TEXT_DARK = (40, 40, 40)    
    WHITE = (255, 255, 255)
    ROW_ALT = (253, 243, 243)   
    LINE_COLOR = (235, 220, 225) 

    font_title = get_font(["DejaVuSans-Bold.ttf", "arialbd.ttf"], 42)
    font_sub = get_font(["DejaVuSans.ttf", "arial.ttf"], 18)
    font_th = get_font(["DejaVuSans-Bold.ttf", "arialbd.ttf"], 13)
    font_td = get_font(["DejaVuSans.ttf", "arial.ttf"], 15)
    font_badge = get_font(["DejaVuSans-Bold.ttf", "arialbd.ttf"], 11)

    insertar_logo(img, width)

    y = espacio_logo
    draw.text((width//2, y + 35), "BOCADILLOS", fill=WINE, font=font_title, anchor="mm")
    draw.text((width//2, y + 85), fecha_str, fill=TEXT_DARK, font=font_sub, anchor="mm")

    y += header_height
    draw.rectangle([0, y, width, y + table_header_height], fill=WINE)
    
    col_prod, col_linea, col_cant, col_totales = 200, 520, 680, 820

    draw.text((col_prod, y + 22), "PRODUCTO", fill=WHITE, font=font_th, anchor="mm")
    draw.text((col_linea, y + 22), "CATEGORÍA", fill=WHITE, font=font_th, anchor="mm")
    draw.text((col_cant, y + 22), "PAQUETE + PIEZAS", fill=WHITE, font=font_th, anchor="mm")
    draw.text((col_totales, y + 22), "TOTAL (PIEZAS)", fill=WHITE, font=font_th, anchor="mm")

    y += table_header_height
    for item in datos:
        bg_color = WHITE if datos.index(item) % 2 == 0 else ROW_ALT
        draw.rectangle([0, y, width, y + row_height], fill=bg_color)
        draw.line([420, y, 420, y + row_height], fill=LINE_COLOR, width=1)
        draw.line([600, y, 600, y + row_height], fill=LINE_COLOR, width=1)
        draw.line([750, y, 750, y + row_height], fill=LINE_COLOR, width=1)

        draw.text((30, y + (row_height//2)), str(item.get("producto", "")), fill=TEXT_DARK, font=font_td, anchor="lm")

        linea_texto = str(item.get("linea", ""))
        badge_bg = WINE_LIGHT if "Mixta" in linea_texto else ((252, 230, 230) if "Dulce" in linea_texto else WINE)
        badge_text = WHITE if "Mixta" in linea_texto else (WINE if "Dulce" in linea_texto else WHITE)

        badge_w, badge_h = 130, 26
        badge_x = col_linea - (badge_w//2)
        badge_y = y + (row_height//2) - (badge_h//2)
        
        draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=13, fill=badge_bg)
        draw.text((col_linea, y + (row_height//2)), linea_texto.upper(), fill=badge_text, font=font_badge, anchor="mm")

        draw.text((col_cant, y + (row_height//2)), str(item.get("cantidad", "")), fill=TEXT_DARK, font=font_th, anchor="mm")
        draw.text((col_totales, y + (row_height//2)), str(item.get("totales", "0")), fill=WINE, font=font_th, anchor="mm")

        draw.line([0, y + row_height, width, y + row_height], fill=LINE_COLOR, width=1)
        y += row_height

    img.save("reporte_plantilla.png")
    return "reporte_plantilla.png"

def generar_plantilla_cocacola(datos, fecha_str):
    width = 900
    espacio_logo = 220
    header_height = 130
    table_header_height = 45
    row_height = 55
    total_height = espacio_logo + header_height + table_header_height + (len(datos) * row_height) + 40

    img = Image.new('RGB', (width, total_height), color=(255, 253, 251))
    draw = ImageDraw.Draw(img)

    WINE = (128, 21, 43)        
    TEXT_DARK = (40, 40, 40)    
    WHITE = (255, 255, 255)
    ROW_ALT = (253, 243, 243)   
    LINE_COLOR = (235, 220, 225) 

    font_title = get_font(["DejaVuSans-Bold.ttf", "arialbd.ttf"], 42)
    font_sub = get_font(["DejaVuSans.ttf", "arial.ttf"], 18)
    font_th = get_font(["DejaVuSans-Bold.ttf", "arialbd.ttf"], 14)
    font_td = get_font(["DejaVuSans.ttf", "arial.ttf"], 16)

    insertar_logo(img, width)

    y = espacio_logo
    draw.text((width//2, y + 35), "COCA-COLA", fill=WINE, font=font_title, anchor="mm")
    draw.text((width//2, y + 85), fecha_str, fill=TEXT_DARK, font=font_sub, anchor="mm")

    y += header_height
    draw.rectangle([0, y, width, y + table_header_height], fill=WINE)
    
    col_prod, col_cant = 300, 750

    draw.text((col_prod, y + 22), "PRESENTACIÓN", fill=WHITE, font=font_th, anchor="mm")
    draw.text((col_cant, y + 22), "PIEZAS TOTALES", fill=WHITE, font=font_th, anchor="mm")

    y += table_header_height
    for item in datos:
        bg_color = WHITE if datos.index(item) % 2 == 0 else ROW_ALT
        draw.rectangle([0, y, width, y + row_height], fill=bg_color)
        draw.line([600, y, 600, y + row_height], fill=LINE_COLOR, width=1)

        draw.text((50, y + (row_height//2)), str(item.get("producto", "")), fill=TEXT_DARK, font=font_td, anchor="lm")
        draw.text((col_cant, y + (row_height//2)), str(item.get("cantidad", "0")), fill=WINE, font=font_th, anchor="mm")

        draw.line([0, y + row_height, width, y + row_height], fill=LINE_COLOR, width=1)
        y += row_height

    img.save("reporte_cocacola.png")
    return "reporte_cocacola.png"

def extraer_datos_voz(texto):
    texto_norm = texto.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    prod_encontrado = None
    for prod in EMPAQUES.keys():
        prod_norm = prod.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        if prod_norm in texto_norm:
            prod_encontrado = prod
            break
            
    cant_encontrada = None
    numeros_digitos = re.findall(r'\d+', texto)
    if numeros_digitos:
        cant_encontrada = int(numeros_digitos[0])
    
    unidad_encontrada = "Paquetes"
    if re.search(r'\bpieza[s]?\b', texto_norm):
        unidad_encontrada = "Piezas"
                
    return prod_encontrado, cant_encontrada, unidad_encontrada

# ==========================================
# POP-UPS DE CONFIRMACIÓN Y VOZ
# ==========================================
@st.dialog("🎙️ Confirmar datos de Entrada")
def dialog_procesar_voz_entrada():
    texto = st.session_state.dictado_entrada
    st.write(f"**El sistema escuchó:** *'{texto}'*")
    st.divider()
    
    prod_encontrado, cant_encontrada, unidad_encontrada = extraer_datos_voz(texto)
    idx_prod = list(EMPAQUES.keys()).index(prod_encontrado) if prod_encontrado else None
    
    prod_confirmado = st.selectbox("Producto detectado:", list(EMPAQUES.keys()), index=idx_prod, placeholder="Selecciona...")
    col_u, col_c = st.columns(2)
    with col_u:
        unidad_confirmada = st.radio("Unidad:", ["Paquetes", "Piezas"], index=0 if unidad_encontrada == "Paquetes" else 1)
    with col_c:
        cant_confirmada = st.number_input("Cantidad:", min_value=1, step=1, value=cant_encontrada, placeholder="0")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Autocompletar"):
            st.session_state["auto_ent_prod"] = prod_confirmado
            if unidad_confirmada == "Paquetes":
                st.session_state["auto_ent_paq"] = cant_confirmada
                st.session_state["auto_ent_pz"] = None
            else:
                st.session_state["auto_ent_paq"] = None
                st.session_state["auto_ent_pz"] = cant_confirmada
            del st.session_state["dictado_entrada"]
            st.rerun()
    with col2:
        if st.button("❌ Cancelar"):
            del st.session_state["dictado_entrada"]
            st.rerun()

@st.dialog("🎙️ Confirmar datos de Horneado")
def dialog_procesar_voz_horneado():
    texto = st.session_state.dictado_horneado
    st.write(f"**El sistema escuchó:** *'{texto}'*")
    st.divider()
    
    prod_encontrado, cant_encontrada, unidad_encontrada = extraer_datos_voz(texto)
    idx_prod = list(EMPAQUES.keys()).index(prod_encontrado) if prod_encontrado else None
    
    prod_confirmado = st.selectbox("Producto detectado:", list(EMPAQUES.keys()), index=idx_prod, placeholder="Selecciona...")
    col_u, col_c = st.columns(2)
    with col_u:
        unidad_confirmada = st.radio("Unidad:", ["Paquetes", "Piezas"], index=0 if unidad_encontrada == "Paquetes" else 1)
    with col_c:
        cant_confirmada = st.number_input("Cantidad:", min_value=1, step=1, value=cant_encontrada, placeholder="0")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Autocompletar"):
            st.session_state["auto_horn_prod"] = prod_confirmado
            if unidad_confirmada == "Paquetes":
                st.session_state["auto_horn_paq"] = cant_confirmada
                st.session_state["auto_horn_pz"] = None
            else:
                st.session_state["auto_horn_paq"] = None
                st.session_state["auto_horn_pz"] = cant_confirmada
            del st.session_state["dictado_horneado"]
            st.rerun()
    with col2:
        if st.button("❌ Cancelar"):
            del st.session_state["dictado_horneado"]
            st.rerun()

@st.dialog("Confirmar Entrada de Mercancía")
def dialog_confirmar_entrada(producto, paquetes, piezas):
    st.write(f"**Producto:** {producto}")
    st.write(f"**Ingreso:** {piezas} piezas en total")
    
    if st.button("✅ Confirmar y Guardar"):
        fecha_ahora = get_hora_mexico().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO entradas (producto, paquetes, piezas_totales, fecha_caducidad, fecha_registro, fecha_actualizacion) VALUES (?, ?, ?, ?, ?, ?)",
                  (producto, paquetes, piezas, fecha_ahora, fecha_ahora, fecha_ahora))
        conn.commit()
        conn.close()
        for key in ["prod_sel", "cant_paq", "cant_piezas", "auto_ent_prod", "auto_ent_paq", "auto_ent_pz"]:
            if key in st.session_state: del st.session_state[key]
        st.success("Guardado exitosamente.")
        st.rerun()

@st.dialog("Confirmar Horneado")
def dialog_confirmar_horneado(producto, paquetes, piezas):
    st.write(f"**Producto a hornear:** {producto}")
    st.write(f"**Horneado:** {piezas} piezas en total")
    
    if st.button("🔥 Confirmar Horneado"):
        fecha_ahora = get_hora_mexico().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO horneado (producto, paquetes, piezas_totales, fecha_hora, fecha_actualizacion) VALUES (?, ?, ?, ?, ?)",
                  (producto, paquetes, piezas, fecha_ahora, fecha_ahora))
        conn.commit()
        conn.close()
        for key in ["hornear_prod", "hornear_cant_paq", "hornear_cant_pz", "auto_horn_prod", "auto_horn_paq", "auto_horn_pz"]:
            if key in st.session_state: del st.session_state[key]
        st.success("Horneado registrado.")
        st.rerun()

@st.dialog("Confirmar Registro Coca-Cola")
def dialog_confirmar_coca(producto, cantidad):
    st.write(f"**Presentación:** {producto}")
    st.write(f"**Cantidad:** {cantidad} piezas")
    
    if st.button("✅ Confirmar y Guardar"):
        fecha_ahora = get_hora_mexico().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO cocacola (producto, cantidad, fecha_caducidad, fecha_registro, fecha_actualizacion) VALUES (?, ?, ?, ?, ?)",
                  (producto, cantidad, fecha_ahora, fecha_ahora, fecha_ahora))
        conn.commit()
        conn.close()
        for key in ["coca_prod", "coca_cant"]:
            if key in st.session_state: del st.session_state[key]
        st.success("Guardado exitosamente.")
        st.rerun()

# ==========================================
# SISTEMA DE LOGIN
# ==========================================
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.markdown("### 📦 Control de Stock")
        with st.form("form_login"):
            usuario_input = st.text_input("👤 Usuario:")
            password_input = st.text_input("🔑 Contraseña:", type="password")
            if st.form_submit_button("Iniciar Sesión", use_container_width=True):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (usuario_input.strip(), password_input))
                user = c.fetchone()
                conn.close()
                if user:
                    st.session_state.autenticado = True
                    st.session_state.usuario_actual = usuario_input.strip()
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
        return False
    return True

if not verificar_login():
    st.stop()

# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
st.sidebar.markdown("### 🏢 Datos de Sesión")
st.sidebar.caption(f"👤 Conectado como: **{st.session_state.get('usuario_actual', 'Usuario')}**")
if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    if "usuario_actual" in st.session_state:
        del st.session_state["usuario_actual"]
    st.rerun()

st.sidebar.divider()

opciones_wa = {
    "URANO": "522281342454", "COSTA DE ORO": "522292780850", "COSTA VERDE": "522299359597",
    "DÍAZ MIRÓN": "522291302759", "EJÉRCITO MEXICANO": "522299272107", "PLAZA RÍO": "522299864120",
    "PLAYAS DEL CONCHAL": "522291794020", "COYOL": "522299398334", "LA PLACITA": "522299208481",
    "CUAUHTÉMOC": "522291651340", "MARIO MOLINA": "522291780851", "RAFAEL CUERVO": "522291980229",
    "RÍO MEDIO": "522291005852", "DIVERPLAZA": "522293763180", "BOLÍVAR": "522291002947",
    "CIRCUNVALACIÓN": "522299393726", "J.B. LOBOS": "522299201956", "YÁÑEZ": "522293764940",
    "PALACIO DE HIERRO": "522299272100", "CIUDAD INDUSTRIAL": "522299200278", "DONATO CASAS": "522291653833",
    "LAS VEGAS": "522291932980", "PUENTE MORENO": "522296893999", "CONDESA": "522299863464",
    "MURILLO VIDAL": "522286886443", "ARAUCARIAS": "522281177133", "ÁVILA CAMACHO": "522288170989",
    "EMILIANO ZAPATA": "522969628525"
}

seleccion_wa = st.sidebar.selectbox("📍 Selecciona la Sucursal", list(opciones_wa.keys()), index=None, placeholder="Elige sucursal...")
numero_whatsapp = opciones_wa[seleccion_wa] if seleccion_wa else ""
if seleccion_wa:
    st.sidebar.caption(f"📱 WhatsApp asociado: **{numero_whatsapp}**")

st.sidebar.divider()

if st.session_state.get('usuario_actual', '').lower() == 'admin':
    with st.sidebar.expander("🚨 Zona de Peligro"):
        confirmar_reset = st.checkbox("Confirmar borrado", key="check_reset")
        if st.button("⚠️ RESET TOTAL"):
            if confirmar_reset:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("DELETE FROM entradas")
                c.execute("DELETE FROM horneado")
                c.execute("DELETE FROM cocacola")
                conn.commit()
                conn.close()
                st.sidebar.success("✅ BD limpiada.")
                st.rerun()

# ==========================================
# INTERFAZ STREAMLIT PRINCIPAL
# ===================
