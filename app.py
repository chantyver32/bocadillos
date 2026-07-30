import streamlit as st
import math

# 1. Configuración de piezas por caja
PIEZAS_POR_CAJA = {
    "Cubilete": 16,
    "Tuti": 27,
    "Salchicha y Chorizo": 20,
    "Hojaldra de Jamón": 48,
    "Volovanes (Todos)": 9
}

st.header("🥐 Champlitte: Control de Horneo y Cajas")

st.subheader("Registro de Horneo")

# 2. Entradas de horneo con sus reglas específicas
col1, col2 = st.columns(2)

with col1:
    # Cubilete: 16 a fuerza (usamos step=16 para obligar a que sean múltiplos de 16)
    horneo_cubilete = st.number_input("Cubiletes (Lotes de 16 a fuerza)", min_value=0, step=16)
    
    # Tuti: de a 9 o por pieza (dejamos step=1 pero ponemos una nota)
    horneo_tuti = st.number_input("Tutis (De a 9 o por pieza)", min_value=0, step=1)
    
    # Volovanes: por pieza
    horneo_volovan = st.number_input("Volovanes (Por pieza)", min_value=0, step=1)

with col2:
    # Salchichas y chorizos: por pieza
    horneo_salchicha = st.number_input("Salchichas y Chorizos (Por pieza)", min_value=0, step=1)
    
    # Hojaldra jamón: por pieza
    horneo_hojaldra = st.number_input("Hojaldras de Jamón (Por pieza)", min_value=0, step=1)

st.divider()

# 3. Cálculo de cajas necesarias según lo horneado
st.subheader("📦 Cálculo de Cajas")

def calcular_cajas(piezas, tipo_pan):
    capacidad = PIEZAS_POR_CAJA[tipo_pan]
    cajas_completas = piezas // capacidad
    sobrantes = piezas % capacidad
    return cajas_completas, sobrantes

# Ejemplo de mostrar resultados si se ingresaron cantidades
if horneo_cubilete > 0:
    cajas, sobran = calcular_cajas(horneo_cubilete, "Cubilete")
    st.write(f"**Cubiletes:** {cajas} caja(s) completa(s) de 16 pz.")

if horneo_tuti > 0:
    cajas, sobran = calcular_cajas(horneo_tuti, "Tuti")
    st.write(f"**Tutis:** {cajas} caja(s) de 27 pz. (Sobran {sobran} pz.)")
    
if horneo_volovan > 0:
    cajas, sobran = calcular_cajas(horneo_volovan, "Volovanes (Todos)")
    st.write(f"**Volovanes:** {cajas} caja(s) de 9 pz. (Sobran {sobran} pz.)")

if horneo_hojaldra > 0:
    cajas, sobran = calcular_cajas(horneo_hojaldra, "Hojaldra de Jamón")
    st.write(f"**Hojaldras:** {cajas} caja(s) de 48 pz. (Sobran {sobran} pz.)")

if horneo_salchicha > 0:
    cajas, sobran = calcular_cajas(horneo_salchicha, "Salchicha y Chorizo")
    st.write(f"**Salchicha/Chorizo:** {cajas} caja(s) de 20 pz. (Sobran {sobran} pz.)")
