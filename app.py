"""Rifa Navideña 2026 — aplicación Streamlit con persistencia Supabase."""
from pathlib import Path
import requests
import streamlit as st

PRECIO = 20_000
TABLA = "rifa_navidena"
IMAGEN = Path(__file__).with_name("rifa_original.png")

st.set_page_config(page_title="Rifa Navideña 2026", page_icon="🎄", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1150px; padding-top: 1.5rem;}
[data-testid="stMetric"] {background: #f5f7f7; border-radius: 12px; padding: 12px;}
@media (prefers-color-scheme: dark) {[data-testid="stMetric"] {background: #20252c;}}
div[data-testid="stButton"] button {min-height: 39px;}
</style>
""", unsafe_allow_html=True)


def config():
    try:
        url = str(st.secrets["SUPABASE_URL"]).strip().rstrip("/")
        key = str(st.secrets["SUPABASE_KEY"]).strip()
        if not url.startswith("https://") or not key:
            raise ValueError("URL o clave incorrectas")
        return url, key
    except (KeyError, FileNotFoundError, ValueError):
        st.error("Falta configurar SUPABASE_URL y SUPABASE_KEY en los Secrets de Streamlit Cloud.")
        st.stop()


BASE_URL, API_KEY = config()
SESSION = requests.Session()
SESSION.headers.update({
    "apikey": API_KEY,
    "Content-Type": "application/json",
})



def solicitar(metodo, url, **kwargs):
    try:
        resp = SESSION.request(metodo, url, timeout=20, **kwargs)
        resp.raise_for_status()
        if resp.content:
            return resp.json()
        return None
    except requests.RequestException as err:
        st.error("No fue posible comunicarse con Supabase. Comprueba los Secrets y los permisos de la tabla.")
        # No mostramos la respuesta completa porque podría contener detalles sensibles.
        st.stop()


def listar():
    datos = solicitar("GET", f"{BASE_URL}/rest/v1/{TABLA}", params={
        "select": "numero,estado,comprador,telefono,pago,valor_pagado,fecha_actualizacion",
        "order": "numero.asc",
        "limit": "100",
    })
    if len(datos) != 100:
        st.error(f"Se encontraron {len(datos)} registros; se esperaban 100. Revisa la tabla y sus permisos en Supabase.")
        st.stop()
    return {int(r["numero"]): r for r in datos}


def guardar(numero, datos):
    headers = {"Prefer": "return=representation"}
    resultado = solicitar("PATCH", f"{BASE_URL}/rest/v1/{TABLA}",
        params={"numero": f"eq.{numero}", "select": "numero"},
        json=datos, headers=headers)
    return bool(resultado)


def formato_moneda(valor):
    return "$" + f"{int(valor):,}".replace(",", ".")


st.title("🎄 Rifa Navideña 2026")
st.caption("Premio: $1.000.000 en efectivo · Puesto: $20.000 · Sorteo: 19 de diciembre de 2026")

with st.expander("🎁 Ver imagen original de la rifa", expanded=False):
    # Mostramos el archivo original, sin alterar sus píxeles ni su contenido.
    st.image(str(IMAGEN), caption="Imagen original de la rifa", width=520)

encabezado_izq, encabezado_der = st.columns([4, 1])
with encabezado_izq:
    st.subheader("Administración de números")
with encabezado_der:
    if st.button("🔄 Actualizar", use_container_width=True):
        st.rerun()

registros = listar()
vendidos = sum(r["estado"] == "Vendido" for r in registros.values())
apartados = sum(r["estado"] == "Apartado" for r in registros.values())
disponibles = 100 - vendidos - apartados
recaudado = sum(int(r.get("valor_pagado") or 0) for r in registros.values())
pendiente = sum(PRECIO - int(r.get("valor_pagado") or 0)
                for r in registros.values() if r["estado"] != "Disponible")

m1, m2, m3, m4 = st.columns(4)
m1.metric("🔴 Vendidos", vendidos)
m2.metric("🟡 Apartados", apartados)
m3.metric("🟢 Disponibles", disponibles)
m4.metric("💵 Recaudado", formato_moneda(recaudado))
st.caption(f"Pendiente por cobrar en números vendidos o apartados: **{formato_moneda(pendiente)}**. El recaudo corresponde a los abonos registrados.")

filtro = st.radio("Filtrar", ["Todos", "Disponible", "Vendido", "Apartado"], horizontal=True)
busqueda = st.text_input("🔎 Buscar número (00–99)", placeholder="Ejemplo: 07")
st.caption("🟢 Disponible  ·  🔴 Vendido  ·  🟡 Apartado. Toca un número para editarlo.")

if "seleccion" not in st.session_state:
    st.session_state.seleccion = None

busqueda_num = None
if busqueda.strip():
    if not busqueda.strip().isdigit() or not 0 <= int(busqueda.strip()) <= 99:
        st.warning("Escribe un número entre 00 y 99.")
    else:
        busqueda_num = int(busqueda.strip())

# Renderizamos filas de 10 para conservar la distribución 00–99 de la imagen.
for inicio in range(0, 100, 10):
    columnas = st.columns(10, gap="small")
    for i, c in enumerate(columnas):
        n = inicio + i
        r = registros[n]
        oculto = (filtro != "Todos" and r["estado"] != filtro) or (busqueda_num is not None and n != busqueda_num)
        icono = {"Disponible": "🟢", "Vendido": "🔴", "Apartado": "🟡"}[r["estado"]]
        with c:
            if oculto:
                st.write(" ")
            else:
                if st.button(f"{icono} {n:02d}", key=f"n{n}", use_container_width=True):
                    st.session_state.seleccion = n
                    st.rerun()

if busqueda_num is not None and st.session_state.seleccion is None:
    if st.button(f"Editar número {busqueda_num:02d}"):
        st.session_state.seleccion = busqueda_num
        st.rerun()

seleccion = st.session_state.seleccion
if seleccion is not None:
    r = registros[seleccion]
    st.divider()
    st.subheader(f"📝 Número {seleccion:02d}")
    with st.form(f"editar_{seleccion}"):
        estado = st.selectbox("Estado", ["Disponible", "Vendido", "Apartado"],
                              index=["Disponible", "Vendido", "Apartado"].index(r["estado"]))
        comprador = st.text_input("Nombre del comprador", value=r.get("comprador") or "", max_chars=120)
        telefono = st.text_input("Teléfono (opcional)", value=r.get("telefono") or "", max_chars=30)
        pago = st.selectbox("Estado del pago", ["Pendiente", "Pagado"],
                            index=["Pendiente", "Pagado"].index(r.get("pago") or "Pendiente"))
        valor = st.number_input("Valor abonado (COP)", min_value=0, max_value=PRECIO, step=1000,
                                value=int(r.get("valor_pagado") or 0))
        st.caption("Para marcar un número como disponible, se eliminarán sus datos de comprador y pago.")
        aceptar = st.form_submit_button("💾 Guardar cambios", type="primary", use_container_width=True)
    if aceptar:
        if estado != "Disponible" and not comprador.strip():
            st.error("Introduce el nombre del comprador para vender o apartar un número.")
        elif estado != "Disponible" and pago == "Pagado" and valor != PRECIO:
            st.error("Si el pago está marcado como Pagado, el valor abonado debe ser $20.000.")
        elif estado != "Disponible" and pago == "Pendiente" and valor == PRECIO:
            st.error("Si ya pagó los $20.000, selecciona Pagado.")
        else:
            if estado == "Disponible":
                nuevo = {"estado": "Disponible", "comprador": "", "telefono": "", "pago": "Pendiente", "valor_pagado": 0}
            else:
                nuevo = {"estado": estado, "comprador": comprador.strip(), "telefono": telefono.strip(),
                         "pago": pago, "valor_pagado": int(valor)}
            from datetime import datetime, timezone
            nuevo["fecha_actualizacion"] = datetime.now(timezone.utc).isoformat()
            if guardar(seleccion, nuevo):
                st.session_state.seleccion = None
                st.toast(f"Número {seleccion:02d} guardado correctamente", icon="✅")
                st.rerun()
            else:
                st.error("Supabase no actualizó este registro.")
    if st.button("Cerrar edición"):
        st.session_state.seleccion = None
        st.rerun()

with st.expander("📋 Resumen de números registrados"):
    import pandas as pd
    filas = [{"Número": f"{n:02d}", "Estado": r["estado"], "Comprador": r.get("comprador", ""),
              "Teléfono": r.get("telefono", ""), "Pago": r.get("pago", "Pendiente"),
              "Abonado": formato_moneda(r.get("valor_pagado") or 0)}
             for n, r in registros.items() if r["estado"] != "Disponible"]
    if filas:
        st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)
    else:
        st.info("Todavía no hay números vendidos ni apartados.")

st.divider()
st.caption("Los cambios se guardan en Supabase. Usa Actualizar para ver cambios hechos desde otros dispositivos. ⚠️ Sin contraseña, cualquier persona con el enlace de esta página podrá consultar y modificar la información: comparte el enlace solo con personas de confianza.")
