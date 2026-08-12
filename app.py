import sqlite3
import urllib.parse
from datetime import datetime, date
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import speech_recognition as sr

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
# FUNCIONES AUXILIARES Y VOZ
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
    img = Image.new('RGB', (600, 40 + len(lineas_texto) * 35 + 40), color=(245, 247, 250))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 600, 50], fill=(31, 78, 121))
    # Requiere fuente por defecto o especificar una, aquí se usa predeterminada
    draw.text((20, 15), titulo, fill=(255, 255, 255))
    y = 70
    for linea in lineas_texto:
        draw.text((20, y), linea, fill=(30, 30, 30))
        y += 32
    img.save("reporte.png")
    return "reporte.png"

def escuchar_voz():
    """Función para capturar voz y convertirla a texto"""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.toast("🎤 Escuchando... habla ahora.")
        try:
            audio = r.listen(source, timeout=5)
            texto = r.recognize_google(audio, language="es-MX")
            return texto
        except sr.UnknownValueError:
            st.error("No se pudo entender el audio.")
        except sr.RequestError:
            st.error("Error al conectar con el servicio de reconocimiento.")
        except Exception as e:
            st.error(f"Error: {e}")
    return ""

# ==========================================
# POP-UPS DE CONFIRMACIÓN (@st.dialog)
# ==========================================
@st.dialog("Confirmar Entrada de Mercancía")
def dialog_confirmar_entrada(producto, paquetes, piezas, caducidad):
    st.write(f"**Producto:** {producto}")
    st.write(f"**Paquetes:** {paquetes} ({piezas} piezas en total)")
    st.write(f"**Caducidad:** {caducidad}")
    
    if st.button("✅ Confirmar y Guardar"):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO entradas (producto, paquetes, piezas_totales, fecha_caducidad, fecha_registro) VALUES (?, ?, ?, ?, ?)",
                  (producto, paquetes, piezas, str(caducidad), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        st.session_state.clear_entrada = True
        st.success("Guardado exitosamente.")
        st.rerun()

@st.dialog("Confirmar Horneado")
def dialog_confirmar_horneado(producto, paquetes, piezas):
    st.write(f"**Producto a hornear:** {producto}")
    st.write(f"**Paquetes:** {paquetes} ({piezas} piezas totales)")
    
    if st.button("🔥 Confirmar Horneado"):
        hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO horneado (producto, paquetes, piezas_totales, fecha_hora) VALUES (?, ?, ?, ?)",
                  (producto, paquetes, piezas, hora_actual))
        conn.commit()
        conn.close()
        st.session_state.clear_horneado = True
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
        st.session_state.clear_coca = True
        st.success("Guardado exitosamente.")
        st.rerun()

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
    
    # Manejo de limpieza de estado
    if "clear_entrada" in st.session_state and st.session_state.clear_entrada:
        st.session_state.pop("clear_entrada")
        st.session_state.prod_sel = None
        st.session_state.cant_paq = None
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.write("Completa el formulario o usa el botón de voz.")
    with col2:
        if st.button("🎙️ Dictar Entrada"):
            texto = escuchar_voz()
            st.info(f"Escuchado: {texto}")
            # Aquí puedes añadir lógica para extraer "producto" y "cantidad" del texto dictado

    with st.form("form_entrada", clear_on_submit=True):
        prod_sel = st.selectbox("Selecciona Producto", list(EMPAQUES.keys()), index=None, placeholder="Elija un producto...", key="prod_sel")
        cant_paq = st.number_input("Cantidad de Paquetes recibidos", min_value=1, step=1, value=None, placeholder="0", key="cant_paq")
        fecha_cad = st.date_input("Fecha de Caducidad", value=None)
        
        btn_guardar = st.form_submit_button("Revisar y Registrar")
        
        if btn_guardar:
            if prod_sel and cant_paq and fecha_cad:
                pz_totales = cant_paq * EMPAQUES[prod_sel]["piezas_x_paq"]
                dialog_confirmar_entrada(prod_sel, cant_paq, pz_totales, fecha_cad)
            else:
                st.error("Por favor completa todos los campos del formulario.")

# ------------------------------------------
# PESTAÑA 2: REGISTRO DE HORNEADO
# ------------------------------------------
with tab2:
    st.header("Horneado de Mercancía")

    if "clear_horneado" in st.session_state and st.session_state.clear_horneado:
        st.session_state.pop("clear_horneado")
        st.session_state.hornear_prod = None
        st.session_state.hornear_cant = None

    if st.button("🎙️ Dictar Horneado"):
        texto = escuchar_voz()
        st.info(f"Escuchado: {texto}")

    with st.form("form_horneado", clear_on_submit=True):
        prod_hornear = st.selectbox("Producto a Hornear", list(EMPAQUES.keys()), index=None, placeholder="Elija un producto...", key="hornear_prod")
        cant_hornear = st.number_input("Paquetes a Hornear", min_value=1, step=1, value=None, placeholder="0", key="hornear_cant")
        
        btn_horneo = st.form_submit_button("Revisar y Hornear")
        
        if btn_horneo:
            if prod_hornear and cant_hornear:
                stock_actual = calcular_stock_actual()
                disp = stock_actual[prod_hornear]["paquetes"]
                
                if cant_hornear > disp:
                    st.warning(f"⚠️ Stock insuficiente. Solo hay {disp} paquetes disponibles en nevera.")
                else:
                    pz_totales = cant_hornear * EMPAQUES[prod_hornear]["piezas_x_paq"]
                    dialog_confirmar_horneado(prod_hornear, cant_hornear, pz_totales)
            else:
                st.error("Por favor completa los campos para registrar el horneado.")

# ------------------------------------------
# PESTAÑA 3: COCA-COLA
# ------------------------------------------
with tab3:
    st.header("Caducidades de Coca-Cola")
    opciones_coca = ["Coca-Cola 3 L", "Coca-Cola 600 ml"]
    
    if "clear_coca" in st.session_state and st.session_state.clear_coca:
        st.session_state.pop("clear_coca")
        st.session_state.coca_prod = None
        st.session_state.coca_cant = None

    if st.button("🎙️ Dictar Coca-Cola"):
        texto = escuchar_voz()
        st.info(f"Escuchado: {texto}")

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
