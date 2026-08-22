import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime, timedelta
import plotly.express as px

# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Asignador Arbitral de Baloncesto",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# ESTILOS
# ============================================================

st.markdown("""
<style>

    /* Fondo general */
    .stApp {
        background-color: #f5f7fa;
    }

    /* Barra lateral */
    section[data-testid="stSidebar"] {
        background-color: #111827;
        min-width: 245px;
        max-width: 245px;
    }

    section[data-testid="stSidebar"] * {
        color: #f9fafb;
    }

    /* Título sidebar */
    .sidebar-title {
        font-size: 18px;
        font-weight: 700;
        color: white;
        margin-bottom: 8px;
    }

    .sidebar-subtitle {
        font-size: 12px;
        color: #9ca3af;
        margin-bottom: 12px;
    }

    /* Radio buttons compactos */
    div[role="radiogroup"] {
        gap: 2px !important;
    }

    div[role="radiogroup"] > label {
        padding: 4px 7px !important;
        margin: 0 !important;
        min-height: 30px !important;
        border-radius: 5px;
    }

    div[role="radiogroup"] > label:hover {
        background-color: #1f2937;
    }

    /* Upload */
    [data-testid="stFileUploader"] {
        background-color: #1f2937;
        border-radius: 8px;
        padding: 8px;
    }

    [data-testid="stFileUploader"] button {
        background-color: #2563eb !important;
        color: white !important;
        border: none !important;
    }

    [data-testid="stFileUploader"] button:hover {
        background-color: #1d4ed8 !important;
        color: white !important;
    }

    /* Títulos */
    h1 {
        color: #111827;
    }

    h2, h3 {
        color: #1f2937;
    }

    /* Tarjetas KPI */
    .kpi-card {
        background: white;
        padding: 16px;
        border-radius: 10px;
        border-left: 5px solid #2563eb;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        min-height: 105px;
    }

    .kpi-title {
        font-size: 13px;
        color: #6b7280;
        margin-bottom: 5px;
    }

    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        color: #111827;
    }

    /* Alertas */
    .alert-card {
        padding: 12px 15px;
        border-radius: 8px;
        margin-bottom: 8px;
        font-size: 14px;
    }

    .alert-red {
        background-color: #fee2e2;
        border-left: 5px solid #dc2626;
        color: #991b1b;
    }

    .alert-yellow {
        background-color: #fef3c7;
        border-left: 5px solid #d97706;
        color: #92400e;
    }

    .alert-green {
        background-color: #dcfce7;
        border-left: 5px solid #16a34a;
        color: #166534;
    }

    /* Separadores */
    .section-title {
        border-bottom: 2px solid #e5e7eb;
        padding-bottom: 7px;
        margin-top: 15px;
        margin-bottom: 15px;
    }

</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNCIONES DE CARGA
# ============================================================

@st.cache_data(show_spinner=False)
def cargar_excel(archivo):

    excel = pd.ExcelFile(archivo)

    hojas_requeridas = [
        "Arbitros",
        "Disponibilidad_Arbitros",
        "Config_Eventos",
        "Programacion_Partidos"
    ]

    datos = {}

    for hoja in hojas_requeridas:
        if hoja in excel.sheet_names:
            datos[hoja] = pd.read_excel(
                archivo,
                sheet_name=hoja
            )

    return datos


# ============================================================
# NORMALIZACIÓN
# ============================================================

@st.cache_data(show_spinner=False)
def normalizar_datos(datos):

    resultado = {}

    for nombre, df in datos.items():

        df = df.copy()

        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
        )

        resultado[nombre] = df

    return resultado


# ============================================================
# PREPARAR INFORMACIÓN
# ============================================================

@st.cache_data(show_spinner=False)
def preparar_programacion(datos):

    arbitros = datos.get("arbitros", pd.DataFrame())
    disponibilidad = datos.get(
        "disponibilidad_arbitros",
        pd.DataFrame()
    )
    configuracion = datos.get(
        "config_eventos",
        pd.DataFrame()
    )
    partidos = datos.get(
        "programacion_partidos",
        pd.DataFrame()
    )

    # --------------------------------------------------------
    # Unificar configuración con partidos
    # --------------------------------------------------------

    if not partidos.empty and not configuracion.empty:

        columnas_config = [
            "id_config_evento",
            "cant_arbitros_campo",
            "cat_req_arb_1",
            "cat_req_arb_2",
            "cat_req_arb_3",
            "cant_oficiales_mesa",
            "cat_req_mesa_1",
            "cat_req_mesa_2"
        ]

        columnas_config = [
            c for c in columnas_config
            if c in configuracion.columns
        ]

        partidos = partidos.merge(
            configuracion[columnas_config],
            on="id_config_evento",
            how="left",
            suffixes=("", "_config")
        )

    return {
        "arbitros": arbitros,
        "disponibilidad": disponibilidad,
        "configuracion": configuracion,
        "partidos": partidos
    }


# ============================================================
# MÉTRICAS
# ============================================================

@st.cache_data(show_spinner=False)
def calcular_metricas(datos):

    arbitros = datos["arbitros"]
    partidos = datos["partidos"]

    total_arbitros = len(arbitros)
    total_partidos = len(partidos)

    if "rol_arbitral" in arbitros.columns:
        hibridos = (
            arbitros["rol_arbitral"]
            .astype(str)
            .str.lower()
            .str.contains("hibrido")
            .sum()
        )
    else:
        hibridos = 0

    if "fecha" in partidos.columns:
        fechas = pd.to_datetime(
            partidos["fecha"],
            errors="coerce"
        )

        dias = fechas.dt.date.nunique()

    else:
        dias = 0

    return {
        "arbitros": total_arbitros,
        "partidos": total_partidos,
        "hibridos": hibridos,
        "dias": dias
    }


# ============================================================
# DETECCIÓN DE ALERTAS
# ============================================================

@st.cache_data(show_spinner=False)
def analizar_alertas(datos):

    arbitros = datos["arbitros"]
    disponibilidad = datos["disponibilidad"]
    partidos = datos["partidos"]

    alertas = []

    if partidos.empty:
        return pd.DataFrame(
            columns=[
                "tipo",
                "severidad",
                "mensaje"
            ]
        )

    # --------------------------------------------------------
    # Verificar disponibilidad básica
    # --------------------------------------------------------

    if disponibilidad.empty:

        alertas.append({
            "tipo": "Disponibilidad",
            "severidad": "CRÍTICA",
            "mensaje":
                "No se encontró información de disponibilidad."
        })

    # --------------------------------------------------------
    # Verificar partidos sin datos
    # --------------------------------------------------------

    for _, partido in partidos.iterrows():

        campos = [
            partido.get("cat_req_arb_1"),
            partido.get("cat_req_arb_2"),
            partido.get("cat_req_arb_3")
        ]

        campos = [
            x for x in campos
            if pd.notna(x)
            and str(x).upper() != "N/A"
        ]

        if len(campos) == 0:

            alertas.append({
                "tipo": "Configuración",
                "severidad": "ALTA",
                "mensaje":
                    f"El partido {partido.get('id_partido', '')} "
                    "no tiene categorías arbitrales configuradas."
            })

    # --------------------------------------------------------
    # Alertas generales
    # --------------------------------------------------------

    if len(alertas) == 0:

        alertas.append({
            "tipo": "Sistema",
            "severidad": "OK",
            "mensaje":
                "No se detectaron inconsistencias críticas en la configuración."
        })

    return pd.DataFrame(alertas)


# ============================================================
# SEMÁFORO
# ============================================================

def mostrar_semaforo(alertas):

    if alertas.empty:
        nivel = "VERDE"
    else:

        if "CRÍTICA" in alertas["severidad"].values:
            nivel = "ROJO"

        elif "ALTA" in alertas["severidad"].values:
            nivel = "ROJO"

        elif "MEDIA" in alertas["severidad"].values:
            nivel = "AMARILLO"

        else:
            nivel = "VERDE"

    if nivel == "ROJO":

        st.error(
            "🔴 **ESTADO CRÍTICO** — "
            "Existen alertas que requieren atención."
        )

    elif nivel == "AMARILLO":

        st.warning(
            "🟡 **ATENCIÓN** — "
            "Existen observaciones en la programación."
        )

    else:

        st.success(
            "🟢 **OPERACIÓN NORMAL** — "
            "No existen alertas críticas."
        )


# ============================================================
# EXPORTAR CSV
# ============================================================

def convertir_csv(df):

    return df.to_csv(
        index=False,
        encoding="utf-8-sig"
    ).encode("utf-8-sig")


# ============================================================
# EXPORTAR XLSX
# ============================================================

def convertir_xlsx(df):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Programacion"
        )

    return output.getvalue()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        '<div class="sidebar-title">🏀 Asignador Arbitral</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="sidebar-subtitle">'
        'Sistema de programación y asignación de personal'
        '</div>',
        unsafe_allow_html=True
    )

    archivo = st.file_uploader(
        "📁 Cargar base de datos",
        type=["xlsx", "xls"],
        help="Seleccione el archivo Excel con las cuatro hojas normalizadas."
    )

    st.markdown("---")

    menu = st.radio(
        "MÓDULOS",
        [
            "🏠 Inicio",
            "📅 Programación",
            "👨‍⚖️ Árbitros",
            "📊 Estadísticas",
            "🚨 Alertas",
            "📋 Datos"
        ],
        label_visibility="collapsed"
    )


# ============================================================
# VALIDACIÓN DE ARCHIVO
# ============================================================

if archivo is None:

    st.title("🏀 Asignador Arbitral de Baloncesto")

    st.info(
        "👈 Cargue el archivo Excel desde la barra lateral "
        "para comenzar el análisis."
    )

    st.markdown("""
    ### ¿Qué hace esta aplicación?

    El sistema permite:

    - 📥 Cargar las bases normalizadas.
    - 🔗 Cruzar árbitros, disponibilidad, eventos y partidos.
    - 📅 Generar la programación semanal.
    - 👨‍⚖️ Asignar árbitros de campo y oficiales de mesa.
    - 🔄 Aplicar sustitución por categoría superior.
    - ⚖️ Equilibrar las asignaciones.
    - 🚨 Detectar conflictos y falta de personal.
    - 📊 Analizar estadísticas.
    - 📄 Generar informes.
    - 💾 Descargar los resultados.
    """)

    st.stop()


# ============================================================
# CARGAR Y PROCESAR
# ============================================================

with st.spinner("Procesando base de datos..."):

    datos_raw = cargar_excel(archivo)

    datos = normalizar_datos(datos_raw)

    datos = preparar_programacion(datos)

    metricas = calcular_metricas(datos)

    alertas = analizar_alertas(datos)


# ============================================================
# INICIO
# ============================================================

if menu == "🏠 Inicio":

    st.title("🏀 Asignador Arbitral de Baloncesto")

    st.caption(
        "Sistema inteligente para programación semanal "
        "de árbitros y oficiales de mesa."
    )

    mostrar_semaforo(alertas)

    st.markdown(
        '<div class="section-title"><h3>Resumen operativo</h3></div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Árbitros registrados</div>
                <div class="kpi-value">{metricas['arbitros']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Partidos</div>
                <div class="kpi-value">{metricas['partidos']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Árbitros híbridos</div>
                <div class="kpi-value">{metricas['hibridos']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c4:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Días programados</div>
                <div class="kpi-value">{metricas['dias']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# PROGRAMACIÓN
# ============================================================

elif menu == "📅 Programación":

    st.title("📅 Programación semanal")

    partidos = datos["partidos"]

    if partidos.empty:

        st.warning("No existen partidos en la base.")

    else:

        columnas = [
            "id_partido",
            "evento",
            "escenario",
            "rama",
            "categoria",
            "fecha",
            "hora_inicio",
            "hora_fin"
        ]

        columnas = [
            c for c in columnas
            if c in partidos.columns
        ]

        tabla = partidos[columnas].copy()

        st.dataframe(
            tabla,
            use_container_width=True,
            hide_index=True
        )

        col1, col2 = st.columns(2)

        with col1:

            st.download_button(
                "⬇️ Descargar CSV",
                convertir_csv(tabla),
                "programacion_semanal.csv",
                "text/csv"
            )

        with col2:

            st.download_button(
                "⬇️ Descargar Excel",
                convertir_xlsx(tabla),
                "programacion_semanal.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


# ============================================================
# ÁRBITROS
# ============================================================

elif menu == "👨‍⚖️ Árbitros":

    st.title("👨‍⚖️ Árbitros")

    arbitros = datos["arbitros"]

    if arbitros.empty:

        st.warning("No existen árbitros registrados.")

    else:

        st.dataframe(
            arbitros,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇️ Descargar base de árbitros",
            convertir_xlsx(arbitros),
            "arbitros.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# ============================================================
# ESTADÍSTICAS
# ============================================================

elif menu == "📊 Estadísticas":

    st.title("📊 Estadísticas")

    arbitros = datos["arbitros"]
    partidos = datos["partidos"]

    col1, col2 = st.columns(2)

    with col1:

        if "rol_arbitral" in arbitros.columns:

            conteo = (
                arbitros["rol_arbitral"]
                .value_counts()
                .reset_index()
            )

            conteo.columns = [
                "Rol",
                "Cantidad"
            ]

            fig = px.bar(
                conteo,
                x="Rol",
                y="Cantidad",
                title="Distribución por rol arbitral"
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False}
            )

    with col2:

        if "categoria" in partidos.columns:

            conteo = (
                partidos["categoria"]
                .value_counts()
                .reset_index()
            )

            conteo.columns = [
                "Categoría",
                "Partidos"
            ]

            fig = px.bar(
                conteo,
                x="Categoría",
                y="Partidos",
                title="Partidos por categoría"
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False}
            )


# ============================================================
# ALERTAS
# ============================================================

elif menu == "🚨 Alertas":

    st.title("🚨 Alertas de programación")

    mostrar_semaforo(alertas)

    if alertas.empty:

        st.success(
            "No se encontraron alertas."
        )

    else:

        for _, alerta in alertas.iterrows():

            severidad = alerta["severidad"]

            if severidad in ["CRÍTICA", "ALTA"]:

                clase = "alert-red"

            elif severidad == "MEDIA":

                clase = "alert-yellow"

            else:

                clase = "alert-green"

            st.markdown(
                f"""
                <div class="alert-card {clase}">
                    <strong>{severidad}</strong><br>
                    {alerta['tipo']} — {alerta['mensaje']}
                </div>
                """,
                unsafe_allow_html=True
            )

        st.download_button(
            "⬇️ Descargar alertas Excel",
            convertir_xlsx(alertas),
            "alertas_programacion.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# ============================================================
# DATOS
# ============================================================

elif menu == "📋 Datos":

    st.title("📋 Bases de datos")

    pestañas = st.tabs([
        "Árbitros",
        "Disponibilidad",
        "Configuración",
        "Partidos"
    ])

    nombres = [
        "arbitros",
        "disponibilidad",
        "configuracion",
        "partidos"
    ]

    for pestaña, nombre in zip(pestañas, nombres):

        with pestaña:

            df = datos[nombre]

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                f"⬇️ Descargar {nombre}.xlsx",
                convertir_xlsx(df),
                f"{nombre}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_{nombre}"
            )