import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Proyectado Champlitte", layout="wide")

# --- 1. INICIALIZACIÓN Y CONEXIÓN A LA BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect("inventario.db")
    c = conn.cursor()
    
    # Tabla principal del inventario
    c.execute('''CREATE TABLE IF NOT EXISTS inventario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT UNIQUE,
                    linea TEXT,
                    cantidad INTEGER DEFAULT 0
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
        productos_default = [
            ("Pastel Carlos y Fichico", "LÍNEA C"),
            ("Pastel Chocofierro Chico", "LÍNEA C"),
            ("Pastel Fresas c/Crema Chico", "LÍNEA C"),
            ("Pastel Macadamia Chico", "LÍNEA C"),
            ("Pastel Milkyway Chico", "LÍNEA C"),
            ("Pastel Moka Almendra Chico", "LÍNEA C"),
            ("Pastel Piña Coco Chico", "LÍNEA C"),
            ("Pastel Zanahoria Chico", "LÍNEA C"),
            ("Pastel Cheesecake Chico", "LÍNEA C"),
            ("Pastel Carlos y Grande", "LÍNEA G"),
            ("Pastel Chocofichero Grande", "LÍNEA G"),
            ("Pastel Fresas c/Crema Grande", "LÍNEA G"),
            ("Pastel Macadamia Grande", "LÍNEA G"),
            ("Pastel Milkyway Grande", "LÍNEA G"),
            ("Pastel Moka Almendra Grande", "LÍNEA G")
        ]
        c.executemany("INSERT INTO inventario (producto, linea, cantidad) VALUES (?, ?, 0)", productos_default)
        
        # Sincronizar tabla de rellenos con valores por defecto
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
        c.execute("UPDATE inventario SET cantidad = ? WHERE id = ?", (row["cantidad"], row["id"]))
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
    # Lógica de recomendación: El pastel con mayor stock en tienda
    conn = sqlite3.connect("inventario.db")
    c = conn.cursor()
    c.execute('''
        SELECT i.producto, r.relleno, i.cantidad 
        FROM inventario i
        JOIN rellenos r ON i.producto = r.producto
        WHERE i.cantidad > 0
        ORDER BY i.cantidad DESC LIMIT 1
    ''')
    recomendacion = c.fetchone()
    conn.close()
    return recomendacion

# --- 3. INTERFAZ DE STREAMLIT ---
st.title("Proyectado de Pastelería Champlitte")

tab1, tab2 = st.tabs(["⚙️ Base de Datos y Rellenos", "🛒 Ventas y Recomendaciones"])

with tab1:
    st.header("Inventario de Sucursal")
    st.write("Llena o modifica los números en la columna **cantidad**.")
    
    df_inventario = load_data("inventario")
    
    # Data Editor para el inventario (se bloquean columnas que no deben alterarse)
    edited_inv = st.data_editor(
        df_inventario, 
        disabled=["id", "producto", "linea"], 
        hide_index=True, 
        use_container_width=True,
        key="inv_editor"
    )
    
    if st.button("Guardar Cantidades", type="primary"):
        update_inventory(edited_inv)
        st.success("¡Base de datos de inventario actualizada!")

    st.divider()

    st.header("Gestor de Rellenos")
    st.write("Edita la columna **relleno** para personalizar las recomendaciones.")
    
    df_rellenos = load_data("rellenos")
    
    # Data Editor para los rellenos
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
    
    # Extraer solo los productos que tengan al menos 1 en cantidad
    df_actual = load_data("inventario")
    disponibles = df_actual[df_actual["cantidad"] > 0]["producto"].tolist()
    
    if disponibles:
        producto_a_vender = st.selectbox("Selecciona el pastel a descontar del inventario:", options=disponibles)
        
        if st.button("Registrar Venta", type="primary"):
            if registrar_venta(producto_a_vender):
                st.success(f"Venta registrada. Se ha descontado 1 unidad de {producto_a_vender}.")
                st.rerun() # Recarga la app para reflejar el descuento inmediato
    else:
        st.warning("No hay stock en la base de datos para realizar ventas.")
        
    st.divider()
    
    st.header("Recomendación de Venta")
    st.write("*(El sistema sugiere el pastel con mayor stock)*")
    
    recomendacion = obtener_recomendacion()
    if recomendacion:
        pastel, relleno, cant = recomendacion
        st.info(f"🍰 **Pastel sugerido:** {pastel}\n\n🍯 **Relleno asignado:** {relleno}\n\n📦 *Stock actual: {cant} unidades*")
    else:
        st.info("Sin datos suficientes para sugerir.")
