import re
import time
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
    try: c.execute("ALTER TABLE entradas ADD COLUMN fecha_actualizacion TEXT")
    except sqlite3.OperationalError: pass

    c.execute('''CREATE TABLE IF NOT EXISTS horneado (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT,
                    paquetes INTEGER,
                    piezas_totales INTEGER,
                    fecha_hora TEXT,
                    fecha_actualizacion TEXT
                )''')
    try: c.execute("ALTER TABLE horneado ADD COLUMN fecha_actualizacion TEXT")
    except sqlite3.OperationalError: pass

    c.execute('''CREATE TABLE IF NOT EXISTS cocacola (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT,
                    cantidad INTEGER,
                    fecha_caducidad TEXT,
                    fecha_registro TEXT,
                    fecha_actualizacion TEXT
                )''')
    try: c.execute("ALTER TABLE cocacola ADD COLUMN fecha_actualizacion TEXT")
    except sqlite3.OperationalError: pass

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
        try: return ImageFont.truetype(name, size)
        except: continue
    return ImageFont.load_default()

def dibujar_logo_texto(draw, width, color_vino, color_texto_oscuro):
    font_champlitte = get_font(["DejaVuSerif-Bold.ttf", "georgiab.ttf", "Times-Bold.ttf", "arialbd.ttf"], 75)
    font_pasteleria = get_font(["DejaVuSans-Bold.ttf", "arialbd.ttf", "Helvetica-Bold.ttf"], 22)
    draw.text((width//2, 60), "Champlitte", fill=color_vino, font=font_champlitte, anchor="mm")
    draw.text((width//2, 130), "PASTELERÍA", fill=color_texto_oscuro, font=font_pasteleria, anchor="mm")

def generar_plantilla_bocadillos(datos, fecha_str):
    width = 900
    espacio_logo = 175 
    header_height = 130
    table_header_height = 45
    row_height = 55
    total_height = espacio_logo + header_height + table_header_height + (len(datos) * row_height) + 40

    img = Image.new('RGB', (width, total_height), color=(255, 253, 251))
    draw = ImageDraw.Draw(img)

    WINE, WINE_LIGHT, TEXT_DARK, WHITE = (128, 21, 43), (160, 40, 70), (40, 40, 40), (255, 255, 255)
    ROW_ALT, LINE_COLOR = (253, 243, 243), (235, 220, 225) 

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
    espacio_logo = 175
    header_height = 130
    table_header_height = 45
    row_height = 55
    total_height = espacio_logo + header_height + table_header_height + (len(datos) * row_height) + 40

    img = Image.new('RGB', (width, total_height), color=(255, 253, 251))
    draw = ImageDraw.Draw(img)

    WINE, TEXT_DARK, WHITE, ROW_ALT, LINE_COLOR = (128, 21, 43), (40, 40, 40), (255, 255, 255), (253, 243, 243), (235, 220, 225) 

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

# ✅ CEREBRO DE VOZ MEJORADO: Entiende "cubilete", y acepta paquetes y piezas al mismo tiempo.
def procesar_texto_voz(texto):
    texto_norm = texto.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    
    prod_encontrado = None
    for prod in EMPAQUES.keys():
        prod_norm = prod.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        # Detecta coincidencias exactas o en singular (ej. cubilete -> cubiletes)
        if prod_norm in texto_norm or (prod_norm.endswith('s') and prod_norm[:-1] in texto_norm):
            prod_encontrado = prod
            break
            
    mapa_numeros = {
        "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, 
        "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, 
        "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, 
        "quince": 15, "dieciseis": 16, "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50
    }
    
    for palabra in sorted(mapa_numeros.keys(), key=len, reverse=True):
        texto_norm = re.sub(rf'\b{palabra}\b', str(mapa_numeros[palabra]), texto_norm)
        
    paquetes = 0
    match_paq = re.search(r'(\d+)\s*(paquete|paquetes|caja|cajas|paq|pq)', texto_norm)
    if match_paq:
        paquetes = int(match_paq.group(1))
        
    piezas = 0
    match_pz = re.search(r'(\d+)\s*(pieza|piezas|suelta|sueltas|pz)', texto_norm)
    if match_pz:
        piezas = int(match_pz.group(1))
        
    if paquetes == 0 and piezas == 0:
        match_any = re.search(r'(\d+)', texto_norm)
        if match_any:
            paquetes = int(match_any.group(1)) 
            
    return prod_encontrado, paquetes, piezas

def boton_whatsapp_bonito(url, texto):
    html_wa = f"""
    <a href="{url}" target="_blank" style="background-color: #25D366; color: white; text-align: center; padding: 12px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; font-family: sans-serif; display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; box-sizing: border-box; font-size: 16px;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 16 16"><path d="M11.42 9.49c-.19-.09-1.1-.54-1.27-.61s-.29-.09-.41.1-.48.61-.59.73-.21.14-.4.05a5.1 5.1 0 0 1-1.5-.92 5.54 5.54 0 0 1-1.04-1.29c-.11-.18 0-.28.09-.38.08-.09.19-.21.28-.32a1.36 1.36 0 0 0 .19-.32.54.54 0 0 0-.03-.52c-.05-.09-.41-1-.56-1.37-.15-.36-.3-.31-.41-.31h-.35a.68.68 0 0 0-.49.23 2.06 2.06 0 0 0-.64 1.53c0 1.22 1.25 2.4 1.42 2.63.17.23 1.79 2.73 4.33 3.82.6.26 1.07.41 1.44.53.6.19 1.15.16 1.58.1.48-.07 1.47-.6 1.68-1.18.21-.58.21-1.07.15-1.18-.06-.1-.23-.15-.42-.24zM8 14.5a6.5 6.5 0 1 1 0-13 6.5 6.5 0 0 1 0 13zM8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0z"/></svg>
        {texto}
    </a>
    <br>
    """
    st.markdown(html_wa, unsafe_allow_html=True)

# ==========================================
# POP-UPS DE CONFIRMACIÓN DIRECTA (1 SOLO PASO)
# ==========================================
@st.dialog("🎙️ Revisar y Guardar Dictado (Entrada)")
def dialog_voz_entrada():
    texto = st.session_state.dictado_entrada
    st.write(f"**Escuchaste:** *'{texto}'*")
    
    prod_enc, paq_enc, pz_enc = procesar_texto_voz(texto)
    idx = list(EMPAQUES.keys()).index(prod_enc) if prod_enc in EMPAQUES else None
    
    prod_sel = st.selectbox("Producto detectado:", list(EMPAQUES.keys()), index=idx, placeholder="Corregir producto...")
    col1, col2 = st.columns(2)
    with col1:
        paq_sel = st.number_input("Paquetes:", min_value=0, step=1, value=paq_enc)
    with col2:
        pz_sel = st.number_input("Piezas sueltas:", min_value=0, step=1, value=pz_enc)
        
    # ✅ Guarda directo a la base de datos desde el Pop-up
    if st.button("✅ Confirmar y Guardar", use_container_width=True):
        if prod_sel and (paq_sel > 0 or pz_sel > 0):
            pz_totales = (paq_sel * EMPAQUES[prod_sel]["piezas_x_paq"]) + pz_sel
            fecha_ahora = get_hora_mexico().strftime("%Y-%m-%d %H:%M:%S")
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO entradas (producto, paquetes, piezas_totales, fecha_caducidad, fecha_registro, fecha_actualizacion) VALUES (?, ?, ?, ?, ?, ?)",
                      (prod_sel, paq_sel, pz_totales, fecha_ahora, fecha_ahora, fecha_ahora))
            conn.commit()
            conn.close()
            del st.session_state.dictado_entrada
            
            st.toast("Guardado.", icon="✅")
            time.sleep(1.5)
            st.rerun()
        else:
            st.error("Verifica que haya un producto y al menos 1 cantidad.")
            
    if st.button("❌ Cancelar", use_container_width=True):
        del st.session_state.dictado_entrada
        st.rerun()

@st.dialog("🎙️ Revisar y Guardar Dictado (Horneado)")
def dialog_voz_horneado():
    texto = st.session_state.dictado_horneado
    st.write(f"**Escuchaste:** *'{texto}'*")
    
    prod_enc, paq_enc, pz_enc = procesar_texto_voz(texto)
    idx = list(EMPAQUES.keys()).index(prod_enc) if prod_enc in EMPAQUES else None
    
    prod_sel = st.selectbox("Producto detectado:", list(EMPAQUES.keys()), index=idx, placeholder="Corregir producto...")
    col1, col2 = st.columns(2)
    with col1:
        paq_sel = st.number_input("Paquetes:", min_value=0, step=1, value=paq_enc)
    with col2:
        pz_sel = st.number_input("Piezas sueltas:", min_value=0, step=1, value=pz_enc)
        
    if st.button("🔥 Confirmar Horneado", use_container_width=True):
        if prod_sel and (paq_sel > 0 or pz_sel > 0):
            pz_a_hornear = (paq_sel * EMPAQUES[prod_sel]["piezas_x_paq"]) + pz_sel
            stock_actual = calcular_stock_actual()
            disp_pz = stock_actual[prod_sel]["piezas_totales"]
            if pz_a_hornear > disp_pz:
                st.error(f"⚠️ Stock insuficiente. Hay {disp_pz} pz disponibles.")
            else:
                fecha_ahora = get_hora_mexico().strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("INSERT INTO horneado (producto, paquetes, piezas_totales, fecha_hora, fecha_actualizacion) VALUES (?, ?, ?, ?, ?)",
                          (prod_sel, paq_sel, pz_a_hornear, fecha_ahora, fecha_ahora))
                conn.commit()
                conn.close()
                del st.session_state.dictado_horneado
                
                st.toast("Horneado registrado.", icon="✅")
                time.sleep(1.5)
                st.rerun()
        else:
            st.error("Verifica que haya un producto y al menos 1 cantidad.")
            
    if st.button("❌ Cancelar", use_container_width=True):
        del st.session_state.dictado_horneado
        st.rerun()

# Pop-ups para el modo MANUAL
@st.dialog("Confirmar Entrada de Mercancía")
def dialog_confirmar_entrada_manual(producto, paquetes, piezas):
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
        
        st.toast("Guardado exitosamente.", icon="✅")
        time.sleep(1.5)
        st.rerun()

@st.dialog("Confirmar Horneado")
def dialog_confirmar_horneado_manual(producto, paquetes, piezas):
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
        
        st.toast("Horneado registrado.", icon="✅")
        time.sleep(1.5)
        st.rerun()

@st.dialog("Confirmar Registro Coca-Cola")
def dialog_confirmar_coca_manual(producto, cantidad, caducidad):
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
        
        st.toast("Guardado exitosamente.", icon="✅")
        time.sleep(1.5)
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
    "URANO": "522291653665", "COSTA DE ORO": "522292780850", "COSTA VERDE": "522299359597",
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

lista_tiendas = list(opciones_wa.keys())
idx_urano = lista_tiendas.index("URANO") if "URANO" in lista_tiendas else 0
seleccion_wa = st.sidebar.selectbox("📍 Selecciona la Sucursal", lista_tiendas, index=idx_urano, placeholder="Elige sucursal...")
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
                
                st.toast("Base de datos limpiada por completo.", icon="✅")
                time.sleep(1.5)
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
        st.info("💡 Dicta ej: 'Llegaron dos paquetes y cinco piezas de tutis'")
        texto_entrada = speech_to_text(
            language='es-MX', 
            start_prompt="🎙️ Toca para Dictar", 
            stop_prompt="🔴 Grabando...", 
            use_container_width=True, 
            just_once=True, 
            key='stt_entrada'
        )
        if texto_entrada:
            st.session_state.dictado_entrada = texto_entrada
            st.rerun()

    if "dictado_entrada" in st.session_state:
        dialog_voz_entrada()

    elif tipo_entrada == "✍️ Manual":
        with st.form("form_entrada", clear_on_submit=True):
            prod_sel = st.selectbox("Producto", list(EMPAQUES.keys()), index=None, placeholder="Elija...")
            col_p, col_z = st.columns(2)
            with col_p:
                cant_paq = st.number_input("Paquetes", min_value=0, step=1, value=None, placeholder="0")
            with col_z:
                cant_piezas = st.number_input("Piezas sueltas", min_value=0, step=1, value=None, placeholder="0")
                
            if st.form_submit_button("Revisar y Registrar", use_container_width=True):
                val_paq = cant_paq if cant_paq is not None else 0
                val_pz = cant_piezas if cant_piezas is not None else 0
                if prod_sel and (val_paq > 0 or val_pz > 0):
                    pz_totales = (val_paq * EMPAQUES[prod_sel]["piezas_x_paq"]) + val_pz
                    dialog_confirmar_entrada_manual(prod_sel, val_paq, pz_totales)
                else:
                    st.error("Registra al menos 1 paquete o pieza.")

# ------------------------------------------
# PESTAÑA 2: HORNEADO
# ------------------------------------------
with tab2:
    st.header("Horneado de Mercancía")
    tipo_horneado = st.radio("Método de captura:", ["✍️ Manual", "🗣️ Voz"], horizontal=True, key="r_horn")
    
    if tipo_horneado == "🗣️ Voz":
        st.info("💡 Dicta ej: 'Hornear tres paquetes y una pieza de Volován de Pierna'")
        texto_horneado = speech_to_text(
            language='es-MX', 
            start_prompt="🎙️ Toca para Dictar", 
            stop_prompt="🔴 Grabando...", 
            use_container_width=True, 
            just_once=True, 
            key='stt_horneado'
        )
        if texto_horneado:
            st.session_state.dictado_horneado = texto_horneado
            st.rerun()

    if "dictado_horneado" in st.session_state:
        dialog_voz_horneado()

    elif tipo_horneado == "✍️ Manual":
        with st.form("form_horneado", clear_on_submit=True):
            prod_hornear = st.selectbox("Producto", list(EMPAQUES.keys()), index=None, placeholder="Elija...")
            col_hp, col_hz = st.columns(2)
            with col_hp:
                cant_hornear_paq = st.number_input("Paquetes", min_value=0, step=1, value=None, placeholder="0")
            with col_hz:
                cant_hornear_pz = st.number_input("Piezas", min_value=0, step=1, value=None, placeholder="0")
            
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
                        dialog_confirmar_horneado_manual(prod_hornear, val_paq_h, pz_a_hornear)
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
            datos_plantilla.append({"producto": prod, "linea": EMPAQUES[prod]["categoria"], "cantidad": cant_texto, "totales": suma_en_piezas})
            lineas_wa.append(f"📦 {prod}: {cant_texto} (Total: {suma_en_piezas} pz)")
            
    if not datos_plantilla:
        datos_plantilla.append({"producto": "Sin inventario", "linea": "-", "cantidad": "0", "totales": 0})
        lineas_wa.append("No hay inventario.")
        
    path_img = generar_plantilla_bocadillos(datos_plantilla, fecha_mex)
    st.image(path_img, caption="Reporte generado automáticamente", use_container_width=True)
    
    if seleccion_wa:
        txt_wa = f"Stock ({seleccion_wa} | {fecha_mex}):\n" + "\n".join(lineas_wa)
        url_wa = f"https://wa.me/{numero_whatsapp}?text={urllib.parse.quote(txt_wa)}"
        boton_whatsapp_bonito(url_wa, f"Enviar Reporte a {seleccion_wa}")
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
        
        if st.form_submit_button("Revisar y Registrar", use_container_width=True):
            if prod_coca and cant_coca and caducidad_coca:
                dialog_confirmar_coca_manual(prod_coca, cant_coca, caducidad_coca)
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
        boton_whatsapp_bonito(url_wa_coca, f"Enviar Coca-Cola a {seleccion_wa}")
    else:
        st.info("ℹ️ Selecciona una sucursal en el menú lateral para WhatsApp.")
