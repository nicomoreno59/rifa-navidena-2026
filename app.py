
import streamlit as st
import requests
from pathlib import Path
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image, ImageDraw

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================
st.set_page_config(
    page_title="Rifa Navideña 2026",
    page_icon="🎄",
    layout="wide"
)

PRECIO_PUESTO = 20000
TABLA = "rifa_navidena"
IMAGEN = Path("rifa_original.png")

ESTADOS = ["Disponible", "Vendido", "Apartado"]
PAGOS = ["Pendiente", "Pagado"]

# ============================================================
# ESTILOS
# ============================================================
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
div.stButton > button {
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONEXIÓN A SUPABASE
# ============================================================
def config():
    try:
        url = str(
            st.secrets["SUPABASE_URL"]
        ).strip().rstrip("/")

        key = str(
            st.secrets["SUPABASE_KEY"]
        ).strip()

        if not url.startswith("https://") or not key:
            raise ValueError("Configuración inválida")

        return url, key

    except Exception:
        st.error(
            "Falta configurar SUPABASE_URL "
            "y SUPABASE_KEY en Streamlit Secrets."
        )
        st.stop()


BASE_URL, API_KEY = config()

SESSION = requests.Session()
SESSION.headers.update({
    "apikey": API_KEY,
    "Content-Type": "application/json",
})


def solicitar(metodo, endpoint, params=None, json_data=None):
    url = f"{BASE_URL}/rest/v1/{endpoint}"

    try:
        respuesta = SESSION.request(
            method=metodo,
            url=url,
            params=params,
            json=json_data,
            timeout=20
        )

        if respuesta.status_code >= 400:
            st.error(
                f"Error de Supabase "
                f"({respuesta.status_code}): "
                f"{respuesta.text[:300]}"
            )
            st.stop()

        if respuesta.text and "application/json" in (
            respuesta.headers.get("Content-Type", "")
        ):
            return respuesta.json()

        return None

    except requests.RequestException as error:
        st.error(f"Error de conexión: {error}")
        st.stop()


# ============================================================
# BASE DE DATOS
# ============================================================
def registro_vacio(numero):
    return {
        "numero": numero,
        "estado": "Disponible",
        "comprador": "",
        "telefono": "",
        "pago": "Pendiente",
        "valor_pagado": 0
    }


def listar():
    datos = solicitar(
        "GET",
        TABLA,
        params={
            "select": (
                "numero,estado,comprador,telefono,"
                "pago,valor_pagado"
            ),
            "order": "numero.asc"
        }
    )

    registros = {}

    for item in datos or []:
        numero = int(item["numero"])

        registros[numero] = {
            "numero": numero,
            "estado": item.get("estado", "Disponible"),
            "comprador": item.get("comprador") or "",
            "telefono": item.get("telefono") or "",
            "pago": item.get("pago", "Pendiente"),
            "valor_pagado": int(
                item.get("valor_pagado") or 0
            )
        }

    for numero in range(100):
        if numero not in registros:
            registros[numero] = registro_vacio(numero)

    return registros


def actualizar_numero(
    numero,
    estado,
    comprador,
    telefono,
    pago,
    valor_pagado
):
    if estado == "Disponible":
        datos = {
            "estado": "Disponible",
            "comprador": "",
            "telefono": "",
            "pago": "Pendiente",
            "valor_pagado": 0
        }
    else:
        datos = {
            "estado": estado,
            "comprador": comprador.strip(),
            "telefono": telefono.strip(),
            "pago": pago,
            "valor_pagado": int(valor_pagado)
        }

    datos["fecha_actualizacion"] = (
        datetime.now(timezone.utc).isoformat()
    )

    solicitar(
        "PATCH",
        TABLA,
        params={"numero": f"eq.{int(numero)}"},
        json_data=datos
    )


# ============================================================
# DIBUJAR ÁRBOL DE NAVIDAD
# ============================================================
def dibujar_arbol(dibujo, cx, cy, escala=1):
    """
    Dibuja un árbol navideño sobre un número vendido.
    No necesita fuentes ni archivos adicionales.
    """

    def punto(x, y):
        return (
            round(cx + x * escala),
            round(cy + y * escala)
        )

    # Contorno blanco para distinguirlo del fondo
    dibujo.polygon(
        [
            punto(0, -19),
            punto(-18, 10),
            punto(-11, 10),
            punto(-11, 16),
            punto(11, 16),
            punto(11, 10),
            punto(18, 10)
        ],
        fill=(255, 255, 255, 245)
    )

    # Tronco
    dibujo.rectangle(
        [
            punto(-4, 8),
            punto(4, 18)
        ],
        fill=(124, 65, 29, 255)
    )

    # Parte inferior del árbol
    dibujo.polygon(
        [
            punto(0, -5),
            punto(-15, 12),
            punto(15, 12)
        ],
        fill=(0, 115, 43, 255)
    )

    # Parte central
    dibujo.polygon(
        [
            punto(0, -12),
            punto(-12, 5),
            punto(12, 5)
        ],
        fill=(0, 145, 52, 255)
    )

    # Parte superior
    dibujo.polygon(
        [
            punto(0, -19),
            punto(-9, -3),
            punto(9, -3)
        ],
        fill=(0, 170, 68, 255)
    )

    # Estrella dorada
    estrella = [
        (0, -23), (2, -19),
        (6, -18), (3, -15),
        (4, -11), (0, -13),
        (-4, -11), (-3, -15),
        (-6, -18), (-2, -19)
    ]

    dibujo.polygon(
        [punto(x, y) for x, y in estrella],
        fill=(255, 213, 0, 255)
    )

    # Bolitas navideñas
    adornos = [
        (-5, -2, (255, 45, 45, 255)),
        (5, 1, (255, 213, 0, 255)),
        (-7, 8, (255, 213, 0, 255)),
        (7, 9, (255, 45, 45, 255)),
    ]

    for x, y, color in adornos:
        px, py = punto(x, y)
        radio = max(2, round(2 * escala))

        dibujo.ellipse(
            (
                px - radio,
                py - radio,
                px + radio,
                py + radio
            ),
            fill=color
        )


# ============================================================
# GENERADOR DE IMAGEN ACTUALIZADA
# ============================================================
def generar_imagen_rifa(registros):
    if not IMAGEN.exists():
        return None

    imagen = Image.open(IMAGEN).convert("RGBA")
    ancho, alto = imagen.size

    capa = Image.new(
        "RGBA",
        imagen.size,
        (0, 0, 0, 0)
    )

    dibujo = ImageDraw.Draw(capa)

    # Coordenadas de referencia de la imagen
    x_inicial = 160
    y_inicial = 360
    salto_x = 49.7
    salto_y = 55.5

    sx = ancho / 720
    sy = alto / 1037

    for numero in range(100):
        estado = registros[numero]["estado"]

        if estado == "Disponible":
            continue

        fila = numero // 10
        columna = numero % 10

        cx = (x_inicial + columna * salto_x) * sx
        cy = (y_inicial + fila * salto_y) * sy

        if estado == "Vendido":
            dibujar_arbol(
                dibujo,
                cx,
                cy,
                escala=min(sx, sy)
            )

        elif estado == "Apartado":
            radio = 17 * sx
            grosor = max(3, round(5 * sx))

            dibujo.ellipse(
                (
                    cx - radio,
                    cy - radio,
                    cx + radio,
                    cy + radio
                ),
                outline=(255, 200, 0, 255),
                width=grosor
            )

    resultado = Image.alpha_composite(
        imagen,
        capa
    ).convert("RGB")

    archivo = BytesIO()
    resultado.save(archivo, format="PNG")

    return archivo.getvalue()


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def formato_dinero(valor):
    return f"${int(valor):,}".replace(",", ".")


def emoji_estado(estado):
    if estado == "Vendido":
        return "🎄"
    elif estado == "Apartado":
        return "🟡"
    return "🟢"


# ============================================================
# ESTADO DE LA INTERFAZ
# ============================================================
if "numero_activo" not in st.session_state:
    st.session_state.numero_activo = None


# ============================================================
# CARGAR REGISTROS
# ============================================================
registros = listar()

vendidos = sum(
    r["estado"] == "Vendido"
    for r in registros.values()
)

apartados = sum(
    r["estado"] == "Apartado"
    for r in registros.values()
)

disponibles = sum(
    r["estado"] == "Disponible"
    for r in registros.values()
)

recaudado = sum(
    r["valor_pagado"]
    for r in registros.values()
)

pendiente = sum(
    max(PRECIO_PUESTO - r["valor_pagado"], 0)
    for r in registros.values()
    if r["estado"] in ("Vendido", "Apartado")
)

imagen_actualizada = generar_imagen_rifa(registros)

# ============================================================
# ENCABEZADO
# ============================================================
st.title("🎄 Rifa Navideña 2026")

st.markdown(
    "**Premio:** $1.000.000 en efectivo  •  "
    "**Puesto:** $20.000  •  "
    "**Sorteo:** 19 de diciembre de 2026"
)

with st.expander("🎁 Ver imagen original de la rifa"):
    if IMAGEN.exists():
        st.image(
            str(IMAGEN),
            width=420
        )


# ============================================================
# IMAGEN PARA WHATSAPP
# ============================================================
st.subheader("📲 Imagen actualizada para WhatsApp")

st.caption(
    "🎄 Árbol navideño = Vendido  |  "
    "🟡 Círculo amarillo = Apartado"
)

col_imagen, col_descarga = st.columns([2, 1])

with col_imagen:
    if imagen_actualizada is not None:
        st.image(
            imagen_actualizada,
            caption="Imagen actualizada de la rifa",
            width=420
        )
    else:
        st.warning(
            "No se encontró el archivo rifa_original.png"
        )

with col_descarga:
    if imagen_actualizada is not None:
        st.download_button(
            "📥 Descargar imagen actualizada",
            data=imagen_actualizada,
            file_name="Rifa_Navidena_2026.png",
            mime="image/png",
            use_container_width=True
        )

    st.info(
        "Descarga esta imagen para compartirla "
        "en tus estados de WhatsApp."
    )

st.divider()

# ============================================================
# ESTADÍSTICAS
# ============================================================
st.subheader("Administración de números")

c1, c2, c3, c4 = st.columns(4)

c1.metric("🎄 Vendidos", vendidos)
c2.metric("🟡 Apartados", apartados)
c3.metric("🟢 Disponibles", disponibles)
c4.metric("💵 Recaudado", formato_dinero(recaudado))

st.caption(
    f"Pendiente por cobrar: "
    f"**{formato_dinero(pendiente)}**"
)

if st.button("🔄 Actualizar información"):
    st.rerun()


# ============================================================
# BUSCADOR Y FILTROS
# ============================================================
st.markdown("### 🔎 Buscar números")

filtro = st.radio(
    "Filtrar por estado",
    ["Todos", "Disponible", "Vendido", "Apartado"],
    horizontal=True
)

busqueda = st.text_input(
    "Buscar número del 00 al 99",
    placeholder="Ejemplo: 07"
)

numeros_visibles = []

for numero in range(100):
    reg = registros[numero]

    if filtro != "Todos" and reg["estado"] != filtro:
        continue

    if busqueda.strip():
        if f"{numero:02d}" != busqueda.strip().zfill(2):
            continue

    numeros_visibles.append(numero)


# ============================================================
# TABLERO DE NÚMEROS
# ============================================================
st.markdown("### 🎟️ Números de la rifa")

st.caption(
    "🟢 Disponible  •  🎄 Vendido  •  🟡 Apartado"
)

for inicio in range(0, len(numeros_visibles), 10):
    grupo = numeros_visibles[inicio:inicio + 10]
    columnas = st.columns(10)

    for indice, numero in enumerate(grupo):
        reg = registros[numero]

        etiqueta = (
            f"{emoji_estado(reg['estado'])} "
            f"{numero:02d}"
        )

        with columnas[indice]:
            if st.button(
                etiqueta,
                key=f"numero_{numero}",
                use_container_width=True
            ):
                st.session_state.numero_activo = numero
                st.rerun()


# ============================================================
# FORMULARIO DEL NÚMERO SELECCIONADO
# ============================================================
if st.session_state.numero_activo is not None:
    numero = st.session_state.numero_activo
    reg = registros[numero]

    st.divider()
    st.subheader(f"📝 Número {numero:02d}")

    with st.form(f"formulario_{numero}"):

        estado = st.selectbox(
            "Estado del número",
            ESTADOS,
            index=ESTADOS.index(reg["estado"])
        )

        comprador = st.text_input(
            "Nombre del comprador",
            value=reg["comprador"]
        )

        telefono = st.text_input(
            "Teléfono",
            value=reg["telefono"]
        )

        pago = st.selectbox(
            "Estado del pago",
            PAGOS,
            index=PAGOS.index(reg["pago"])
        )

        valor_pagado = st.number_input(
            "Valor abonado (COP)",
            min_value=0,
            max_value=PRECIO_PUESTO,
            value=int(reg["valor_pagado"]),
            step=1000
        )

        col1, col2, col3 = st.columns(3)

        guardar = col1.form_submit_button(
            "💾 Guardar",
            use_container_width=True
        )

        liberar = col2.form_submit_button(
            "♻️ Liberar",
            use_container_width=True
        )

        cerrar = col3.form_submit_button(
            "✖️ Cerrar",
            use_container_width=True
        )

    if guardar:
        if estado != "Disponible" and not comprador.strip():
            st.warning(
                "Debes escribir el nombre del comprador."
            )
        else:
            actualizar_numero(
                numero,
                estado,
                comprador,
                telefono,
                pago,
                valor_pagado
            )

            st.session_state.numero_activo = None
            st.rerun()

    if liberar:
        actualizar_numero(
            numero,
            "Disponible",
            "",
            "",
            "Pendiente",
            0
        )

        st.session_state.numero_activo = None
        st.rerun()

    if cerrar:
        st.session_state.numero_activo = None
        st.rerun()


# ============================================================
# RESUMEN DE COMPRADORES
# ============================================================
st.divider()

with st.expander("📋 Ver compradores registrados"):
    encontrados = False

    for numero in range(100):
        reg = registros[numero]

        if reg["estado"] == "Disponible":
            continue

        encontrados = True

        st.write(
            f"**{numero:02d}** · "
            f"{reg['estado']} · "
            f"{reg['comprador']} · "
            f"{reg['telefono'] or 'Sin teléfono'} · "
            f"{reg['pago']} · "
            f"{formato_dinero(reg['valor_pagado'])}"
        )

    if not encontrados:
        st.info("Todavía no hay compradores registrados.")

st.divider()

st.caption(
    "Los registros se guardan en Supabase. "
    "La imagen original permanece intacta. "
    "Sin contraseña, cualquiera que tenga el enlace "
    "de administración puede consultar y modificar los datos."
)
