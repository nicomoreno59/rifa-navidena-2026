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
.metric-box {
    padding: 14px 18px;
    border-radius: 14px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
}
.small-note {
    font-size: 0.92rem;
    opacity: 0.85;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONEXIÓN A SUPABASE
# ============================================================
def config():
    try:
        url = str(st.secrets["SUPABASE_URL"]).strip().rstrip("/")
        key = str(st.secrets["SUPABASE_KEY"]).strip()

        if not url.startswith("https://") or not key:
            raise ValueError("SUPABASE_URL o SUPABASE_KEY inválidos.")

        return url, key

    except Exception:
        st.error("Falta configurar SUPABASE_URL y SUPABASE_KEY en los Secrets de Streamlit.")
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
        resp = SESSION.request(
            method=metodo,
            url=url,
            params=params,
            json=json_data,
            timeout=20
        )

        if resp.status_code >= 400:
            detalle = resp.text[:500] if resp.text else "Sin detalle"
            st.error(f"Error al comunicar con Supabase ({resp.status_code}): {detalle}")
            st.stop()

        if resp.text:
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return resp.json()

        return None

    except requests.RequestException as err:
        st.error(f"No fue posible comunicarse con Supabase: {err}")
        st.stop()


# ============================================================
# FUNCIONES DE DATOS
# ============================================================
def registro_vacio(numero):
    return {
        "numero": numero,
        "estado": "Disponible",
        "comprador": "",
        "telefono": "",
        "pago": "Pendiente",
        "valor_pagado": 0,
        "fecha_actualizacion": None
    }


def listar():
    datos = solicitar(
        "GET",
        TABLA,
        params={
            "select": "numero,estado,comprador,telefono,pago,valor_pagado,fecha_actualizacion",
            "order": "numero.asc"
        }
    )

    registros = {}

    for item in datos or []:
        numero = int(item["numero"])
        registros[numero] = {
            "numero": numero,
            "estado": item.get("estado", "Disponible"),
            "comprador": item.get("comprador", "") or "",
            "telefono": item.get("telefono", "") or "",
            "pago": item.get("pago", "Pendiente"),
            "valor_pagado": int(item.get("valor_pagado", 0) or 0),
            "fecha_actualizacion": item.get("fecha_actualizacion")
        }

    for numero in range(100):
        if numero not in registros:
            registros[numero] = registro_vacio(numero)

    return registros


def actualizar_numero(numero, estado, comprador, telefono, pago, valor_pagado):
    numero = int(numero)

    if estado == "Disponible":
        payload = {
            "estado": "Disponible",
            "comprador": "",
            "telefono": "",
            "pago": "Pendiente",
            "valor_pagado": 0,
            "fecha_actualizacion": datetime.now(timezone.utc).isoformat()
        }
    else:
        payload = {
            "estado": estado,
            "comprador": comprador.strip(),
            "telefono": telefono.strip(),
            "pago": pago,
            "valor_pagado": int(valor_pagado),
            "fecha_actualizacion": datetime.now(timezone.utc).isoformat()
        }

    solicitar(
        "PATCH",
        TABLA,
        params={"numero": f"eq.{numero}"},
        json_data=payload
    )


# ============================================================
# IMAGEN ACTUALIZADA PARA ESTADOS
# ============================================================
def generar_imagen_rifa(registros):
    if not IMAGEN.exists():
        return None

    imagen = Image.open(IMAGEN).convert("RGBA")
    ancho, alto = imagen.size

    capa = Image.new("RGBA", imagen.size, (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(capa)

    # Coordenadas ajustadas para TU imagen original (720x1037 aprox.)
    # Se escalan automáticamente si cambia el tamaño del archivo.
    x_inicial = 160
    y_inicial = 360
    salto_x = 49.7
    salto_y = 55.5
    radio = 17

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
        r = radio * sx
        grosor = max(4, int(5 * sx))

        if estado == "Vendido":
            color = (235, 35, 55, 235)

            dibujo.line(
                [(cx - r, cy - r), (cx + r, cy + r)],
                fill=color,
                width=grosor
            )
            dibujo.line(
                [(cx + r, cy - r), (cx - r, cy + r)],
                fill=color,
                width=grosor
            )

        elif estado == "Apartado":
            color = (255, 210, 40, 245)

            dibujo.ellipse(
                (cx - r, cy - r, cx + r, cy + r),
                outline=color,
                width=grosor
            )

    resultado = Image.alpha_composite(imagen, capa).convert("RGB")

    buffer = BytesIO()
    resultado.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# FUNCIONES DE APOYO
# ============================================================
def color_estado(estado):
    if estado == "Vendido":
        return "🔴"
    if estado == "Apartado":
        return "🟡"
    return "🟢"


def texto_estado_corto(estado):
    if estado == "Vendido":
        return "V"
    if estado == "Apartado":
        return "A"
    return "D"


def filtrar_registros(registros, filtro, busqueda):
    resultado = []

    for numero in range(100):
        reg = registros[numero]

        coincide_filtro = (
            filtro == "Todos" or reg["estado"] == filtro
        )

        coincide_busqueda = (
            not busqueda or f"{numero:02d}" == busqueda.strip()
        )

        if coincide_filtro and coincide_busqueda:
            resultado.append(numero)

    return resultado


# ============================================================
# ESTADO DE SESIÓN
# ============================================================
if "numero_activo" not in st.session_state:
    st.session_state.numero_activo = None


# ============================================================
# CARGAR DATOS
# ============================================================
registros = listar()

vendidos = sum(1 for r in registros.values() if r["estado"] == "Vendido")
apartados = sum(1 for r in registros.values() if r["estado"] == "Apartado")
disponibles = sum(1 for r in registros.values() if r["estado"] == "Disponible")
recaudado = sum(int(r["valor_pagado"]) for r in registros.values())

pendiente = 0
for r in registros.values():
    if r["estado"] in ("Vendido", "Apartado"):
        pendiente += max(PRECIO_PUESTO - int(r["valor_pagado"]), 0)

imagen_actualizada = generar_imagen_rifa(registros)

# ============================================================
# ENCABEZADO
# ============================================================
st.title("🎄 Rifa Navideña 2026")
st.markdown(
    f"**Premio:** `1.000.000 en efectivo`  •  **Puesto:** `{PRECIO_PUESTO:,.0f}`"
    .replace(",", ".")
    + " • **Sorteo:** 19 de diciembre de 2026"
)

with st.expander("🎁 Ver imagen original de la rifa"):
    if IMAGEN.exists():
        st.image(str(IMAGEN), caption="Imagen original de la rifa", use_container_width=False, width=420)
    else:
        st.warning("No se encontró el archivo `rifa_original.png`.")

# ============================================================
# IMAGEN ACTUALIZADA PARA PUBLICAR
# ============================================================
st.subheader("📲 Imagen actualizada para publicar")
st.caption("🔴 X roja = Vendido  |  🟡 Círculo amarillo = Apartado")

col_img1, col_img2 = st.columns([2, 1])

with col_img1:
    if imagen_actualizada is not None:
        st.image(
            imagen_actualizada,
            caption="Vista previa de la imagen actualizada",
            use_container_width=False,
            width=420
        )
    else:
        st.warning("No se pudo generar la imagen. Verifica que exista `rifa_original.png`.")

with col_img2:
    if imagen_actualizada is not None:
        st.download_button(
            label="📥 Descargar imagen actualizada",
            data=imagen_actualizada,
            file_name="Rifa_Navidena_2026_Actualizada.png",
            mime="image/png",
            use_container_width=True
        )
    st.info("Usa esta imagen para compartir la rifa en estados de WhatsApp.")

st.divider()

# ============================================================
# ADMINISTRACIÓN
# ============================================================
st.subheader("Administración de números")

col_a, col_b, col_c, col_d, col_e = st.columns([1, 1, 1, 1, 0.8])

with col_a:
    st.metric("🔴 Vendidos", vendidos)

with col_b:
    st.metric("🟡 Apartados", apartados)

with col_c:
    st.metric("🟢 Disponibles", disponibles)

with col_d:
    st.metric("💵 Recaudado", f"${recaudado:,.0f}".replace(",", "."))

with col_e:
    if st.button("🔄 Actualizar", use_container_width=True):
        st.rerun()

st.caption(
    f"Pendiente por cobrar en números vendidos o apartados: "
    f"**${pendiente:,.0f}**. El recaudo corresponde a los abonos registrados."
    .replace(",", ".")
)

# ============================================================
# FILTROS
# ============================================================
st.markdown("### Filtrar")

filtro = st.radio(
    "Estado",
    options=["Todos", "Disponible", "Vendido", "Apartado"],
    horizontal=True,
    label_visibility="collapsed"
)

busqueda = st.text_input(
    "🔎 Buscar número (00–99)",
    placeholder="Ejemplo: 07"
)

numeros_visibles = filtrar_registros(registros, filtro, busqueda)

st.caption("🟢 Disponible · 🔴 Vendido · 🟡 Apartado. Toca un número para editarlo.")

# ============================================================
# TABLERO 00 - 99
# ============================================================
columnas = st.columns(10)
contador_col = 0

for numero in numeros_visibles:
    reg = registros[numero]
    emoji = color_estado(reg["estado"])

    etiqueta = f"{emoji} {numero:02d}"

    with columnas[contador_col]:
        if st.button(etiqueta, key=f"btn_{numero}", use_container_width=True):
            st.session_state.numero_activo = numero
            st.rerun()

    contador_col += 1
    if contador_col == 10:
        columnas = st.columns(10)
        contador_col = 0

# ============================================================
# FORMULARIO DE EDICIÓN
# ============================================================
if st.session_state.numero_activo is not None:
    numero = st.session_state.numero_activo
    reg = registros[numero]

    st.markdown("---")
    st.subheader(f"📝 Número {numero:02d}")

    with st.form(f"form_numero_{numero}"):
        estado = st.selectbox(
            "Estado",
            options=ESTADOS,
            index=ESTADOS.index(reg["estado"])
        )

        comprador = st.text_input(
            "Nombre del comprador",
            value=reg["comprador"]
        )

        telefono = st.text_input(
            "Teléfono (opcional)",
            value=reg["telefono"]
        )

        pago = st.selectbox(
            "Estado del pago",
            options=PAGOS,
            index=PAGOS.index(reg["pago"]) if reg["pago"] in PAGOS else 0
        )

        valor_pagado = st.number_input(
            "Valor abonado (COP)",
            min_value=0,
            max_value=PRECIO_PUESTO,
            step=1000,
            value=int(reg["valor_pagado"])
        )

        st.caption("Si marcas el número como Disponible, se borrarán comprador, teléfono y pago.")

        col_g1, col_g2, col_g3 = st.columns(3)

        guardar = col_g1.form_submit_button("💾 Guardar cambios", use_container_width=True)
        liberar = col_g2.form_submit_button("♻️ Liberar número", use_container_width=True)
        cerrar = col_g3.form_submit_button("✖️ Cerrar", use_container_width=True)

    if cerrar:
        st.session_state.numero_activo = None
        st.rerun()

    if liberar:
        actualizar_numero(numero, "Disponible", "", "", "Pendiente", 0)
        st.success(f"El número {numero:02d} volvió a estar disponible.")
        st.session_state.numero_activo = None
        st.rerun()

    if guardar:
        if estado in ("Vendido", "Apartado") and not comprador.strip():
            st.warning("Debes escribir al menos el nombre del comprador.")
        else:
            actualizar_numero(numero, estado, comprador, telefono, pago, valor_pagado)
            st.success(f"Se guardó correctamente el número {numero:02d}.")
            st.session_state.numero_activo = numero
            st.rerun()

# ============================================================
# RESUMEN DE NÚMEROS REGISTRADOS
# ============================================================
st.markdown("---")
with st.expander("📋 Resumen de números registrados"):
    registrados = [
        r for r in registros.values()
        if r["estado"] in ("Vendido", "Apartado")
    ]

    if not registrados:
        st.info("Todavía no hay números vendidos ni apartados.")
    else:
        for r in registrados:
            numero_txt = f"{r['numero']:02d}"
            estado_txt = r["estado"]
            comprador_txt = r["comprador"] or "Sin nombre"
            telefono_txt = r["telefono"] or "Sin teléfono"
            pago_txt = r["pago"]
            valor_txt = f"${int(r['valor_pagado']):,}".replace(",", ".")

            st.write(
                f"**{numero_txt}** · {estado_txt} · {comprador_txt} · "
                f"{telefono_txt} · {pago_txt} · {valor_txt}"
            )

st.markdown("---")
st.caption(
    "Los cambios se guardan en Supabase. Usa Actualizar para ver cambios hechos desde otros dispositivos. "
    "⚠️ Sin contraseña, cualquier persona con el enlace de esta página podrá consultar y modificar la información: "
    "comparte el enlace solo con personas de confianza."
)
