# ============================================================
# APP.PY
# BASKETBALL REFEREES SCHEDULER
# Sistema de programación, asignación y análisis de árbitros
# ============================================================

import io
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)

# OpenAI es opcional para que el sistema siga funcionando aunque
# la API no tenga cuota, la clave no exista o el servicio falle.
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Basketball Referees Scheduler",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

MAX_CAMPO_DIA = 2
MAX_CAMPO_SEMANA = 14

DIAS_ES = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo",
}


# ============================================================
# ESTILOS
# No se utilizan bloques HTML para construir la interfaz.
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f2f4f5;
    }

    section[data-testid="stSidebar"] {
        background-color: #202b33;
        border-right: 1px solid #17202a;
    }

    section[data-testid="stSidebar"] * {
        color: #f4f6f7;
    }

    h1, h2, h3 {
        color: #17202a;
    }

    .section-title {
        background-color: #273746;
        color: #ffffff;
        padding: 9px 13px;
        border-radius: 7px;
        font-weight: 600;
        margin: 15px 0 12px 0;
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

    /* Uploader: texto oscuro sobre fondo claro */
    section[data-testid="stFileUploaderDropzone"] {
        background-color: #eef1f3 !important;
        border: 1px dashed #7f8c8d !important;
        border-radius: 8px !important;
    }

    section[data-testid="stFileUploaderDropzone"] * {
        color: #17202a !important;
    }

    section[data-testid="stFileUploaderDropzone"] button {
        background-color: #c7ccd1 !important;
        color: #17202a !important;
        border: 1px solid #9aa1a7 !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
    }

    section[data-testid="stFileUploaderDropzone"] button:hover {
        background-color: #b7bdc2 !important;
        color: #17202a !important;
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

    .footer-text {
        margin-top: 30px;
        padding: 12px;
        text-align: center;
        color: #7f8c8d;
        font-size: 11px;
        border-top: 1px solid #dfe4e8;
    }

    .file-name-box {
        background-color: #ffffff;
        border: 1px solid #dfe4e8;
        border-left: 5px solid #273746;
        border-radius: 7px;
        padding: 10px 13px;
        margin-bottom: 12px;
        color: #17202a;
        font-size: 13px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# UTILIDADES
# ============================================================

def limpiar_texto(valor):
    if pd.isna(valor):
        return ""
    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(
        c for c in texto if unicodedata.category(c) != "Mn"
    )


def categoria_numero(categoria):
    texto = limpiar_texto(categoria)
    if "1ra" in texto or "primera" in texto:
        return 3
    if "2da" in texto or "segunda" in texto:
        return 2
    if "3ra" in texto or "tercera" in texto:
        return 1
    return 0


def categoria_superior_o_igual(categoria_disponible, categoria_requerida):
    return (
        categoria_numero(categoria_disponible)
        >= categoria_numero(categoria_requerida)
    )


def es_campo(rol):
    texto = limpiar_texto(rol)
    return "arbitro de campo" in texto and "hibrido" not in texto


def es_mesa(rol):
    texto = limpiar_texto(rol)
    return "oficial de mesa" in texto and "hibrido" not in texto


def es_hibrido(rol):
    return "hibrido" in limpiar_texto(rol)


def convertir_fecha(valor):
    try:
        return pd.to_datetime(valor, errors="coerce")
    except Exception:
        return pd.NaT


def hora_a_minutos(valor):
    if pd.isna(valor):
        return None

    texto = str(valor).strip()

    try:
        if ":" in texto:
            partes = texto.split(":")
            return int(partes[0]) * 60 + int(partes[1][:2])
        return int(float(texto))
    except Exception:
        try:
            hora = pd.to_datetime(texto)
            return hora.hour * 60 + hora.minute
        except Exception:
            return None


def obtener_dia_es(fecha):
    try:
        return DIAS_ES.get(pd.Timestamp(fecha).weekday(), "")
    except Exception:
        return ""


def valor_seguro(valor):
    if pd.isna(valor):
        return ""
    return str(valor)


# ============================================================
# DISPONIBILIDAD
# ============================================================

def intervalo_disponible(disponibilidad, fecha, inicio, fin):
    if disponibilidad is None or disponibilidad.empty:
        return False

    try:
        fecha_normalizada = pd.Timestamp(fecha).date()
    except Exception:
        return False

    dia_semana = obtener_dia_es(fecha)

    for _, fila in disponibilidad.iterrows():
        dia = fila.get("dia")
        fecha_disp = None

        try:
            fecha_convertida = pd.to_datetime(dia, errors="coerce")
            if pd.notna(fecha_convertida):
                fecha_disp = fecha_convertida.date()
        except Exception:
            fecha_disp = None

        if fecha_disp is None:
            if limpiar_texto(dia) == limpiar_texto(dia_semana):
                fecha_disp = fecha_normalizada
            else:
                continue

        if fecha_disp != fecha_normalizada:
            continue

        inicio_disp = hora_a_minutos(fila.get("hora_inicio"))
        fin_disp = hora_a_minutos(fila.get("hora_fin"))

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
    partidos = datos["programacion_partidos"].copy()

    if partidos.empty:
        return partidos

    partidos["fecha_dt"] = partidos["fecha"].apply(convertir_fecha)
    partidos["inicio_min"] = partidos["hora_inicio"].apply(hora_a_minutos)
    partidos["fin_min"] = partidos["hora_fin"].apply(hora_a_minutos)

    partidos = partidos[partidos["fecha_dt"].notna()].copy()

    columnas_orden = [
        c
        for c in ["fecha_dt", "inicio_min", "escenario", "id_partido"]
        if c in partidos.columns
    ]

    if columnas_orden:
        partidos = partidos.sort_values(by=columnas_orden)

    return partidos.reset_index(drop=True)


def crear_registro_asignacion(
    partido,
    arb,
    funcion,
    categoria_req,
    sustitucion,
    categoria_utilizada,
):
    return {
        "id_partido": partido.get("id_partido"),
        "fecha": partido.get("fecha"),
        "dia": partido.get("dia"),
        "hora_inicio": partido.get("hora_inicio"),
        "hora_fin": partido.get("hora_fin"),
        "evento": partido.get("evento"),
        "escenario": partido.get("escenario"),
        "rama": partido.get("rama"),
        "categoria_partido": partido.get("categoria"),
        "id_arbitro": arb.get("id_arbitro"),
        "nombre_completo": arb.get("nombre_completo"),
        "documento_identidad": arb.get("documento_identidad"),
        "rol_arbitral": arb.get("rol_arbitral"),
        "funcion_asignada": funcion,
        "categoria_requerida": categoria_req,
        "categoria_utilizada": categoria_utilizada,
        "sustitucion_categoria": "SI" if sustitucion else "NO",
    }


# ============================================================
# MOTOR DE ASIGNACIÓN
# ============================================================

@st.cache_data(show_spinner=False)
def ejecutar_asignacion(datos):
    arbitros = datos["arbitros"].copy()
    disponibilidad = datos["disponibilidad_arbitros"].copy()
    partidos = preparar_partidos(datos)

    asignaciones = []
    alertas = []

    if arbitros.empty or partidos.empty:
        return pd.DataFrame(), pd.DataFrame()

    disponibilidad_por_arbitro = {
        aid: grupo.copy()
        for aid, grupo in disponibilidad.groupby("id_arbitro")
    }

    carga_dia = defaultdict(int)
    carga_semana = defaultdict(int)
    historial = defaultdict(list)

    def candidatos(partido, funcion, categoria_requerida):
        resultado = []

        fecha = partido["fecha_dt"]
        inicio = partido["inicio_min"]
        fin = partido["fin_min"]

        if pd.isna(fecha) or inicio is None or fin is None:
            return resultado

        fecha_clave = fecha.date()

        for _, arb in arbitros.iterrows():
            aid = arb.get("id_arbitro")
            rol = arb.get("rol_arbitral", "")

            if funcion == "CAMPO":
                categoria = arb.get("categoria_campo")
                puede = es_campo(rol) or es_hibrido(rol)
            else:
                categoria = arb.get("categoria_mesa")
                puede = es_mesa(rol) or es_hibrido(rol)

            if not puede:
                continue

            if not categoria_superior_o_igual(
                categoria, categoria_requerida
            ):
                continue

            disp = disponibilidad_por_arbitro.get(
                aid, pd.DataFrame()
            )

            if not intervalo_disponible(
                disp, fecha, inicio, fin
            ):
                continue

            conflicto = False

            for anterior in historial.get(aid, []):
                if anterior["fecha"] != fecha:
                    continue

                if inicio < anterior["fin"] and fin > anterior["inicio"]:
                    conflicto = True
                    break

                if anterior["fin"] == inicio:
                    mismo_escenario = (
                        limpiar_texto(anterior["escenario"])
                        == limpiar_texto(partido.get("escenario"))
                    )

                    if not mismo_escenario:
                        conflicto = True
                        break

                    if anterior["id_partido"] == partido.get("id_partido"):
                        conflicto = True
                        break

            if conflicto:
                continue

            campos_dia = carga_dia[(aid, fecha_clave)]
            campos_semana = carga_semana[aid]

            if (
                funcion == "CAMPO"
                and campos_semana >= MAX_CAMPO_SEMANA
            ):
                continue

            exceso_diario = (
                funcion == "CAMPO"
                and campos_dia >= MAX_CAMPO_DIA
            )

            diferencia_categoria = (
                categoria_numero(categoria)
                - categoria_numero(categoria_requerida)
            )

            numero_asignaciones = len(historial.get(aid, []))

            puntuacion = (
                diferencia_categoria * 100
                + numero_asignaciones * 10
            )

            if exceso_diario:
                puntuacion += 1000

            if es_hibrido(rol):
                puntuacion += 5

            resultado.append(
                {
                    "arbitro": arb,
                    "puntuacion": puntuacion,
                    "exceso_diario": exceso_diario,
                }
            )

        resultado.sort(key=lambda x: x["puntuacion"])
        return resultado

    def asignar_funcion(partido, funcion, categorias):
        asignados_partido = []

        for categoria_req in categorias:
            candidatos_disponibles = candidatos(
                partido, funcion, categoria_req
            )

            if not candidatos_disponibles:
                alertas.append(
                    {
                        "id_partido": partido.get("id_partido"),
                        "fecha": partido.get("fecha"),
                        "hora": (
                            f"{partido.get('hora_inicio')} - "
                            f"{partido.get('hora_fin')}"
                        ),
                        "evento": partido.get("evento"),
                        "escenario": partido.get("escenario"),
                        "tipo": funcion,
                        "severidad": "CRÍTICA",
                        "categoria_requerida": categoria_req,
                        "mensaje": (
                            "No existe personal disponible para "
                            f"{funcion.lower()} con categoría "
                            f"{categoria_req}."
                        ),
                    }
                )
                continue

            seleccionado = candidatos_disponibles[0]
            arb = seleccionado["arbitro"]
            aid = arb.get("id_arbitro")

            categoria_utilizada = (
                arb.get("categoria_campo")
                if funcion == "CAMPO"
                else arb.get("categoria_mesa")
            )

            sustitucion = (
                categoria_numero(categoria_utilizada)
                > categoria_numero(categoria_req)
            )

            registro = crear_registro_asignacion(
                partido,
                arb,
                funcion,
                categoria_req,
                sustitucion,
                categoria_utilizada,
            )

            asignados_partido.append(registro)

            historial[aid].append(
                {
                    "id_partido": partido.get("id_partido"),
                    "fecha": partido["fecha_dt"],
                    "inicio": partido["inicio_min"],
                    "fin": partido["fin_min"],
                    "escenario": partido.get("escenario"),
                    "funcion": funcion,
                }
            )

            if funcion == "CAMPO":
                clave_dia = (
                    aid,
                    partido["fecha_dt"].date(),
                )
                carga_dia[clave_dia] += 1
                carga_semana[aid] += 1

                if carga_dia[clave_dia] > MAX_CAMPO_DIA:
                    alertas.append(
                        {
                            "id_partido": partido.get("id_partido"),
                            "fecha": partido.get("fecha"),
                            "hora": (
                                f"{partido.get('hora_inicio')} - "
                                f"{partido.get('hora_fin')}"
                            ),
                            "evento": partido.get("evento"),
                            "escenario": partido.get("escenario"),
                            "tipo": "CARGA",
                            "severidad": "MEDIA",
                            "categoria_requerida": categoria_req,
                            "mensaje": (
                                f"El árbitro {arb.get('nombre_completo')} "
                                f"supera la carga recomendada de "
                                f"{MAX_CAMPO_DIA} partidos de campo "
                                "en el día."
                            ),
                        }
                    )

        return asignados_partido

    for _, partido in partidos.iterrows():
        categorias_campo = []

        try:
            cantidad_campo = int(
                partido.get("cant_arbitros_campo", 0)
            )
        except Exception:
            cantidad_campo = 0

        for i in range(1, min(cantidad_campo, 3) + 1):
            categoria = partido.get(f"cat_req_arb_{i}")
            if (
                pd.notna(categoria)
                and limpiar_texto(categoria)
                not in ["", "n/a", "na"]
            ):
                categorias_campo.append(str(categoria).strip())

        asignaciones.extend(
            asignar_funcion(
                partido,
                "CAMPO",
                categorias_campo,
            )
        )

        categorias_mesa = []

        try:
            cantidad_mesa = int(
                partido.get("cant_oficiales_mesa", 0)
            )
        except Exception:
            cantidad_mesa = 0

        for i in range(1, min(cantidad_mesa, 2) + 1):
            categoria = partido.get(f"cat_req_mesa_{i}")
            if (
                pd.notna(categoria)
                and limpiar_texto(categoria)
                not in ["", "n/a", "na"]
            ):
                categorias_mesa.append(str(categoria).strip())

        asignaciones.extend(
            asignar_funcion(
                partido,
                "MESA",
                categorias_mesa,
            )
        )

    return pd.DataFrame(asignaciones), pd.DataFrame(alertas)


# ============================================================
# CARGA EXCEL
# ============================================================

@st.cache_data(show_spinner=False)
def cargar_excel_archivo(archivo_bytes):
    excel = pd.ExcelFile(io.BytesIO(archivo_bytes))
    hojas = excel.sheet_names

    requeridas = [
        "Arbitros",
        "Disponibilidad_Arbitros",
        "Config_Eventos",
        "Programacion_Partidos",
    ]

    faltantes = [
        hoja for hoja in requeridas if hoja not in hojas
    ]

    if faltantes:
        raise ValueError(
            "Faltan las siguientes hojas: "
            + ", ".join(faltantes)
        )

    return {
        "arbitros": pd.read_excel(
            io.BytesIO(archivo_bytes),
            sheet_name="Arbitros",
        ),
        "disponibilidad_arbitros": pd.read_excel(
            io.BytesIO(archivo_bytes),
            sheet_name="Disponibilidad_Arbitros",
        ),
        "config_eventos": pd.read_excel(
            io.BytesIO(archivo_bytes),
            sheet_name="Config_Eventos",
        ),
        "programacion_partidos": pd.read_excel(
            io.BytesIO(archivo_bytes),
            sheet_name="Programacion_Partidos",
        ),
    }


# ============================================================
# IA
# ============================================================

def obtener_api_key():
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

    return None


def generar_analisis_ia(datos, asignaciones, alertas):
    """
    La IA es complementaria.
    Un error de API, ausencia de cuota o ausencia de clave
    NO detiene la aplicación ni los PDF.
    """

    api_key = obtener_api_key()

    if not api_key:
        return (
            False,
            "No se encontró OPENAI_API_KEY en Streamlit Secrets.",
        )

    if OpenAI is None:
        return (
            False,
            "La biblioteca openai no está instalada.",
        )

    total_arbitros = len(datos["arbitros"])
    total_partidos = len(datos["programacion_partidos"])
    total_asignaciones = len(asignaciones)
    total_alertas = len(alertas)

    criticas = 0
    medias = 0

    if not alertas.empty and "severidad" in alertas.columns:
        criticas = int(
            (alertas["severidad"] == "CRÍTICA").sum()
        )
        medias = int(
            (alertas["severidad"] == "MEDIA").sum()
        )

    cobertura = (
        total_asignaciones / max(total_partidos, 1) * 100
    )

    sustituciones = 0
    if (
        not asignaciones.empty
        and "sustitucion_categoria" in asignaciones.columns
    ):
        sustituciones = int(
            (
                asignaciones["sustitucion_categoria"]
                == "SI"
            ).sum()
        )

    cargas = ""
    if not asignaciones.empty:
        conteo = (
            asignaciones[
                asignaciones["funcion_asignada"] == "CAMPO"
            ]["nombre_completo"]
            .value_counts()
            .head(15)
        )
        cargas = "; ".join(
            f"{nombre}: {cantidad}"
            for nombre, cantidad in conteo.items()
        )

    alertas_resumen = ""
    if not alertas.empty:
        columnas = [
            c
            for c in [
                "id_partido",
                "tipo",
                "severidad",
                "categoria_requerida",
                "mensaje",
            ]
            if c in alertas.columns
        ]
        alertas_resumen = alertas[columnas].head(40).to_dict(
            orient="records"
        )

    prompt = f"""
Actúa como analista senior de operaciones deportivas y asignación
de árbitros de baloncesto.

Analiza exclusivamente los datos estadísticos proporcionados.
No inventes información.

Indicadores:
- Árbitros registrados: {total_arbitros}
- Partidos programados: {total_partidos}
- Asignaciones realizadas: {total_asignaciones}
- Cobertura calculada: {cobertura:.1f}%
- Alertas totales: {total_alertas}
- Alertas críticas: {criticas}
- Alertas medias: {medias}
- Sustituciones de categoría superior: {sustituciones}

Carga de campo de los principales árbitros:
{cargas or "Sin datos"}

Alertas:
{alertas_resumen or "Sin alertas"}

Redacta un análisis ejecutivo breve y profesional en español.
Incluye exactamente estas secciones:

1. Situación general
2. Hallazgos relevantes
3. Riesgos operativos
4. Recomendaciones
5. Conclusión ejecutiva

Máximo aproximadamente 700 palabras.
No utilices tablas ni Markdown complejo; utiliza títulos y párrafos
claros para que el texto pueda incorporarse directamente a un PDF.
"""

    try:
        client = OpenAI(
            api_key=api_key,
            timeout=20.0,
        )

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt,
        )

        texto = getattr(response, "output_text", None)

        if not texto:
            return (
                False,
                "La API no devolvió texto de análisis.",
            )

        return True, texto.strip()

    except Exception as error:
        mensaje = str(error)

        if "insufficient_quota" in mensaje or "429" in mensaje:
            return (
                False,
                "La API de OpenAI no tiene cuota disponible "
                "para este proyecto. El PDF ejecutivo se generó "
                "sin interpretación IA.",
            )

        return (
            False,
            f"No fue posible generar el análisis mediante IA: {mensaje}",
        )


# ============================================================
# EXCEL / CSV
# ============================================================

def generar_excel(datos, asignaciones, alertas):
    buffer = io.BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl",
    ) as writer:
        datos["arbitros"].to_excel(
            writer,
            sheet_name="Arbitros",
            index=False,
        )

        datos["disponibilidad_arbitros"].to_excel(
            writer,
            sheet_name="Disponibilidad",
            index=False,
        )

        datos["config_eventos"].to_excel(
            writer,
            sheet_name="Config_Eventos",
            index=False,
        )

        datos["programacion_partidos"].to_excel(
            writer,
            sheet_name="Partidos",
            index=False,
        )

        asignaciones.to_excel(
            writer,
            sheet_name="Asignaciones",
            index=False,
        )

        alertas.to_excel(
            writer,
            sheet_name="Alertas",
            index=False,
        )

    return buffer.getvalue()


def generar_csv(df):
    return df.to_csv(
        index=False,
        encoding="utf-8-sig",
    ).encode("utf-8-sig")


# ============================================================
# GRÁFICOS PARA PDF
# ============================================================

def grafico_alertas(alertas):
    fig, ax = plt.subplots(figsize=(8, 4.5))

    if alertas.empty:
        ax.text(
            0.5,
            0.5,
            "No existen alertas",
            ha="center",
            va="center",
            fontsize=15,
        )
        ax.axis("off")
        return fig

    conteo = alertas["severidad"].value_counts()
    conteo.plot(kind="bar", ax=ax)

    ax.set_title("Alertas por nivel de severidad")
    ax.set_xlabel("Severidad")
    ax.set_ylabel("Cantidad")
    plt.tight_layout()

    return fig


def grafico_funciones(asignaciones):
    fig, ax = plt.subplots(figsize=(8, 4.5))

    if asignaciones.empty:
        ax.text(
            0.5,
            0.5,
            "Sin asignaciones",
            ha="center",
            va="center",
            fontsize=15,
        )
        ax.axis("off")
        return fig

    conteo = asignaciones["funcion_asignada"].value_counts()
    conteo.plot(kind="bar", ax=ax)

    ax.set_title("Asignaciones por función")
    ax.set_xlabel("Función")
    ax.set_ylabel("Cantidad")
    plt.tight_layout()

    return fig


def grafico_carga(asignaciones):
    fig, ax = plt.subplots(figsize=(9, 5))

    if asignaciones.empty:
        ax.text(
            0.5,
            0.5,
            "Sin información",
            ha="center",
            va="center",
        )
        ax.axis("off")
        return fig

    campo = asignaciones[
        asignaciones["funcion_asignada"] == "CAMPO"
    ]

    if campo.empty:
        ax.text(
            0.5,
            0.5,
            "No existen asignaciones de campo",
            ha="center",
            va="center",
        )
        ax.axis("off")
        return fig

    conteo = (
        campo["nombre_completo"]
        .value_counts()
        .head(15)
        .sort_values()
    )

    conteo.plot(kind="barh", ax=ax)

    ax.set_title("Carga de árbitros de campo")
    ax.set_xlabel("Partidos")
    ax.set_ylabel("Árbitro")
    plt.tight_layout()

    return fig


def figura_a_bytes(fig):
    buffer = io.BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=140,
        bbox_inches="tight",
    )
    plt.close(fig)
    buffer.seek(0)
    return buffer


# ============================================================
# ESTILOS PDF
# ============================================================

def estilos_pdf():
    styles = getSampleStyleSheet()

    return {
        "titulo": ParagraphStyle(
            "TituloInforme",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontSize=20,
            spaceAfter=12,
        ),
        "subtitulo": ParagraphStyle(
            "SubtituloInforme",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#273746"),
            spaceBefore=10,
            spaceAfter=7,
        ),
        "normal": ParagraphStyle(
            "NormalInforme",
            parent=styles["BodyText"],
            fontSize=8.5,
            leading=11,
        ),
        "tabla": ParagraphStyle(
            "TablaInforme",
            parent=styles["BodyText"],
            fontSize=6.5,
            leading=8,
        ),
        "ia": ParagraphStyle(
            "AnalisisIA",
            parent=styles["BodyText"],
            fontSize=9,
            leading=13,
            spaceAfter=7,
        ),
    }


def p_tabla(valor, estilo):
    texto = valor_seguro(valor)
    texto = (
        texto.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return Paragraph(texto, estilo)


# ============================================================
# PDF OPERATIVO
# ============================================================

def generar_pdf_operativo(
    datos,
    asignaciones,
    alertas,
    nombre_archivo,
):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0.8 * cm,
        leftMargin=0.8 * cm,
        topMargin=0.8 * cm,
        bottomMargin=0.8 * cm,
    )

    estilos = estilos_pdf()
    elementos = []

    elementos.append(
        Paragraph(
            "INFORME OPERATIVO DE PROGRAMACIÓN",
            estilos["titulo"],
        )
    )

    elementos.append(
        Paragraph(
            f"Base procesada: {nombre_archivo}",
            estilos["normal"],
        )
    )

    elementos.append(Spacer(1, 8))

    total_partidos = len(
        datos["programacion_partidos"]
    )

    resumen = [
        ["Indicador", "Resultado"],
        ["Árbitros registrados", str(len(datos["arbitros"]))],
        ["Partidos programados", str(total_partidos)],
        ["Asignaciones realizadas", str(len(asignaciones))],
        ["Alertas generadas", str(len(alertas))],
    ]

    tabla_resumen = Table(
        resumen,
        colWidths=[7 * cm, 5 * cm],
    )

    tabla_resumen.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#273746"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.grey,
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (1, -1),
                    "CENTER",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 10))

    # --------------------------------------------------------
    # PROGRAMACIÓN / ASIGNACIONES
    # --------------------------------------------------------

    elementos.append(
        Paragraph(
            "Asignaciones y programación",
            estilos["subtitulo"],
        )
    )

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
        "sustitucion_categoria",
    ]

    columnas = [
        c for c in columnas if c in asignaciones.columns
    ]

    if asignaciones.empty:
        elementos.append(
            Paragraph(
                "No existen asignaciones.",
                estilos["normal"],
            )
        )
    else:
        encabezado = [
            p_tabla(c.replace("_", " ").title(), estilos["tabla"])
            for c in columnas
        ]

        filas = [encabezado]

        for _, fila in asignaciones.iterrows():
            filas.append(
                [
                    p_tabla(fila.get(c, ""), estilos["tabla"])
                    for c in columnas
                ]
            )

        anchos = [
            2.0, 1.7, 1.5, 1.5, 3.2, 3.0, 1.6,
            2.3, 4.0, 2.2, 2.0, 2.0, 1.8
        ]

        tabla = Table(
            filas,
            repeatRows=1,
            colWidths=[
                valor * cm
                for valor in anchos[:len(columnas)]
            ],
        )

        tabla.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#273746"),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.25,
                        colors.grey,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                ]
            )
        )

        elementos.append(tabla)

    elementos.append(PageBreak())

    # --------------------------------------------------------
    # ALERTAS
    # --------------------------------------------------------

    elementos.append(
        Paragraph(
            "Centro de alertas",
            estilos["subtitulo"],
        )
    )

    if alertas.empty:
        elementos.append(
            Paragraph(
                "No se generaron alertas.",
                estilos["normal"],
            )
        )
    else:
        columnas_alertas = [
            "id_partido",
            "fecha",
            "hora",
            "evento",
            "escenario",
            "tipo",
            "severidad",
            "categoria_requerida",
            "mensaje",
        ]

        columnas_alertas = [
            c for c in columnas_alertas
            if c in alertas.columns
        ]

        filas = [
            [
                p_tabla(
                    c.replace("_", " ").title(),
                    estilos["tabla"],
                )
                for c in columnas_alertas
            ]
        ]

        for _, fila in alertas.iterrows():
            filas.append(
                [
                    p_tabla(
                        fila.get(c, ""),
                        estilos["tabla"],
                    )
                    for c in columnas_alertas
                ]
            )

        tabla_alertas = Table(
            filas,
            repeatRows=1,
            colWidths=[
                1.5 * cm,
                2.0 * cm,
                2.4 * cm,
                3.2 * cm,
                3.0 * cm,
                1.8 * cm,
                2.0 * cm,
                2.4 * cm,
                9.0 * cm,
            ][:len(columnas_alertas)],
        )

        tabla_alertas.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#273746"),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.25,
                        colors.grey,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                ]
            )
        )

        elementos.append(tabla_alertas)

    elementos.append(PageBreak())

    # --------------------------------------------------------
    # BASE DE ÁRBITROS
    # --------------------------------------------------------

    elementos.append(
        Paragraph(
            "Base de árbitros",
            estilos["subtitulo"],
        )
    )

    arb = datos["arbitros"].copy()

    if arb.empty:
        elementos.append(
            Paragraph(
                "No existen árbitros registrados.",
                estilos["normal"],
            )
        )
    else:
        columnas_arb = list(arb.columns)

        # Para mantener el PDF operativo legible, se divide la
        # base en páginas si tiene demasiadas columnas.
        columnas_arb = columnas_arb[:12]

        filas = [
            [
                p_tabla(c, estilos["tabla"])
                for c in columnas_arb
            ]
        ]

        for _, fila in arb.iterrows():
            filas.append(
                [
                    p_tabla(fila.get(c, ""), estilos["tabla"])
                    for c in columnas_arb
                ]
            )

        ancho = 26 / max(len(columnas_arb), 1)

        tabla_arb = Table(
            filas,
            repeatRows=1,
            colWidths=[
                ancho * cm for _ in columnas_arb
            ],
        )

        tabla_arb.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#273746"),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.25,
                        colors.grey,
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                ]
            )
        )

        elementos.append(tabla_arb)

    doc.build(elementos)

    return buffer.getvalue()


# ============================================================
# PDF GERENCIAL
# ============================================================

def generar_pdf_gerencial(
    datos,
    asignaciones,
    alertas,
    nombre_archivo,
    analisis_ia,
    ia_disponible,
    detalle_ia,
):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.3 * cm,
        leftMargin=1.3 * cm,
        topMargin=1.3 * cm,
        bottomMargin=1.3 * cm,
    )

    estilos = estilos_pdf()
    elementos = []

    elementos.append(
        Paragraph(
            "INFORME GERENCIAL",
            estilos["titulo"],
        )
    )

    elementos.append(
        Paragraph(
            "Sistema de Programación y Asignación "
            "de Árbitros de Baloncesto",
            estilos["subtitulo"],
        )
    )

    elementos.append(
        Paragraph(
            f"Base procesada: {nombre_archivo}",
            estilos["normal"],
        )
    )

    elementos.append(
        Paragraph(
            f"Fecha de generación: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            estilos["normal"],
        )
    )

    elementos.append(Spacer(1, 12))

    total_arbitros = len(datos["arbitros"])
    total_partidos = len(datos["programacion_partidos"])
    total_asignaciones = len(asignaciones)
    total_alertas = len(alertas)

    criticas = 0
    medias = 0

    if not alertas.empty:
        if "severidad" in alertas.columns:
            criticas = int(
                (alertas["severidad"] == "CRÍTICA").sum()
            )
            medias = int(
                (alertas["severidad"] == "MEDIA").sum()
            )

    cobertura = (
        total_asignaciones
        / max(total_partidos, 1)
        * 100
    )

    sustituciones = 0
    if not asignaciones.empty:
        sustituciones = int(
            (
                asignaciones["sustitucion_categoria"]
                == "SI"
            ).sum()
        )

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    resumen = [
        ["Indicador", "Resultado"],
        ["Árbitros registrados", str(total_arbitros)],
        ["Partidos programados", str(total_partidos)],
        ["Asignaciones realizadas", str(total_asignaciones)],
        ["Cobertura de asignaciones", f"{cobertura:.1f}%"],
        ["Alertas totales", str(total_alertas)],
        ["Alertas críticas", str(criticas)],
        ["Alertas medias", str(medias)],
        ["Sustituciones de categoría", str(sustituciones)],
    ]

    tabla = Table(
        resumen,
        colWidths=[9 * cm, 6 * cm],
    )

    tabla.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#273746"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.grey,
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (1, -1),
                    "CENTER",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8.5,
                ),
            ]
        )
    )

    elementos.append(tabla)
    elementos.append(Spacer(1, 10))

    # --------------------------------------------------------
    # GRÁFICOS
    # --------------------------------------------------------

    elementos.append(
        Paragraph(
            "Indicadores visuales",
            estilos["subtitulo"],
        )
    )

    elementos.append(
        Image(
            figura_a_bytes(
                grafico_alertas(alertas)
            ),
            width=16 * cm,
            height=8 * cm,
        )
    )

    elementos.append(PageBreak())

    elementos.append(
        Image(
            figura_a_bytes(
                grafico_funciones(asignaciones)
            ),
            width=16 * cm,
            height=8 * cm,
        )
    )

    elementos.append(Spacer(1, 8))

    elementos.append(
        Image(
            figura_a_bytes(
                grafico_carga(asignaciones)
            ),
            width=16 * cm,
            height=8 * cm,
        )
    )

    elementos.append(PageBreak())

    # --------------------------------------------------------
    # IA
    # --------------------------------------------------------

    elementos.append(
        Paragraph(
            "Análisis ejecutivo",
            estilos["subtitulo"],
        )
    )

    if ia_disponible and analisis_ia:
        elementos.append(
            Paragraph(
                "Interpretación generada mediante IA",
                estilos["normal"],
            )
        )

        # Separar párrafos y convertirlos a elementos PDF.
        for bloque in re.split(
            r"\n\s*\n|\n",
            analisis_ia,
        ):
            bloque = bloque.strip()
            if bloque:
                elementos.append(
                    Paragraph(
                        bloque.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;"),
                        estilos["ia"],
                    )
                )
    else:
        elementos.append(
            Paragraph(
                "El análisis mediante IA no estuvo disponible "
                "para esta ejecución.",
                estilos["normal"],
            )
        )

        elementos.append(
            Spacer(1, 5)
        )

        elementos.append(
            Paragraph(
                detalle_ia,
                estilos["normal"],
            )
        )

        elementos.append(
            Spacer(1, 8)
        )

        elementos.append(
            Paragraph(
                "Resumen automático sin IA",
                estilos["subtitulo"],
            )
        )

        if criticas > 0:
            resumen_texto = (
                f"Se identificaron {criticas} alertas críticas "
                "que requieren revisión antes de considerar "
                "la programación como completamente segura."
            )
        elif total_alertas > 0:
            resumen_texto = (
                f"Se identificaron {total_alertas} alertas, "
                "sin alertas críticas."
            )
        else:
            resumen_texto = (
                "No se identificaron alertas durante el proceso."
            )

        elementos.append(
            Paragraph(
                resumen_texto,
                estilos["ia"],
            )
        )

        elementos.append(
            Paragraph(
                f"La cobertura calculada fue de {cobertura:.1f}% "
                f"con {total_asignaciones} asignaciones sobre "
                f"{total_partidos} partidos programados.",
                estilos["ia"],
            )
        )

        elementos.append(
            Paragraph(
                f"Se registraron {sustituciones} sustituciones "
                "de categoría superior.",
                estilos["ia"],
            )
        )

    elementos.append(PageBreak())

    # --------------------------------------------------------
    # RECOMENDACIONES OPERATIVAS AUTOMÁTICAS
    # --------------------------------------------------------

    elementos.append(
        Paragraph(
            "Conclusiones y recomendaciones operativas",
            estilos["subtitulo"],
        )
    )

    recomendaciones = []

    if criticas > 0:
        recomendaciones.append(
            "Revisar prioritariamente las alertas críticas "
            "antes de publicar la programación."
        )

    if cobertura < 100:
        recomendaciones.append(
            "Completar las asignaciones faltantes mediante "
            "revisión de disponibilidad, categorías o "
            "incorporación de personal adicional."
        )

    if sustituciones > 0:
        recomendaciones.append(
            "Revisar las sustituciones de categoría superior "
            "para confirmar que sean operativamente aceptables."
        )

    if not recomendaciones:
        recomendaciones.append(
            "La programación no presenta incidencias críticas "
            "según las reglas evaluadas."
        )

    for numero, recomendacion in enumerate(
        recomendaciones,
        start=1,
    ):
        elementos.append(
            Paragraph(
                f"{numero}. {recomendacion}",
                estilos["ia"],
            )
        )

    doc.build(elementos)

    return buffer.getvalue()


# ============================================================
# GRÁFICOS NATIVOS
# ============================================================

def mostrar_barras_simples(
    serie,
    titulo,
    max_items=8,
):
    if serie is None or len(serie) == 0:
        st.caption("Sin datos para mostrar.")
        return

    serie = (
        serie
        .sort_values(ascending=False)
        .head(max_items)
        .sort_values(ascending=True)
    )

    st.markdown(f"**{titulo}**")
    st.bar_chart(
        serie,
        use_container_width=True,
    )


# ============================================================
# ESTADO DE SESIÓN
# ============================================================

if "archivo_nombre" not in st.session_state:
    st.session_state.archivo_nombre = None

if "archivo_bytes" not in st.session_state:
    st.session_state.archivo_bytes = None

if "datos" not in st.session_state:
    st.session_state.datos = None

if "asignaciones" not in st.session_state:
    st.session_state.asignaciones = None

if "alertas" not in st.session_state:
    st.session_state.alertas = None

if "pdf_operativo" not in st.session_state:
    st.session_state.pdf_operativo = None

if "pdf_gerencial" not in st.session_state:
    st.session_state.pdf_gerencial = None

if "analisis_ia" not in st.session_state:
    st.session_state.analisis_ia = None

if "ia_disponible" not in st.session_state:
    st.session_state.ia_disponible = False

if "detalle_ia" not in st.session_state:
    st.session_state.detalle_ia = ""

if "reset_uploader" not in st.session_state:
    st.session_state.reset_uploader = 0


# ============================================================
# HEADER NATIVO
# ============================================================

st.title("🏀 Basketball Referees Scheduler")
st.caption(
    "Sistema inteligente de programación, asignación y "
    "control de árbitros de baloncesto."
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## 🏀 Menú")

    # Antes de cargar: uploader.
    # Después de cargar: desaparece el uploader y queda únicamente
    # el botón para iniciar una nueva carga.
    if st.session_state.archivo_bytes is None:

        archivo = st.file_uploader(
            "Cargar base de datos",
            type=["xlsx", "xls"],
            key=f"excel_upload_{st.session_state.reset_uploader}",
            help=(
                "Seleccione el Excel normalizado con las cuatro "
                "hojas requeridas."
            ),
        )

    else:
        st.success(
            "Base de datos cargada",
        )

        if st.button(
            "🔄 Cargar otra base de datos",
            use_container_width=True,
        ):
            st.session_state.archivo_nombre = None
            st.session_state.archivo_bytes = None
            st.session_state.datos = None
            st.session_state.asignaciones = None
            st.session_state.alertas = None
            st.session_state.pdf_operativo = None
            st.session_state.pdf_gerencial = None
            st.session_state.analisis_ia = None
            st.session_state.ia_disponible = False
            st.session_state.detalle_ia = ""
            st.session_state.reset_uploader += 1
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
            "📥 Descargas",
        ],
        index=0,
    )

    st.divider()

    st.caption("Sistema de asignación automática")
    st.caption("Baloncesto · Análisis de datos")


# ============================================================
# DETECTAR NUEVO ARCHIVO
# ============================================================

if (
    st.session_state.archivo_bytes is None
    and "archivo" in locals()
    and archivo is not None
):
    nuevos_bytes = archivo.getvalue()
    nuevo_nombre = archivo.name

    if (
        st.session_state.archivo_nombre != nuevo_nombre
        or st.session_state.archivo_bytes != nuevos_bytes
    ):
        st.session_state.archivo_nombre = nuevo_nombre
        st.session_state.archivo_bytes = nuevos_bytes

        # El cálculo y los informes se regeneran para la nueva base.
        st.session_state.datos = None
        st.session_state.asignaciones = None
        st.session_state.alertas = None
        st.session_state.pdf_operativo = None
        st.session_state.pdf_gerencial = None
        st.session_state.analisis_ia = None
        st.session_state.ia_disponible = False
        st.session_state.detalle_ia = ""


# ============================================================
# SIN ARCHIVO
# ============================================================

if st.session_state.archivo_bytes is None:
    st.info(
        "👈 Carga el archivo Excel normalizado desde la barra "
        "lateral para iniciar el procesamiento automático."
    )

    st.subheader("Estructura esperada")

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
# PROCESAMIENTO
# ============================================================

if st.session_state.datos is None:

    try:
        with st.spinner(
            "Procesando base de datos y ejecutando asignaciones..."
        ):
            datos = cargar_excel_archivo(
                st.session_state.archivo_bytes
            )

            asignaciones, alertas = ejecutar_asignacion(
                datos
            )

            st.session_state.datos = datos
            st.session_state.asignaciones = asignaciones
            st.session_state.alertas = alertas

        # ----------------------------------------------------
        # IA
        #
        # Se intenta una sola vez por archivo.
        # Si falla, el resto del sistema continúa.
        # ----------------------------------------------------

        with st.spinner(
            "Generando informe gerencial..."
        ):
            ia_ok, resultado_ia = generar_analisis_ia(
                datos,
                asignaciones,
                alertas,
            )

            st.session_state.ia_disponible = ia_ok

            if ia_ok:
                st.session_state.analisis_ia = resultado_ia
                st.session_state.detalle_ia = (
                    "Análisis IA generado correctamente."
                )
            else:
                st.session_state.analisis_ia = None
                st.session_state.detalle_ia = resultado_ia

        # ----------------------------------------------------
        # DOS PDF AUTOMÁTICOS
        # ----------------------------------------------------

        with st.spinner(
            "Preparando los dos informes PDF..."
        ):
            st.session_state.pdf_operativo = (
                generar_pdf_operativo(
                    datos,
                    asignaciones,
                    alertas,
                    st.session_state.archivo_nombre,
                )
            )

            st.session_state.pdf_gerencial = (
                generar_pdf_gerencial(
                    datos,
                    asignaciones,
                    alertas,
                    st.session_state.archivo_nombre,
                    st.session_state.analisis_ia,
                    st.session_state.ia_disponible,
                    st.session_state.detalle_ia,
                )
            )

    except Exception as error:
        st.error(
            "❌ Se produjo un error al procesar el archivo."
        )
        st.exception(error)
        st.stop()


# ============================================================
# REFERENCIAS DE SESIÓN
# ============================================================

datos = st.session_state.datos
asignaciones = st.session_state.asignaciones
alertas = st.session_state.alertas

nombre_archivo = st.session_state.archivo_nombre


# ============================================================
# IDENTIFICACIÓN DE BASE PROCESADA
# ============================================================

st.info(
    f"📁 Cálculos realizados con la base: **{nombre_archivo}**"
)

if st.session_state.ia_disponible:
    st.success(
        "🤖 Análisis IA disponible y agregado al informe gerencial."
    )
else:
    st.warning(
        f"🤖 {st.session_state.detalle_ia}"
    )


# ============================================================
# MÉTRICAS
# ============================================================

total_arbitros = len(datos["arbitros"])
total_partidos = len(datos["programacion_partidos"])
total_asignaciones = len(asignaciones)
total_alertas = len(alertas)

alertas_criticas = 0
alertas_medias = 0

if not alertas.empty and "severidad" in alertas.columns:
    alertas_criticas = int(
        (alertas["severidad"] == "CRÍTICA").sum()
    )
    alertas_medias = int(
        (alertas["severidad"] == "MEDIA").sum()
    )


# ============================================================
# RESUMEN
# ============================================================

if modulo == "📊 Resumen":

    st.markdown(
        '<div class="section-title">Resumen ejecutivo</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.metric("Árbitros", total_arbitros)

    with c2:
        st.metric("Partidos", total_partidos)

    with c3:
        st.metric("Asignaciones", total_asignaciones)

    with c4:
        st.metric("Alertas críticas", alertas_criticas)

    with c5:
        st.metric("Alertas medias", alertas_medias)

    st.subheader("Estado general")

    if total_alertas == 0:
        st.success(
            "🟢 Programación generada sin alertas."
        )
    elif alertas_criticas > 0:
        st.error(
            f"🔴 Existen {alertas_criticas} alertas críticas "
            "que requieren revisión."
        )
    else:
        st.warning(
            f"🟡 Se generaron {total_alertas} alertas."
        )

    col1, col2 = st.columns(2)

    with col1:
        if not asignaciones.empty:
            mostrar_barras_simples(
                asignaciones[
                    "funcion_asignada"
                ].value_counts(),
                "Asignaciones por función",
            )
        else:
            st.caption("Sin asignaciones.")

    with col2:
        if not alertas.empty:
            mostrar_barras_simples(
                alertas["severidad"].value_counts(),
                "Alertas por severidad",
            )
        else:
            st.caption("Sin alertas.")

    st.subheader("Informes automáticos")

    st.write(
        "Los dos informes fueron generados automáticamente "
        "a partir de la base procesada."
    )

    p1, p2 = st.columns(2)

    nombre_base = re.sub(
        r"\.(xlsx|xls)$",
        "",
        nombre_archivo,
        flags=re.IGNORECASE,
    )

    with p1:
        st.download_button(
            "📄 Descargar PDF operativo",
            data=st.session_state.pdf_operativo,
            file_name=(
                f"Informe_Operativo_{nombre_base}.pdf"
            ),
            mime="application/pdf",
            use_container_width=True,
        )

    with p2:
        st.download_button(
            "📊 Descargar PDF gerencial",
            data=st.session_state.pdf_gerencial,
            file_name=(
                f"Informe_Gerencial_{nombre_base}.pdf"
            ),
            mime="application/pdf",
            use_container_width=True,
        )


# ============================================================
# PROGRAMACIÓN
# ============================================================

elif modulo == "📅 Programación":

    st.markdown(
        '<div class="section-title">Programación semanal</div>',
        unsafe_allow_html=True,
    )

    if asignaciones.empty:
        st.warning("No existen asignaciones.")
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
            "sustitucion_categoria",
        ]

        columnas = [
            c for c in columnas
            if c in asignaciones.columns
        ]

        st.dataframe(
            asignaciones[columnas],
            use_container_width=True,
            height=570,
            hide_index=True,
        )


# ============================================================
# ÁRBITROS
# ============================================================

elif modulo == "👨‍⚖️ Árbitros":

    st.markdown(
        '<div class="section-title">Base de árbitros</div>',
        unsafe_allow_html=True,
    )

    st.dataframe(
        datos["arbitros"],
        use_container_width=True,
        height=550,
        hide_index=True,
    )


# ============================================================
# ALERTAS
# ============================================================

elif modulo == "🚨 Alertas":

    st.markdown(
        '<div class="section-title">Centro de alertas</div>',
        unsafe_allow_html=True,
    )

    if alertas.empty:
        st.success("🟢 No se generaron alertas.")
    else:
        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric("Total", total_alertas)

        with c2:
            st.metric("Críticas", alertas_criticas)

        with c3:
            st.metric("Medias", alertas_medias)

        st.subheader("Detalle")

        st.dataframe(
            alertas,
            use_container_width=True,
            hide_index=True,
            height=500,
        )


# ============================================================
# ESTADÍSTICAS
# ============================================================

elif modulo == "📈 Estadísticas":

    st.markdown(
        '<div class="section-title">Estadísticas de asignación</div>',
        unsafe_allow_html=True,
    )

    if asignaciones.empty:
        st.info("No existen asignaciones.")
    else:
        campo = asignaciones[
            asignaciones["funcion_asignada"] == "CAMPO"
        ]

        mesa = asignaciones[
            asignaciones["funcion_asignada"] == "MESA"
        ]

        col1, col2 = st.columns(2)

        with col1:
            if not campo.empty:
                mostrar_barras_simples(
                    campo["nombre_completo"].value_counts(),
                    "Carga de campo por árbitro",
                    max_items=10,
                )
            else:
                st.caption(
                    "No existen asignaciones de campo."
                )

        with col2:
            if not mesa.empty:
                mostrar_barras_simples(
                    mesa["nombre_completo"].value_counts(),
                    "Carga de mesa por oficial",
                    max_items=10,
                )
            else:
                st.caption(
                    "No existen asignaciones de mesa."
                )

        st.subheader("Sustituciones de categoría")

        sustituciones = asignaciones[
            asignaciones["sustitucion_categoria"] == "SI"
        ]

        if sustituciones.empty:
            st.success(
                "No fue necesario utilizar sustituciones "
                "de categoría superior."
            )
        else:
            st.warning(
                f"Se realizaron {len(sustituciones)} "
                "sustituciones de categoría superior."
            )

            st.dataframe(
                sustituciones,
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# DESCARGAS
# ============================================================

elif modulo == "📥 Descargas":

    st.markdown(
        '<div class="section-title">Centro de descargas</div>',
        unsafe_allow_html=True,
    )

    st.write(
        f"Resultados generados con la base: **{nombre_archivo}**"
    )

    nombre_base = re.sub(
        r"\.(xlsx|xls)$",
        "",
        nombre_archivo,
        flags=re.IGNORECASE,
    )

    excel_bytes = generar_excel(
        datos,
        asignaciones,
        alertas,
    )

    st.download_button(
        "📊 Descargar Excel completo",
        data=excel_bytes,
        file_name=(
            f"Programacion_{nombre_base}.xlsx"
        ),
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
    )

    if not asignaciones.empty:
        st.download_button(
            "📄 Descargar asignaciones CSV",
            data=generar_csv(asignaciones),
            file_name=(
                f"Asignaciones_{nombre_base}.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )

    if not alertas.empty:
        st.download_button(
            "🚨 Descargar alertas CSV",
            data=generar_csv(alertas),
            file_name=(
                f"Alertas_{nombre_base}.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )

    st.divider()

    st.subheader("Informes PDF automáticos")

    st.write(
        "Estos informes fueron preparados automáticamente "
        "al finalizar el procesamiento de la base."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "📄 Descargar PDF operativo",
            data=st.session_state.pdf_operativo,
            file_name=(
                f"Informe_Operativo_{nombre_base}.pdf"
            ),
            mime="application/pdf",
            use_container_width=True,
        )

    with col2:
        st.download_button(
            "📊 Descargar PDF gerencial",
            data=st.session_state.pdf_gerencial,
            file_name=(
                f"Informe_Gerencial_{nombre_base}.pdf"
            ),
            mime="application/pdf",
            use_container_width=True,
        )

    st.subheader("Estado de IA")

    if st.session_state.ia_disponible:
        st.success(
            "🤖 El informe gerencial contiene interpretación IA."
        )
    else:
        st.warning(
            "🤖 El informe gerencial fue generado sin IA."
        )
        st.caption(
            st.session_state.detalle_ia
        )


# ============================================================
# PIE
# ============================================================

st.markdown(
    '<div class="footer-text">'
    'Basketball Referees Scheduler · '
    'Sistema de programación y análisis de árbitros'
    '</div>',
    unsafe_allow_html=True,
)
