import sqlite3
import pandas as pd
import streamlit as st

# 1. Función para crear la base de datos y la tabla si no existen
def inicializar_bd():
    # Se conecta al archivo pasteleria.db (lo crea si no existe)
    conexion = sqlite3.connect('pasteleria.db')
    cursor = conexion.cursor()
    
    # Crea la estructura de la tabla
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio REAL NOT NULL
        )
    ''')
    conexion.commit()
    conexion.close()

# 2. Función para insertar los datos desde la interfaz
def guardar_producto(producto, cantidad, precio):
    conexion = sqlite3.connect('pasteleria.db')
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO inventario (producto, cantidad, precio) 
        VALUES (?, ?, ?)
    ''', (producto, cantidad, precio))
    conexion.commit()
    conexion.close()

# 3. Función para extraer los datos y mostrarlos
def obtener_datos():
    conexion = sqlite3.connect('pasteleria.db')
    # Usamos pandas para transformar la consulta SQL directamente en un DataFrame
    df = pd.read_sql('SELECT * FROM inventario', conexion)
    conexion.close()
    return df

# --- INTERFAZ GRÁFICA CON STREAMLIT ---

st.title("Control de Inventario")

# Ejecutamos la inicialización de la base de datos
inicializar_bd()

# Creamos un formulario para que los datos se envíen juntos al hacer clic
with st.form("formulario_ingreso"):
    st.subheader("Registrar nuevo ingreso")
    
    nombre_prod = st.text_input("Nombre del producto (ej. Harina, Pastel de chocolate)")
    cantidad_prod = st.number_input("Cantidad", min_value=1, step=1)
    precio_prod = st.number_input("Precio ($)", min_value=0.0, step=0.5)
    
    # Botón de envío
    enviado = st.form_submit_button("Guardar en Base de Datos")
    
    if enviado:
        if nombre_prod != "":
            guardar_producto(nombre_prod, cantidad_prod, precio_prod)
            st.success(f"¡'{nombre_prod}' se guardó correctamente!")
        else:
            st.error("Por favor, ingresa el nombre del producto.")

# Mostrar los datos guardados en tiempo real
st.divider()
st.subheader("Registros actuales en SQLite")

# Cargamos el DataFrame
df_inventario = obtener_datos()

if not df_inventario.empty:
    st.dataframe(df_inventario, use_container_width=True, hide_index=True)
else:
    st.info("La base de datos está vacía. Registra tu primer producto.")
