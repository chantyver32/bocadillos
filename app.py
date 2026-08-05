import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import date, timedelta

st.set_page_config(page_title="Proyectado Champlitte", layout="wide")

# --- SIDEBAR: ADMINISTRACIÓN ---
with st.sidebar:
    st.header("🛠️ Administración")
    st.warning("⚠️ **Peligro:** Borrar la base de datos eliminará todo el inventario guardado y restablecerá los valores por defecto.")
    
    confirmar = st.checkbox("Habilitar borrado de base de datos")
    
    if confirmar:
        if st.button("Borrar Base de Datos", type="primary", use_container_width=True):
            if os.path.exists("inventario.db"):
                try:
                    os.remove("inventario.db")
                    st.success("Base de datos eliminada. Reiniciando...")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al borrar: {e}")
            else:
                st.info("La base de datos no existe actualmente.")

# --- 1. INICIALIZACIÓN Y CONEXIÓN A LA BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect("inventario.db")
    c = conn.cursor()
    
    # Tabla principal del inventario actualizada con fecha de caducidad
    c.execute('''CREATE TABLE IF NOT EXISTS inventario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT UNIQUE,
                    linea TEXT,
                    cantidad INTEGER DEFAULT 0,
                    caducidad DATE
                )''')
    
    # Tabla secundaria para los rellenos
    c.execute('''CREATE TABLE IF NOT EXISTS rellenos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT UNIQUE,
                    relleno TEXT
                )''')
    
    # Insertar los productos por defecto si la tabla está vacía
    c.execute("SELECT COUNT(*) FROM inventario")
    if c.fetchone()[0] == 0:
        # Por defecto, ponemos una fecha de caducidad de 3 días a partir de hoy
        fecha_default = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
        
        productos_default = [
            ("Pastel Carlos V Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Chocofierro Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Fresas c/Crema Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Macadamia Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Milkyway Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Moka Almendra Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Piña Coco Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Zanahoria Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Cheesecake Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Carlos V Grande", "LÍNEA G", 0, fecha_default),
            ("Pastel Chocofichero Grande", "LÍNEA G", 0, fecha_default),
            ("Pastel Fresas c/Crema Grande", "LÍNEA G", 0, fecha_default),
            ("Pastel Macadamia Grande", "LÍNEA G", 0, fecha_default),
            ("Pastel Milkyway Grande", "LÍNEA G", 0, fecha_default),
            ("Pastel Moka Almendra Grande", "LÍNEA G", 0, fecha_default)
        ]
        c.executemany("INSERT INTO inventario (producto, linea, cantidad, caducidad) VALUES (?, ?, ?, ?)", productos_default)
        
        rellenos_default = [(p[0], "Sin asignar") for p in productos_default]
        c.executemany("INSERT INTO rellenos (producto, relleno) VALUES (?, ?)", rellenos_default)
        
    conn.commit()
    conn.close()

init_db()

# --- 2. FUNCIONES DE LECTURA Y ESCRITURA ---
def load_data(table_name):
    conn = sqlite3.connect("inventario.db")
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

def update_inventory(df_updated):
    conn = sqlite3.connect("inventario.db")
    c = conn.cursor()
    for _, row in df_updated.iterrows():
        # Manejo de la fecha por si se deja vacía en la interfaz
        caducidad_str = str(row["caducidad"]) if pd.notnull(row["caducidad"]) else None
        c.execute("UPDATE inventario SET cantidad = ?, caducidad = ? WHERE id = ?", (row["cantidad"], caducidad_str, row["id"]))
    conn.commit()
    conn.close()

def update_fillings(df_updated):
    conn = sqlite3.connect("inventario.db")
    c = conn.cursor()
    for _, row in df_updated.iterrows():
        c.execute("UPDATE rellenos SET relleno = ? WHERE id = ?", (row["relleno"], row["id"]))
    conn.commit()
    conn.close()

def registrar_venta(producto):
    conn = sqlite3.connect("inventario.db")
    c = conn.cursor()
    c.execute("UPDATE inventario SET cantidad = cantidad - 1 WHERE producto = ? AND cantidad > 0", (producto,))
    exito = c.rowcount > 0
    conn.commit()
    conn.close()
    return exito

def obtener_recomendacion():
    # Lógica de recomendación: Prioriza fecha próxima a caducar. En caso de empate, el mayor stock.
    conn = sqlite3.connect("inventario.db")
    c = conn.cursor()
    c.execute('''
        SELECT i.producto, r.relleno, i.cantidad, i.caducidad
        FROM inventario i
        JOIN rellenos r ON i.producto = r.producto
        WHERE i.cantidad > 0 AND i.caducidad IS NOT NULL
        ORDER BY i.caducidad ASC, i.cantidad DESC LIMIT 1
    ''')
    recomendacion = c.fetchone()
    conn.close()
    return recomendacion

# --- 3. INTERFAZ DE STREAMLIT ---
st.title("Proyectado de Pastelería Champlitte")

tab1, tab2 = st.tabs(["⚙️ Base de Datos y Rellenos", "🛒 Ventas y Recomendaciones"])

with tab1:
    st.header("Inventario de Sucursal")
    st.write("Llena o modifica los números y selecciona la **fecha de caducidad**.")
    
    df_inventario = load_data("inventario")
    # Convertir la columna texto a formato de fecha para que Streamlit muestre el calendario
    df_inventario['caducidad'] = pd.to_datetime(df_inventario['caducidad'], errors='coerce').dt.date
    
    edited_inv = st.data_editor(
        df_inventario, 
        disabled=["id", "producto", "linea"], 
        column_config={
            "caducidad": st.column_config.DateColumn(
                "Fecha de Caducidad",
                format="YYYY-MM-DD",
                step=1
            )
        },
        hide_index=True, 
        use_container_width=True,
        key="inv_editor"
    )
    
    if st.button("Guardar Cantidades y Fechas", type="primary"):
        update_inventory(edited_inv)
        st.success("¡Base de datos de inventario actualizada!")

    st.divider()

    st.header("Gestor de Rellenos")
    st.write("Edita la columna **relleno** para personalizar las recomendaciones.")
    
    df_rellenos = load_data("rellenos")
    
    edited_rellenos = st.data_editor(
        df_rellenos, 
        disabled=["id", "producto"], 
        hide_index=True, 
        use_container_width=True,
        key="rell_editor"
    )
    
    if st.button("Guardar Rellenos"):
        update_fillings(edited_rellenos)
        st.success("¡Rellenos actualizados correctamente!")


with tab2:
    st.header("Punto de Venta")
    
    df_actual = load_data("inventario")
    disponibles = df_actual[df_actual["cantidad"] > 0]["producto"].tolist()
    
    if disponibles:
        # Se agrega index=None para que aparezca vacío por defecto y permita teclear
        producto_a_vender = st.selectbox(
            "Selecciona el pastel a descontar del inventario:", 
            options=disponibles,
            index=None,
            placeholder="Escribe el nombre del pastel..."
        )
        
        # El botón solo funciona si hay un pastel seleccionado
        if producto_a_vender:
            if st.button("Registrar Venta", type="primary"):
                if registrar_venta(producto_a_vender):
                    st.success(f"Venta registrada. Se ha descontado 1 unidad de {producto_a_vender}.")
                    st.rerun() 
        else:
            st.button("Registrar Venta", type="primary", disabled=True)
            
    else:
        st.warning("No hay stock en la base de datos para realizar ventas.")
        
    st.divider()
    
    st.header("Recomendación de Venta")
    st.write("*(El sistema sugiere el pastel más próximo a caducar. Si hay empate, sugiere el de mayor stock)*")
    
    recomendacion = obtener_recomendacion()
    if recomendacion:
        pastel, relleno, cant, caducidad = recomendacion
        # Se cambió "Pastel sugerido" por "Pastel recomendado"
        st.info(f"🍰 **Pastel recomendado:** {pastel}\n\n🍯 **Relleno asignado:** {relleno}\n\n📦 *Stock actual: {cant} unidades*\n\n⏳ *Fecha límite:* **{caducidad}**")
    else:
        st.info("Sin datos suficientes para sugerir.")
