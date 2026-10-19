
import streamlit as st
import requests
import base64

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

IMAGEN = (
    Path(__file__).resolve().parent
    / "rifa_original.png"
)

ESTADOS = [
    "Disponible",
    "Vendido"
]

PAGOS = [
    "Pendiente",
    "Pagado"
]


# ============================================================
# ESTILOS
# CINCO NÚMEROS POR FILA EN CELULAR
# ============================================================

st.markdown("""
<style>

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

/* Tablero de cinco columnas */

.st-key-tablero_cinco [data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
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
    padding: 0.3rem 0.1rem !important;
    white-space: nowrap !important;
    font-size: clamp(
        0.68rem,
        2.6vw,
        0.96rem
    ) !important;
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

            raise ValueError(
                "Credenciales inválidas"
            )

        return url, clave

    except (
        KeyError,
        ValueError,
        FileNotFoundError
    ):

        st.error(
            "Configura SUPABASE_URL y "
            "SUPABASE_KEY en Streamlit Secrets."
        )

        st.stop()


BASE_URL, API_KEY = configurar_supabase()

SESSION = requests.Session()

SESSION.headers.update({
    "apikey": API_KEY,
    "Content-Type": "application/json"
})


def solicitar(
    metodo,
    params=None,
    json_data=None
):

    try:

        encabezados = {}

        if metodo == "PATCH":

            encabezados["Prefer"] = (
                "return=representation"
            )

        respuesta = SESSION.request(
            metodo,
            f"{BASE_URL}/rest/v1/{TABLA}",
            params=params,
            json=json_data,
            headers=encabezados,
            timeout=20
        )

        respuesta.raise_for_status()

        if (
            respuesta.text
            and "application/json"
            in respuesta.headers.get(
                "Content-Type", ""
            )
        ):

            return respuesta.json()

        return None

    except requests.HTTPError as error:

        codigo = (
            error.response.status_code
            if error.response is not None
            else "desconocido"
        )

        st.error(
            f"Error de Supabase ({codigo}). "
            "Comprueba los permisos y la conexión."
        )

        st.stop()

    except requests.RequestException as error:

        st.error(
            "No fue posible conectarse "
            "con Supabase."
        )

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
        params={
            "select": (
                "numero,estado,comprador,"
                "telefono,pago,valor_pagado"
            ),
            "order": "numero.asc"
        }
    )

    registros = {
        numero: registro_vacio(numero)
        for numero in range(100)
    }

    for item in datos or []:

        numero = int(item["numero"])

        if 0 <= numero <= 99:

            registros[numero] = {
                "numero": numero,
                "estado": (
                    item.get("estado")
                    or "Disponible"
                ),
                "comprador": (
                    item.get("comprador")
                    or ""
                ),
                "telefono": (
                    item.get("telefono")
                    or ""
                ),
                "pago": (
                    item.get("pago")
                    or "Pendiente"
                ),
                "valor_pagado": int(
                    item.get("valor_pagado")
                    or 0
                )
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
        "valor_pagado": int(
            valor_pagado
        ),
        "fecha_actualizacion": (
            datetime.now(
                timezone.utc
            ).isoformat()
        )
    }

    actualizados = solicitar(
        "PATCH",
        params={
            "numero": f"eq.{numero}"
        },
        json_data=datos
    )

    if not actualizados:

        st.error(
            "Supabase no confirmó "
            "la actualización."
        )

        st.stop()


# ============================================================
# DIBUJAR ÁRBOL NAVIDEÑO
# ============================================================

def dibujar_arbol(
    dibujo,
    cx,
    cy,
    escala=1
):

    def punto(x, y):

        return (
            round(cx + x * escala),
            round(cy + y * escala)
        )

    # Contorno blanco

    dibujo.polygon(
        [
            punto(0, -20),
            punto(-18, 10),
            punto(-10, 10),
            punto(-10, 16),
            punto(10, 16),
            punto(10, 10),
            punto(18, 10)
        ],
        fill=(255, 255, 255, 250)
    )

    # Tronco

    dibujo.rectangle(
        [
            punto(-4, 8),
            punto(4, 18)
        ],
        fill=(125, 65, 28, 255)
    )

    # Parte inferior

    dibujo.polygon(
        [
            punto(0, -5),
            punto(-15, 12),
            punto(15, 12)
        ],
        fill=(0, 110, 45, 255)
    )

    # Parte central

    dibujo.polygon(
        [
            punto(0, -12),
            punto(-12, 5),
            punto(12, 5)
        ],
        fill=(0, 142, 54, 255)
    )

    # Parte superior

    dibujo.polygon(
        [
            punto(0, -19),
            punto(-9, -3),
            punto(9, -3)
        ],
        fill=(0, 174, 66, 255)
    )

    # Estrella dorada

    dibujo.polygon(
        [
            punto(0, -24),
            punto(2, -20),
            punto(6, -19),
            punto(3, -16),
            punto(4, -12),
            punto(0, -14),
            punto(-4, -12),
            punto(-3, -16),
            punto(-6, -19),
            punto(-2, -20)
        ],
        fill=(255, 213, 0, 255)
    )

    # Adornos

    adornos = [
        (-5, -2, (255, 55, 55, 255)),
        (5, 1, (255, 218, 0, 255)),
        (-7, 8, (255, 218, 0, 255)),
        (7, 9, (255, 55, 55, 255))
    ]

    for x, y, color in adornos:

        px, py = punto(x, y)

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
# GENERAR IMAGEN ACTUALIZADA
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

    # Coordenadas para la imagen original
    # de referencia 720 x 1037.

    sx = ancho / 720
    sy = alto / 1037

    for numero in range(100):

        estado = registros[numero][
            "estado"
        ]

        if estado != "Vendido":

            continue

        fila, columna = divmod(
            numero,
            10
        )

        cx = (
            162 + columna * 50.4
        ) * sx

        cy = (
            362 + fila * 55.3
        ) * sy

        dibujar_arbol(
            dibujo,
            cx,
            cy,
            escala=min(sx, sy)
        )

    imagen = Image.alpha_composite(
        original,
        capa
    ).convert("RGB")

    archivo = BytesIO()

    imagen.save(
        archivo,
        format="PNG"
    )

    return archivo.getvalue()


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def dinero(valor):

    return f"${int(valor):,}".replace(
        ",", "."
    )


def icono(estado):

    if estado == "Vendido":
        return "🎄"

    if estado == "Disponible":
        return "🟢"

    return "⚪"


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

disponibles = sum(
    r["estado"] == "Disponible"
    for r in registros.values()
)

recaudado = sum(
    r["valor_pagado"]
    for r in registros.values()
    if r["estado"] == "Vendido"
)

pendiente = sum(
    max(
        PRECIO_PUESTO - r["valor_pagado"],
        0
    )
    for r in registros.values()
    if r["estado"] == "Vendido"
)

sin_clasificar = [
    r["numero"]
    for r in registros.values()
    if r["estado"] not in ESTADOS
]


# ============================================================
# ENCABEZADO
# ============================================================

st.title(
    "🎄 Rifa Navideña 2026"
)

st.markdown(
    "**Premio:** $1.000.000 en efectivo · "
    "**Puesto:** $20.000 · "
    "**Sorteo:** 19 de diciembre de 2026"
)


with st.expander(
    "🎁 Ver imagen original de la rifa"
):

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
    "🎄 Árbol de Navidad = Vendido · "
    "🟢 Sin marca = Disponible"
)

imagen_actualizada = generar_imagen_rifa(
    registros
)


if imagen_actualizada is not None:

    izquierda, derecha = st.columns(
        [2, 1]
    )

    # --------------------------------------------------------
    # VISTA PREVIA
    # --------------------------------------------------------

    with izquierda:

        st.image(
            imagen_actualizada,
            caption="Imagen actualizada de la rifa",
            use_container_width=True
        )

    # --------------------------------------------------------
    # DESCARGAR Y COMPARTIR
    # --------------------------------------------------------

    with derecha:

        # BOTÓN ORIGINAL DE DESCARGA

        st.download_button(
            "📥 Descargar imagen actualizada",
            data=imagen_actualizada,
            file_name=(
                "Rifa_Navidena_2026_Actualizada.png"
            ),
            mime="image/png",
            use_container_width=True
        )

        # ====================================================
        # NUEVO BOTÓN PARA COMPARTIR DESDE EL CELULAR
        # ====================================================

        imagen_base64 = base64.b64encode(
            imagen_actualizada
        ).decode("ascii")

        html_compartir = f"""
        <div style="
            width:100%;
            font-family:Arial,sans-serif;
        ">

            <button
                id="compartir-rifa"
                type="button"
                style="
                    width:100%;
                    background:#16803c;
                    color:white;
                    border:none;
                    border-radius:10px;
                    padding:14px 10px;
                    font-size:15px;
                    font-weight:600;
                    cursor:pointer;
                "
            >
                📲 Compartir o guardar en Fotos
            </button>

            <p
                id="mensaje-compartir"
                style="
                    color:#9ca3af;
                    font-size:13px;
                    line-height:1.5;
                    margin-top:10px;
                "
            >
                Abre las opciones del celular
                para compartir o guardar la imagen.
            </p>

        </div>

        <script>
        (() => {{

            const boton = document.getElementById(
                "compartir-rifa"
            );

            const mensaje = document.getElementById(
                "mensaje-compartir"
            );

            // Convertir PNG a archivo para compartir

            const datos = atob("{imagen_base64}");

            const bytes = new Uint8Array(
                datos.length
            );

            for (
                let i = 0;
                i < datos.length;
                i++
            ) {{
                bytes[i] = datos.charCodeAt(i);
            }}

            const archivo = new File(
                [bytes],
                "Rifa_Navidena_2026_Actualizada.png",
                {{
                    type: "image/png"
                }}
            );

            // Compartir con acción directa del usuario

            boton.addEventListener(
                "click",
                async () => {{

                    const compatible = (
                        typeof navigator.share === "function"
                        &&
                        typeof navigator.canShare === "function"
                        &&
                        navigator.canShare({{
                            files: [archivo]
                        }})
                    );

                    if (!compatible) {{

                        mensaje.textContent =
                            "Este navegador no permite " +
                            "compartir la imagen directamente. " +
                            "Usa Descargar imagen.";

                        return;
                    }}

                    try {{

                        await navigator.share({{
                            files: [archivo]
                        }});

                        mensaje.textContent =
                            "Puedes compartir o guardar " +
                            "la imagen desde el menú.";

                    }} catch (error) {{

                        if (
                            error.name === "AbortError"
                        ) {{
                            return;
                        }}

                        mensaje.textContent =
                            "No se pudo abrir el menú. " +
                            "Usa Descargar imagen.";

                    }}

                }}
            );

        }})();
        </script>
        """

        st.html(
            html_compartir,
            unsafe_allow_javascript=True
        )

        st.info(
            "Desde tu celular, toca Compartir "
            "y busca Guardar imagen, Fotos "
            "o WhatsApp."
        )

else:

    st.warning(
        "No se encontró el archivo "
        "rifa_original.png."
    )


st.divider()


# ============================================================
# ADMINISTRACIÓN Y ESTADÍSTICAS
# ============================================================

st.subheader(
    "Administración de números"
)

c1, c2, c3 = st.columns(3)

c1.metric(
    "🎄 Vendidos",
    vendidos
)

c2.metric(
    "🟢 Disponibles",
    disponibles
)

c3.metric(
    "💵 Recaudado",
    dinero(recaudado)
)

st.caption(
    f"💰 Pendiente por cobrar: "
    f"**{dinero(pendiente)}**"
)

if sin_clasificar:

    st.warning(
        "Hay números con estados antiguos. "
        "Actualízalos a Disponible o Vendido: "
        + ", ".join(
            f"{n:02d}"
            for n in sin_clasificar
        )
    )


if st.button(
    "🔄 Actualizar información"
):

    st.rerun()


# ============================================================
# BUSCADOR Y FILTROS
# ============================================================

st.markdown(
    "### 🔎 Buscar números"
)

filtro = st.radio(
    "Filtrar números",
    [
        "Todos",
        "Disponible",
        "Vendido"
    ],
    horizontal=True
)

busqueda = st.text_input(
    "Buscar número del 00 al 99",
    placeholder="Ejemplo: 07"
).strip()


numeros_visibles = []

for numero in range(100):

    registro = registros[numero]

    if (
        filtro != "Todos"
        and registro["estado"] != filtro
    ):

        continue

    if busqueda:

        if (
            f"{numero:02d}"
            != busqueda.zfill(2)
        ):

            continue

    numeros_visibles.append(
        numero
    )


# ============================================================
# TABLERO DE CINCO NÚMEROS POR FILA
# ============================================================

st.subheader(
    "🎟️ Números de la rifa"
)

st.caption(
    "🟢 Disponible · 🎄 Vendido"
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

            etiqueta = (
                f"{icono(estado)} {numero:02d}"
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
# FORMULARIO PARA REGISTRAR VENTAS
# ============================================================

if st.session_state.numero_activo is not None:

    numero = st.session_state.numero_activo

    registro = registros[numero]

    st.divider()

    st.subheader(
        f"📝 Número {numero:02d}"
    )

    indice_estado = (
        ESTADOS.index(registro["estado"])
        if registro["estado"] in ESTADOS
        else 0
    )

    with st.form(
        f"formulario_{numero}"
    ):

        estado = st.selectbox(
            "Estado del número",
            ESTADOS,
            index=indice_estado
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
            )
        )

        abonado = st.number_input(
            "Valor abonado (COP)",
            min_value=0,
            max_value=PRECIO_PUESTO,
            value=int(
                registro["valor_pagado"]
            ),
            step=1000
        )

        st.caption(
            "Al liberar un número se borran "
            "sus datos de comprador y pago."
        )

        c1, c2, c3 = st.columns(3)

        guardar = c1.form_submit_button(
            "💾 Guardar",
            use_container_width=True
        )

        liberar = c2.form_submit_button(
            "♻️ Liberar",
            use_container_width=True
        )

        cerrar = c3.form_submit_button(
            "✖️ Cerrar",
            use_container_width=True
        )

    # --------------------------------------------------------
    # GUARDAR
    # --------------------------------------------------------

    if guardar:

        if (
            estado == "Vendido"
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

    # --------------------------------------------------------
    # LIBERAR
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CERRAR
    # --------------------------------------------------------

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

    registrados = [
        r
        for r in registros.values()
        if r["estado"] == "Vendido"
    ]

    if not registrados:

        st.info(
            "Todavía no hay números vendidos."
        )

    for registro in registrados:

        st.write(
            f"**{registro['numero']:02d}** · "
            f"{registro['comprador']} · "
            f"{registro['telefono'] or 'Sin teléfono'} · "
            f"{registro['pago']} · "
            f"{dinero(registro['valor_pagado'])}"
        )


# ============================================================
# INFORMACIÓN FINAL
# ============================================================

st.divider()

st.caption(
    "Los registros se guardan en Supabase. "
    "Usa Actualizar para ver cambios "
    "realizados desde otros celulares. "
    "La imagen original permanece intacta."
)

st.caption(
    "⚠️ Sin contraseña, cualquier persona "
    "con el enlace puede consultar y "
    "modificar los registros de compradores."
)
