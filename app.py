import streamlit as st

# 1. Definimos cuántas piezas trae cada caja exactamente
PIEZAS_POR_CAJA = {
    "Cubilete": 16,
    "Tuti": 27,
    "Volovanes (Pierna, Picadillo, Jamón, Cochinita)": 9,
    "Chorizo y Salchicha": 20,
    "Hojaldra Jamón": 48
}

# Simulamos tu stock actual (en piezas individuales crudas)
if "stock_piezas" not in st.session_state:
    st.session_state.stock_piezas = {
        "Cubilete": 160,  
        "Tuti": 135,
        "Volovanes (Pierna, Picadillo, Jamón, Cochinita)": 90,
        "Chorizo y Salchicha": 100,
        "Hojaldra Jamón": 96
    }

st.header("📦 Registro de Horneo por Cajas")

st.write("### Stock actual (En piezas):")
st.write(st.session_state.stock_piezas)
st.divider()

# 2. Ahora los inputs son para CAJAS (van de 1 en 1)
st.subheader("¿Cuántas CAJAS vas a hornear?")

col1, col2 = st.columns(2)
with col1:
    cajas_cubilete = st.number_input("Cajas de Cubiletes", min_value=0, step=1)
    cajas_tuti = st.number_input("Cajas de Tutis", min_value=0, step=1)
    cajas_volovan = st.number_input("Cajas de Volovanes", min_value=0, step=1)

with col2:
    cajas_chorizo = st.number_input("Cajas de Chorizo/Salchicha", min_value=0, step=1)
    cajas_hojaldra = st.number_input("Cajas de Hojaldra Jamón", min_value=0, step=1)

# 3. Al presionar el botón, hacemos la multiplicación y la resta
if st.button("Restar Cajas del Stock"):
    
    # Multiplicamos el número de cajas ingresadas por la capacidad de cada una
    resta_cubilete = cajas_cubilete * PIEZAS_POR_CAJA["Cubilete"]
    resta_tuti = cajas_tuti * PIEZAS_POR_CAJA["Tuti"]
    resta_volovan = cajas_volovan * PIEZAS_POR_CAJA["Volovanes (Pierna, Picadillo, Jamón, Cochinita)"]
    resta_chorizo = cajas_chorizo * PIEZAS_POR_CAJA["Chorizo y Salchicha"]
    resta_hojaldra = cajas_hojaldra * PIEZAS_POR_CAJA["Hojaldra Jamón"]
    
    # Se le resta al stock total de piezas
    st.session_state.stock_piezas["Cubilete"] -= resta_cubilete
    st.session_state.stock_piezas["Tuti"] -= resta_tuti
    st.session_state.stock_piezas["Volovanes (Pierna, Picadillo, Jamón, Cochinita)"] -= resta_volovan
    st.session_state.stock_piezas["Chorizo y Salchicha"] -= resta_chorizo
    st.session_state.stock_piezas["Hojaldra Jamón"] -= resta_hojaldra
    
    st.success("✅ ¡Stock actualizado correctamente!")
    
    st.write("### Nuevo Stock (En piezas):")
    st.write(st.session_state.stock_piezas)
