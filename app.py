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
    
    # Se elimina la restricción UNIQUE de producto para permitir lotes con distintas fechas
    c.execute('''CREATE TABLE IF NOT EXISTS inventario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT,
                    linea TEXT,
                    cantidad INTEGER DEFAULT 0,
                    caducidad DATE
                )''')
    
    # Insertar los productos por defecto si la tabla está vacía
    c.execute("SELECT COUNT(*) FROM inventario")
    if c.fetchone()[0] == 0:
        fecha_default = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
        
        productos_default = [
            ("Pastel Carlos V Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Chocoferrero Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Fresas c/Crema Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Macadamia Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Milkyway Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Moka Almendra Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Piña Coco Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Zanahoria Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Cheesecake Chico", "LÍNEA C", 0, fecha_default),
            ("Pastel Carlos V Grande", "LÍNEA G", 0, fecha_default),
            ("Pastel Chocoferrero Grande", "LÍNEA G", 0, fecha_default),
            ("Pastel Fresas c/Crema Grande", "LÍNEA G", 0, fecha_default),
            ("Pastel Macadamia Grande", "LÍNEA G", 0, fecha_default),
            ("Pastel Milkyway Grande", "LÍNEA G", 0, fecha_default),
            ("Pastel Moka Almendra Grande", "LÍNEA G", 0, fecha_default)
        ]
        c.executemany("INSERT INTO inventario (producto, linea, cantidad, caducidad) VALUES (?, ?, ?, ?)", productos_default)
        
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
    # Para sincronizar altas y bajas dinámicas, vaciamos e insertamos de nuevo
    c.execute("DELETE FROM inventario") 
    
    for _, row in df_updated.iterrows():
        cad_str = str(row["caducidad"]) if pd.notnull(row["caducidad"]) and str(row["caducidad"]) not in ["NaT", "", "None"] else None
        id_val = int(row["id"]) if pd.notnull(row.get("id")) else None
        
        c.execute("INSERT INTO inventario (id, producto, linea, cantidad, caducidad) VALUES (?, ?, ?, ?, ?)", 
                  (id_val, row["producto"], row["linea"], row["cantidad"], cad_str))
    
    conn.commit()
    conn.close()

def registrar_venta(producto):
    conn = sqlite3.connect("inventario.db")
    c = conn.cursor()
    # Sistema PEPS (FIFO): Descuenta del lote que caduca primero
    c.execute('''
        SELECT id FROM inventario 
        WHERE producto = ? AND cantidad > 0 
        ORDER BY caducidad ASC 
        LIMIT 1
    ''', (producto,))
    
    row = c.fetchone()
    exito = False
    if row:
        lote_id = row[0]
        c.execute("UPDATE inventario SET cantidad = cantidad - 1 WHERE id = ?", (lote_id,))
        conn.commit()
        exito = True
        
    conn.close()
    return exito

def obtener_recomendaciones():
    # Encuentra la fecha de caducidad más cercana y trae todos los pasteles de esa fecha
    conn = sqlite3.connect("inventario.db")
    c = conn.cursor()
    c.execute('''
        SELECT producto, SUM(cantidad) as cantidad_total, caducidad
        FROM inventario
        WHERE cantidad > 0 AND caducidad IS NOT NULL
          AND caducidad = (
              SELECT MIN(caducidad) 
              FROM inventario 
              WHERE cantidad > 0 AND caducidad IS NOT NULL
          )
        GROUP BY producto, caducidad
        ORDER BY cantidad_total DESC
    ''')
    recomendaciones = c.fetchall()
    conn.close()
    return recomendaciones

# --- 3. INTERFAZ DE STREAMLIT ---
st.title("Proyectado de Pastelería Champlitte")

tab1, tab2 = st.tabs(["⚙️ Inventario", "🛒 Ventas y Recomendaciones"])

# Listas para facilitar la creación de nuevas filas
lista_productos = [
    "Pastel Carlos V Chico", "Pastel Chocoferrero Chico", "Pastel Fresas c/Crema Chico", 
    "Pastel Macadamia Chico", "Pastel Milkyway Chico", "Pastel Moka Almendra Chico", 
    "Pastel Piña Coco Chico", "Pastel Zanahoria Chico", "Pastel Cheesecake Chico", 
    "Pastel Carlos V Grande", "Pastel Chocoferrero Grande", "Pastel Fresas c/Crema Grande", 
    "Pastel Macadamia Grande", "Pastel Milkyway Grande", "Pastel Moka Almendra Grande"
]
lista_lineas = ["LÍNEA C", "LÍNEA G"]

with tab1:
    st.header("Inventario de Sucursal")
    st.write("Llena los números y fechas. **Si tienes el mismo pastel con distinta caducidad, agrega una fila nueva al final de la tabla.**")
    
    df_inventario = load_data("inventario")
    df_inventario['caducidad'] = pd.to_datetime(df_inventario['caducidad'], errors='coerce').dt.date
    
    edited_inv = st.data_editor(
        df_inventario, 
        num_rows="dynamic", # Habilita agregar/eliminar filas libremente
        column_config={
            "id": st.column_config.Column("ID", disabled=True, hidden=True),
            "producto": st.column_config.SelectboxColumn("Producto", options=lista_productos, required=True),
            "linea": st.column_config.SelectboxColumn("Línea", options=lista_lineas, required=True),
            "caducidad": st.column_config.DateColumn("Fecha de Caducidad", format="YYYY-MM-DD", step=1)
        },
        hide_index=True, 
        use_container_width=True,
        key="inv_editor"
    )
    
    if st.button("Guardar Inventario", type="primary"):
        update_inventory(edited_inv)
        st.success("¡Base de datos de inventario actualizada con éxito!")

with tab2:
    st.header("Punto de Venta")
    
    df_actual = load_data("inventario")
    # Utilizamos .unique() para no repetir nombres en el selector aunque haya múltiples lotes
    disponibles = df_actual[df_actual["cantidad"] > 0]["producto"].unique().tolist()
    
    if disponibles:
        producto_a_vender = st.selectbox(
            "Selecciona el pastel a descontar del inventario:", 
            options=disponibles,
            index=None,
            placeholder="Escribe el nombre del pastel..."
        )
        
        if producto_a_vender:
            if st.button("Registrar Venta", type="primary"):
                if registrar_venta(producto_a_vender):
                    st.success(f"Venta registrada. Se descontó 1 unidad del lote más próximo a caducar de {producto_a_vender}.")
                    st.rerun() 
        else:
            st.button("Registrar Venta", type="primary", disabled=True)
            
    else:
        st.warning("No hay stock en la base de datos para realizar ventas.")
        
    st.divider()
    
    st.header("Recomendación de Venta")
    st.write("*(El sistema sugiere los pasteles más próximos a caducar)*")
    
    recomendaciones = obtener_recomendaciones()
    if recomendaciones:
        st.write("### 🍰 Pasteles Recomendados:")
        for rec in recomendaciones:
            pastel, cant, caducidad = rec
            st.info(f"**{pastel}**\n\n📦 *Total en stock: {cant} unidades*  |  ⏳ *Fecha límite:* **{caducidad}**")
    else:
        st.info("Sin datos suficientes para sugerir.")
        
