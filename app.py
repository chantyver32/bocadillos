import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import date, timedelta

# Configuración inicial de la página
st.set_page_config(page_title="Proyectado Champlitte", layout="wide")

# --- MOSTRAR MENSAJE DE ÉXITO PENDIENTE ---
if "mensaje_exito" in st.session_state:
    st.success(st.session_state["mensaje_exito"])
    del st.session_state["mensaje_exito"]

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
                    st.session_state["mensaje_exito"] = "Base de datos eliminada. Reiniciando..."
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al borrar: {e}")
            else:
                st.info("La base de datos no existe actualmente.")

# --- 1. INICIALIZACIÓN Y CONEXIÓN A LA BASE DE DATOS ---
def init_db():
    with sqlite3.connect("inventario.db") as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS inventario (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        producto TEXT,
                        linea TEXT,
                        cantidad INTEGER DEFAULT 0,
                        caducidad DATE
                    )''')
        
        c.execute("SELECT COUNT(*) FROM inventario")
        if c.fetchone()[0] == 0:
            for prod, linea in PRODUCTOS.items():
                c.execute("INSERT INTO inventario (producto, linea, cantidad, caducidad) VALUES (?, ?, 0, NULL)", (prod, linea))
        conn.commit()

init_db()

# --- 2. FUNCIONES DE LECTURA Y ESCRITURA ---
def load_data():
    with sqlite3.connect("inventario.db") as conn:
        df = pd.read_sql_query("SELECT * FROM inventario", conn)
    return df

def procesar_ingreso(producto, linea, fechas_lista):
    with sqlite3.connect("inventario.db") as conn:
        c = conn.cursor()
        for d in fechas_lista:
            fecha_str = d.strftime("%Y-%m-%d")
            c.execute("SELECT id FROM inventario WHERE producto = ? AND caducidad = ?", (producto, fecha_str))
            row = c.fetchone()
            
            if row:
                c.execute("UPDATE inventario SET cantidad = cantidad + 1 WHERE id = ?", (row[0],))
            else:
                c.execute("INSERT INTO inventario (producto, linea, cantidad, caducidad) VALUES (?, ?, 1, ?)", (producto, linea, fecha_str))
        conn.commit()

def registrar_venta(producto):
    exito = False
    with sqlite3.connect("inventario.db") as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id FROM inventario 
            WHERE producto = ? AND cantidad > 0 AND caducidad IS NOT NULL
            ORDER BY caducidad ASC 
            LIMIT 1
        ''', (producto,)) 
        
        row = c.fetchone()
        if row:
            c.execute("UPDATE inventario SET cantidad = cantidad - 1 WHERE id = ?", (row[0],))
            conn.commit()
            exito = True
    return exito

def obtener_recomendaciones():
    with sqlite3.connect("inventario.db") as conn:
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
    return recomendaciones

def actualizar_inventario_manual(df_updated):
    with sqlite3.connect("inventario.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM inventario") 
        for _, row in df_updated.iterrows():
            cad_str = str(row["caducidad"]) if pd.notnull(row["caducidad"]) and str(row["caducidad"]) not in ["NaT", "", "None"] else None
            c.execute("INSERT INTO inventario (producto, linea, cantidad, caducidad) VALUES (?, ?, ?, ?)", 
                      (row["producto"], row["linea"], row["cantidad"], cad_str))
        conn.commit()

# --- 3. INTERFAZ DE STREAMLIT ---
st.title("Proyectado de Pastelería")

tab1, tab2 = st.tabs(["⚙️ Ingresos e Inventario", "🛒 Ventas y Recomendaciones"])

with tab1:
    st.header("Ingreso Rápido de Pasteles")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        prod_ingreso = st.selectbox(
            "Selecciona el pastel a ingresar:", 
            options=list(PRODUCTOS.keys()),
            index=None,
            placeholder="Escribe o selecciona un pastel..."
        )
    with col2:
        cant_ingreso = st.number_input("Cantidad que ingresa:", min_value=1, step=1, value=1)
    
    if prod_ingreso:
        st.write(f"📅 **Asigna la caducidad para las {cant_ingreso} unidades:**")
        
        columnas_fechas = st.columns(4) 
        fechas_asignadas = []
        
        for i in range(cant_ingreso):
            with columnas_fechas[i % 4]: 
                fecha = st.date_input(f"Caducidad unidad {i+1}", key=f"date_{i}")
                fechas_asignadas.append(fecha)
                
        if st.button("➕ Añadir al Inventario", type="primary"):
            procesar_ingreso(prod_ingreso, PRODUCTOS[prod_ingreso], fechas_asignadas)
            st.session_state["mensaje_exito"] = f"Se agregaron correctamente {cant_ingreso} unidades de {prod_ingreso}."
            st.rerun()
    else:
        st.info("👆 Selecciona un pastel para habilitar el registro de fechas.")

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
            "id": None, 
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
                    st.session_state["mensaje_exito"] = f"Venta registrada. Se descontó 1 unidad de {producto_a_vender}."
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
        
