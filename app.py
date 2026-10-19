
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
IMAGEN = Path(__file__).resolve().parent / "rifa_original.png"

ESTADOS = ["Disponible", "Vendido", "Apartado"]
PAGOS = ["Pendiente", "Pagado"]

# ============================================================
# ESTILOS: 5 NÚMEROS POR FILA EN CELULAR Y COMPUTADOR
# ============================================================
st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

/* Mantener cinco columnas en pantallas pequeñas */
.st-key-tablero_cinco [data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-wrap: nowrap !important;
    gap: 0.25rem !important;
}

.st-key-tablero_cinco [data-testid="stColumn"] {
    flex: 1 1 0% !important;
    width: 0 !important;
    min-width: 0 !important;
}

.st-key-tablero_cinco [data-testid="stButton"] {
    width: 100% !important;
}

.st-key-tablero_cinco [data-testid="stButton"] button {
    width: 100% !important;
    min-width: 0 !important;
    min-height: 2.65rem;
    white-space: nowrap !important;
    padding: 0.3rem 0.1rem !important;
    font-size: clamp(0.68rem, 2.6vw, 0.96rem) !important;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONEXIÓN A SUPABASE
# ============================================================
def configurar_supabase():
    try:
        url = str(
            st.secrets["SUPABASE_URL"]
        ).strip().rstrip("/")

        clave = str(
            st.secrets["SUPABASE_KEY"]
        ).strip()

        if not url.startswith("https://") or not clave:
            raise ValueError("Credenciales inválidas")

        return url, clave

    except (KeyError, ValueError, FileNotFoundError):
        st.error(
            "Configura SUPABASE_URL y SUPABASE_KEY "
            "en los Secrets de Streamlit."
        )
        st.stop()


BASE_URL, API_KEY = configurar_supabase()

SESSION = requests.Session()

SESSION.headers.update({
    "apikey": API_KEY,
    "Content-Type": "application/json"
})


def solicitar(metodo, params=None, json_data=None):
    try:
        respuesta = SESSION.request(
            metodo,
            f"{BASE_URL}/rest/v1/{TABLA}",
            params=params,
            json=json_data,
            timeout=20,
            headers={
                "Prefer": "return=representation"
            } if metodo == "PATCH" else None,
        )

        respuesta.raise_for_status()

        if (
            respuesta.text
            and "application/json"
            in respuesta.headers.get("Content-Type", "")
        ):
            return respuesta.json()

        return None

    except requests.HTTPError as exc:
        codigo = (
            exc.response.status_code
            if exc.response is not None
            else "desconocido"
        )

        st.error(
            f"Supabase devolvió un error ({codigo}). "
            "Revisa la conexión y los permisos."
        )
        st.stop()

    except requests.RequestException as exc:
        st.error(
            f"No fue posible conectarse con Supabase: {exc}"
        )
        st.stop()


# ============================================================
# REGISTROS
# ============================================================
def registro_vacio(numero):
    return {
        "numero": numero,
        "estado": "Disponible",
        "comprador": "",
        "telefono": "",
        "pago": "Pendiente",
        "valor_pagado": 0,
    }


def listar():
    datos = solicitar(
        "GET",
        params={
            "select": (
                "numero,estado,comprador,telefono,"
                "pago,valor_pagado"
            ),
            "order": "numero.asc",
        }
    )

    registros = {
        i: registro_vacio(i)
        for i in range(100)
    }

    for item in datos or []:
        numero = int(item["numero"])

        if 0 <= numero <= 99:
            registros[numero] = {
                "numero": numero,
                "estado": (
                    item.get("estado") or "Disponible"
                ),
                "comprador": (
                    item.get("comprador") or ""
                ),
                "telefono": (
                    item.get("telefono") or ""
                ),
                "pago": (
                    item.get("pago") or "Pendiente"
                ),
                "valor_pagado": int(
                    item.get("valor_pagado") or 0
                ),
            }

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
        comprador = ""
        telefono = ""
        pago = "Pendiente"
        valor_pagado = 0

    datos = {
        "estado": estado,
        "comprador": comprador.strip(),
        "telefono": telefono.strip(),
        "pago": pago,
        "valor_pagado": int(valor_pagado),
        "fecha_actualizacion": (
            datetime.now(timezone.utc).isoformat()
        ),
    }

    actualizados = solicitar(
        "PATCH",
        params={
            "numero": f"eq.{numero}"
        },
        json_data=datos,
    )

    if not actualizados:
        st.error(
            "Supabase no confirmó el cambio. "
            "No se modificó el tablero."
        )
        st.stop()


# ============================================================
# DIBUJAR ÁRBOL NAVIDEÑO EN LOS NÚMEROS VENDIDOS
# ============================================================
def dibujar_arbol(dibujo, cx, cy, escala=1):

    def p(x, y):
        return (
            round(cx + x * escala),
            round(cy + y * escala)
        )

    # Contorno blanco
    dibujo.polygon(
        [
            p(0, -20),
            p(-18, 10),
            p(-10, 10),
            p(-10, 16),
            p(10, 16),
            p(10, 10),
            p(18, 10)
        ],
        fill=(255, 255, 255, 250),
    )

    # Tronco
    dibujo.rectangle(
        [
            p(-4, 8),
            p(4, 18)
        ],
        fill=(125, 65, 28, 255)
    )

    # Parte inferior
    dibujo.polygon(
        [
            p(0, -5),
            p(-15, 12),
            p(15, 12)
        ],
        fill=(0, 110, 45, 255)
    )

    # Parte central
    dibujo.polygon(
        [
            p(0, -12),
            p(-12, 5),
            p(12, 5)
        ],
        fill=(0, 142, 54, 255)
    )

    # Parte superior
    dibujo.polygon(
        [
            p(0, -19),
            p(-9, -3),
            p(9, -3)
        ],
        fill=(0, 174, 66, 255)
    )

    # Estrella dorada
    dibujo.polygon(
        [
            p(0, -24),
            p(2, -20),
            p(6, -19),
            p(3, -16),
            p(4, -12),
            p(0, -14),
            p(-4, -12),
            p(-3, -16),
            p(-6, -19),
            p(-2, -20)
        ],
        fill=(255, 213, 0, 255)
    )

    # Decoraciones
    adornos = [
        (-5, -2, (255, 55, 55, 255)),
        (5, 1, (255, 218, 0, 255)),
        (-7, 8, (255, 218, 0, 255)),
        (7, 9, (255, 55, 55, 255)),
    ]

    for x, y, color in adornos:
        px, py = p(x, y)

        radio = max(
            1,
            round(2 * escala)
        )

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
# GENERAR IMAGEN ACTUALIZADA PARA WHATSAPP
# ============================================================
def generar_imagen_rifa(registros):

    if not IMAGEN.exists():
        return None

    original = Image.open(
        IMAGEN
    ).convert("RGBA")

    ancho, alto = original.size

    capa = Image.new(
        "RGBA",
        original.size,
        (0, 0, 0, 0)
    )

    dibujo = ImageDraw.Draw(capa)

    sx = ancho / 720
    sy = alto / 1037

    for numero in range(100):

        estado = registros[numero]["estado"]

        if estado == "Disponible":
            continue

        fila, columna = divmod(numero, 10)

        cx = (
            162 + columna * 50.4
        ) * sx

        cy = (
            362 + fila * 55.3
        ) * sy

        if estado == "Vendido":

            dibujar_arbol(
                dibujo,
                cx,
                cy,
                escala=min(sx, sy)
            )

        elif estado == "Apartado":

            radio = 17 * sx

            dibujo.ellipse(
                (
                    cx - radio,
                    cy - radio,
                    cx + radio,
                    cy + radio
                ),
                outline=(255, 203, 0, 255),
                width=max(
                    3,
                    round(5 * sx)
                ),
            )

    imagen = Image.alpha_composite(
        original,
        capa
    ).convert("RGB")

    buffer = BytesIO()

    imagen.save(
        buffer,
        format="PNG"
    )

    return buffer.getvalue()


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def dinero(valor):
    return f"${int(valor):,}".replace(",", ".")


def icono(estado):

    return {
        "Vendido": "🎄",
        "Apartado": "🟡"
    }.get(
        estado,
        "🟢"
    )


# ============================================================
# ESTADO DE LA PÁGINA
# ============================================================
if "numero_activo" not in st.session_state:
    st.session_state.numero_activo = None


# ============================================================
# CARGAR LOS REGISTROS DE SUPABASE
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
    max(
        PRECIO_PUESTO - r["valor_pagado"],
        0
    )
    for r in registros.values()
    if r["estado"] in ("Vendido", "Apartado")
)


# ============================================================
# ENCABEZADO
# ============================================================
st.title("🎄 Rifa Navideña 2026")

st.markdown(
    "**Premio:** $1.000.000 en efectivo · "
    "**Puesto:** $20.000 · "
    "**Sorteo:** 19 de diciembre de 2026"
)

with st.expander("🎁 Ver imagen original de la rifa"):

    if IMAGEN.exists():
        st.image(
            str(IMAGEN),
            width=420
        )


# ============================================================
# IMAGEN ACTUALIZADA PARA WHATSAPP
# ============================================================
st.subheader(
    "📲 Imagen actualizada para WhatsApp"
)

st.caption(
    "🎄 Árbol = Vendido · "
    "🟡 Círculo amarillo = Apartado"
)

imagen_actualizada = generar_imagen_rifa(
    registros
)

if imagen_actualizada is not None:

    izquierda, derecha = st.columns(
        [2, 1]
    )

    with izquierda:

        st.image(
            imagen_actualizada,
            caption="Vista previa para publicar",
            use_container_width=True
        )

    with derecha:

        st.download_button(
            "📥 Descargar imagen actualizada",
            data=imagen_actualizada,
            file_name=(
                "Rifa_Navidena_2026_Actualizada.png"
            ),
            mime="image/png",
            use_container_width=True,
        )

else:

    st.warning(
        "No se encontró rifa_original.png "
        "en el repositorio."
    )

st.divider()


# ============================================================
# ADMINISTRACIÓN Y ESTADÍSTICAS
# ============================================================
st.subheader(
    "Administración de números"
)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "🎄 Vendidos",
    vendidos
)

c2.metric(
    "🟡 Apartados",
    apartados
)

c3.metric(
    "🟢 Disponibles",
    disponibles
)

c4.metric(
    "💵 Recaudado",
    dinero(recaudado)
)

st.caption(
    f"Pendiente por cobrar: "
    f"**{dinero(pendiente)}**"
)

if st.button(
    "🔄 Actualizar información"
):
    st.rerun()


# ============================================================
# BUSCADOR Y FILTROS
# ============================================================
filtro = st.radio(
    "Filtrar números",
    [
        "Todos",
        "Disponible",
        "Vendido",
        "Apartado"
    ],
    horizontal=True,
)

busqueda = st.text_input(
    "🔎 Buscar número (00–99)",
    placeholder="Ejemplo: 07"
).strip()


numeros_visibles = []

for n in range(100):

    if (
        filtro != "Todos"
        and registros[n]["estado"] != filtro
    ):
        continue

    if (
        busqueda
        and f"{n:02d}" != busqueda.zfill(2)
    ):
        continue

    numeros_visibles.append(n)


# ============================================================
# TABLERO: SIEMPRE 5 NÚMEROS POR FILA
# INCLUSO EN CELULAR
# ============================================================
st.subheader(
    "🎟️ Números de la rifa"
)

st.caption(
    "🟢 Disponible · "
    "🎄 Vendido · "
    "🟡 Apartado"
)

with st.container(
    key="tablero_cinco"
):

    if not numeros_visibles:

        st.info(
            "No hay números que coincidan "
            "con la búsqueda."
        )

    for inicio in range(
        0,
        len(numeros_visibles),
        5
    ):

        grupo = numeros_visibles[
            inicio:inicio + 5
        ]

        columnas = st.columns(
            5,
            gap="small"
        )

        for indice, numero in enumerate(
            grupo
        ):

            estado = registros[numero][
                "estado"
            ]

            with columnas[indice]:

                if st.button(
                    f"{icono(estado)} {numero:02d}",
                    key=f"numero_{numero}",
                    use_container_width=True,
                ):

                    st.session_state.numero_activo = numero

                    st.rerun()


# ============================================================
# EDITAR O LIBERAR UN NÚMERO
# ============================================================
if st.session_state.numero_activo is not None:

    numero = st.session_state.numero_activo

    registro = registros[numero]

    st.divider()

    st.subheader(
        f"📝 Número {numero:02d}"
    )

    with st.form(
        f"formulario_{numero}"
    ):

        estado = st.selectbox(
            "Estado",
            ESTADOS,
            index=ESTADOS.index(
                registro["estado"]
            )
        )

        comprador = st.text_input(
            "Nombre del comprador",
            value=registro["comprador"]
        )

        telefono = st.text_input(
            "Teléfono (opcional)",
            value=registro["telefono"]
        )

        pago = st.selectbox(
            "Estado del pago",
            PAGOS,
            index=(
                PAGOS.index(registro["pago"])
                if registro["pago"] in PAGOS
                else 0
            ),
        )

        abonado = st.number_input(
            "Valor abonado (COP)",
            min_value=0,
            max_value=PRECIO_PUESTO,
            value=int(
                registro["valor_pagado"]
            ),
            step=1000,
        )

        st.caption(
            "Al liberar un número se borran "
            "sus datos de comprador y pago."
        )

        a, b, c = st.columns(3)

        guardar = a.form_submit_button(
            "💾 Guardar",
            use_container_width=True
        )

        liberar = b.form_submit_button(
            "♻️ Liberar",
            use_container_width=True
        )

        cerrar = c.form_submit_button(
            "✖️ Cerrar",
            use_container_width=True
        )

    if guardar:

        if (
            estado != "Disponible"
            and not comprador.strip()
        ):

            st.warning(
                "Escribe el nombre del comprador "
                "antes de guardar."
            )

        else:

            actualizar_numero(
                numero,
                estado,
                comprador,
                telefono,
                pago,
                abonado
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

with st.expander(
    "📋 Ver compradores registrados"
):

    ocupados = [
        r
        for r in registros.values()
        if r["estado"] != "Disponible"
    ]

    if not ocupados:

        st.info(
            "Todavía no hay compradores registrados."
        )

    for r in ocupados:

        st.write(
            f"**{r['numero']:02d}** · "
            f"{r['estado']} · "
            f"{r['comprador']} · "
            f"{r['telefono'] or 'Sin teléfono'} · "
            f"{r['pago']} · "
            f"{dinero(r['valor_pagado'])}"
        )


# ============================================================
# INFORMACIÓN FINAL
# ============================================================
st.caption(
    "Los cambios se guardan en Supabase. "
    "Usa Actualizar para ver modificaciones "
    "desde otros celulares. "
    "Sin contraseña, cualquier persona con "
    "el enlace puede consultar y modificar "
    "los registros."
)
