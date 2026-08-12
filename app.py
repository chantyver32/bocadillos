import re
import sqlite3
import urllib.parse
from datetime import datetime, date
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from streamlit_mic_recorder import speech_to_text

# ==========================================
# CONFIGURACIÓN Y BASE DE DATOS
# ==========================================
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
    "Hojaldra Jamón": {"categoria": "Dulce - Salado", "piezas_x_paq": 48},
}

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
                    fecha_registro TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS horneado (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT,
                    paquetes INTEGER,
                    piezas_totales INTEGER,
                    fecha_hora TEXT
                )''')
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
# FUNCIONES AUXILIARES Y EXTRACCIÓN DE VOZ
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

def generar_plantilla_bocadillos(datos, fecha_actualizacion):
    width = 900
    header_height = 130
    table_header_height = 45
    row_height = 55
    total_height = header_height + table_header_height + (len(datos) * row_height)

    img = Image.new('RGB', (width, total_height), color=(255, 253, 251))
    draw = ImageDraw.Draw(img)

    WINE = (128, 21, 43)        
    WINE_LIGHT = (160, 40, 70)  
    TEXT_DARK = (40, 40, 40)    
    WHITE = (255, 255, 255)
    ROW_ALT = (253, 243, 243)   
    LINE_COLOR = (235, 220, 225) 

    def get_font(names, size):
        for name in names:
            try:
                return ImageFont.truetype(name, size)
            except:
                continue
        return ImageFont.load_default()

    font_title = get_font(["DejaVuSans-Bold.ttf", "arialbd.ttf", "Helvetica-Bold.ttf"], 42)
    font_sub = get_font(["DejaVuSans.ttf", "arial.ttf", "Helvetica.ttf"], 15)
    font_th = get_font(["DejaVuSans-Bold.ttf", "arialbd.ttf", "Helvetica-Bold.ttf"], 13)
    font_td = get_font(["DejaVuSans.ttf", "arial.ttf", "Helvetica.ttf"], 15)
    font_badge = get_font(["DejaVuSans-Bold.ttf", "arialbd.ttf", "Helvetica-Bold.ttf"], 11)
    font_logo1 = get_font(["DejaVuSerif-BoldItalic.ttf", "georgiai.ttf", "Times-BoldItalic.ttf"], 28)
    font_logo2 = get_font(["DejaVuSans.ttf", "arial.ttf", "Helvetica.ttf"], 14)

    draw.text((width//2, 35), "BOCADILLOS", fill=WINE, font=font_title, anchor="mm")
    draw.text((width//2, 80), f"ACTUALIZADO AL {fecha_actualizacion}", fill=TEXT_DARK, font=font_sub, anchor="mm")

    draw.text((width - 30, 40), "Champlitte", fill=WINE, font=font_logo1, anchor="rm")
    draw.text((width - 30, 70), "Pastelería", fill=WINE_LIGHT, font=font_logo2, anchor="rm")

    y = header_height
    draw.rectangle([0, y, width, y + table_header_height], fill=WINE)
    
    col_prod = 200
    col_linea = 520
    col_cant = 680
    col_fecha = 820

    draw.text((col_prod, y + 22), "PRODUCTO", fill=WHITE, font=font_th, anchor="mm")
    draw.text((col_linea, y + 22), "LÍNEA", fill=WHITE, font=font_th, anchor="mm")
    draw.text((col_cant, y + 22), "CANTIDAD", fill=WHITE, font=font_th, anchor="mm")
    draw.text((col_fecha, y + 22), "FECHA", fill=WHITE, font=font_th, anchor="mm")

    y += table_header_height

    for i, item in enumerate(datos):
        bg_color = WHITE if i % 2 == 0 else ROW_ALT
        draw.rectangle([0, y, width, y + row_height], fill=bg_color)

        draw.line([420, y, 420, y + row_height], fill=LINE_COLOR, width=1)
        draw.line([600, y, 600, y + row_height], fill=LINE_COLOR, width=1)
        draw.line([750, y, 750, y + row_height], fill=LINE_COLOR, width=1)

        draw.text((30, y + (row_height//2)), str(item.get("producto", "")), fill=TEXT_DARK, font=font_td, anchor="lm")

        linea_texto = str(item.get("linea", ""))
        
        badge_bg = (252, 230, 230) if "Dulce" in linea_texto else WINE
        badge_text = WINE if "Dulce" in linea_texto else WHITE
        if linea_texto == "Dulce - Salado":
            badge_bg = WINE_LIGHT
            badge_text = WHITE

        badge_w, badge_h = 130, 26
        badge_x = col_linea - (badge_w//2)
        badge_y = y + (row_height//2) - (badge_h//2)
        
        draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=13, fill=badge_bg)
        draw.text((col_linea, y + (row_height//2)), f"LÍNEA {linea_texto[:1].upper()}" if len(linea_texto) > 1 else linea_texto.upper(), fill=badge_text, font=font_badge, anchor="mm")

        draw.text((col_cant, y + (row_height//2)), str(item.get("cantidad", "")), fill=TEXT_DARK, font=font_th, anchor="mm")

        fecha_texto = item.get("fecha", "")
        if fecha_texto and fecha_texto != "-":
            draw.text((col_fecha, y + (row_height//2)), fecha_texto, fill=TEXT_DARK, font=font_td, anchor="mm")
        else:
            draw.text((col_fecha, y + (row_height//2)), "-", fill=TEXT_DARK, font=font_td, anchor="mm")

        draw.line([0, y + row_height, width, y + row_height], fill=LINE_COLOR, width=1)
        y += row_height

    img.save("reporte_plantilla.png")
    return "reporte_plantilla.png"

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
    else:
        mapa_numeros = {
            "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, 
            "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, 
            "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, 
            "quince": 15, "dieciseis": 16, "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50
        }
        for palabra, valor in mapa_numeros.items():
            if re.search(rf'\b{palabra}\b', texto_norm):
                cant_encontrada = valor
                break
    
    unidad_encontrada = "Paquetes"
    if re.search(r'\bpieza[s]?\b', texto_norm):
        unidad_encontrada = "Piezas"
    elif re.search(r'\bpaquete[s]?\b', texto_norm):
        unidad_encontrada = "Paquetes"
                
    return prod_encontrado, cant_encontrada, unidad_encontrada

# ==========================================
# POP-UPS DE CONFIRMACIÓN Y VOZ (@st.dialog)
# ==========================================
@st.dialog("🎙️ Confirmar datos de Entrada")
def dialog_procesar_voz_entrada():
    texto = st.session_state.dictado_entrada
    st.write(f"**El sistema escuchó:** *'{texto}'*")
    st.divider()
    
    prod_encontrado, cant_encontrada, unidad_encontrada = extraer_datos_voz(texto)
    idx_prod = list(EMPAQUES.keys()).index(prod_encontrado) if prod_encontrado else None
    
    prod_confirmado = st.selectbox("Producto detectado:", list(EMPAQUES.keys()), index=idx_prod)
    col_u, col_c = st.columns(2)
    with col_u:
        unidad_confirmada = st.radio("Unidad:", ["Paquetes", "Piezas"], index=0 if unidad_encontrada == "Paquetes" else 1, key="rad_ent")
    with col_c:
        cant_confirmada = st.number_input("Cantidad detectada:", min_value=1, step=1, value=cant_encontrada, key="num_ent")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Autocompletar"):
            st.session_state["auto_ent_prod"] = prod_confirmado
            if unidad_confirmada == "Paquetes":
                st.session_state["auto_ent_paq"] = cant_confirmada
                st.session_state["auto_ent_pz"] = 0
            else:
                st.session_state["auto_ent_paq"] = 0
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
    
    prod_confirmado = st.selectbox("Producto detectado:", list(EMPAQUES.keys()), index=idx_prod, key="sel_horn")
    col_u, col_c = st.columns(2)
    with col_u:
        unidad_confirmada = st.radio("Unidad:", ["Paquetes", "Piezas"], index=0 if unidad_encontrada == "Paquetes" else 1, key="rad_horn")
    with col_c:
        cant_confirmada = st.number_input("Cantidad detectada:", min_value=1, step=1, value=cant_encontrada, key="num_horn")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Autocompletar"):
            st.session_state["auto_horn_prod"] = prod_confirmado
            if unidad_confirmada == "Paquetes":
                st.session_state["auto_horn_paq"] = cant_confirmada
                st.session_state["auto_horn_pz"] = 0
            else:
                st.session_state["auto_horn_paq"] = 0
                st.session_state["auto_horn_pz"] = cant_confirmada
            del st.session_state["dictado_horneado"]
            st.rerun()
    with col2:
        if st.button("❌ Cancelar"):
            del st.session_state["dictado_horneado"]
            st.rerun()

@st.dialog("Confirmar Entrada de Mercancía")
def dialog_confirmar_entrada(producto, paquetes, piezas, caducidad):
    st.write(f"**Producto:** {producto}")
    st.write(f"**Ingreso:** {piezas} piezas en total")
    st.write(f"**Caducidad:** {caducidad}")
    
    if st.button("✅ Confirmar y Guardar"):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO entradas (producto, paquetes, piezas_totales, fecha_caducidad, fecha_registro) VALUES (?, ?, ?, ?, ?)",
                  (producto, paquetes, piezas, str(caducidad), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
        hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO horneado (producto, paquetes, piezas_totales, fecha_hora) VALUES (?, ?, ?, ?)",
                  (producto, paquetes, piezas, hora_actual))
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
    
    if st.button("✅ Confirmar y Guardar"):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO cocacola (producto, cantidad, fecha_caducidad, fecha_registro) VALUES (?, ?, ?, ?)",
                  (producto, cantidad, str(caducidad), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        
        for key in ["coca_prod", "coca_cant"]:
            if key in st.session_state: del st.session_state[key]
                
        st.success("Guardado exitosamente.")
        st.rerun()

# ==========================================
# SISTEMA DE LOGIN
# ==========================================
st.set_page_config(page_title="Control de Stock", page_icon="📦", layout="centered")

def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.markdown("### 📦 Control de Stock y Horneado")
        st.markdown("### Control de Acceso")
        
        with st.form("form_login"):
            usuario_input = st.text_input("👤 Usuario:", key="login_usr")
            password_input = st.text_input("🔑 Contraseña:", type="password", key="login_pwd")
            btn_login = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            
            if btn_login:
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
idx_defecto = lista_tiendas.index("MÉXICO") if "MÉXICO" in lista_tiendas else 0
seleccion_wa = st.sidebar.selectbox("📍 Selecciona la Sucursal", lista_tiendas, index=idx_defecto)
numero_whatsapp = opciones_wa[seleccion_wa]
st.sidebar.caption(f"📱 WhatsApp: **{numero_whatsapp}**")
st.sidebar.divider()

if st.session_state.get('usuario_actual', '').lower() == 'admin':
    with st.sidebar.expander("🚨 Zona de Peligro"):
        st.warning("¡ATENCIÓN! Esto borrará el inventario completo de la base de datos.")
        confirmar_reset = st.checkbox("Confirmar borrado de datos", key="check_reset")
        if st.button("⚠️ EJECUTAR RESET TOTAL", use_container_width=True):
            if confirmar_reset:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("DELETE FROM entradas")
                c.execute("DELETE FROM horneado")
                c.execute("DELETE FROM cocacola")
                conn.commit()
                conn.close()
                st.sidebar.success("✅ Base de datos limpiada.")
                st.rerun()
            else:
                st.sidebar.error("Debes confirmar seleccionando la casilla.")

# ==========================================
# INTERFAZ STREAMLIT PRINCIPAL
# ==========================================
st.title("📦 Control de Stock y Horneado")

tab1, tab2, tab3 = st.tabs(["📥 Entradas", "🥐 Horneado", "🥤 Coca-Cola"])

# ------------------------------------------
# PESTAÑA 1: ENTRADAS Y VISUALIZACIÓN
# ------------------------------------------
with tab1:
    st.subheader("Control e Inventario de Bocadillos")
    
    with st.expander("🎙️ Registrar Entrada por Voz", expanded=False):
        st.caption("Presiona el botón, dicte por ejemplo: *'Cubiletes 5 paquetes'* y suelta.")
        audio_entrada = speech_to_text(language='es-ES', start_prompt="🎙️ Hablar", stop_prompt="🛑 Detener", key="voice_ent")
        if audio_entrada:
            st.session_state.dictado_entrada = audio_entrada
            dialog_procesar_voz_entrada()

    with st.form("form_entrada", clear_on_submit=True):
        prod_default = st.session_state.get("auto_ent_prod", list(EMPAQUES.keys())[0])
        idx_p = list(EMPAQUES.keys()).index(prod_default) if prod_default in EMPAQUES else 0
        producto = st.selectbox("Selecciona el producto:", list(EMPAQUES.keys()), index=idx_p, key="prod_sel")
        
        col1, col2 = st.columns(2)
        with col1:
            pa
