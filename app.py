import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import date, timedelta

st.set_page_config(page_title="Proyectado Champlitte", layout="wide")

# --- DATOS MAESTROS DE LA PASTELERÍA ---
PRODUCTOS = {
    "Pastel Carlos V Chico": "LÍNEA C",
    "Pastel Chocoferrero Chico": "LÍNEA C",
    "Pastel Fresas c/Crema Chico": "LÍNEA C",
    "Pastel Macadamia Chico": "LÍNEA C",
    "Pastel Milkyway Chico": "LÍNEA C",
    "Pastel Moka Almendra Chico": "LÍNEA C",
    "Pastel Piña Coco Chico": "LÍNEA C",
    "Pastel Zanahoria Chico": "LÍNEA C",
    "Pastel Cheesecake Chico": "LÍNEA C",
    "Pastel Carlos V Grande": "LÍNEA G",
    "Pastel Chocoferrero Grande": "LÍNEA G",
    "Pastel Fresas c/Crema Grande": "LÍNEA G",
    "Pastel Macadamia Grande": "LÍNEA G",
    "Pastel Milkyway Grande": "LÍNEA G",
    "Pastel Moka Almendra Grande": "LÍNEA G"
}

# --- SIDEBAR: ADMINISTRACIÓN ---
with st.sidebar:
    st.header("🛠️ Administración")
    st.warning("⚠️ **Peligro:** Borrar la base de datos eliminará todo el inventario guardado.")
    
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS inventario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT,
                    linea TEXT,
                    cantidad INTEGER DEFAULT 0,
                    caducidad DATE
                )''')
    
    # Pre-cargar el catálogo visible en 0 solo la primera vez
    c.execute("SELECT COUNT(*) FROM inventario")
    if c.fetchone()[0] == 0:
        for prod, linea in PRODUCTOS.items():
            c.execute("INSERT INTO inventario (producto, linea, cantidad, caducidad) VALUES (?, ?, 0, NULL)", (prod, linea))
            
    conn.commit()
    conn.close()

init_db()

# --- 2. FUNCIONES DE LECTURA Y ESCRITURA ---
def load_data():
    conn = sqlite3.connect("inventario.db")
    df = pd.read_sql_query("SELECT * FROM inventario", conn)
    conn.close()
    return df

def procesar_ingreso(producto, linea, fechas_lista):
    conn = sqlite3.connect("inventario.db")
    c = conn.cursor()
    
    for d in fechas_lista:
        fecha_str = d.strftime("%Y-%m-%d")
        # Verificar si ya existe ese lote exacto (mismo pastel, misma fecha)
        c.execute("SELECT id FROM inventario WHERE producto = ? AND caducidad = ?", (producto, fecha_str))
        row = c.fetchone()
        
        if row:
            # Si existe, solo le sumamos 1 a la cantidad de ese lote
            c.execute("UPDATE inventario SET cantidad = cantidad + 1 WHERE id = ?", (row[0],))
        else:
            # Si es una fecha nueva para este pastel, creamos el lote
            c.execute("INSERT INTO inventario (producto, linea, cantidad, caducidad) VALUES (?, ?, 1, ?)", (producto, linea, fecha_str))
            
    conn.commit()
    conn.close()

def registrar_venta(producto):
    conn = sqlite3.connect("inventario.db")
    c = conn.cursor()
    # Sistema PEPS: Descuenta del lote de este pastel que caduca primero
    c.execute('''
        SELECT id FROM inventario 
        WHERE producto = ? AND cantidad > 0 AND caducidad IS NOT NULL
        ORDER BY caducidad ASC 
        LIMIT 1
    ''')
    
    row = c.fetchone()
    exito = False
    if row:
        c.execute("UPDATE inventario SET cantidad = cantidad - 1 WHERE id = ?", (row[0],))
        conn.commit()
        exito = True
        
    conn.close()
    return exito

def obtener_recomendaciones():
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

def actualizar_inventario_manual(df_updated):
    # Función de respaldo por si se corrigen cantidades manualmente en la tabla
    conn = sqlite3.connect("inventario.db")
    c = conn.cursor()
    c.execute("DELETE FROM inventario") 
    for _, row in df_updated.iterrows():
        cad_str = str(row["caducidad"]) if pd.notnull(row["caducidad"]) and str(row["caducidad"]) not in ["NaT", "", "None"] else None
        c.execute("INSERT INTO inventario (producto, linea, cantidad, caducidad) VALUES (?, ?, ?, ?)", 
                  (row["producto"], row["linea"], row["cantidad"], cad_str))
    conn.commit()
    conn.close()


# --- 3. INTERFAZ DE STREAMLIT ---
st.title("Proyectado de Pastelería")

tab1, tab2 = st.tabs(["⚙️ Ingresos e Inventario", "🛒 Ventas y Recomendaciones"])

with tab1:
    st.header("Ingreso Rápido de Pasteles")
    
    # Formulario dinámico
    col1, col2 = st.columns([2, 1])
    with col1:
        prod_ingreso = st.selectbox("Selecciona el pastel a ingresar:", options=list(PRODUCTOS.keys()))
    with col2:
        cant_ingreso = st.number_input("Cantidad que ingresa:", min_value=1, step=1, value=1)
    
    st.write(f"📅 **Asigna la caducidad para las {cant_ingreso} unidades:**")
    
    # Generador automático de calendarios basado en la cantidad
    columnas_fechas = st.columns(4) # Organiza los calendarios en hasta 4 columnas para que no se vea amontonado
    fechas_asignadas = []
    
    for i in range(cant_ingreso):
        with columnas_fechas[i % 4]: # Distribuye uniformemente
            fecha = st.date_input(f"Caducidad unidad {i+1}", key=f"date_{i}")
            fechas_asignadas.append(fecha)
            
    if st.button("➕ Añadir al Inventario", type="primary"):
        procesar_ingreso(prod_ingreso, PRODUCTOS[prod_ingreso], fechas_asignadas)
        st.success(f"Se han ingresado {cant_ingreso} unidades de {prod_ingreso} correctamente.")
        st.rerun()

    st.divider()
    
    st.subheader("Visor de Inventario Actual")
    st.write("*(Solo se muestran los productos con existencia o registrados. Puedes corregir cantidades aquí si hubo un error)*")
    
    df_inventario = load_data()
    df_mostrar = df_inventario.copy()
    df_mostrar['caducidad'] = pd.to_datetime(df_mostrar['caducidad'], errors='coerce').dt.date
    
    edited_inv = st.data_editor(
        df_mostrar, 
        num_rows="dynamic",
        column_config={
            "id": st.column_config.Column("ID", disabled=True, hidden=True),
            "producto": st.column_config.SelectboxColumn("Producto", options=list(PRODUCTOS.keys()), required=True),
            "linea": st.column_config.Column("Línea", disabled=True),
            "caducidad": st.column_config.DateColumn("Fecha de Caducidad", format="YYYY-MM-DD")
        },
        hide_index=True, 
        use_container_width=True,
        key="inv_editor"
    )
    
    if st.button("Guardar Cambios Manuales"):
        actualizar_inventario_manual(edited_inv)
        st.success("¡Tabla actualizada correctamente!")


with tab2:
    st.header("Punto de Venta")
    
    df_actual = load_data()
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
