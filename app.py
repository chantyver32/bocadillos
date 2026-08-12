import re
import sqlite3
import urllib.parse
from datetime import datetime, date

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from streamlit_mic_recorder import speech_to_text


# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================

st.set_page_config(
    page_title="Control de Stock",
    page_icon="📦",
    layout="centered"
)

DB_NAME = "inventario_bocadillos.db"


# ==========================================
# EMPAQUES
# ==========================================

EMPAQUES = {
    "Cubiletes": {
        "categoria": "Dulce",
        "piezas_x_paq": 16
    },
    "Tutis": {
        "categoria": "Dulce",
        "piezas_x_paq": 27
    },
    "Volován de Jamón": {
        "categoria": "Salado",
        "piezas_x_paq": 9
    },
    "Volován de Cochinita": {
        "categoria": "Salado",
        "piezas_x_paq": 9
    },
    "Volován de Picadillo": {
        "categoria": "Salado",
        "piezas_x_paq": 9
    },
    "Volován de Pierna": {
        "categoria": "Salado",
        "piezas_x_paq": 9
    },
    "Chorizo Hojaldrado": {
        "categoria": "Salado",
        "piezas_x_paq": 20
    },
    "Salchicha Hojaldrada": {
        "categoria": "Salado",
        "piezas_x_paq": 20
    },
    "Hojaldra Jamón": {
        "categoria": "Dulce - Salado",
        "piezas_x_paq": 48
    },
}


# ==========================================
# FUNCIONES DE FECHA Y HORA
# ==========================================

def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fecha_hoy():
    return date.today().strftime("%Y-%m-%d")


# ==========================================
# BASE DE DATOS
# ==========================================

def init_db():

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # USUARIOS
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    c.execute("""
        INSERT OR IGNORE INTO usuarios
        (username, password)
        VALUES ('admin', 'admin')
    """)

    # ENTRADAS
    c.execute("""
        CREATE TABLE IF NOT EXISTS entradas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            paquetes INTEGER,
            piezas_totales INTEGER,
            fecha_caducidad TEXT,
            fecha_registro TEXT
        )
    """)

    # HORNEADO
    c.execute("""
        CREATE TABLE IF NOT EXISTS horneado (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            paquetes INTEGER,
            piezas_totales INTEGER,
            fecha_hora TEXT
        )
    """)

    # COCA COLA
    c.execute("""
        CREATE TABLE IF NOT EXISTS cocacola (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            cantidad INTEGER,
            fecha_caducidad TEXT,
            fecha_registro TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ==========================================
# STOCK ACTUAL
# ==========================================

def calcular_stock_actual():

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    stock = {}

    for prod in EMPAQUES.keys():

        c.execute("""
            SELECT SUM(piezas_totales)
            FROM entradas
            WHERE producto = ?
        """, (prod,))

        entradas_pz = c.fetchone()[0] or 0

        c.execute("""
            SELECT SUM(piezas_totales)
            FROM horneado
            WHERE producto = ?
        """, (prod,))

        salidas_pz = c.fetchone()[0] or 0

        piezas_disp = entradas_pz - salidas_pz

        pz_x_paq = EMPAQUES[prod]["piezas_x_paq"]

        paq_disp = piezas_disp // pz_x_paq
        pz_sueltas = piezas_disp % pz_x_paq

        stock[prod] = {
            "paquetes": paq_disp,
            "piezas_sueltas": pz_sueltas,
            "piezas_totales": piezas_disp
        }

    conn.close()

    return stock


# ==========================================
# LÍNEA DEL PRODUCTO
# ==========================================

def obtener_linea(producto):

    categoria = EMPAQUES.get(producto, {}).get(
        "categoria",
        ""
    )

    if producto == "Hojaldra Jamón":
        return "S"

    if "Dulce" in categoria:
        return "D"

    return "S"


# ==========================================
# GENERAR IMAGEN DEL REPORTE
# ==========================================

def generar_plantilla_bocadillos(datos, fecha_actualizacion):

    width = 900
    header_height = 130
    table_header_height = 45
    row_height = 55

    total_height = (
        header_height
        + table_header_height
        + (len(datos) * row_height)
    )

    img = Image.new(
        "RGB",
        (width, total_height),
        color=(255, 253, 251)
    )

    draw = ImageDraw.Draw(img)

    WINE = (128, 21, 43)
    WINE_LIGHT = (160, 40, 70)
    TEXT_DARK = (40, 40, 40)
    WHITE = (255, 255, 255)
    ROW_ALT = (253, 243, 243)
    LINE_COLOR = (235, 220, 225)

    def get_font(names, size):

        for name in names:

            try:
                return ImageFont.truetype(
                    name,
                    size
                )
            except:
                continue

        return ImageFont.load_default()

    font_title = get_font(
        [
            "DejaVuSans-Bold.ttf",
            "arialbd.ttf",
            "Helvetica-Bold.ttf"
        ],
        42
    )

    font_sub = get_font(
        [
            "DejaVuSans.ttf",
            "arial.ttf",
            "Helvetica.ttf"
        ],
        15
    )

    font_th = get_font(
        [
            "DejaVuSans-Bold.ttf",
            "arialbd.ttf",
            "Helvetica-Bold.ttf"
        ],
        13
    )

    font_td = get_font(
        [
            "DejaVuSans.ttf",
            "arial.ttf",
            "Helvetica.ttf"
        ],
        15
    )

    font_badge = get_font(
        [
            "DejaVuSans-Bold.ttf",
            "arialbd.ttf",
            "Helvetica-Bold.ttf"
        ],
        11
    )

    font_logo1 = get_font(
        [
            "DejaVuSerif-BoldItalic.ttf",
            "georgiai.ttf",
            "Times-BoldItalic.ttf"
        ],
        28
    )

    font_logo2 = get_font(
        [
            "DejaVuSans.ttf",
            "arial.ttf",
            "Helvetica.ttf"
        ],
        14
    )

    # ==========================================
    # ENCABEZADO
    # ==========================================

    draw.text(
        (width // 2, 35),
        "BOCADILLOS",
        fill=WINE,
        font=font_title,
        anchor="mm"
    )

    draw.text(
        (width // 2, 80),
        f"ACTUALIZADO AL {fecha_actualizacion}",
        fill=TEXT_DARK,
        font=font_sub,
        anchor="mm"
    )

    draw.text(
        (width - 30, 40),
        "Champlitte",
        fill=WINE,
        font=font_logo1,
        anchor="rm"
    )

    draw.text(
        (width - 30, 70),
        "Pastelería",
        fill=WINE_LIGHT,
        font=font_logo2,
        anchor="rm"
    )

    # ==========================================
    # ENCABEZADO TABLA
    # ==========================================

    y = header_height

    draw.rectangle(
        [
            0,
            y,
            width,
            y + table_header_height
        ],
        fill=WINE
    )

    col_prod = 200
    col_linea = 520
    col_cant = 680
    col_piezas = 820

    draw.text(
        (col_prod, y + 22),
        "PRODUCTO",
        fill=WHITE,
        font=font_th,
        anchor="mm"
    )

    draw.text(
        (col_linea, y + 22),
        "LÍNEA",
        fill=WHITE,
        font=font_th,
        anchor="mm"
    )

    draw.text(
        (col_cant, y + 22),
        "CANTIDAD",
        fill=WHITE,
        font=font_th,
        anchor="mm"
    )

    draw.text(
        (col_piezas, y + 22),
        "PIEZAS",
        fill=WHITE,
        font=font_th,
        anchor="mm"
    )

    y += table_header_height

    # ==========================================
    # FILAS
    # ==========================================

    for i, item in enumerate(datos):

        bg_color = (
            WHITE
            if i % 2 == 0
            else ROW_ALT
        )

        draw.rectangle(
            [
                0,
                y,
                width,
                y + row_height
            ],
            fill=bg_color
        )

        # Líneas
        draw.line(
            [420, y, 420, y + row_height],
            fill=LINE_COLOR,
            width=1
        )

        draw.line(
            [600, y, 600, y + row_height],
            fill=LINE_COLOR,
            width=1
        )

        draw.line(
            [750, y, 750, y + row_height],
            fill=LINE_COLOR,
            width=1
        )

        # Producto
        draw.text(
            (30, y + row_height // 2),
            str(item.get("producto", "")),
            fill=TEXT_DARK,
            font=font_td,
            anchor="lm"
        )

        # Línea
        linea = str(item.get("linea", "S"))

        if linea == "D":
            badge_bg = (252, 230, 230)
            badge_text = WINE
        else:
            badge_bg = WINE
            badge_text = WHITE

        badge_w = 130
        badge_h = 26

        badge_x = col_linea - badge_w // 2
        badge_y = (
            y
            + row_height // 2
            - badge_h // 2
        )

        draw.rounded_rectangle(
            [
                badge_x,
                badge_y,
                badge_x + badge_w,
                badge_y + badge_h
            ],
            radius=13,
            fill=badge_bg
        )

        draw.text(
            (
                col_linea,
                y + row_height // 2
            ),
            f"LÍNEA {linea}",
            fill=badge_text,
            font=font_badge,
            anchor="mm"
        )

        # Cantidad
        draw.text(
            (
                col_cant,
                y + row_height // 2
            ),
            str(item.get("cantidad", "")),
            fill=TEXT_DARK,
            font=font_th,
            anchor="mm"
        )

        # Piezas
        piezas = item.get("piezas", "-")

        if piezas is None or piezas == "":
            piezas = "-"

        draw.text(
            (
                col_piezas,
                y + row_height // 2
            ),
            str(piezas),
            fill=TEXT_DARK,
            font=font_th,
            anchor="mm"
        )

        draw.line(
            [
                0,
                y + row_height,
                width,
                y + row_height
            ],
            fill=LINE_COLOR,
            width=1
        )

        y += row_height

    img.save("reporte_plantilla.png")

    return "reporte_plantilla.png"


# ==========================================
# EXTRACCIÓN DE VOZ
# ==========================================

def extraer_datos_voz(texto):

    if not texto:
        return None, None, "Paquetes"

    texto_norm = (
        texto
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )

    prod_encontrado = None

    for prod in EMPAQUES.keys():

        prod_norm = (
            prod
            .lower()
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )

        if prod_norm in texto_norm:
            prod_encontrado = prod
            break

    cant_encontrada = None

    numeros_digitos = re.findall(
        r"\d+",
        texto
    )

    if numeros_digitos:

        cant_encontrada = int(
            numeros_digitos[0]
        )

    else:

        mapa_numeros = {

            "un": 1,
            "uno": 1,
            "una": 1,
            "dos": 2,
            "tres": 3,
            "cuatro": 4,
            "cinco": 5,
            "seis": 6,
            "siete": 7,
            "ocho": 8,
            "nueve": 9,
            "diez": 10,
            "once": 11,
            "doce": 12,
            "trece": 13,
            "catorce": 14,
            "quince": 15,
            "dieciseis": 16,
            "dieciséis": 16,
            "veinte": 20,
            "treinta": 30,
            "cuarenta": 40,
            "cincuenta": 50
        }

        for palabra, valor in mapa_numeros.items():

            if re.search(
                rf"\b{palabra}\b",
                texto_norm
            ):
                cant_encontrada = valor
                break

    unidad_encontrada = "Paquetes"

    if re.search(
        r"\bpieza[s]?\b",
        texto_norm
    ):
        unidad_encontrada = "Piezas"

    elif re.search(
        r"\bpaquete[s]?\b",
        texto_norm
    ):
        unidad_encontrada = "Paquetes"

    return (
        prod_encontrado,
        cant_encontrada,
        unidad_encontrada
    )


# ==========================================
# DIÁLOGO VOZ ENTRADA
# ==========================================

@st.dialog("🎙️ Confirmar datos de Entrada")
def dialog_procesar_voz_entrada():

    texto = st.session_state.dictado_entrada

    st.write(
        f"**El sistema escuchó:** *'{texto}'*"
    )

    st.divider()

    (
        prod_encontrado,
        cant_encontrada,
        unidad_encontrada
    ) = extraer_datos_voz(texto)

    productos = list(EMPAQUES.keys())

    if prod_encontrado in productos:
        idx_prod = productos.index(
            prod_encontrado
        )
    else:
        idx_prod = 0

    prod_confirmado = st.selectbox(
        "Producto detectado:",
        productos,
        index=idx_prod,
        key="voz_prod_ent"
    )

    col_u, col_c = st.columns(2)

    with col_u:

        unidad_confirmada = st.radio(
            "Unidad:",
            ["Paquetes", "Piezas"],
            index=(
                0
                if unidad_encontrada == "Paquetes"
                else 1
            ),
            key="rad_ent"
        )

    with col_c:

        cant_confirmada = st.number_input(
            "Cantidad detectada:",
            min_value=1,
            step=1,
            value=(
                cant_encontrada
                if cant_encontrada
                else 1
            ),
            key="num_ent"
        )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "✅ Autocompletar",
            use_container_width=True
        ):

            st.session_state[
                "auto_ent_prod"
            ] = prod_confirmado

            if unidad_confirmada == "Paquetes":

                st.session_state[
                    "auto_ent_paq"
                ] = cant_confirmada

                st.session_state[
                    "auto_ent_pz"
                ] = 0

            else:

                st.session_state[
                    "auto_ent_paq"
                ] = 0

                st.session_state[
                    "auto_ent_pz"
                ] = cant_confirmada

            del st.session_state[
                "dictado_entrada"
            ]

            st.rerun()

    with col2:

        if st.button(
            "❌ Cancelar",
            use_container_width=True
        ):

            del st.session_state[
                "dictado_entrada"
            ]

            st.rerun()


# ==========================================
# DIÁLOGO VOZ HORNEADO
# ==========================================

@st.dialog("🎙️ Confirmar datos de Horneado")
def dialog_procesar_voz_horneado():

    texto = st.session_state.dictado_horneado

    st.write(
        f"**El sistema escuchó:** *'{texto}'*"
    )

    st.divider()

    (
        prod_encontrado,
        cant_encontrada,
        unidad_encontrada
    ) = extraer_datos_voz(texto)

    productos = list(EMPAQUES.keys())

    if prod_encontrado in productos:
        idx_prod = productos.index(
            prod_encontrado
        )
    else:
        idx_prod = 0

    prod_confirmado = st.selectbox(
        "Producto detectado:",
        productos,
        index=idx_prod,
        key="sel_horn"
    )

    col_u, col_c = st.columns(2)

    with col_u:

        unidad_confirmada = st.radio(
            "Unidad:",
            ["Paquetes", "Piezas"],
            index=(
                0
                if unidad_encontrada == "Paquetes"
                else 1
            ),
            key="rad_horn"
        )

    with col_c:

        cant_confirmada = st.number_input(
            "Cantidad detectada:",
            min_value=1,
            step=1,
            value=(
                cant_encontrada
                if cant_encontrada
                else 1
            ),
            key="num_horn"
        )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "✅ Autocompletar",
            use_container_width=True
        ):

            st.session_state[
                "auto_horn_prod"
            ] = prod_confirmado

            if unidad_confirmada == "Paquetes":

                st.session_state[
                    "auto_horn_paq"
                ] = cant_confirmada

                st.session_state[
                    "auto_horn_pz"
                ] = 0

            else:

                st.session_state[
                    "auto_horn_paq"
                ] = 0

                st.session_state[
                    "auto_horn_pz"
                ] = cant_confirmada

            del st.session_state[
                "dictado_horneado"
            ]

            st.rerun()

    with col2:

        if st.button(
            "❌ Cancelar",
            use_container_width=True
        ):

            del st.session_state[
                "dictado_horneado"
            ]

            st.rerun()


# ==========================================
# CONFIRMAR ENTRADA
# ==========================================

@st.dialog("Confirmar Entrada de Mercancía")
def dialog_confirmar_entrada(
    producto,
    paquetes,
    piezas
):

    total_piezas = (
        paquetes
        * EMPAQUES[producto]["piezas_x_paq"]
        + piezas
    )

    fecha_registro = ahora()

    st.write(
        f"**Producto:** {producto}"
    )

    st.write(
        f"**Paquetes:** {paquetes}"
    )

    st.write(
        f"**Piezas:** {piezas}"
    )

    st.write(
        f"**Total:** {total_piezas} piezas"
    )

    st.write(
        f"**Fecha de registro:** {fecha_registro}"
    )

    st.info(
        "La fecha de caducidad se establecerá "
        "automáticamente con la fecha de registro."
    )

    if st.button(
        "✅ Confirmar y Guardar",
        use_container_width=True
    ):

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("""
            INSERT INTO entradas
            (
                producto,
                paquetes,
                piezas_totales,
                fecha_caducidad,
                fecha_registro
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            producto,
            paquetes,
            total_piezas,
            fecha_registro,
            fecha_registro
        ))

        conn.commit()
        conn.close()

        claves = [
            "prod_sel",
            "cant_paq",
            "cant_piezas",
            "auto_ent_prod",
            "auto_ent_paq",
            "auto_ent_pz"
        ]

        for key in claves:

            if key in st.session_state:
                del st.session_state[key]

        st.success(
            "✅ Entrada guardada exitosamente."
        )

        st.rerun()


# ==========================================
# CONFIRMAR HORNEADO
# ==========================================

@st.dialog("Confirmar Horneado")
def dialog_confirmar_horneado(
    producto,
    paquetes,
    piezas
):

    total_piezas = (
      
