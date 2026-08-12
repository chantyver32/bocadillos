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
# FUNCIONES AUXILIARES Y DIBUJO DE IMAGEN
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

def get_font(names, size):
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except:
            continue
    return ImageFont.load_default()

def dibujar_logo_texto(draw, width, color_vino, color_texto_oscuro):
    font_champlitte = get_font(["DejaVuSerif-Bold.ttf", "georgiab.ttf", "Times-Bold.ttf", "arialbd.ttf"], 75)
    font_pasteleria = get_font(["DejaVuSans-Bold.ttf", "arialbd.ttf", "Helvetica-Bold.ttf"], 22)
    draw.text((width//2, 60), "Champlitte", fill=color_vino, font=font_champlitte, anchor="mm")
    draw.text((width//2, 110), "PASTELERÍA", fill=color_texto_oscuro, font=font_pasteleria, anchor="mm")

def generar_plantilla_bocadillos(datos, fecha_str):
    width = 900
    espacio_logo = 160 
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

    dibujar_logo_texto(draw, width, WINE, TEXT_DARK)

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
    espacio_logo = 160
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

    dibujar_logo_texto(draw, width, WINE, TEXT_DARK)

    y = espacio_logo
    draw.text((width//2, y + 35), "COCA-COLA", fill=WINE, font=font_title, anchor="mm")
    draw.text((width//2, y + 85), fecha_str, fill=TEXT_DARK, font=font_sub, anchor="mm")

    y += header_height
    draw.rectangle([0, y, width, y + table_header_height], fill=WINE)
    
    col_prod, col_cant, col_cad = 200, 550, 780

    draw.text((col_prod, y + 22), "PRESENTACIÓN", fill=WHITE, font=font_th, anchor="mm")
    draw.text((col_cant, y + 22), "PIEZAS", fill=WHITE, font=font_th, anchor="mm")
    draw.text((col_cad, y + 22), "CADUCIDAD", fill=WHITE, font=font_th, anchor="mm")

    y += table_header_height
    for item in datos:
        bg_color = WHITE if datos.index(item) % 2 == 0 else ROW_ALT
        draw.rectangle([0, y, width, y + row_height], fill=bg_color)
        draw.line([420, y, 420, y + row_height], fill=LINE_COLOR, width=1)
        draw.line([660, y, 660, y + row_height], fill=LINE_COLOR, width=1)

        draw.text((50, y + (row_height//2)), str(item.get("producto", "")), fill=TEXT_DARK, font=font_td, anchor="lm")
        draw.text((col_cant, y + (row_height//2)), str(item.get("cantidad", "0")), fill=WINE, font=font_th, anchor="mm")
        
        draw.text((col_cad, y + (row_height//2)), str(item.get("caducidad", "-")), fill=TEXT_DARK, font=font_th, anchor="mm")

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
        if st.button("✅ Autocompletar", use_container_width=True):
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
        if st.button("❌ Cancelar", use_container_width=True):
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
        if st.button("✅ Autocompletar", use_container_width=True):
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
        if st.button("❌ Cancelar", use_container_width=True):
            del st.session_state["dictado_horneado"]
            st.rerun()

@st.dialog("Confirmar Entrada de Mercancía")
def dialog_confirmar_entrada(producto, paquetes, piezas):
    st.write(f"**Producto:** {producto}")
    st.write(f"**Ingreso:** {piezas} piezas en total")
    
    if st.button("✅ Confirmar y Guardar", use_container_width=True):
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
    
    if st.button("🔥 Confirmar Horneado", use_container_width=True):
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
def dialog_confirmar_coca(producto, cantidad, caducidad):
    st.write(f"**Presentación:** {producto}")
    st.write(f"**Cantidad:** {cantidad} piezas")
    st.write(f"**Caducidad:** {caducidad}")
    
    if st.button("✅ Confirmar y Guardar", use_container_width=True):
        fecha_ahora = get_hora_mexico().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO cocacola (producto, cantidad, fecha_caducidad, fecha_registro, fecha_actualizacion) VALUES (?, ?, ?, ?, ?)",
                  (producto, cantidad, str(caducidad), fecha_ahora, fecha_ahora))
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
        if st.button("⚠️ RESET TOTAL", use_container_width=True):
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
# ==========================================
st.title("📦 Control de Stock y Horneado")
tab1, tab2, tab3 = st.tabs(["📥 Entradas", "🥐 Horneado", "🥤 Coca-Cola"])

# ------------------------------------------
# PESTAÑA 1: RECEPCIÓN
# ------------------------------------------
with tab1:
    st.header("Registrar Nueva Mercancía")
    tipo_entrada = st.radio("Método:", ["✍️ Manual", "🗣️ Voz"], horizontal=True)
    if tipo_entrada == "🗣️ Voz":
        st.info("💡 Dicta: 'Llegaron cinco piezas de Volován de Jamón'")
        
        # ✅ AQUÍ REGRESAMOS use_container_width=True AL MICRÓFONO
        texto_entrada = speech_to_text(
            language='es-MX', 
            start_prompt="🎙️ Dictar", 
            stop_prompt="🔴 Grabando...", 
            use_container_width=True, 
            just_once=True, 
            key='stt_entrada'
        )
        if texto_entrada:
            st.session_state.dictado_entrada = texto_entrada
            st.rerun()

    if "dictado_entrada" in st.session_state:
        dialog_procesar_voz_entrada()

    idx_default = list(EMPAQUES.keys()).index(st.session_state["auto_ent_prod"]) if "auto_ent_prod" in st.session_state and st.session_state["auto_ent_prod"] in EMPAQUES else None
    cant_default_paq = st.session_state.get("auto_ent_paq", None)
    cant_default_pz = st.session_state.get("auto_ent_pz", None)

    with st.form("form_entrada", clear_on_submit=True):
        prod_sel = st.selectbox("Producto", list(EMPAQUES.keys()), index=idx_default, placeholder="Elija...")
        col_p, col_z = st.columns(2)
        with col_p:
            cant_paq = st.number_input("Paquetes", min_value=0, step=1, value=cant_default_paq, placeholder="0")
        with col_z:
            cant_piezas = st.number_input("Piezas sueltas", min_value=0, step=1, value=cant_default_pz, placeholder="0")
            
        # ✅ BOTÓN DE ENVIAR ANCHO
        if st.form_submit_button("Revisar y Registrar", use_container_width=True):
            val_paq = cant_paq if cant_paq is not None else 0
            val_pz = cant_piezas if cant_piezas is not None else 0
            if prod_sel and (val_paq > 0 or val_pz > 0):
                pz_totales = (val_paq * EMPAQUES[prod_sel]["piezas_x_paq"]) + val_pz
                dialog_confirmar_entrada(prod_sel, val_paq, pz_totales)
            else:
                st.error("Registra al menos 1 paquete o pieza.")

# ------------------------------------------
# PESTAÑA 2: HORNEADO
# ------------------------------------------
with tab2:
    st.header("Horneado de Mercancía")
    tipo_horneado = st.radio("Método de captura:", ["✍️ Manual", "🗣️ Voz"], horizontal=True, key="r_horn")
    if tipo_horneado == "🗣️ Voz":
        st.info("💡 Dicta: 'Hornear tres paquetes de Volován de Pierna'")
        
        # ✅ AQUÍ REGRESAMOS use_container_width=True AL MICRÓFONO
        texto_horneado = speech_to_text(
            language='es-MX', 
            start_prompt="🎙️ Dictar", 
            stop_prompt="🔴 Grabando...", 
            use_container_width=True, 
            just_once=True, 
            key='stt_horneado'
        )
        if texto_horneado:
            st.session_state.dictado_horneado = texto_horneado
            st.rerun()

    if "dictado_horneado" in st.session_state:
        dialog_procesar_voz_horneado()
        
    idx_default_h = list(EMPAQUES.keys()).index(st.session_state["auto_horn_prod"]) if "auto_horn_prod" in st.session_state and st.session_state["auto_horn_prod"] in EMPAQUES else None
    cant_default_paq_h = st.session_state.get("auto_horn_paq", None)
    cant_default_pz_h = st.session_state.get("auto_horn_pz", None)

    with st.form("form_horneado", clear_on_submit=True):
        prod_hornear = st.selectbox("Producto", list(EMPAQUES.keys()), index=idx_default_h, placeholder="Elija...")
        col_hp, col_hz = st.columns(2)
        with col_hp:
            cant_hornear_paq = st.number_input("Paquetes", min_value=0, step=1, value=cant_default_paq_h, placeholder="0")
        with col_hz:
            cant_hornear_pz = st.number_input("Piezas", min_value=0, step=1, value=cant_default_pz_h, placeholder="0")
        
        # ✅ BOTÓN DE ENVIAR ANCHO
        if st.form_submit_button("Revisar y Hornear", use_container_width=True):
            val_paq_h = cant_hornear_paq if cant_hornear_paq is not None else 0
            val_pz_h = cant_hornear_pz if cant_hornear_pz is not None else 0
            if prod_hornear and (val_paq_h > 0 or val_pz_h > 0):
                pz_a_hornear = (val_paq_h * EMPAQUES[prod_hornear]["piezas_x_paq"]) + val_pz_h
                stock_actual = calcular_stock_actual()
                disp_pz = stock_actual[prod_hornear]["piezas_totales"]
                if pz_a_hornear > disp_pz:
                    st.warning(f"⚠️ Stock insuficiente. Solo hay {disp_pz} pz.")
                else:
                    dialog_confirmar_horneado(prod_hornear, val_paq_h, pz_a_hornear)
            else:
                st.error("Completa cantidad.")

    st.markdown("---")
    st.subheader("🖼️ Reporte Visual de Stock")
    stock_actual = calcular_stock_actual()
    datos_plantilla = []
    
    fecha_mex = get_hora_mexico().strftime('%d %m %Y - %H:%M')
    lineas_wa = []
    
    for prod, datos in stock_actual.items():
        if datos['piezas_totales'] > 0:
            cant_texto = f"{datos['paquetes']} pq"
            if datos['piezas_sueltas'] > 0:
                cant_texto += f" + {datos['piezas_sueltas']} pz"
            
            suma_en_piezas = datos['piezas_totales'] 
            datos_plantilla.append({
                "producto": prod,
                "linea": EMPAQUES[prod]["categoria"],
                "cantidad": cant_texto,
                "totales": suma_en_piezas
            })
            lineas_wa.append(f"📦 {prod}: {cant_texto} (Total: {suma_en_piezas} pz)")
            
    if not datos_plantilla:
        datos_plantilla.append({"producto": "Sin inventario", "linea": "-", "cantidad": "0", "totales": 0})
        lineas_wa.append("No hay inventario.")
        
    path_img = generar_plantilla_bocadillos(datos_plantilla, fecha_mex)
    st.image(path_img, caption="Reporte generado automáticamente", use_container_width=True)
    
    if seleccion_wa:
        txt_wa = f"Stock ({seleccion_wa} | {fecha_mex}):\n" + "\n".join(lineas_wa)
        url_wa = f"https://wa.me/{numero_whatsapp}?text={urllib.parse.quote(txt_wa)}"
        st.markdown(f"[📲 **Enviar reporte WhatsApp a {seleccion_wa}**]({url_wa})", unsafe_allow_html=True)
    else:
        st.info("ℹ️ Selecciona una sucursal en el menú lateral para WhatsApp.")

# ------------------------------------------
# PESTAÑA 3: COCA-COLA
# ------------------------------------------
with tab3:
    st.header("Inventario de Coca-Cola")
    opciones_coca = ["Coca-Cola 3 L", "Coca-Cola 600 ml"]
    
    with st.form("form_coca", clear_on_submit=True):
        prod_coca = st.selectbox("Presentación", opciones_coca, index=None, placeholder="Seleccionar...")
        cant_coca = st.number_input("Piezas", min_value=1, step=1, value=None, placeholder="0")
        caducidad_coca = st.date_input("Fecha de Caducidad", value=None)
        
        # ✅ BOTÓN DE ENVIAR ANCHO
        if st.form_submit_button("Revisar y Registrar", use_container_width=True):
            if prod_coca and cant_coca and caducidad_coca:
                dialog_confirmar_coca(prod_coca, cant_coca, caducidad_coca)
            else:
                st.error("Completa todos los campos, incluyendo la caducidad.")

    st.markdown("---")
    st.subheader("🖼️ Reporte Visual de Coca-Cola")
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT producto, SUM(cantidad), fecha_caducidad FROM cocacola GROUP BY producto, fecha_caducidad ORDER BY fecha_caducidad ASC")
    stock_coca = c.fetchall()
    conn.close()
    
    datos_coca = []
    lineas_wa_coca = []
    fecha_mex_coca = get_hora_mexico().strftime('%d %m %Y - %H:%M')

    if stock_coca:
        for prod, total, cad in stock_coca:
            datos_coca.append({"producto": prod, "cantidad": total, "caducidad": cad})
            lineas_wa_coca.append(f"🥤 {prod}: {total} piezas (Vence: {cad})")
    else:
        datos_coca.append({"producto": "Sin inventario", "cantidad": 0, "caducidad": "-"})
        lineas_wa_coca.append("No hay inventario de refrescos.")

    path_coca = generar_plantilla_cocacola(datos_coca, fecha_mex_coca)
    st.image(path_coca, caption="Reporte de Refrescos", use_container_width=True)

    if seleccion_wa:
        txt_wa_coca = f"Coca-Cola ({seleccion_wa} | {fecha_mex_coca}):\n" + "\n".join(lineas_wa_coca)
        url_wa_coca = f"https://wa.me/{numero_whatsapp}?text={urllib.parse.quote(txt_wa_coca)}"
        st.markdown(f"[📲 **Enviar reporte Coca-Cola a {seleccion_wa}**]({url_wa_coca})", unsafe_allow_html=True)
    else:
        st.info("ℹ️ Selecciona una sucursal en el menú lateral para WhatsApp.")
