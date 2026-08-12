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
    # Tabla Usuarios para Login
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    username TEXT UNIQUE, 
                    password TEXT
                )''')
    # Crear usuario admin por defecto si no existe
    c.execute("INSERT OR IGNORE INTO usuarios (username, password) VALUES ('admin', 'admin')")
    
    # Tablas de Inventario
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
    """Calcula el stock basándose en las piezas totales para no perder piezas sueltas."""
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
        
        # Calcular cuántos paquetes enteros y cuántas piezas sueltas quedan
        paq_disp = piezas_disp // pz_x_paq
        pz_sueltas = piezas_disp % pz_x_paq
        
        stock[prod] = {
            "paquetes": paq_disp,
            "piezas_sueltas": pz_sueltas,
            "piezas_totales": piezas_disp
        }
    conn.close()
    return stock

def generar_imagen_stock(titulo, lineas_texto):
    """Genera una imagen bonita estilo reporte/tabla con filas alternadas."""
    ancho = 600
    alto_encabezado = 60
    alto_fila = 40
    margen = 20
    alto_total = alto_encabezado + (len(lineas_texto) * alto_fila) + margen * 2

    # Fondo general suave
    img = Image.new('RGB', (ancho, alto_total), color=(245, 247, 250))
    draw = ImageDraw.Draw(img)
    
    # Rectángulo del encabezado (Azul oscuro elegante)
    draw.rectangle([0, 0, ancho, alto_encabezado], fill=(31, 78, 121))
    draw.text((margen, 20), f"📊 {titulo}", fill=(255, 255, 255))
    
    # Dibujar las filas con estilo "cebra" (colores alternos) para que se vea bonito
    y = alto_encabezado + margen
    for i, linea in enumerate(lineas_texto):
        color_fondo = (255, 255, 255) if i % 2 == 0 else (235, 240, 245)
        
        # Dibujar fondo de la fila
        draw.rectangle([margen, y, ancho - margen, y + alto_fila], fill=color_fondo)
        
        # Borde sutil en la parte inferior de la fila
        draw.line([margen, y + alto_fila, ancho - margen, y + alto_fila], fill=(220, 225, 230), width=1)
        
        # Texto de la fila
        draw.text((margen + 15, y + 12), linea, fill=(40, 40, 40))
        y += alto_fila

    img.save("reporte.png")
    return "reporte.png"

def extraer_datos_voz(texto):
    texto_norm = texto.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    
    # 1. Extraer Producto (ignorando acentos y mayúsculas)
    prod_encontrado = None
    for prod in EMPAQUES.keys():
        prod_norm = prod.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        if prod_norm in texto_norm:
            prod_encontrado = prod
            break
            
    # 2. Extraer Cantidad (soporta dígitos y palabras)
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
    
    # 3. Extraer Unidad (Piezas o Paquetes)
    unidad_encontrada = "Paquetes" # Paquetes por defecto
    if re.search(r'\bpieza[s]?\b', texto_norm):
        unidad_encontrada = "Piezas"
    elif re.search(r'\bpaquete[s]?\b', texto_norm):
        unidad_encontrada = "Paquetes"
                
    return prod_encontrado, cant_encontrada, unidad_encontrada

# ==========================================
# POP-UPS DE CONFIRMACIÓN (@st.dialog)
# ==========================================
@st.dialog("🎙️ Confirmar datos dictados")
def dialog_procesar_voz():
    texto_dictado = st.session_state.ultimo_dictado
    st.write(f"**El sistema escuchó:** *'{texto_dictado}'*")
    st.divider()
    
    prod_encontrado, cant_encontrada, unidad_encontrada = extraer_datos_voz(texto_dictado)

    st.write("Verifica si los datos extraídos son correctos:")
    
    idx_prod = list(EMPAQUES.keys()).index(prod_encontrado) if prod_encontrado else None
    
    prod_confirmado = st.selectbox("Producto detectado:", list(EMPAQUES.keys()), index=idx_prod)
    
    col_u, col_c = st.columns(2)
    with col_u:
        unidad_confirmada = st.radio("Unidad:", ["Paquetes", "Piezas"], index=0 if unidad_encontrada == "Paquetes" else 1)
    with col_c:
        cant_confirmada = st.number_input("Cantidad detectada:", min_value=1, step=1, value=cant_encontrada)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Autocompletar"):
            st.session_state["auto_prod"] = prod_confirmado
            if unidad_confirmada == "Paquetes":
                st.session_state["auto_cant_paq"] = cant_confirmada
                st.session_state["auto_cant_pz"] = 0
            else:
                st.session_state["auto_cant_paq"] = 0
                st.session_state["auto_cant_pz"] = cant_confirmada
                
            del st.session_state["ultimo_dictado"] # Limpiamos la memoria
            st.rerun()
    with col2:
        if st.button("❌ Cancelar"):
            del st.session_state["ultimo_dictado"]
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
        
        # Limpieza de variables si existían
        for key in ["prod_sel", "cant_paq", "cant_piezas", "auto_prod", "auto_cant_paq", "auto_cant_pz"]:
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
        
        for key in ["hornear_prod", "hornear_cant_paq", "hornear_cant_pz"]:
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
            if key in st.session_state:
                del st.session_state[key]
                
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

# ⭐️ AHORA MÉXICO ESTÁ EN LA LISTA COMO SUCURSAL ⭐️
opciones_wa = {
    "MÉXICO": "521234567890", # <- Puedes cambiar este número por el oficial
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

# ⭐️ MÉXICO AHORA ES LA SUCURSAL POR DEFECTO ⭐️
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
                st.sidebar.success("✅ Base de datos limpiada por completo.")
                st.rerun()
            else:
                st.sidebar.error("Debes confirmar seleccionando la casilla.")

# ==========================================
# INTERFAZ STREAMLIT PRINCIPAL
# ==========================================
st.title("📦 Control de Stock y Horneado")

tab1, tab2, tab3 = st.tabs([
    "📥 Entradas", 
    "🥐 Horneado", 
    "🥤 Coca-Cola"
])

# ------------------------------------------
# PESTAÑA 1: RECEPCIÓN DE MERCANCÍA
# ------------------------------------------
with tab1:
    st.header("Registrar Nueva Mercancía")
    
    tipo_entrada = st.radio(
        "Selecciona el método de captura:", 
        ["✍️ Entrada Manual", "🗣️ Entrada por Voz"], 
        horizontal=True
    )
    
    if tipo_entrada == "🗣️ Entrada por Voz":
        st.info("💡 Dicta el producto y la cantidad (Ej: 'Llegaron cinco piezas de Volován de Jamón')")
        texto_entrada = speech_to_text(
            language='es-MX', 
            start_prompt="🎙️ Toca para Dictar", 
            stop_prompt="🔴 Grabando...", 
            use_container_width=True, 
            just_once=True, 
            key='stt_entrada'
        )
        
        if texto_entrada:
            st.session_state.ultimo_dictado = texto_entrada
            st.rerun()

    # Disparador del pop-up de voz
    if "ultimo_dictado" in st.session_state:
        dialog_procesar_voz()

    # Rescatar variables en caso de autocompletado por voz
    idx_default = None
    if "auto_prod" in st.session_state and st.session_state["auto_prod"] in EMPAQUES:
        idx_default = list(EMPAQUES.keys()).index(st.session_state["auto_prod"])
        
    cant_default_paq = st.session_state.get("auto_cant_paq", 0)
    cant_default_pz = st.session_state.get("auto_cant_pz", 0)

    with st.form("form_entrada", clear_on_submit=True):
        prod_sel = st.selectbox(
            "Selecciona Producto", 
            list(EMPAQUES.keys()), 
            index=idx_default, 
            placeholder="Elija un producto...", 
            key="prod_sel"
        )
        
        col_p, col_z = st.columns(2)
        with col_p:
            cant_paq = st.number_input("Paquetes", min_value=0, step=1, value=cant_default_paq, key="cant_paq")
        with col_z:
            cant_piezas = st.number_input("Piezas sueltas", min_value=0, step=1, value=cant_default_pz, key="cant_piezas")
            
        fecha_cad = st.date_input("Fecha de Caducidad", value=None)
        
        btn_guardar = st.form_submit_button("Revisar y Registrar")
        
        if btn_guardar:
            if prod_sel and (cant_paq > 0 or cant_piezas > 0) and fecha_cad:
                pz_totales = (cant_paq * EMPAQUES[prod_sel]["piezas_x_paq"]) + cant_piezas
                dialog_confirmar_entrada(prod_sel, cant_paq, pz_totales, fecha_cad)
            else:
                st.error("Por favor completa los campos y asegúrate de registrar al menos 1 paquete o pieza.")

# ------------------------------------------
# PESTAÑA 2: REGISTRO DE HORNEADO
# ------------------------------------------
with tab2:
    st.header("Horneado de Mercancía")

    with st.form("form_horneado", clear_on_submit=True):
        prod_hornear = st.selectbox("Producto a Hornear", list(EMPAQUES.keys()), index=None, placeholder="Elija un producto...", key="hornear_prod")
        
        col_hp, col_hz = st.columns(2)
        with col_hp:
            cant_hornear_paq = st.number_input("Paquetes a Hornear", min_value=0, step=1, value=0, key="hornear_cant_paq")
        with col_hz:
            cant_hornear_pz = st.number_input("Piezas a Hornear", min_value=0, step=1, value=0, key="hornear_cant_pz")
        
        btn_horneo = st.form_submit_button("Revisar y Hornear")
        
        if btn_horneo:
            if prod_hornear and (cant_hornear_paq > 0 or cant_hornear_pz > 0):
                pz_a_hornear = (cant_hornear_paq * EMPAQUES[prod_hornear]["piezas_x_paq"]) + cant_hornear_pz
                
                stock_actual = calcular_stock_actual()
                disp_pz = stock_actual[prod_hornear]["piezas_totales"]
                
                if pz_a_hornear > disp_pz:
                    st.warning(f"⚠️ Stock insuficiente. Solo hay {disp_pz} piezas disponibles en nevera para este producto.")
                else:
                    dialog_confirmar_horneado(prod_hornear, cant_hornear_paq, pz_a_hornear)
            else:
                st.error("Por favor completa los campos seleccionando un producto y una cantidad.")

    st.markdown("---")
    st.subheader("🖼️ Stock Disponible en Nevera")
    
    stock_actual = calcular_stock_actual()
    lineas_reporte = []
    
    for prod, datos in stock_actual.items():
        if datos['piezas_sueltas'] > 0:
            lineas_reporte.append(f"📦 {prod}: {datos['paquetes']} paq + {datos['piezas_sueltas']} pzs")
        else:
            lineas_reporte.append(f"📦 {prod}: {datos['paquetes']} paq")
        
    path_img = generar_imagen_stock(f"STOCK {seleccion_wa} - {datetime.now().strftime('%d/%m/%Y %H:%M')}", lineas_reporte)
    
    st.image(path_img, caption="Reporte actual generado automáticamente")
    
    texto_whatsapp = f"Stock en Nevera ({seleccion_wa} - {datetime.now().strftime('%d/%m/%Y %H:%M')}):\n" + "\n".join(lineas_reporte)
    url_wa = f"https://wa.me/{numero_whatsapp}?text={urllib.parse.quote(texto_whatsapp)}"
    
    st.markdown(f"[📲 **Enviar reporte por WhatsApp a {seleccion_wa}**]({url_wa})", unsafe_allow_html=True)

# ------------------------------------------
# PESTAÑA 3: COCA-COLA
# ------------------------------------------
with tab3:
    st.header("Caducidades de Coca-Cola")
    opciones_coca = ["Coca-Cola 3 L", "Coca-Cola 600 ml"]
    
    texto_coca = speech_to_text(language='es-MX', start_prompt="🎙️ Dictar Coca-Cola", stop_prompt="🔴 Grabando...", use_container_width=True, just_once=True, key='stt_coca')
    if texto_coca:
        st.info(f"Escuchaste: {texto_coca}")

    with st.form("form_coca", clear_on_submit=True):
        prod_coca = st.selectbox("Presentación", opciones_coca, index=None, placeholder="Seleccionar formato...", key="coca_prod")
        cant_coca = st.number_input("Cantidad de Piezas", min_value=1, step=1, value=None, placeholder="0", key="coca_cant")
        fecha_coca = st.date_input("Fecha de Caducidad", value=None)
        
        btn_coca = st.form_submit_button("Revisar y Registrar")
        
        if btn_coca:
            if prod_coca and cant_coca and fecha_coca:
                dialog_confirmar_coca(prod_coca, cant_coca, fecha_coca)
            else:
                st.error("Por favor completa todos los campos.")
