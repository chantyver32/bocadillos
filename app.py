import re
import time
import os
import sqlite3
import urllib.parse
from datetime import datetime, timedelta
import pytz
import pandas as pd
import streamlit as st
from streamlit_mic_recorder import speech_to_text

# Intentamos cargar Turso, si no está instalado o hay error, usamos el local
try:
    import libsql_experimental as sqlite3_turso
except ImportError:
    sqlite3_turso = sqlite3

# ==========================================
# CONFIGURACIÓN Y BASE DE DATOS
# ==========================================
st.set_page_config(page_title="Control de Stock", page_icon="📦", layout="centered")

DB_NAME = "inventario_bocadillos.db"

def get_conexion():
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    if turso_url and turso_token:
        try:
            return sqlite3_turso.connect(turso_url, auth_token=turso_token)
        except TypeError:
            pass
    return sqlite3.connect(DB_NAME)

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
    conn = get_conexion()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    username TEXT UNIQUE, 
                    password TEXT
                )''')
    c.execute("INSERT OR IGNORE INTO usuarios (username, password) VALUES ('admin', 'admin')")
    
    # Usuario urano sin permisos de edición (contraseña minúscula)
    c.execute("INSERT OR IGNORE INTO usuarios (username, password) VALUES ('urano', 'urano')")
    # Forzamos la actualización por si ya se había creado con mayúscula en la corrida anterior
    c.execute("UPDATE usuarios SET password = 'urano' WHERE username = 'urano'")
    
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
                    fecha_actualizacion TEXT,
                    fecha_caducidad TEXT
                )''')
    try: c.execute("ALTER TABLE horneado ADD COLUMN fecha_actualizacion TEXT")
    except sqlite3.OperationalError: pass
    try: c.execute("ALTER TABLE horneado ADD COLUMN fecha_caducidad TEXT")
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

    c.execute('''CREATE TABLE IF NOT EXISTS malteadas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT,
                    cantidad INTEGER,
                    fecha_caducidad TEXT,
                    fecha_registro TEXT,
                    fecha_actualizacion TEXT
                )''')

    conn.commit()
    conn.close()

init_db()

# ==========================================
# FUNCIONES AUXILIARES Y GENERACIÓN HTML
# ==========================================
def calcular_stock_detallado():
    conn = get_conexion()
    c = conn.cursor()
    
    c.execute("SELECT producto, fecha_caducidad, SUM(piezas_totales) FROM entradas GROUP BY producto, fecha_caducidad")
    entradas_data = c.fetchall()
    
    c.execute("SELECT producto, fecha_caducidad, SUM(piezas_totales) FROM horneado GROUP BY producto, fecha_caducidad")
    salidas_data = c.fetchall()
    
    salidas_dict = {f"{prod}_{cad}": total or 0 for prod, cad, total in salidas_data}
    
    stock_detallado = []
    
    for prod in EMPAQUES.keys():
        encontro_stock = False
        for prod_e, cad_e, total_ent in entradas_data:
            if prod_e == prod:
                key = f"{prod}_{cad_e}"
                total_sal = salidas_dict.get(key, 0)
                disp = total_ent - total_sal
                if disp > 0:
                    encontro_stock = True
                    pz_x_paq = EMPAQUES[prod]["piezas_x_paq"]
                    stock_detallado.append({
                        "producto": prod,
                        "caducidad": cad_e,
                        "paquetes": disp // pz_x_paq,
                        "piezas_sueltas": disp % pz_x_paq,
                        "piezas_totales": disp
                    })
        if not encontro_stock:
            stock_detallado.append({
                "producto": prod,
                "caducidad": "-",
                "paquetes": 0,
                "piezas_sueltas": 0,
                "piezas_totales": 0
            })
            
    conn.close()
    return stock_detallado

def get_fechas_disp(producto):
    stock = calcular_stock_detallado()
    fechas = [item["caducidad"] for item in stock if item["producto"] == producto and item["piezas_totales"] > 0]
    fechas.sort(key=lambda date_str: datetime.strptime(date_str, '%d/%m/%Y'))
    return fechas

def generar_html_tabla(titulo, subtitulo, columnas, claves_datos, datos, fecha_str, sucursal=""):
    WINE = "#8b1c31"
    html = f"""<div style="background-color: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.15); max-width: 900px; margin: auto; margin-bottom: 20px;">
    <div style="text-align: center; color: {WINE}; font-family: 'Georgia', serif;">
    <h1 style="margin: 0; font-size: 32px; font-weight: bold;">Champlitte {sucursal.title() if sucursal else ''}</h1>
    <h4 style="margin: 5px 0 15px 0; color: #333; letter-spacing: 2px; font-size: 12px; font-family: sans-serif; font-weight: bold;">{subtitulo}</h4>
    <h2 style="margin: 0; font-size: 24px; font-weight: bold;">{titulo}</h2>
    <p style="color: #666; font-size: 12px; margin-top: 5px; font-family: sans-serif;">{fecha_str}</p>
    </div>
    <div style="overflow-x: auto;">
    <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-family: sans-serif; font-size: 14px; min-width: 600px;">
    <thead>
    <tr style="background-color: {WINE}; color: white; text-align: center; font-size: 12px;">
    """
    for i, col in enumerate(columnas):
        rad_l = "border-top-left-radius: 8px;" if i == 0 else ""
        rad_r = "border-top-right-radius: 8px;" if i == len(columnas)-1 else ""
        html += f'<th style="padding: 12px; {rad_l} {rad_r}">{col}</th>\n'
        
    html += "</tr>\n</thead>\n<tbody>\n"

    row_color_alt = False
    for row in datos:
        bg_color = "#fffafb" if row_color_alt else "#ffffff"
        row_color_alt = not row_color_alt
        html += f'<tr style="background-color: {bg_color}; border-bottom: 1px solid #f0f0f0; text-align: center; color: {WINE}; font-weight: bold; font-size: 13px;">\n'
        
        for idx, clave in enumerate(claves_datos):
            val = row.get(clave, "-")
            
            style = "padding: 12px; "
            if idx == 0:
                style += "text-align: left; font-weight: normal; color: #333;"
            elif clave == "totales" or (clave == "cantidad" and isinstance(val, (int, float))):
                style += f"font-weight: bold; color: {WINE};"
            elif clave == "linea":
                bg_badge = "#f8eef0" if "Dulce" in str(val) else WINE
                color_badge = WINE if "Dulce" in str(val) else "white"
                if "Mixta" in str(val): bg_badge, color_badge = "#a02846", "white"
                val = f'<span style="background-color: {bg_badge}; color: {color_badge}; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{val.upper()}</span>'
            else:
                style += "font-weight: normal; color: #555;"
                
            html += f'<td style="{style}">{val}</td>\n'
        html += "</tr>\n"

    if not datos:
        html += f'<tr><td colspan="{len(columnas)}" style="padding: 20px; text-align: center; color: #666; font-style: italic;">No hay inventario registrado.</td></tr>\n'

    html += "</tbody>\n</table>\n</div>\n</div>"
    return html

def procesar_texto_voz(texto):
    texto_norm = texto.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    
    mapa_numeros = {
        "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, 
        "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, 
        "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, 
        "quince": 15, "dieciseis": 16, "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50
    }
    for palabra in sorted(mapa_numeros.keys(), key=len, reverse=True):
        texto_norm = re.sub(rf'\b{palabra}\b', str(mapa_numeros[palabra]), texto_norm)
        
    prod_encontrado = None
    aliases = {
        "hojaldra": "Hojaldra Jamón",
        "volovan de jamon": "Volován de Jamón",
        "cochinita": "Volován de Cochinita",
        "picadillo": "Volován de Picadillo",
        "pierna": "Volován de Pierna",
        "chorizo": "Chorizo Hojaldrado",
        "salchicha": "Salchicha Hojaldrada",
        "cubilete": "Cubiletes",
        "tuti": "Tutis",
        "jamon": "Volován de Jamón"
    }
    for alias, prod_real in aliases.items():
        if alias in texto_norm:
            prod_encontrado = prod_real
            break

    paquetes = 0
    match_paq = re.search(r'(\d+)\s*(paquete|paquetes|caja|cajas|paq|pq)', texto_norm)
    if match_paq: paquetes = int(match_paq.group(1))
        
    piezas = 0
    match_pz = re.search(r'(\d+)\s*(pieza|piezas|suelta|sueltas|pz)', texto_norm)
    if match_pz: piezas = int(match_pz.group(1))
        
    if paquetes == 0 and piezas == 0:
        match_any = re.search(r'(\d+)', texto_norm)
        if match_any: paquetes = int(match_any.group(1)) 

    fecha_detectada = None
    meses_dict = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
    }
    match_fecha = re.search(r'(\d+)\s*(?:de\s*)?(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)', texto_norm)
    if match_fecha:
        dia = int(match_fecha.group(1))
        mes_str = match_fecha.group(2)
        mes = meses_dict[mes_str]
        anio = get_hora_mexico().year
        try:
            fecha_detectada = datetime(anio, mes, dia).date()
        except ValueError:
            pass 
            
    return prod_encontrado, paquetes, piezas, fecha_detectada

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
# POP-UPS DE CONFIRMACIÓN Y DIRECCIONAMIENTO
# ==========================================
@st.dialog("🎙️ Revisar y Guardar Dictado (Entrada)")
def dialog_voz_entrada():
    texto = st.session_state.dictado_entrada
    st.write(f"**Escuchaste:** *'{texto}'*")
    
    prod_enc, paq_enc, pz_enc, fecha_enc = procesar_texto_voz(texto)
    idx = list(EMPAQUES.keys()).index(prod_enc) if prod_enc in EMPAQUES else None
    
    prod_sel = st.selectbox("Producto detectado:", list(EMPAQUES.keys()), index=idx, placeholder="Corregir producto...")
    col1, col2 = st.columns(2)
    with col1:
        paq_sel = st.number_input("Paquetes:", min_value=0, step=1, value=paq_enc)
    with col2:
        pz_sel = st.number_input("Piezas sueltas:", min_value=0, step=1, value=pz_enc)
    
    cad_sel = st.date_input("Fecha de Caducidad:", value=fecha_enc, format="DD/MM/YYYY")
        
    if st.button("✅ Confirmar y Guardar", use_container_width=True):
        if prod_sel and (paq_sel > 0 or pz_sel > 0) and cad_sel:
            pz_totales = (paq_sel * EMPAQUES[prod_sel]["piezas_x_paq"]) + pz_sel
            
            st.info(f"**Ingreso:** {paq_sel} paquetes y {pz_sel} piezas sueltas (Total: {pz_totales} pz)")
            
            fecha_ahora = get_hora_mexico().strftime("%d/%m/%Y %H:%M:%S")
            cad_str = cad_sel.strftime("%d/%m/%Y")
            
            conn = get_conexion()
            c = conn.cursor()
            c.execute("INSERT INTO entradas (producto, paquetes, piezas_totales, fecha_caducidad, fecha_registro, fecha_actualizacion) VALUES (?, ?, ?, ?, ?, ?)",
                      (prod_sel, paq_sel, pz_totales, cad_str, fecha_ahora, fecha_ahora))
            conn.commit()
            conn.close()
            del st.session_state.dictado_entrada
            
            st.toast("Guardado.", icon="✅")
            time.sleep(1.5)
            st.rerun()
        else:
            st.error("Verifica que haya un producto, al menos 1 cantidad y fecha de caducidad.")
            
    if st.button("❌ Cancelar", use_container_width=True):
        del st.session_state.dictado_entrada
        st.rerun()

@st.dialog("🎙️ Revisar y Guardar Dictado (Horneado)")
def dialog_voz_horneado():
    texto = st.session_state.dictado_horneado
    st.write(f"**Escuchaste:** *'{texto}'*")
    
    prod_enc, paq_enc, pz_enc, fecha_enc = procesar_texto_voz(texto)
    idx = list(EMPAQUES.keys()).index(prod_enc) if prod_enc in EMPAQUES else None
    
    prod_sel = st.selectbox("Producto detectado:", list(EMPAQUES.keys()), index=idx, placeholder="Corregir producto...")
    
    fechas_disp = get_fechas_disp(prod_sel) if prod_sel else []
    
    if not fechas_disp:
        st.warning(f"No hay stock registrado para {prod_sel}.")
    else:
        st.info("💡 Se sugiere hornear la caja con la caducidad más próxima (PEPS).")
        
        idx_cad = 0
        if fecha_enc:
            fecha_enc_str = fecha_enc.strftime("%d/%m/%Y")
            if fecha_enc_str in fechas_disp:
                idx_cad = fechas_disp.index(fecha_enc_str)
                
        cad_sel = st.selectbox("Selecciona la fecha a hornear (Caducidad):", fechas_disp, index=idx_cad)
        
        col1, col2 = st.columns(2)
        with col1:
            paq_sel = st.number_input("Paquetes:", min_value=0, step=1, value=paq_enc)
        with col2:
            pz_sel = st.number_input("Piezas sueltas:", min_value=0, step=1, value=pz_enc)
            
        if st.button("🔥 Confirmar Horneado", use_container_width=True):
            if prod_sel and (paq_sel > 0 or pz_sel > 0) and cad_sel:
                pz_a_hornear = (paq_sel * EMPAQUES[prod_sel]["piezas_x_paq"]) + pz_sel
                
                stock = calcular_stock_detallado()
                disp_pz = sum([item["piezas_totales"] for item in stock if item["producto"] == prod_sel and item["caducidad"] == cad_sel])
                
                if pz_a_hornear > disp_pz:
                    st.error(f"⚠️ Stock insuficiente para esa caducidad. Hay {disp_pz} pz disponibles.")
                else:
                    st.info(f"**Horneado:** {paq_sel} paquetes y {pz_sel} piezas sueltas (Total: {pz_a_hornear} pz)")
                    
                    fecha_ahora = get_hora_mexico().strftime("%d/%m/%Y %H:%M:%S")
                    conn = get_conexion()
                    c = conn.cursor()
                    c.execute("INSERT INTO horneado (producto, paquetes, piezas_totales, fecha_hora, fecha_actualizacion, fecha_caducidad) VALUES (?, ?, ?, ?, ?, ?)",
                              (prod_sel, paq_sel, pz_a_hornear, fecha_ahora, fecha_ahora, cad_sel))
                    conn.commit()
                    conn.close()
                    del st.session_state.dictado_horneado
                    
                    st.toast("Horneado registrado.", icon="✅")
                    time.sleep(1.5)
                    st.rerun()
            else:
                st.error("Verifica cantidades.")
            
    if st.button("❌ Cancelar", use_container_width=True):
        del st.session_state.dictado_horneado
        st.rerun()

@st.dialog("Confirmar Entrada de Mercancía")
def dialog_confirmar_entrada_manual(producto, paquetes, piezas_sueltas, piezas_totales, caducidad):
    st.write(f"**Producto:** {producto}")
    st.write(f"**Ingreso:** {paquetes} paquetes y {piezas_sueltas} piezas sueltas")
    st.write(f"**Total General:** {piezas_totales} piezas")
    st.write(f"**Caducidad:** {caducidad.strftime('%d/%m/%Y')}")
    
    if st.button("✅ Confirmar y Guardar", use_container_width=True):
        fecha_ahora = get_hora_mexico().strftime("%d/%m/%Y %H:%M:%S")
        cad_str = caducidad.strftime("%d/%m/%Y")
        conn = get_conexion()
        c = conn.cursor()
        c.execute("INSERT INTO entradas (producto, paquetes, piezas_totales, fecha_caducidad, fecha_registro, fecha_actualizacion) VALUES (?, ?, ?, ?, ?, ?)",
                  (producto, paquetes, piezas_totales, cad_str, fecha_ahora, fecha_ahora))
        conn.commit()
        conn.close()
        
        st.toast("Guardado exitosamente.", icon="✅")
        time.sleep(1.5)
        st.rerun()

@st.dialog("Confirmar Horneado")
def dialog_confirmar_horneado_manual(producto, paquetes, piezas_sueltas, piezas_totales, caducidad):
    st.write(f"**Producto a hornear:** {producto}")
    st.write(f"**A hornear:** {paquetes} paquetes y {piezas_sueltas} piezas sueltas")
    st.write(f"**Total General:** {piezas_totales} piezas")
    st.write(f"**Caja / Caducidad elegida:** {caducidad}")
    
    if st.button("🔥 Confirmar Horneado", use_container_width=True):
        fecha_ahora = get_hora_mexico().strftime("%d/%m/%Y %H:%M:%S")
        conn = get_conexion()
        c = conn.cursor()
        c.execute("INSERT INTO horneado (producto, paquetes, piezas_totales, fecha_hora, fecha_actualizacion, fecha_caducidad) VALUES (?, ?, ?, ?, ?, ?)",
                  (producto, paquetes, piezas_totales, fecha_ahora, fecha_ahora, caducidad))
        conn.commit()
        conn.close()
        
        st.toast("Horneado registrado.", icon="✅")
        time.sleep(1.5)
        st.rerun()

@st.dialog("Confirmar Registro Refrescos/Malteadas")
def dialog_confirmar_generico_manual(producto, cantidad, caducidad, tabla):
    st.write(f"**Presentación:** {producto}")
    st.write(f"**Cantidad:** {cantidad} piezas")
    st.write(f"**Caducidad:** {caducidad.strftime('%d/%m/%Y')}")
    if st.button("✅ Confirmar y Guardar", use_container_width=True):
        fecha_ahora = get_hora_mexico().strftime("%d/%m/%Y %H:%M:%S")
        cad_str = caducidad.strftime("%d/%m/%Y")
        conn = get_conexion()
        c = conn.cursor()
        c.execute(f"INSERT INTO {tabla} (producto, cantidad, fecha_caducidad, fecha_registro, fecha_actualizacion) VALUES (?, ?, ?, ?, ?)",
                  (producto, cantidad, cad_str, fecha_ahora, fecha_ahora))
        conn.commit()
        conn.close()
        
        st.toast("Guardado exitosamente.", icon="✅")
        time.sleep(1.5)
        st.rerun()

# ==========================================
# SISTEMA DE LOGIN Y NAVEGACIÓN
# ==========================================
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "show_nav_dialog" not in st.session_state:
        st.session_state.show_nav_dialog = False

    if not st.session_state.autenticado:
        st.markdown("### 📦 Control de Stock")
        with st.form("form_login"):
            usuario_input = st.text_input("👤 Usuario:")
            password_input = st.text_input("🔑 Contraseña:", type="password")
            if st.form_submit_button("Iniciar Sesión", use_container_width=True):
                conn = get_conexion()
                c = conn.cursor()
                c.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (usuario_input.strip(), password_input))
                user = c.fetchone()
                conn.close()
                if user:
                    st.session_state.autenticado = True
                    st.session_state.usuario_actual = usuario_input.strip()
                    st.session_state.show_nav_dialog = True
                    st.toast("¡Bienvenid@!", icon="👋")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
        return False
    return True

if not verificar_login():
    st.stop()

# Pop-up Inicial de Acción
if st.session_state.get("show_nav_dialog", False):
    @st.dialog("👋 ¿Qué acción vas a realizar?")
    def inicio_rapido_dialog():
        st.write("Selecciona la pestaña a la que deseas ir:")
        if st.button("📥 Registrar Entrada de Bocadillos", use_container_width=True):
            st.session_state.menu_radio = "📥 Entradas"
            st.session_state.show_nav_dialog = False
            st.rerun()
        if st.button("🥐 Hornear Bocadillos", use_container_width=True):
            st.session_state.menu_radio = "🥐 Horneado"
            st.session_state.show_nav_dialog = False
            st.rerun()
    inicio_rapido_dialog()
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
                conn = get_conexion()
                c = conn.cursor()
                c.execute("DELETE FROM entradas")
                c.execute("DELETE FROM horneado")
                c.execute("DELETE FROM cocacola")
                c.execute("DELETE FROM malteadas")
                conn.commit()
                conn.close()
                
                st.toast("Base de datos limpiada por completo.", icon="✅")
                time.sleep(1.5)
                st.rerun()

# ==========================================
# INTERFAZ STREAMLIT PRINCIPAL (SISTEMA DE PESTAÑAS)
# ==========================================
st.title("📦 Control de Stock y Horneado")

if "menu_radio" not in st.session_state:
    st.session_state.menu_radio = "📥 Entradas"

opciones_menu = ["📥 Entradas", "🥐 Horneado", "🥤 Coca-Cola", "🥛 Malteadas", "📄 Formatos"]
seccion = st.radio("Navegación", opciones_menu, horizontal=True, key="menu_radio", label_visibility="collapsed")

# ------------------------------------------
# SECCIÓN 1: RECEPCIÓN
# ------------------------------------------
if seccion == "📥 Entradas":
    st.header("Registrar Nueva Mercancía")
    tipo_entrada = st.radio("Método:", ["✍️ Manual", "🗣️ Voz"], horizontal=True)
    
    if tipo_entrada == "🗣️ Voz":
        st.info("💡 Dicta ej: 'Llegaron dos paquetes y cinco piezas de tutis el 15 de agosto'")
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
                
            caducidad_sel = st.date_input("Fecha de Caducidad", value=None, format="DD/MM/YYYY")
                
            if st.form_submit_button("Revisar y Registrar", use_container_width=True):
                val_paq = cant_paq if cant_paq is not None else 0
                val_pz = cant_piezas if cant_piezas is not None else 0
                if prod_sel and (val_paq > 0 or val_pz > 0) and caducidad_sel:
                    pz_totales = (val_paq * EMPAQUES[prod_sel]["piezas_x_paq"]) + val_pz
                    dialog_confirmar_entrada_manual(prod_sel, val_paq, val_pz, pz_totales, caducidad_sel)
                else:
                    st.error("Registra al menos 1 paquete/pieza y la fecha de caducidad.")
    
    # Bloque protegido de edición rápida
    if st.session_state.get('usuario_actual', '').lower() != 'urano':
        st.markdown("---")
        st.subheader("✏️ Edición Rápida (Entradas)")
        st.caption("Edita directamente las cantidades o caducidad en la tabla y presiona Guardar. *El ID está oculto por comodidad.*")
        
        conn = get_conexion()
        df_ent = pd.read_sql("SELECT id, producto, paquetes, piezas_totales, fecha_caducidad, fecha_actualizacion FROM entradas", conn)
        
        if not df_ent.empty:
            df_ent['piezas_sueltas'] = df_ent.apply(lambda r: r['piezas_totales'] - (r['paquetes'] * EMPAQUES.get(r['producto'], {}).get('piezas_x_paq', 1)), axis=1)
            df_mostrar = df_ent[['id', 'producto', 'paquetes', 'piezas_sueltas', 'fecha_caducidad', 'fecha_actualizacion']]
            
            edited_df = st.data_editor(
                df_mostrar,
                column_config={
                    "id": None, 
                    "producto": st.column_config.SelectboxColumn("Producto", options=list(EMPAQUES.keys()), required=True),
                    "paquetes": st.column_config.NumberColumn("Paquetes", min_value=0, step=1, required=True),
                    "piezas_sueltas": st.column_config.NumberColumn("Sueltas", min_value=0, step=1, required=True),
                    "fecha_caducidad": st.column_config.TextColumn("Caducidad", required=True),
                    "fecha_actualizacion": st.column_config.TextColumn("Fecha/Hora (Registro)", disabled=True)
                },
                hide_index=True,
                use_container_width=True,
                key="edit_entradas"
            )
            
            if st.button("💾 Guardar Cambios en Entradas", type="primary", use_container_width=True):
                c = conn.cursor()
                cambios = 0
                for i in range(len(edited_df)):
                    row = edited_df.iloc[i]
                    orig = df_mostrar.iloc[i]
                    if not row.equals(orig):
                        prod = row['producto']
                        pz_x_paq = EMPAQUES.get(prod, {}).get("piezas_x_paq", 1)
                        nuevo_tot = int((row['paquetes'] * pz_x_paq) + row['piezas_sueltas'])
                        f_act = get_hora_mexico().strftime("%d/%m/%Y %H:%M:%S")
                        
                        c.execute("UPDATE entradas SET producto=?, paquetes=?, piezas_totales=?, fecha_caducidad=?, fecha_actualizacion=? WHERE id=?", 
                                  (prod, int(row['paquetes']), nuevo_tot, str(row['fecha_caducidad']), f_act, int(row['id'])))
                        cambios += 1
                if cambios > 0:
                    conn.commit()
                    st.toast(f"{cambios} registro(s) actualizado(s).", icon="✅")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.info("No se detectaron cambios en la tabla.")
        else:
            st.info("No hay registros de Entradas para editar.")
        conn.close()

# ------------------------------------------
# SECCIÓN 2: HORNEADO
# ------------------------------------------
elif seccion == "🥐 Horneado":
    st.header("Horneado de Mercancía")
    tipo_horneado = st.radio("Método de captura:", ["✍️ Manual", "🗣️ Voz"], horizontal=True, key="r_horn")
    
    if tipo_horneado == "🗣️ Voz":
        st.info("💡 Dicta ej: 'Hornear tres paquetes de cochinita del 20 de septiembre'")
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
        prod_hornear = st.selectbox("Producto a Hornear", list(EMPAQUES.keys()), index=None, placeholder="Elija...", key="sel_prod_horn")
        
        if prod_hornear:
            fechas_disp = get_fechas_disp(prod_hornear)
            if not fechas_disp:
                st.warning(f"No hay inventario registrado para {prod_hornear}")
            else:
                st.info("💡 El sistema recomienda hornear las cajas más antiguas primero (Arriba).")
                with st.form("form_horneado", clear_on_submit=True):
                    cad_hornear = st.selectbox("Seleccionar Caja/Caducidad", fechas_disp)
                    col_hp, col_hz = st.columns(2)
                    with col_hp:
                        cant_hornear_paq = st.number_input("Paquetes", min_value=0, step=1, value=None, placeholder="0")
                    with col_hz:
                        cant_hornear_pz = st.number_input("Piezas", min_value=0, step=1, value=None, placeholder="0")
                    
                    if st.form_submit_button("Revisar y Hornear", use_container_width=True):
                        val_paq_h = cant_hornear_paq if cant_hornear_paq is not None else 0
                        val_pz_h = cant_hornear_pz if cant_hornear_pz is not None else 0
                        
                        if (val_paq_h > 0 or val_pz_h > 0) and cad_hornear:
                            pz_a_hornear = (val_paq_h * EMPAQUES[prod_hornear]["piezas_x_paq"]) + val_pz_h
                            
                            stock = calcular_stock_detallado()
                            disp_pz = sum([item["piezas_totales"] for item in stock if item["producto"] == prod_hornear and item["caducidad"] == cad_hornear])
                            
                            if pz_a_hornear > disp_pz:
                                st.warning(f"⚠️ Stock insuficiente en la caducidad {cad_hornear}. Solo hay {disp_pz} pz.")
                            else:
                                dialog_confirmar_horneado_manual(prod_hornear, val_paq_h, val_pz_h, pz_a_hornear, cad_hornear)
                        else:
                            st.error("Completa cantidad.")

    st.markdown("---")
    st.subheader("🖼️ Reportes Visuales")
    stock_actual = calcular_stock_detallado()
    
    datos_plantilla = []
    fecha_mex = get_hora_mexico().strftime('%d/%m/%Y - %H:%M')
    lineas_wa = []
    datos_resumen = []
    
    for prod in EMPAQUES.keys():
        stock_prod = [item for item in stock_actual if item['producto'] == prod and item['piezas_totales'] > 0]
        if stock_prod:
            total_pz = sum(item['piezas_totales'] for item in stock_prod)
            try:
                prox_horneo = min(stock_prod, key=lambda x: datetime.strptime(x['caducidad'], '%d/%m/%Y'))['caducidad']
            except ValueError:
                prox_horneo = stock_prod[0]['caducidad']
                
            datos_resumen.append({
                "producto": prod,
                "totales": total_pz,
                "prox_horneo": prox_horneo
            })
            
            for item in stock_prod:
                cant_texto = f"{item['paquetes']} pq"
                if item['piezas_sueltas'] > 0:
                    cant_texto += f" + {item['piezas_sueltas']} pz"
                
                suma_en_piezas = item['piezas_totales']
                caducidad = item['caducidad']
                datos_plantilla.append({
                    "producto": item['producto'], 
                    "linea": EMPAQUES[item['producto']]["categoria"], 
                    "cantidad": cant_texto, 
                    "totales": suma_en_piezas,
                    "caducidad": caducidad
                })
                lineas_wa.append(f"📦 {item['producto']} (Vence: {caducidad}): {cant_texto} (Total: {suma_en_piezas} pz)")
    
    html_resumen = generar_html_tabla(
        titulo="RESUMEN (TOTALES)", 
        subtitulo="CONTROL DE BOCADILLOS", 
        columnas=["PRODUCTO", "TOTAL (PIEZAS)", "PRÓXIMO HORNEO"],
        claves_datos=["producto", "totales", "prox_horneo"],
        datos=datos_resumen, 
        fecha_str=fecha_mex, 
        sucursal=seleccion_wa
    )
    st.markdown(html_resumen, unsafe_allow_html=True)
    
    with st.expander("👁️ Ver Reporte Detallado por Caja"):
        html_detalle = generar_html_tabla(
            titulo="BOCADILLOS - DETALLE", 
            subtitulo="DESGLOSE DE CAJAS", 
            columnas=["PRODUCTO", "CATEGORÍA", "CANTIDAD", "TOTAL (PZ)", "CADUCIDAD"],
            claves_datos=["producto", "linea", "cantidad", "totales", "caducidad"],
            datos=datos_plantilla, 
            fecha_str=fecha_mex, 
            sucursal=seleccion_wa
        )
        st.markdown(html_detalle, unsafe_allow_html=True)
    
    if seleccion_wa:
        txt_wa = f"Stock ({seleccion_wa} | {fecha_mex}):\n" + "\n".join(lineas_wa) if lineas_wa else f"Stock ({seleccion_wa} | {fecha_mex}):\nNo hay inventario."
        url_wa = f"https://wa.me/{numero_whatsapp}?text={urllib.parse.quote(txt_wa)}"
        boton_whatsapp_bonito(url_wa, f"Enviar Reporte a {seleccion_wa}")
    else:
        st.info("ℹ️ Selecciona una sucursal en el menú lateral para WhatsApp.")
        
    # Bloque protegido de edición rápida
    if st.session_state.get('usuario_actual', '').lower() != 'urano':
        st.markdown("---")
        st.subheader("✏️ Edición Rápida (Historial de Horneado)")
        st.caption("Modificar estas salidas afectará el inventario total disponible de forma automática.")
        
        conn = get_conexion()
        df_horn = pd.read_sql("SELECT id, producto, paquetes, piezas_totales, fecha_caducidad, fecha_actualizacion FROM horneado", conn)
        
        if not df_horn.empty:
            df_horn['piezas_sueltas'] = df_horn.apply(lambda r: r['piezas_totales'] - (r['paquetes'] * EMPAQUES.get(r['producto'], {}).get('piezas_x_paq', 1)), axis=1)
            df_mostrar_h = df_horn[['id', 'producto', 'paquetes', 'piezas_sueltas', 'fecha_caducidad', 'fecha_actualizacion']]
            
            edited_df_h = st.data_editor(
                df_mostrar_h,
                column_config={
                    "id": None, 
                    "producto": st.column_config.SelectboxColumn("Producto", options=list(EMPAQUES.keys()), required=True),
                    "paquetes": st.column_config.NumberColumn("Paquetes", min_value=0, step=1, required=True),
                    "piezas_sueltas": st.column_config.NumberColumn("Sueltas", min_value=0, step=1, required=True),
                    "fecha_caducidad": st.column_config.TextColumn("Caducidad de Caja", required=True),
                    "fecha_actualizacion": st.column_config.TextColumn("Fecha/Hora (Registro)", disabled=True)
                },
                hide_index=True,
                use_container_width=True,
                key="edit_horneado"
            )
            
            if st.button("💾 Guardar Cambios de Horneado", type="primary", use_container_width=True):
                c = conn.cursor()
                cambios = 0
                for i in range(len(edited_df_h)):
                    row = edited_df_h.iloc[i]
                    orig = df_mostrar_h.iloc[i]
                    if not row.equals(orig):
                        prod = row['producto']
                        pz_x_paq = EMPAQUES.get(prod, {}).get("piezas_x_paq", 1)
                        nuevo_tot = int((row['paquetes'] * pz_x_paq) + row['piezas_sueltas'])
                        f_act = get_hora_mexico().strftime("%d/%m/%Y %H:%M:%S")
                        
                        c.execute("UPDATE horneado SET producto=?, paquetes=?, piezas_totales=?, fecha_caducidad=?, fecha_actualizacion=? WHERE id=?", 
                                  (prod, int(row['paquetes']), nuevo_tot, str(row['fecha_caducidad']), f_act, int(row['id'])))
                        cambios += 1
                if cambios > 0:
                    conn.commit()
                    st.toast(f"{cambios} registro(s) actualizado(s).", icon="✅")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.info("No se detectaron cambios en la tabla.")
        else:
            st.info("No hay registros en Horneado.")
        conn.close()

# ------------------------------------------
# SECCIÓN 3: COCA-COLA
# ------------------------------------------
elif seccion == "🥤 Coca-Cola":
    st.header("Inventario de Coca-Cola")
    opciones_coca = ["Coca-Cola 3 L", "Coca-Cola 600 ml"]
    
    with st.form("form_coca", clear_on_submit=True):
        prod_coca = st.selectbox("Presentación", opciones_coca, index=None, placeholder="Seleccionar...")
        cant_coca = st.number_input("Piezas", min_value=1, step=1, value=None, placeholder="0")
        caducidad_coca = st.date_input("Fecha de Caducidad", value=None, format="DD/MM/YYYY")
        
        if st.form_submit_button("Revisar y Registrar", use_container_width=True):
            if prod_coca and cant_coca and caducidad_coca:
                dialog_confirmar_generico_manual(prod_coca, cant_coca, caducidad_coca, "cocacola")
            else:
                st.error("Completa todos los campos, incluyendo la caducidad.")

    st.markdown("---")
    st.subheader("🖼️ Reporte Visual de Coca-Cola")
    
    conn = get_conexion()
    c = conn.cursor()
    c.execute("SELECT producto, SUM(cantidad), fecha_caducidad FROM cocacola GROUP BY producto, fecha_caducidad ORDER BY fecha_caducidad ASC")
    stock_coca = c.fetchall()
    
    datos_coca = []
    lineas_wa_coca = []
    fecha_mex_coca = get_hora_mexico().strftime('%d/%m/%Y - %H:%M')

    if stock_coca:
        for prod, total, cad in stock_coca:
            datos_coca.append({"producto": prod, "cantidad": total, "caducidad": cad})
            lineas_wa_coca.append(f"🥤 {prod}: {total} piezas (Vence: {cad})")
    else:
        lineas_wa_coca.append("No hay inventario de refrescos.")

    html_coca = generar_html_tabla(
        titulo="COCA-COLA", 
        subtitulo="CONTROL DE REFRESCOS",
        columnas=["PRESENTACIÓN", "PIEZAS", "CADUCIDAD"],
        claves_datos=["producto", "cantidad", "caducidad"],
        datos=datos_coca, 
        fecha_str=fecha_mex_coca, 
        sucursal=seleccion_wa
    )
    st.markdown(html_coca, unsafe_allow_html=True)

    if seleccion_wa:
        txt_wa_coca = f"Coca-Cola ({seleccion_wa} | {fecha_mex_coca}):\n" + "\n".join(lineas_wa_coca)
        url_wa_coca = f"https://wa.me/{numero_whatsapp}?text={urllib.parse.quote(txt_wa_coca)}"
        boton_whatsapp_bonito(url_wa_coca, f"Enviar Coca-Cola a {seleccion_wa}")

    # Bloque protegido de edición rápida
    if st.session_state.get('usuario_actual', '').lower() != 'urano':
        st.markdown("---")
        st.subheader("✏️ Edición Rápida (Coca-Cola)")
        
        df_coca = pd.read_sql("SELECT id, producto, cantidad, fecha_caducidad, fecha_actualizacion FROM cocacola", conn)
        
        if not df_coca.empty:
            edited_df_c = st.data_editor(
                df_coca,
                column_config={
                    "id": None, 
                    "producto": st.column_config.SelectboxColumn("Presentación", options=opciones_coca, required=True),
                    "cantidad": st.column_config.NumberColumn("Cantidad (Pz)", min_value=0, step=1, required=True),
                    "fecha_caducidad": st.column_config.TextColumn("Caducidad", required=True),
                    "fecha_actualizacion": st.column_config.TextColumn("Fecha/Hora (Registro)", disabled=True)
                },
                hide_index=True,
                use_container_width=True,
                key="edit_coca"
            )
            
            if st.button("💾 Guardar Cambios (Coca-Cola)", type="primary", use_container_width=True):
                c = conn.cursor()
                cambios = 0
                for i in range(len(edited_df_c)):
                    row = edited_df_c.iloc[i]
                    orig = df_coca.iloc[i]
                    if not row.equals(orig):
                        f_act = get_hora_mexico().strftime("%d/%m/%Y %H:%M:%S")
                        c.execute("UPDATE cocacola SET producto=?, cantidad=?, fecha_caducidad=?, fecha_actualizacion=? WHERE id=?", 
                                  (row['producto'], int(row['cantidad']), str(row['fecha_caducidad']), f_act, int(row['id'])))
                        cambios += 1
                if cambios > 0:
                    conn.commit()
                    st.toast(f"{cambios} registro(s) actualizado(s).", icon="✅")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.info("No se detectaron cambios en la tabla.")
        else:
            st.info("No hay registros en Coca-Cola.")

        with st.expander("🗑️ Reiniciar Registro de Coca-Cola"):
            confirmar_reset_coca = st.checkbox("Confirmar borrado de Coca-Cola", key="check_reset_coca")
            if st.button("⚠️ Borrar Todo el Inventario de Coca-Cola", use_container_width=True):
                if confirmar_reset_coca:
                    c = conn.cursor()
                    c.execute("DELETE FROM cocacola")
                    conn.commit()
                    st.toast("Inventario de Coca-Cola limpiado.", icon="✅")
                    time.sleep(1.5)
                    st.rerun()
    conn.close()

# ------------------------------------------
# SECCIÓN 4: MALTEADAS
# ------------------------------------------
elif seccion == "🥛 Malteadas":
    st.header("Inventario de Malteadas")
    opciones_malteadas = ["Fresa", "Vainilla", "Chocolate"]
    
    with st.form("form_malteadas", clear_on_submit=True):
        prod_malteadas = st.selectbox("Sabor", opciones_malteadas, index=None, placeholder="Seleccionar...")
        cant_malteadas = st.number_input("Piezas", min_value=1, step=1, value=None, placeholder="0")
        caducidad_malteadas = st.date_input("Fecha de Caducidad", value=None, format="DD/MM/YYYY")
        
        if st.form_submit_button("Revisar y Registrar", use_container_width=True):
            if prod_malteadas and cant_malteadas and caducidad_malteadas:
                dialog_confirmar_generico_manual(prod_malteadas, cant_malteadas, caducidad_malteadas, "malteadas")
            else:
                st.error("Completa todos los campos, incluyendo la caducidad.")

    st.markdown("---")
    st.subheader("🖼️ Reporte Visual de Malteadas")
    
    conn = get_conexion()
    c = conn.cursor()
    c.execute("SELECT producto, SUM(cantidad), fecha_caducidad FROM malteadas GROUP BY producto, fecha_caducidad ORDER BY fecha_caducidad ASC")
    stock_malteadas = c.fetchall()
    
    datos_malteadas = []
    lineas_wa_malteadas = []
    fecha_mex_malteadas = get_hora_mexico().strftime('%d/%m/%Y - %H:%M')

    if stock_malteadas:
        for prod, total, cad in stock_malteadas:
            datos_malteadas.append({"producto": f"Malteada de {prod}", "cantidad": total, "caducidad": cad})
            lineas_wa_malteadas.append(f"🥛 Malteada de {prod}: {total} piezas (Vence: {cad})")
    else:
        lineas_wa_malteadas.append("No hay inventario de malteadas.")

    html_malteadas = generar_html_tabla(
        titulo="MALTEADAS", 
        subtitulo="CONTROL DE BEBIDAS",
        columnas=["SABOR", "PIEZAS", "CADUCIDAD"],
        claves_datos=["producto", "cantidad", "caducidad"],
        datos=datos_malteadas, 
        fecha_str=fecha_mex_malteadas, 
        sucursal=seleccion_wa
    )
    st.markdown(html_malteadas, unsafe_allow_html=True)

    if seleccion_wa:
        txt_wa_malteadas = f"Malteadas ({seleccion_wa} | {fecha_mex_malteadas}):\n" + "\n".join(lineas_wa_malteadas)
        url_wa_malteadas = f"https://wa.me/{numero_whatsapp}?text={urllib.parse.quote(txt_wa_malteadas)}"
        boton_whatsapp_bonito(url_wa_malteadas, f"Enviar Malteadas a {seleccion_wa}")

    # Bloque protegido de edición rápida
    if st.session_state.get('usuario_actual', '').lower() != 'urano':
        st.markdown("---")
        st.subheader("✏️ Edición Rápida (Malteadas)")
        
        df_malt = pd.read_sql("SELECT id, producto, cantidad, fecha_caducidad, fecha_actualizacion FROM malteadas", conn)
        
        if not df_malt.empty:
            edited_df_m = st.data_editor(
                df_malt,
                column_config={
                    "id": None, 
                    "producto": st.column_config.SelectboxColumn("Sabor", options=opciones_malteadas, required=True),
                    "cantidad": st.column_config.NumberColumn("Cantidad (Pz)", min_value=0, step=1, required=True),
                    "fecha_caducidad": st.column_config.TextColumn("Caducidad", required=True),
                    "fecha_actualizacion": st.column_config.TextColumn("Fecha/Hora (Registro)", disabled=True)
                },
                hide_index=True,
                use_container_width=True,
                key="edit_malt"
            )
            
            if st.button("💾 Guardar Cambios (Malteadas)", type="primary", use_container_width=True):
                c = conn.cursor()
                cambios = 0
                for i in range(len(edited_df_m)):
                    row = edited_df_m.iloc[i]
                    orig = df_malt.iloc[i]
                    if not row.equals(orig):
                        f_act = get_hora_mexico().strftime("%d/%m/%Y %H:%M:%S")
                        c.execute("UPDATE malteadas SET producto=?, cantidad=?, fecha_caducidad=?, fecha_actualizacion=? WHERE id=?", 
                                  (row['producto'], int(row['cantidad']), str(row['fecha_caducidad']), f_act, int(row['id'])))
                        cambios += 1
                if cambios > 0:
                    conn.commit()
                    st.toast(f"{cambios} registro(s) actualizado(s).", icon="✅")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.info("No se detectaron cambios en la tabla.")
        else:
            st.info("No hay registros en Malteadas.")

        with st.expander("🗑️ Reiniciar Registro de Malteadas"):
            confirmar_reset_malteadas = st.checkbox("Confirmar borrado de Malteadas", key="check_reset_malteadas")
            if st.button("⚠️ Borrar Todo el Inventario de Malteadas", use_container_width=True):
                if confirmar_reset_malteadas:
                    c = conn.cursor()
                    c.execute("DELETE FROM malteadas")
                    conn.commit()
                    st.toast("Inventario de Malteadas limpiado.", icon="✅")
                    time.sleep(1.5)
                    st.rerun()
    conn.close()

# ------------------------------------------
# SECCIÓN 5: FORMATOS (NUEVA PESTAÑA)
# ------------------------------------------
elif seccion == "📄 Formatos":
    st.header("Formatos Operativos")
    
    # --- FORMATO 1: TEMPERATURAS ---
    with st.expander("🌡️ Formato de Temperaturas", expanded=False):
        st.subheader("Registro de Temperaturas (CONGELACIÓN)")
        
        # Calcular fecha del "próximo lunes" o el inicio de la semana para automatizar el llenado
        hoy = get_hora_mexico().date()
        dias_para_lunes = (0 - hoy.weekday()) % 7
        if dias_para_lunes == 0: 
            dias_para_lunes = 7 # Si hoy es lunes, empezar a proyectar desde el prox. Si hoy es domingo (6), será 1 día (mañana lunes)
            
        inicio_semana_1 = hoy + timedelta(days=dias_para_lunes)
        if hoy.weekday() == 6:
            inicio_semana_1 = hoy + timedelta(days=1)
            
        inicio_semana_2 = inicio_semana_1 + timedelta(days=7)
        
        # Diccionarios para meses en español
        meses_es = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        
        def generar_df_semana(fecha_inicio):
            fecha_fin = fecha_inicio + timedelta(days=6)
            datos_semana = []
            for i in range(7):
                dia_actual = fecha_inicio + timedelta(days=i)
                datos_semana.append({
                    "DÍA": dias_semana[i],
                    "FECHA": dia_actual.strftime("%d/%m/%Y"),
                    "HORA": "",
                    "TEMPERATURA": "",
                    "PERSONA": ""
                })
            df = pd.DataFrame(datos_semana)
            texto_mes = meses_es[fecha_inicio.month].capitalize()
            texto_anio = fecha_inicio.year
            texto_rango = f"Semana del {fecha_inicio.day} de {meses_es[fecha_inicio.month]} al {fecha_fin.day} de {meses_es[fecha_fin.month]}"
            return df, texto_mes, texto_anio, texto_rango
        
        df_sem1, mes1, anio1, rango1 = generar_df_semana(inicio_semana_1)
        df_sem2, mes2, anio2, rango2 = generar_df_semana(inicio_semana_2)
        
        st.markdown(f"**Mes:** {mes1} | **Año:** {anio1} | **{rango1}**")
        st.dataframe(df_sem1, hide_index=True, use_container_width=True)
        
        st.divider()
        
        st.markdown(f"**Mes:** {mes2} | **Año:** {anio2} | **{rango2}**")
        st.dataframe(df_sem2, hide_index=True, use_container_width=True)
        
        st.caption("Nota: Todo el alimento/producto debe estar acomodado bajo el sistema PEPS. La temperatura de la unidad debe estar entre los -18°C a -25°C.")

    # --- FORMATO 2: PRECONTEO DE BOCADILLOS (TIPO IMAGEN) ---
    with st.expander("📝 Formato de Preconteo (Ref: 1000043855.jpg)", expanded=False):
        st.subheader("PRECONTEO DE BOCADILLOS")
        
        # Empatamos nombres del sistema con los nombres exactos de la imagen que solicitaste
        mapa_preconteo = {
            "Cubiletes": "Cubilete Queso",
            "Tutis": "Tuti",
            "Chorizo Hojaldrado": "Choricito Hojaldrado",
            "Hojaldra Jamón": "Hojaldra Jamón",
            "Salchicha Hojaldrada": "Salchichita Hojaldrada",
            "Volován de Cochinita": "Volován Cochinita",
            "Volován de Jamón": "Volován Jamón Queso",
            "Volován de Pierna": "Volován Pierna",
            "Volován de Picadillo": "Volován Picadillo"
        }
        
        # Llamar a la base de datos para recuperar stock total
        stock_actual_bd = calcular_stock_detallado()
        totales_por_producto = {}
        for item in stock_actual_bd:
            prod = item["producto"]
            totales_por_producto[prod] = totales_por_producto.get(prod, 0) + item["piezas_totales"]
            
        # Armar las filas imitando los recuadros en blanco para relleno posterior o visualización de totales
        datos_preconteo = []
        for prod_bd, nombre_imagen in mapa_preconteo.items():
            total_pz = totales_por_producto.get(prod_bd, 0)
            datos_preconteo.append({
                "PRODUCTO": nombre_imagen,
                "TOTAL SISTEMA (PZ)": total_pz if total_pz > 0 else "",
                " ": "", "  ": "", "   ": "", "    ": "", "     ": "", "      ": ""  # Columnas vacías imitando la hoja
            })
            
        df_preconteo = pd.DataFrame(datos_preconteo)
        
        # Mostrar usando st.table para un formato estático mucho más parecido al visual de la imagen impresa
        st.table(df_preconteo)
