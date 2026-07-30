import streamlit as st

# 1. Simulamos tu inventario inicial (esto vendría de tu base de datos o archivo)
if "inventario" not in st.session_state:
    st.session_state.inventario = {
        "Cubilete": 160,          # Tienes 160 crudos
        "Tuti": 100,
        "Volovan": 50,
        "Salchicha_Chorizo": 80,
        "Hojaldra": 100
    }

st.header("🥐 Restar del Inventario")

# Mostramos el inventario actual
st.write("### Inventario Actual (Crudos):")
st.write(st.session_state.inventario)

st.divider()

# 2. Entradas de lo que vas a hornear hoy
st.subheader("¿Qué vas a hornear?")
horneo_cubilete = st.number_input("Cubiletes a hornear (múltiplos de 16)", min_value=0, step=16)
horneo_volovan = st.number_input("Volovanes a hornear (por pieza)", min_value=0, step=1)

# 3. Botón para aplicar la resta
if st.button("Registrar y Restar del Inventario"):
    
    # Verificamos que haya suficiente inventario antes de restar
    if horneo_cubilete > st.session_state.inventario["Cubilete"]:
        st.error("⚠️ No tienes suficientes Cubiletes en el inventario.")
    elif horneo_volovan > st.session_state.inventario["Volovan"]:
        st.error("⚠️ No tienes suficientes Volovanes en el inventario.")
    else:
        # A LA CANTIDAD SE LE RESTA LO HORNEADO
        st.session_state.inventario["Cubilete"] -= horneo_cubilete
        st.session_state.inventario["Volovan"] -= horneo_volovan
        
        st.success("✅ ¡Cantidades restadas con éxito!")
        
        # Volvemos a mostrar el inventario actualizado
        st.write("### Nuevo Inventario:")
        st.write(st.session_state.inventario)
