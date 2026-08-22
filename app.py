# ============================================================
# APP.PY
# BASKETBALL REFEREES SCHEDULER
# SISTEMA DE PROGRAMACIÓN, ASIGNACIÓN Y ANÁLISIS DE ÁRBITROS
#
# INTEGRACIONES:
#   - Carga de Excel
#   - Asignación automática
#   - Control de disponibilidad
#   - Alertas
#   - Excel de resultados
#   - CSV
#   - PDF operativo automático
#   - PDF ejecutivo automático
#   - Análisis mediante IA
#   - Identificación del archivo procesado
#   - Botón "Cargar otra base de datos"
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import unicodedata
import hashlib

from datetime import datetime, timedelta
from collections import defaultdict

# ============================================================
# OPENAI
# ============================================================

try:
    from openai import OpenAI
    OPENAI_DISPONIBLE = True
except ImportError:
    OPENAI_DISPONIBLE = False

# ============================================================
# REPORTES
# ============================================================

import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)
from reportlab.lib.units import cm

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
    KeepTogether
)

# ============================================================
# CONFIGURACIÓN STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Basketball Referees Scheduler",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# ESTILOS
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #f2f4f5;
    }

    .main {
        background-color: #f2f4f5;
    }

    section[data-testid="stSidebar"] {
        background-color: #202b33;
        border-right: 1px solid #17202a;
    }

    section[data-testid="stSidebar"] * {
        color: #f4f6f7;
    }

    section[data-testid="stSidebar"] label {
        font-size: 13px;
    }

    h1, h2, h3 {
        color: #17202a;
    }

    .app-title {
        font-size: 30px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 2px;
    }

    .app-subtitle {
        font-size: 14px;
        color: #d5d8dc;
        margin-top: 0;
    }

    div[data-testid="stVerticalBlock"] .header-box {
        background: linear-gradient(
            135deg,
            #17202a 0%,
            #273746 100%
        );
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 18px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.10);
    }

    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #dfe4e8;
        border-radius: 10px;
        padding: 14px 16px;
        box-shadow: 0 2px 7px rgba(0,0,0,0.05);
        min-height: 95px;
    }

    div[data-testid="metric-container"] label {
        color: #7b8794 !important;
        font-size: 12px !important;
    }

    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #17202a !important;
        font-size: 25px !important;
        font-weight: 700 !important;
    }

    .section-title {
        background-color: #273746;
        color: #ffffff;
        padding: 9px 13px;
        border-radius: 7px;
        font-weight: 600;
        margin: 15px 0 12px 0;
    }

    .file-status {
        background-color: #ffffff;
        border-left: 5px solid #273746;
        border-radius: 8px;
        padding: 13px 16px;
        margin-bottom: 15px;
        box-shadow: 0 2px 7px rgba(0,0,0,0.05);
    }

    .file-status-title {
        font-weight: 700;
        color: #273746;
        font-size: 14px;
    }

    .file-status-name {
        color: #566573;
        font-size: 13px;
        margin-top: 3px;
    }

    .stDownloadButton button {
        background-color: #273746 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }

    .stDownloadButton button:hover {
        background-color: #34495e !important;
    }

    section[data-testid="stFileUploaderDropzone"] {
        background-color: #ffffff;
        border: 1px dashed #7f8c8d;
        border-radius: 8px;
    }

    [data-testid="stDataFrame"] {
        border-radius: 7px;
        overflow: hidden;
    }

    div[data-testid="stAlert"] {
        border-radius: 8px;
    }

    .footer-text {
        margin-top: 30px;
        padding: 12px;
        text-align: center;
        color: #7f8c8d;
        font-size: 11px;
        border-top: 1px solid #dfe4e8;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# CONSTANTES
# ============================================================

MAX_CAMPO_DIA = 2
MAX_CAMPO_SEMANA = 14

ORDEN_CATEGORIAS = {
    "3ra": 1,
    "2da": 2,
    "1ra": 3
}

MODELO_IA = "gpt-5.6-luna"

# ============================================================
# FUNCIONES DE TEXTO
# ============================================================

def limpiar_texto(valor):

    if pd.isna(valor):
        return ""

    texto = str(valor).strip().lower()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        c
        for c in texto
        if unicodedata.category(c) != "Mn"
    )

    return texto


# ============================================================
# CATEGORÍAS
# ============================================================

def categoria_numero(categoria):

    texto = limpiar_texto(categoria)

    if "1ra" in texto or "primera" in texto:
        return 3

    if "2da" in texto or "segunda" in texto:
        return 2

    if "3ra" in texto or "tercera" in texto:
        return 1

    return 0


def categoria_superior_o_igual(
    categoria_disponible,
    categoria_requerida
):

    return (
        categoria_numero(categoria_disponible)
        >= categoria_numero(categoria_requerida)
    )


# ============================================================
# ROLES
# ============================================================

def es_campo(rol):

    texto = limpiar_texto(rol)

    return (
        "arbitro de campo" in texto
        and "hibrido" not in texto
    )


def es_mesa(rol):

    texto = limpiar_texto(rol)

    return (
        "oficial de mesa" in texto
        and "hibrido" not in texto
    )


def es_hibrido(rol):

    return "hibrido" in limpiar_texto(rol)


# ============================================================
# FECHAS
# ============================================================

def convertir_fecha(valor):

    try:

        resultado = pd.to_datetime(
            valor,
            errors="coerce"
        )

        return resultado

    except Exception:

        return pd.NaT


# ============================================================
# HORAS
# ============================================================

def hora_a_minutos(valor):

    if pd.isna(valor):
        return None

    texto = str(valor).strip()

    try:

        if ":" in texto:

            partes = texto.split(":")

            horas = int(partes[0])

            minutos = int(
                partes[1][:2]
            )

            return (
                horas * 60
                + minutos
            )

        return int(float(texto))

    except Exception:

        try:

            hora = pd.to_datetime(texto)

            return (
                hora.hour * 60
                + hora.minute
            )

        except Exception:

            return None


# ============================================================
# DÍAS
# ============================================================

DIAS_ES = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo"
}


def obtener_dia_es(fecha):

    try:

        fecha = pd.Timestamp(fecha)

        return DIAS_ES.get(
            fecha.weekday(),
            ""
        )

    except Exception:

        return ""


# ============================================================
# DISPONIBILIDAD
# ============================================================

def intervalo_disponible(
    disponibilidad,
    fecha,
    inicio,
    fin
):

    if disponibilidad is None:
        return False

    if disponibilidad.empty:
        return False

    try:

        fecha_normalizada = (
            pd.Timestamp(fecha).date()
        )

    except Exception:

        return False

    dia_semana = obtener_dia_es(fecha)

    for _, fila in disponibilidad.iterrows():

        dia = fila.get("dia")

        fecha_disp = None

        try:

            fecha_convertida = pd.to_datetime(
                dia,
                errors="coerce"
            )

            if pd.notna(fecha_convertida):

                fecha_disp = (
                    fecha_convertida.date()
                )

        except Exception:

            fecha_disp = None

        if fecha_disp is None:

            dia_texto = limpiar_texto(dia)

            if dia_texto == limpiar_texto(dia_semana):

                fecha_disp = fecha_normalizada

            else:

                continue

        if fecha_disp != fecha_normalizada:
            continue

        inicio_disp = hora_a_minutos(
            fila.get("hora_inicio")
        )

        fin_disp = hora_a_minutos(
            fila.get("hora_fin")
        )

        if (
            inicio_disp is not None
            and fin_disp is not None
            and inicio_disp <= inicio
            and fin_disp >= fin
        ):

            return True

    return False


# ============================================================
# PREPARAR PARTIDOS
# ============================================================

@st.cache_data(show_spinner=False)
def preparar_partidos(datos):

    partidos = datos[
        "programacion_partidos"
    ].copy()

    if partidos.empty:
        return partidos

    partidos["fecha_dt"] = (
        partidos["fecha"].apply(
            convertir_fecha
        )
    )

    partidos["inicio_min"] = (
        partidos["hora_inicio"].apply(
            hora_a_minutos
        )
    )

    partidos["fin_min"] = (
        partidos["hora_fin"].apply(
            hora_a_minutos
        )
    )

    partidos = partidos[
        partidos["fecha_dt"].notna()
    ].copy()

    columnas_orden = [
        "fecha_dt",
        "inicio_min",
        "escenario",
        "id_partido"
    ]

    columnas_orden = [
        c
        for c in columnas_orden
        if c in partidos.columns
    ]

    if columnas_orden:

        partidos = partidos.sort_values(
            by=columnas_orden
        )

    return partidos.reset_index(drop=True)


# ============================================================
# CREAR REGISTRO
# ============================================================

def crear_registro_asignacion(
    partido,
    arb,
    funcion,
    categoria_req,
    sustitucion,
    categoria_utilizada
):

    return {

        "id_partido":
            partido.get("id_partido"),

        "fecha":
            partido.get("fecha"),

        "dia":
            partido.get("dia"),

        "hora_inicio":
            partido.get("hora_inicio"),

        "hora_fin":
            partido.get("hora_fin"),

        "evento":
            partido.get("evento"),

        "escenario":
            partido.get("escenario"),

        "rama":
            partido.get("rama"),

        "categoria_partido":
            partido.get("categoria"),

        "id_arbitro":
            arb.get("id_arbitro"),

        "nombre_completo":
            arb.get("nombre_completo"),

        "documento_identidad":
            arb.get("documento_identidad"),

        "rol_arbitral":
            arb.get("rol_arbitral"),

        "funcion_asignada":
            funcion,

        "categoria_requerida":
            categoria_req,

        "categoria_utilizada":
            categoria_utilizada,

        "sustitucion_categoria":
            "SI" if sustitucion else "NO"
    }


# ============================================================
# MOTOR DE ASIGNACIÓN
# ============================================================

@st.cache_data(show_spinner=False)
def ejecutar_asignacion(datos):

    arbitros = datos[
        "arbitros"
    ].copy()

    disponibilidad = datos[
        "disponibilidad_arbitros"
    ].copy()

    partidos = preparar_partidos(datos)

    asignaciones = []

    alertas = []

    if arbitros.empty or partidos.empty:

        return (
            pd.DataFrame(),
            pd.DataFrame()
        )

    disponibilidad_por_arbitro = {

        aid: grupo.copy()

        for aid, grupo
        in disponibilidad.groupby("id_arbitro")
    }

    carga_dia = defaultdict(int)

    carga_semana = defaultdict(int)

    historial = defaultdict(list)

    def candidatos(
        partido,
        funcion,
        categoria_requerida
    ):

        resultado = []

        fecha = partido["fecha_dt"]

        inicio = partido["inicio_min"]

        fin = partido["fin_min"]

        if (
            pd.isna(fecha)
            or inicio is None
            or fin is None
        ):

            return resultado

        fecha_clave = fecha.date()

        for _, arb in arbitros.iterrows():

            aid = arb.get("id_arbitro")

            rol = arb.get(
                "rol_arbitral",
                ""
            )

            if funcion == "CAMPO":

                categoria = arb.get(
                    "categoria_campo"
                )

                puede = (
                    es_campo(rol)
                    or es_hibrido(rol)
                )

            else:

                categoria = arb.get(
                    "categoria_mesa"
                )

                puede = (
                    es_mesa(rol)
                    or es_hibrido(rol)
                )

            if not puede:
                continue

            if not categoria_superior_o_igual(
                categoria,
                categoria_requerida
            ):

                continue

            disp = (
                disponibilidad_por_arbitro.get(
                    aid,
                    pd.DataFrame()
                )
            )

            if not intervalo_disponible(
                disp,
                fecha,
                inicio,
                fin
            ):

                continue

            conflicto = False

            historial_arb = historial.get(
                aid,
                []
            )

            for anterior in historial_arb:

                if anterior["fecha"] != fecha:
                    continue

                if (
                    inicio < anterior["fin"]
                    and
                    fin > anterior["inicio"]
                ):

                    conflicto = True
                    break

                if anterior["fin"] == inicio:

                    mismo_escenario = (
                        limpiar_texto(
                            anterior["escenario"]
                        )
                        ==
                        limpiar_texto(
                            partido.get("escenario")
                        )
                    )

                    if not mismo_escenario:

                        conflicto = True
                        break

                    if (
                        anterior["id_partido"]
                        ==
                        partido.get("id_partido")
                    ):

                        conflicto = True
                        break

            if conflicto:
                continue

            campos_dia = carga_dia[
                (aid, fecha_clave)
            ]

            campos_semana = carga_semana[aid]

            if (
                funcion == "CAMPO"
                and
                campos_semana >= MAX_CAMPO_SEMANA
            ):

                continue

            exceso_diario = (
                funcion == "CAMPO"
                and
                campos_dia >= MAX_CAMPO_DIA
            )

            diferencia_categoria = (
                categoria_numero(categoria)
                -
                categoria_numero(
                    categoria_requerida
                )
            )

            numero_asignaciones = len(
                historial_arb
            )

            puntuacion = 0

            puntuacion += (
                diferencia_categoria * 100
            )

            puntuacion += (
                numero_asignaciones * 10
            )

            if exceso_diario:

                puntuacion += 1000

            if es_hibrido(rol):

                puntuacion += 5

            resultado.append({

                "arbitro": arb,

                "puntuacion": puntuacion,

                "exceso_diario": exceso_diario
            })

        resultado.sort(
            key=lambda x:
            x["puntuacion"]
        )

        return resultado

    def asignar_funcion(
        partido,
        funcion,
        categorias
    ):

        asignados_partido = []

        for categoria_req in categorias:

            candidatos_disponibles = (
                candidatos(
                    partido,
                    funcion,
                    categoria_req
                )
            )

            if not candidatos_disponibles:

                alertas.append({

                    "id_partido":
                        partido.get("id_partido"),

                    "fecha":
                        partido.get("fecha"),

                    "hora":
                        (
                            f"{partido.get('hora_inicio')}"
                            f" - "
                            f"{partido.get('hora_fin')}"
                        ),

                    "evento":
                        partido.get("evento"),

                    "escenario":
                        partido.get("escenario"),

                    "tipo":
                        funcion,

                    "severidad":
                        "CRÍTICA",

                    "categoria_requerida":
                        categoria_req,

                    "mensaje":
                        (
                            "No existe personal "
                            "disponible para "
                            f"{funcion.lower()} "
                            "con categoría "
                            f"{categoria_req}."
                        )
                })

                continue

            seleccionado = (
                candidatos_disponibles[0]
            )

            arb = seleccionado["arbitro"]

            aid = arb.get("id_arbitro")

            if funcion == "CAMPO":

                categoria_utilizada = (
                    arb.get("categoria_campo")
                )

            else:

                categoria_utilizada = (
                    arb.get("categoria_mesa")
                )

            sustitucion = (
                categoria_numero(
                    categoria_utilizada
                )
                >
                categoria_numero(
                    categoria_req
                )
            )

            registro = (
                crear_registro_asignacion(
                    partido,
                    arb,
                    funcion,
                    categoria_req,
                    sustitucion,
                    categoria_utilizada
                )
            )

            asignados_partido.append(registro)

            historial[aid].append({

                "id_partido":
                    partido.get("id_partido"),

                "fecha":
                    partido["fecha_dt"],

                "inicio":
                    partido["inicio_min"],

                "fin":
                    partido["fin_min"],

                "escenario":
                    partido.get("escenario"),

                "funcion":
                    funcion
            })

            if funcion == "CAMPO":

                clave_dia = (
                    aid,
                    partido["fecha_dt"].date()
                )

                carga_dia[clave_dia] += 1

                carga_semana[aid] += 1

                if (
                    carga_dia[clave_dia]
                    > MAX_CAMPO_DIA
                ):

                    alertas.append({

                        "id_partido":
                            partido.get(
                                "id_partido"
                            ),

                        "fecha":
                            partido.get(
                                "fecha"
                            ),

                        "hora":
                            (
                                f"{partido.get('hora_inicio')}"
                                f" - "
                                f"{partido.get('hora_fin')}"
                            ),

                        "evento":
                            partido.get("evento"),

                        "escenario":
                            partido.get("escenario"),

                        "tipo":
                            "CARGA",

                        "severidad":
                            "MEDIA",

                        "categoria_requerida":
                            categoria_req,

                        "mensaje":
                            (
                                f"El árbitro "
                                f"{arb.get('nombre_completo')} "
                                f"supera la carga "
                                f"recomendada de "
                                f"{MAX_CAMPO_DIA} "
                                "partidos de campo "
                                "en el día."
                            )
                    })

        return asignados_partido

    for _, partido in partidos.iterrows():

        categorias_campo = []

        try:

            cantidad_campo = int(
                partido.get(
                    "cant_arbitros_campo",
                    0
                )
            )

        except Exception:

            cantidad_campo = 0

        for i in range(
            1,
            min(cantidad_campo, 3) + 1
        ):

            categoria = partido.get(
                f"cat_req_arb_{i}"
            )

            if (
                pd.notna(categoria)
                and
                limpiar_texto(categoria)
                not in ["", "n/a", "na"]
            ):

                categorias_campo.append(
                    str(categoria).strip()
                )

        registros_campo = (
            asignar_funcion(
                partido,
                "CAMPO",
                categorias_campo
            )
        )

        asignaciones.extend(
            registros_campo
        )

        categorias_mesa = []

        try:

            cantidad_mesa = int(
                partido.get(
                    "cant_oficiales_mesa",
                    0
                )
            )

        except Exception:

            cantidad_mesa = 0

        for i in range(
            1,
            min(cantidad_mesa, 2) + 1
        ):

            categoria = partido.get(
                f"cat_req_mesa_{i}"
            )

            if (
                pd.notna(categoria)
                and
                limpiar_texto(categoria)
                not in ["", "n/a", "na"]
            ):

                categorias_mesa.append(
                    str(categoria).strip()
                )

        registros_mesa = (
            asignar_funcion(
                partido,
                "MESA",
                categorias_mesa
            )
        )

        asignaciones.extend(
            registros_mesa
        )

    return (
        pd.DataFrame(asignaciones),
        pd.DataFrame(alertas)
    )


# ============================================================
# CARGAR EXCEL
# ============================================================

@st.cache_data(show_spinner=False)
def cargar_excel_archivo(archivo_bytes):

    excel = pd.ExcelFile(
        io.BytesIO(archivo_bytes)
    )

    hojas = excel.sheet_names

    requeridas = [
        "Arbitros",
        "Disponibilidad_Arbitros",
        "Config_Eventos",
        "Programacion_Partidos"
    ]

    faltantes = [
        hoja
        for hoja in requeridas
        if hoja not in hojas
    ]

    if faltantes:

        raise ValueError(
            "Faltan las siguientes hojas: "
            + ", ".join(faltantes)
        )

    return {

        "arbitros":
            pd.read_excel(
                io.BytesIO(archivo_bytes),
                sheet_name="Arbitros"
            ),

        "disponibilidad_arbitros":
            pd.read_excel(
                io.BytesIO(archivo_bytes),
                sheet_name="Disponibilidad_Arbitros"
            ),

        "config_eventos":
            pd.read_excel(
                io.BytesIO(archivo_bytes),
                sheet_name="Config_Eventos"
            ),

        "programacion_partidos":
            pd.read_excel(
                io.BytesIO(archivo_bytes),
                sheet_name="Programacion_Partidos"
            )
    }


# ============================================================
# EXCEL
# ============================================================

def generar_excel(
    datos,
    asignaciones,
    alertas
):

    buffer = io.BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl"
    ) as writer:

        datos["arbitros"].to_excel(
            writer,
            sheet_name="Arbitros",
            index=False
        )

        datos["disponibilidad_arbitros"].to_excel(
            writer,
            sheet_name="Disponibilidad",
            index=False
        )

        datos["config_eventos"].to_excel(
            writer,
            sheet_name="Config_Eventos",
            index=False
        )

        datos["programacion_partidos"].to_excel(
            writer,
            sheet_name="Partidos",
            index=False
        )

        if not asignaciones.empty:

            asignaciones.to_excel(
                writer,
                sheet_name="Asignaciones",
                index=False
            )

        if not alertas.empty:

            alertas.to_excel(
                writer,
                sheet_name="Alertas",
                index=False
            )

    return buffer.getvalue()


# ============================================================
# CSV
# ============================================================

def generar_csv(df):

    return df.to_csv(
        index=False,
        encoding="utf-8-sig"
    ).encode("utf-8-sig")


# ============================================================
# GRÁFICOS PDF
# ============================================================

def grafico_alertas(alertas):

    fig, ax = plt.subplots(
        figsize=(8, 4.5)
    )

    if alertas.empty:

        ax.text(
            0.5,
            0.5,
            "No existen alertas",
            ha="center",
            va="center",
            fontsize=15
        )

        ax.axis("off")

        return fig

    conteo = (
        alertas["severidad"]
        .value_counts()
    )

    conteo.plot(
        kind="bar",
        ax=ax
    )

    ax.set_title(
        "Alertas por nivel de severidad"
    )

    ax.set_xlabel("Severidad")
    ax.set_ylabel("Cantidad")

    plt.tight_layout()

    return fig


def grafico_funciones(asignaciones):

    fig, ax = plt.subplots(
        figsize=(8, 4.5)
    )

    if asignaciones.empty:

        ax.text(
            0.5,
            0.5,
            "Sin asignaciones",
            ha="center",
            va="center",
            fontsize=15
        )

        ax.axis("off")

        return fig

    conteo = (
        asignaciones["funcion_asignada"]
        .value_counts()
    )

    conteo.plot(
        kind="bar",
        ax=ax
    )

    ax.set_title(
        "Asignaciones por función"
    )

    ax.set_xlabel("Función")
    ax.set_ylabel("Cantidad")

    plt.tight_layout()

    return fig


def grafico_carga(asignaciones):

    fig, ax = plt.subplots(
        figsize=(9, 5)
    )

    if asignaciones.empty:

        ax.text(
            0.5,
            0.5,
            "Sin información",
            ha="center",
            va="center"
        )

        ax.axis("off")

        return fig

    if "funcion_asignada" not in asignaciones.columns:

        ax.axis("off")

        return fig

    campo = asignaciones[
        asignaciones[
            "funcion_asignada"
        ] == "CAMPO"
    ]

    if campo.empty:

        ax.text(
            0.5,
            0.5,
            "No existen asignaciones de campo",
            ha="center",
            va="center"
        )

        ax.axis("off")

        return fig

    conteo = (
        campo["nombre_completo"]
        .value_counts()
        .head(15)
        .sort_values()
    )

    conteo.plot(
        kind="barh",
        ax=ax
    )

    ax.set_title(
        "Carga de árbitros de campo"
    )

    ax.set_xlabel("Partidos")
    ax.set_ylabel("Árbitro")

    plt.tight_layout()

    return fig


# ============================================================
# CONVERTIR FIGURA A BYTES
# ============================================================

def figura_a_bytes(fig):

    imagen = io.BytesIO()

    fig.savefig(
        imagen,
        format="png",
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig)

    imagen.seek(0)

    return imagen


# ============================================================
# IA - CLIENTE
# ============================================================

def obtener_cliente_openai():

    if not OPENAI_DISPONIBLE:
        return None

    try:

        api_key = st.secrets.get(
            "OPENAI_API_KEY",
            None
        )

    except Exception:

        return None

    if not api_key:
        return None

    try:

        return OpenAI(
            api_key=api_key
        )

    except Exception:

        return None


# ============================================================
# IA - GENERACIÓN DEL ANÁLISIS
# ============================================================

def generar_analisis_ia(
    datos,
    asignaciones,
    alertas
):

    cliente = obtener_cliente_openai()

    if cliente is None:

        return (
            "El análisis mediante inteligencia artificial "
            "no está disponible porque no se encontró "
            "una OPENAI_API_KEY válida en los Secrets "
            "de Streamlit."
        )

    total_arbitros = len(
        datos["arbitros"]
    )

    total_partidos = len(
        datos["programacion_partidos"]
    )

    total_asignaciones = len(
        asignaciones
    )

    total_alertas = len(
        alertas
    )

    criticas = 0
    medias = 0

    if not alertas.empty:

        criticas = len(
            alertas[
                alertas["severidad"]
                == "CRÍTICA"
            ]
        )

        medias = len(
            alertas[
                alertas["severidad"]
                == "MEDIA"
            ]
        )

    sustituciones = 0

    if not asignaciones.empty:

        sustituciones = len(
            asignaciones[
                asignaciones[
                    "sustitucion_categoria"
                ] == "SI"
            ]
        )

    funciones = {}

    if not asignaciones.empty:

        funciones = (
            asignaciones[
                "funcion_asignada"
            ]
            .value_counts()
            .to_dict()
        )

    cargas = {}

    if not asignaciones.empty:

        campo = asignaciones[
            asignaciones[
                "funcion_asignada"
            ] == "CAMPO"
        ]

        if not campo.empty:

            cargas = (
                campo[
                    "nombre_completo"
                ]
                .value_counts()
                .head(10)
                .to_dict()
            )

    resumen_alertas = []

    if not alertas.empty:

        for _, fila in alertas.head(20).iterrows():

            resumen_alertas.append({
                "id_partido":
                    str(
                        fila.get(
                            "id_partido",
                            ""
                        )
                    ),

                "tipo":
                    str(
                        fila.get(
                            "tipo",
                            ""
                        )
                    ),

                "severidad":
                    str(
                        fila.get(
                            "severidad",
                            ""
                        )
                    ),

                "mensaje":
                    str(
                        fila.get(
                            "mensaje",
                            ""
                        )
                    )
            })

    contexto = {
        "arbitros_registrados":
            total_arbitros,

        "partidos_programados":
            total_partidos,

        "asignaciones_realizadas":
            total_asignaciones,

        "alertas_totales":
            total_alertas,

        "alertas_criticas":
            criticas,

        "alertas_medias":
            medias,

        "sustituciones_categoria":
            sustituciones,

        "asignaciones_por_funcion":
            funciones,

        "mayores_cargas_campo":
            cargas,

        "principales_alertas":
            resumen_alertas
    }

    prompt = f"""
Eres un analista senior de operaciones deportivas
especializado en gestión arbitral y planificación
de competiciones de baloncesto.

Analiza los resultados de un sistema automático de
programación de árbitros.

DATOS CALCULADOS:

{contexto}

Genera un informe ejecutivo profesional en español.

El análisis debe contener exactamente estas secciones:

1. DIAGNÓSTICO GENERAL
Explica el estado general de la programación.

2. CAPACIDAD OPERATIVA
Evalúa si la cantidad y distribución de árbitros
parece adecuada para los partidos programados.

3. DISTRIBUCIÓN DE CARGA
Analiza la distribución de asignaciones y señala
posibles concentraciones o desequilibrios.

4. ALERTAS Y RIESGOS
Interpreta las alertas críticas y medias.
Explica cuáles representan mayor riesgo operativo.

5. CATEGORÍAS Y SUSTITUCIONES
Analiza el uso de categorías superiores cuando
se hayan producido sustituciones.

6. RECOMENDACIONES GERENCIALES
Entrega entre 4 y 7 recomendaciones concretas,
accionables y orientadas a mejorar la planificación.

7. CONCLUSIÓN EJECUTIVA
Escribe una conclusión breve para un director,
coordinador deportivo o responsable de arbitraje.

No inventes datos.
No atribuyas causas que no estén respaldadas
por los datos.
Diferencia claramente entre hechos observados
y recomendaciones.
Usa lenguaje profesional, ejecutivo y claro.
"""

    try:

        respuesta = cliente.responses.create(
            model=MODELO_IA,
            input=prompt
        )

        texto = respuesta.output_text

        if not texto:
            return (
                "La IA no produjo contenido "
                "para el informe."
            )

        return texto

    except Exception as error:

        return (
            "No fue posible generar el análisis "
            "mediante IA.\n\n"
            f"Detalle técnico: {str(error)}"
        )


# ============================================================
# PDF OPERATIVO
# ============================================================

def generar_pdf_operativo(
    datos,
    asignaciones,
    alertas,
    nombre_archivo
):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0.8 * cm,
        leftMargin=0.8 * cm,
        topMargin=0.8 * cm,
        bottomMargin=0.8 * cm
    )

    styles = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "TituloOperativo",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        spaceAfter=8
    )

    subtitulo = ParagraphStyle(
        "SubtituloOperativo",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#273746"),
        spaceBefore=8,
        spaceAfter=6
    )

    normal = ParagraphStyle(
        "NormalOperativo",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10
    )

    elementos = []

    elementos.append(
        Paragraph(
            "PROGRAMACIÓN OPERATIVA DE ÁRBITROS",
            titulo
        )
    )

    elementos.append(
        Paragraph(
            f"Base procesada: {nombre_archivo}",
            normal
        )
    )

    elementos.append(
        Paragraph(
            f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            normal
        )
    )

    elementos.append(
        Spacer(1, 8)
    )

    # ========================================================
    # TABLA DE ALERTAS
    # ========================================================

    elementos.append(
        Paragraph(
            "1. ALERTAS",
            subtitulo
        )
    )

    if alertas.empty:

        elementos.append(
            Paragraph(
                "No se generaron alertas durante "
                "el proceso de asignación.",
                normal
            )
        )

    else:

        datos_alertas = [[
            "Partido",
            "Fecha",
            "Hora",
            "Evento",
            "Escenario",
            "Tipo",
            "Severidad",
            "Categoría",
            "Mensaje"
        ]]

        for _, fila in alertas.iterrows():

            datos_alertas.append([

                str(
                    fila.get(
                        "id_partido",
                        ""
                    )
                ),

                str(
                    fila.get(
                        "fecha",
                        ""
                    )
                ),

                str(
                    fila.get(
                        "hora",
                        ""
                    )
                ),

                str(
                    fila.get(
                        "evento",
                        ""
                    )
                ),

                str(
                    fila.get(
                        "escenario",
                        ""
                    )
                ),

                str(
                    fila.get(
                        "tipo",
                        ""
                    )
                ),

                str(
                    fila.get(
                        "severidad",
                        ""
                    )
                ),

                str(
                    fila.get(
                        "categoria_requerida",
                        ""
                    )
                ),

                str(
                    fila.get(
                        "mensaje",
                        ""
                    )
                )
            ])

        tabla_alertas = Table(
            datos_alertas,
            repeatRows=1,
            colWidths=[
                1.4 * cm,
                1.8 * cm,
                2.0 * cm,
                3.0 * cm,
                3.0 * cm,
                1.7 * cm,
                2.0 * cm,
                1.7 * cm,
                8.0 * cm
            ]
        )

        estilo = [

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#273746")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.3,
                colors.grey
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                6
            )
        ]

        for i in range(
            1,
            len(datos_alertas)
        ):

            severidad = str(
                datos_alertas[i][6]
            )

            if severidad == "CRÍTICA":

                estilo.append(
                    (
                        "BACKGROUND",
                        (6, i),
                        (6, i),
                        colors.HexColor("#f5b7b1")
                    )
                )

            elif severidad == "MEDIA":

                estilo.append(
                    (
                        "BACKGROUND",
                        (6, i),
                        (6, i),
                        colors.HexColor("#f9e79f")
                    )
                )

        tabla_alertas.setStyle(
            TableStyle(estilo)
        )

        elementos.append(
            tabla_alertas
        )

    elementos.append(PageBreak())

    # ========================================================
    # PROGRAMACIÓN
    # ========================================================

    elementos.append(
        Paragraph(
            "2. PROGRAMACIÓN Y ASIGNACIONES",
            subtitulo
        )
    )

    if asignaciones.empty:

        elementos.append(
            Paragraph(
                "No existen asignaciones.",
                normal
            )
        )

    else:

        columnas = [

            "id_partido",
            "fecha",
            "dia",
            "hora_inicio",
            "hora_fin",
            "evento",
            "escenario",
            "rama",
            "categoria_partido",
            "nombre_completo",
            "funcion_asignada",
            "categoria_requerida",
            "categoria_utilizada",
            "sustitucion_categoria"
        ]

        disponibles = [
            c
            for c in columnas
            if c in asignaciones.columns
        ]

        tabla_prog = [
            disponibles
        ]

        for _, fila in asignaciones.iterrows():

            tabla_prog.append([

                str(
                    fila.get(
                        c,
                        ""
                    )
                )

                for c in disponibles
            ])

        anchos = [
            1.3 * cm,
            1.7 * cm,
            1.7 * cm,
            1.5 * cm,
            1.5 * cm,
            3.0 * cm,
            2.8 * cm,
            1.5 * cm,
            2.0 * cm,
            4.0 * cm,
            2.0 * cm,
            1.9 * cm,
            1.9 * cm,
            1.7 * cm
        ]

        tabla_prog = Table(
            tabla_prog,
            repeatRows=1,
            colWidths=anchos[
                :len(disponibles)
            ]
        )

        tabla_prog.setStyle(
            TableStyle([

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#273746")
                ),

                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.25,
                    colors.grey
                ),

                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    5.8
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP"
                )
            ])
        )

        elementos.append(
            tabla_prog
        )

    doc.build(elementos)

    return buffer.getvalue()


# ============================================================
# PDF EJECUTIVO CON IA
# ============================================================

def generar_pdf_ejecutivo(
    datos,
    asignaciones,
    alertas,
    nombre_archivo,
    analisis_ia
):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.3 * cm,
        leftMargin=1.3 * cm,
        topMargin=1.3 * cm,
        bottomMargin=1.3 * cm
    )

    styles = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "TituloEjecutivo",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=10
    )

    subtitulo = ParagraphStyle(
        "SubtituloEjecutivo",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#273746"),
        spaceBefore=10,
        spaceAfter=7
    )

    normal = ParagraphStyle(
        "NormalEjecutivo",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13
    )

    ia_style = ParagraphStyle(
        "IAStyle",
        parent=normal,
        fontSize=9,
        leading=13,
        spaceAfter=6
    )

    elementos = []

    elementos.append(
        Paragraph(
            "INFORME EJECUTIVO",
            titulo
        )
    )

    elementos.append(
        Paragraph(
            "Sistema Inteligente de Programación "
            "de Árbitros de Baloncesto",
            subtitulo
        )
    )

    elementos.append(
        Paragraph(
            f"<b>Base analizada:</b> {nombre_archivo}",
            normal
        )
    )

    elementos.append(
        Paragraph(
            f"<b>Fecha de generación:</b> "
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')}",
            normal
        )
    )

    elementos.append(
        Spacer(1, 8)
    )

    # ========================================================
    # KPIs
    # ========================================================

    total_arbitros = len(
        datos["arbitros"]
    )

    total_partidos = len(
        datos["programacion_partidos"]
    )

    total_asignaciones = len(
        asignaciones
    )

    total_alertas = len(
        alertas
    )

    criticas = 0
    medias = 0

    if not alertas.empty:

        criticas = len(
            alertas[
                alertas["severidad"]
                == "CRÍTICA"
            ]
        )

        medias = len(
            alertas[
                alertas["severidad"]
                == "MEDIA"
            ]
        )

    resumen = [

        [
            "Indicador",
            "Resultado"
        ],

        [
            "Árbitros registrados",
            str(total_arbitros)
        ],

        [
            "Partidos programados",
            str(total_partidos)
        ],

        [
            "Asignaciones realizadas",
            str(total_asignaciones)
        ],

        [
            "Alertas totales",
            str(total_alertas)
        ],

        [
            "Alertas críticas",
            str(criticas)
        ],

        [
            "Alertas medias",
            str(medias)
        ]
    ]

    tabla = Table(
        resumen,
        colWidths=[
            8 * cm,
            7 * cm
        ]
    )

    tabla.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#273746")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.grey
            ),

            (
                "ALIGN",
                (1, 1),
                (1, -1),
                "CENTER"
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                9
            )
        ])
    )

    elementos.append(tabla)

    elementos.append(
        PageBreak()
    )

    # ========================================================
    # GRÁFICO ALERTAS
    # ========================================================

    elementos.append(
        Paragraph(
            "Indicadores de operación",
            subtitulo
        )
    )

    fig1 = grafico_alertas(alertas)

    imagen1 = figura_a_bytes(fig1)

    elementos.append(
        Image(
            imagen1,
            width=16 * cm,
            height=8 * cm
        )
    )

    elementos.append(
        Spacer(1, 8)
    )

    fig2 = grafico_funciones(asignaciones)

    imagen2 = figura_a_bytes(fig2)

    elementos.append(
        Image(
            imagen2,
            width=16 * cm,
            height=8 * cm
        )
    )

    elementos.append(
        PageBreak()
    )

    # ========================================================
    # CARGA
    # ========================================================

    elementos.append(
        Paragraph(
            "Distribución de carga",
            subtitulo
        )
    )

    fig3 = grafico_carga(asignaciones)

    imagen3 = figura_a_bytes(fig3)

    elementos.append(
        Image(
            imagen3,
            width=16 * cm,
            height=8.5 * cm
        )
    )

    elementos.append(
        PageBreak()
    )

    # ========================================================
    # ANÁLISIS IA
    # ========================================================

    elementos.append(
        Paragraph(
            "Análisis gerencial mediante inteligencia artificial",
            subtitulo
        )
    )

    # Convertimos saltos y títulos de IA en párrafos.
    bloques = re.split(
        r"\n\s*\n",
        analisis_ia
    )

    for bloque in bloques:

        bloque = bloque.strip()

        if not bloque:
            continue

        # Escapar caracteres básicos para ReportLab.
        bloque = (
            bloque
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        # Títulos de sección
        if re.match(
            r"^\d+\.",
            bloque
        ):

            elementos.append(
                Paragraph(
                    f"<b>{bloque}</b>",
                    ia_style
                )
            )

        else:

            bloque = bloque.replace(
                "\n",
                "<br/>"
            )

            elementos.append(
                Paragraph(
                    bloque,
                    ia_style
                )
            )

        elementos.append(
            Spacer(1, 3)
        )

    doc.build(elementos)

    return buffer.getvalue()


# ============================================================
# GRÁFICOS NATIVOS STREAMLIT
# ============================================================

def mostrar_barras_simples(
    serie,
    titulo,
    max_items=8
):

    if serie is None or len(serie) == 0:

        st.caption(
            "Sin datos para mostrar."
        )

        return

    serie = (
        serie
        .sort_values(
            ascending=False
        )
        .head(max_items)
        .sort_values(
            ascending=True
        )
    )

    st.markdown(
        f"**{titulo}**"
    )

    st.bar_chart(
        serie,
        use_container_width=True
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="header-box">

        <div class="app-title">
            🏀 Basketball Referees Scheduler
        </div>

        <div class="app-subtitle">
            Sistema inteligente de programación,
            asignación, control y análisis de árbitros.
        </div>

    </div>
    """,
    unsafe_allow_html=True
)

# ============================================================
# ESTADO DE LA APLICACIÓN
# ============================================================

if "upload_version" not in st.session_state:

    st.session_state.upload_version = 0

if "processed_file_name" not in st.session_state:

    st.session_state.processed_file_name = None

if "processed_file_hash" not in st.session_state:

    st.session_state.processed_file_hash = None

if "pdf_operativo" not in st.session_state:

    st.session_state.pdf_operativo = None

if "pdf_ejecutivo" not in st.session_state:

    st.session_state.pdf_ejecutivo = None

if "analisis_ia" not in st.session_state:

    st.session_state.analisis_ia = None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "## 🏀 Menú"
    )

    upload_key = (
        f"excel_upload_"
        f"{st.session_state.upload_version}"
    )

    archivo = st.file_uploader(
        "Cargar base de datos",
        type=["xlsx", "xls"],
        key=upload_key
    )

    # ========================================================
    # BOTÓN CARGAR OTRA BASE
    # ========================================================

    if (
        st.session_state.processed_file_name
        is not None
    ):

        st.success(
            "Base procesada correctamente."
        )

        if st.button(
            "🔄 Cargar otra base de datos",
            use_container_width=True
        ):

            st.session_state.upload_version += 1

            st.session_state.processed_file_name = None
            st.session_state.processed_file_hash = None
            st.session_state.pdf_operativo = None
            st.session_state.pdf_ejecutivo = None
            st.session_state.analisis_ia = None

            st.rerun()

    st.divider()

    modulo = st.radio(
        "Módulos",
        [
            "📊 Resumen",
            "📅 Programación",
            "👨‍⚖️ Árbitros",
            "🚨 Alertas",
            "📈 Estadísticas",
            "📥 Descargas"
        ],
        index=0
    )

    st.divider()

    st.caption(
        "Sistema de asignación automática"
    )

    st.caption(
        "Baloncesto · Análisis de datos · IA"
    )


# ============================================================
# SIN ARCHIVO
# ============================================================

if archivo is None:

    st.info(
        "👈 Carga el archivo Excel normalizado "
        "desde la barra lateral para iniciar "
        "el procesamiento automático."
    )

    st.subheader(
        "Estructura esperada"
    )

    st.write(
        "El archivo debe contener las hojas:"
    )

    st.write(
        "- `Arbitros`\n"
        "- `Disponibilidad_Arbitros`\n"
        "- `Config_Eventos`\n"
        "- `Programacion_Partidos`"
    )

    st.stop()


# ============================================================
# IDENTIFICACIÓN DEL ARCHIVO
# ============================================================

archivo_bytes = archivo.getvalue()

archivo_hash = hashlib.md5(
    archivo_bytes
).hexdigest()

nombre_archivo = archivo.name


# ============================================================
# PROCESAMIENTO
# ============================================================

try:

    with st.spinner(
        "Procesando base de datos y realizando asignaciones..."
    ):

        datos = cargar_excel_archivo(
            archivo_bytes
        )

        asignaciones, alertas = (
            ejecutar_asignacion(
                datos
            )
        )

except Exception as error:

    st.error(
        "❌ Se produjo un error al procesar "
        "el archivo."
    )

    st.exception(error)

    st.stop()


# ============================================================
# DETECTAR SI ES UNA BASE NUEVA
# ============================================================

base_nueva = (
    st.session_state.processed_file_hash
    != archivo_hash
)


# ============================================================
# GENERACIÓN AUTOMÁTICA DE INFORMES
# ============================================================

if base_nueva:

    with st.spinner(
        "Generando informes automáticos..."
    ):

        # ----------------------------------------------------
        # IA
        # ----------------------------------------------------

        with st.spinner(
            "Generando análisis ejecutivo mediante IA..."
        ):

            analisis_ia = generar_analisis_ia(
                datos,
                asignaciones,
                alertas
            )

        # ----------------------------------------------------
        # PDF OPERATIVO
        # ----------------------------------------------------

        pdf_operativo = generar_pdf_operativo(
            datos,
            asignaciones,
            alertas,
            nombre_archivo
        )

        # ----------------------------------------------------
        # PDF EJECUTIVO
        # ----------------------------------------------------

        pdf_ejecutivo = generar_pdf_ejecutivo(
            datos,
            asignaciones,
            alertas,
            nombre_archivo,
            analisis_ia
        )

        # ----------------------------------------------------
        # GUARDAR EN SESSION STATE
        # ----------------------------------------------------

        st.session_state.processed_file_name = (
            nombre_archivo
        )

        st.session_state.processed_file_hash = (
            archivo_hash
        )

        st.session_state.pdf_operativo = (
            pdf_operativo
        )

        st.session_state.pdf_ejecutivo = (
            pdf_ejecutivo
        )

        st.session_state.analisis_ia = (
            analisis_ia
        )


# ============================================================
# INFORMACIÓN DE LA BASE PROCESADA
# ============================================================

st.markdown(
    f"""
    <div class="file-status">

        <div class="file-status-title">
            ✓ Cálculos realizados con la base:
        </div>

        <div class="file-status-name">
            📄 {nombre_archivo}
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# MÉTRICAS
# ============================================================

total_arbitros = len(
    datos["arbitros"]
)

total_partidos = len(
    datos["programacion_partidos"]
)

total_asignaciones = len(
    asignaciones
)

total_alertas = len(
    alertas
)

alertas_criticas = 0

alertas_medias = 0

if not alertas.empty:

    if "severidad" in alertas.columns:

        alertas_criticas = len(
            alertas[
                alertas["severidad"]
                == "CRÍTICA"
            ]
        )

        alertas_medias = len(
            alertas[
                alertas["severidad"]
                == "MEDIA"
            ]
        )


# ============================================================
# RESUMEN
# ============================================================

if modulo == "📊 Resumen":

    st.markdown(
        '<div class="section-title">'
        'Resumen ejecutivo'
        '</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:

        st.metric(
            label="Árbitros",
            value=total_arbitros
        )

    with c2:

        st.metric(
            label="Partidos",
            value=total_partidos
        )

    with c3:

        st.metric(
            label="Asignaciones",
            value=total_asignaciones
        )

    with c4:

        st.metric(
            label="Alertas críticas",
            value=alertas_criticas
        )

    with c5:

        st.metric(
            label="Alertas medias",
            value=alertas_medias
        )

    st.subheader(
        "Estado general"
    )

    if total_alertas == 0:

        st.success(
            "🟢 Programación generada "
            "sin alertas."
        )

    elif alertas_criticas > 0:

        st.error(
            f"🔴 Existen {alertas_criticas} "
            "alertas críticas que requieren "
            "revisión."
        )

    else:

        st.warning(
            f"🟡 Se generaron {total_alertas} "
            "alertas durante la programación."
        )

    col1, col2 = st.columns(2)

    with col1:

        if not asignaciones.empty:

            serie = (
                asignaciones[
                    "funcion_asignada"
                ]
                .value_counts()
            )

            mostrar_barras_simples(
                serie,
                "Asignaciones por función"
            )

        else:

            st.caption(
                "Sin asignaciones."
            )

    with col2:

        if not alertas.empty:

            serie = (
                alertas[
                    "severidad"
                ]
                .value_counts()
            )

            mostrar_barras_simples(
                serie,
                "Alertas por severidad"
            )

        else:

            st.caption(
                "Sin alertas."
            )

    # ========================================================
    # ESTADO IA
    # ========================================================

    st.subheader(
        "🤖 Análisis ejecutivo IA"
    )

    if (
        st.session_state.analisis_ia
        and
        "no está disponible" not in
        st.session_state.analisis_ia
    ):

        st.success(
            "✓ El análisis gerencial mediante IA "
            "fue generado automáticamente."
        )

        with st.expander(
            "Ver interpretación ejecutiva"
        ):

            st.write(
                st.session_state.analisis_ia
            )

    else:

        st.warning(
            "El informe ejecutivo fue generado, "
            "pero el análisis IA no está disponible. "
            "Verifica OPENAI_API_KEY en Streamlit Secrets."
        )


# ============================================================
# PROGRAMACIÓN
# ============================================================

elif modulo == "📅 Programación":

    st.markdown(
        '<div class="section-title">'
        'Programación semanal'
        '</div>',
        unsafe_allow_html=True
    )

    if asignaciones.empty:

        st.warning(
            "No existen asignaciones."
        )

    else:

        columnas = [

            "fecha",
            "dia",
            "hora_inicio",
            "hora_fin",
            "evento",
            "escenario",
            "rama",
            "categoria_partido",
            "nombre_completo",
            "funcion_asignada",
            "categoria_requerida",
            "categoria_utilizada",
            "sustitucion_categoria"
        ]

        columnas = [
            c
            for c in columnas
            if c in asignaciones.columns
        ]

        st.dataframe(
            asignaciones[columnas],
            use_container_width=True,
            height=570,
            hide_index=True
        )


# ============================================================
# ÁRBITROS
# ============================================================

elif modulo == "👨‍⚖️ Árbitros":

    st.markdown(
        '<div class="section-title">'
        'Base de árbitros'
        '</div>',
        unsafe_allow_html=True
    )

    st.dataframe(
        datos["arbitros"],
        use_container_width=True,
        height=550,
        hide_index=True
    )


# ============================================================
# ALERTAS
# ============================================================

elif modulo == "🚨 Alertas":

    st.markdown(
        '<div class="section-title">'
        'Centro de alertas'
        '</div>',
        unsafe_allow_html=True
    )

    if alertas.empty:

        st.success(
            "🟢 No se generaron alertas."
        )

    else:

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "Total",
                total_alertas
            )

        with c2:

            st.metric(
                "Críticas",
                alertas_criticas
            )

        with c3:

            st.metric(
                "Medias",
                alertas_medias
            )

        st.subheader(
            "Detalle"
        )

        st.dataframe(
            alertas,
            use_container_width=True,
            hide_index=True,
            height=500
        )


# ============================================================
# ESTADÍSTICAS
# ============================================================

elif modulo == "📈 Estadísticas":

    st.markdown(
        '<div class="section-title">'
        'Estadísticas de asignación'
        '</div>',
        unsafe_allow_html=True
    )

    if asignaciones.empty:

        st.info(
            "No existen asignaciones."
        )

    else:

        campo = asignaciones[
            asignaciones[
                "funcion_asignada"
            ] == "CAMPO"
        ]

        mesa = asignaciones[
            asignaciones[
                "funcion_asignada"
            ] == "MESA"
        ]

        col1, col2 = st.columns(2)

        with col1:

            if not campo.empty:

                mostrar_barras_simples(
                    campo[
                        "nombre_completo"
                    ].value_counts(),
                    "Carga de campo por árbitro",
                    max_items=10
                )

            else:

                st.caption(
                    "No existen asignaciones "
                    "de campo."
                )

        with col2:

            if not mesa.empty:

                mostrar_barras_simples(
                    mesa[
                        "nombre_completo"
                    ].value_counts(),
                    "Carga de mesa por oficial",
                    max_items=10
                )

            else:

                st.caption(
                    "No existen asignaciones "
                    "de mesa."
                )

        st.subheader(
            "Sustituciones de categoría"
        )

        sustituciones = (
            asignaciones[
                asignaciones[
                    "sustitucion_categoria"
                ] == "SI"
            ]
        )

        if sustituciones.empty:

            st.success(
                "No fue necesario utilizar "
                "sustituciones de categoría "
                "superior."
            )

        else:

            st.warning(
                f"Se realizaron "
                f"{len(sustituciones)} "
                "sustituciones de categoría "
                "superior."
            )

            st.dataframe(
                sustituciones,
                use_container_width=True,
                hide_index=True
            )


# ============================================================
# DESCARGAS
# ============================================================

elif modulo == "📥 Descargas":

    st.markdown(
        '<div class="section-title">'
        'Centro de descargas'
        '</div>',
        unsafe_allow_html=True
    )

    st.write(
        f"Los informes fueron generados "
        f"automáticamente a partir de:"
    )

    st.info(
        f"📄 {nombre_archivo}"
    )

    # ========================================================
    # EXCEL
    # ========================================================

    excel_bytes = generar_excel(
        datos,
        asignaciones,
        alertas
    )

    st.download_button(
        label="📊 Descargar Excel completo",
        data=excel_bytes,
        file_name=(
            "programacion_arbitros.xlsx"
        ),
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True
    )

    # ========================================================
    # CSV ASIGNACIONES
    # ========================================================

    if not asignaciones.empty:

        st.download_button(
            label="📄 Descargar asignaciones CSV",
            data=generar_csv(
                asignaciones
            ),
            file_name=(
                "asignaciones_arbitros.csv"
            ),
            mime="text/csv",
            use_container_width=True
        )

    # ========================================================
    # CSV ALERTAS
    # ========================================================

    if not alertas.empty:

        st.download_button(
            label="🚨 Descargar alertas CSV",
            data=generar_csv(
                alertas
            ),
            file_name=(
                "alertas_programacion.csv"
            ),
            mime="text/csv",
            use_container_width=True
        )

    # ========================================================
    # PDFs AUTOMÁTICOS
    # ========================================================

    st.divider()

    st.subheader(
        "📕 Informes PDF automáticos"
    )

    st.write(
        "Los dos informes fueron generados "
        "automáticamente al finalizar el procesamiento."
    )

    pdf1, pdf2 = st.columns(2)

    with pdf1:

        st.markdown(
            "**PDF 1 · Informe operativo**"
        )

        st.caption(
            "Programación y alertas en formato "
            "preparado para impresión."
        )

        if st.session_state.pdf_operativo:

            st.download_button(
                label="⬇️ Descargar PDF operativo",
                data=(
                    st.session_state.pdf_operativo
                ),
                file_name=(
                    "informe_operativo_arbitros.pdf"
                ),
                mime="application/pdf",
                use_container_width=True
            )

    with pdf2:

        st.markdown(
            "**PDF 2 · Informe ejecutivo IA**"
        )

        st.caption(
            "KPIs, gráficos, análisis gerencial "
            "y recomendaciones mediante IA."
        )

        if st.session_state.pdf_ejecutivo:

            st.download_button(
                label="⬇️ Descargar PDF ejecutivo IA",
                data=(
                    st.session_state.pdf_ejecutivo
                ),
                file_name=(
                    "informe_ejecutivo_IA_arbitros.pdf"
                ),
                mime="application/pdf",
                use_container_width=True
            )

    # ========================================================
    # ANÁLISIS IA
    # ========================================================

    st.divider()

    st.subheader(
        "🤖 Interpretación gerencial IA"
    )

    if st.session_state.analisis_ia:

        with st.expander(
            "Ver análisis completo"
        ):

            st.write(
                st.session_state.analisis_ia
            )

    else:

        st.warning(
            "No existe análisis IA disponible."
        )


# ============================================================
# PIE DE PÁGINA
# ============================================================

st.markdown(
    """
    <div class="footer-text">
        Basketball Referees Scheduler ·
        Sistema de programación,
        asignación y análisis inteligente
        de árbitros
    </div>
    """,
    unsafe_allow_html=True
)