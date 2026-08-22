# ============================================================
# APP.PY
# SISTEMA DE PROGRAMACIÓN Y ASIGNACIÓN DE ÁRBITROS
# BALONCESTO
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import io
import unicodedata
from collections import defaultdict

# ============================================================
# REPORTES
# ============================================================

import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
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
    Image
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
# ESTILOS PROFESIONALES
# ============================================================

st.markdown(
    """
    <style>

    /* ======================================================
       FONDO GENERAL
       ====================================================== */

    .stApp {
        background-color: #f3f5f7;
    }

    .main {
        background-color: #f3f5f7;
    }

    /* ======================================================
       SIDEBAR
       ====================================================== */

    section[data-testid="stSidebar"] {
        background-color: #202b33;
    }

    section[data-testid="stSidebar"] * {
        color: #f4f6f7;
    }

    section[data-testid="stSidebar"] .stRadio > div {
        gap: 3px;
    }

    section[data-testid="stSidebar"] label {
        padding: 5px 8px !important;
        margin: 0 !important;
        border-radius: 6px;
        font-size: 13px;
    }

    section[data-testid="stSidebar"] label:hover {
        background-color: #34495e;
    }

    /* ======================================================
       ENCABEZADO NATIVO
       ====================================================== */

    .app-header-line {
        height: 5px;
        background: linear-gradient(
            90deg,
            #17202a,
            #273746,
            #34495e
        );
        border-radius: 0 0 8px 8px;
        margin-bottom: 15px;
    }

    /* ======================================================
       KPI
       ====================================================== */

    .kpi-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 14px;
        border: 1px solid #dfe4e8;
        box-shadow: 0 2px 7px rgba(0,0,0,0.05);
        min-height: 85px;
    }

    .kpi-title {
        font-size: 12px;
        color: #7b8794;
        margin-bottom: 5px;
    }

    .kpi-value {
        font-size: 25px;
        font-weight: 700;
        color: #17202a;
    }

    /* ======================================================
       SECCIONES
       ====================================================== */

    .section-title {
        background-color: #273746;
        color: white;
        padding: 9px 13px;
        border-radius: 7px;
        font-weight: 600;
        margin: 15px 0 10px 0;
    }

    /* ======================================================
       ALERTAS
       ====================================================== */

    .alert-critical {
        background-color: #fdecea;
        border-left: 5px solid #c0392b;
        padding: 10px 13px;
        margin-bottom: 7px;
        border-radius: 5px;
        color: #7b241c;
    }

    .alert-medium {
        background-color: #fef9e7;
        border-left: 5px solid #f1c40f;
        padding: 10px 13px;
        margin-bottom: 7px;
        border-radius: 5px;
        color: #7d6608;
    }

    .alert-low {
        background-color: #eafaf1;
        border-left: 5px solid #27ae60;
        padding: 10px 13px;
        margin-bottom: 7px;
        border-radius: 5px;
        color: #196f3d;
    }

    /* ======================================================
       BOTONES
       ====================================================== */

    .stDownloadButton button {
        background-color: #273746 !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
    }

    .stDownloadButton button:hover {
        background-color: #34495e !important;
    }

    /* ======================================================
       FILE UPLOADER
       ====================================================== */

    section[data-testid="stFileUploaderDropzone"] {
        background-color: white;
        border: 1px dashed #7f8c8d;
        border-radius: 8px;
    }

    section[data-testid="stFileUploaderDropzone"] button {
        background-color: #273746 !important;
        color: white !important;
    }

    /* ======================================================
       DATAFRAME
       ====================================================== */

    [data-testid="stDataFrame"] {
        border-radius: 7px;
        overflow: hidden;
    }

    /* ======================================================
       TÍTULOS NATIVOS
       ====================================================== */

    h1, h2, h3 {
        color: #17202a !important;
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

    if (
        "1ra" in texto
        or "primera" in texto
        or "1era" in texto
    ):
        return 3

    if (
        "2da" in texto
        or "segunda" in texto
        or "2da" in texto
    ):
        return 2

    if (
        "3ra" in texto
        or "tercera" in texto
        or "3era" in texto
    ):
        return 1

    return 0


def categoria_superior_o_igual(
    categoria_disponible,
    categoria_requerida
):

    return (
        categoria_numero(categoria_disponible)
        >=
        categoria_numero(categoria_requerida)
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

        return pd.to_datetime(
            valor,
            errors="coerce"
        )

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

            hora = pd.to_datetime(
                texto
            )

            return (
                hora.hour * 60
                + hora.minute
            )

        except Exception:

            return None


# ============================================================
# DÍAS DE LA SEMANA
# CORRECCIÓN: NO UTILIZA locale="es_ES"
# ============================================================

DIAS_SEMANA = {
    0: "lunes",
    1: "martes",
    2: "miercoles",
    3: "jueves",
    4: "viernes",
    5: "sabado",
    6: "domingo"
}


def obtener_dia_semana_es(fecha):

    try:

        fecha = pd.Timestamp(fecha)

        return DIAS_SEMANA.get(
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

        fecha_timestamp = pd.Timestamp(
            fecha
        )

        fecha_normalizada = (
            fecha_timestamp.date()
        )

        dia_semana = obtener_dia_semana_es(
            fecha_timestamp
        )

        dia_semana_ingles = (
            fecha_timestamp.day_name().lower()
        )

    except Exception:

        return False

    for _, fila in disponibilidad.iterrows():

        dia = fila.get("dia")

        if pd.isna(dia):
            continue

        fecha_disp = None

        # ----------------------------------------------------
        # INTENTAR FECHA EXACTA
        # ----------------------------------------------------

        try:

            fecha_convertida = pd.to_datetime(
                dia,
                errors="coerce"
            )

            if not pd.isna(
                fecha_convertida
            ):

                fecha_disp = (
                    fecha_convertida.date()
                )

        except Exception:

            fecha_disp = None

        # ----------------------------------------------------
        # SI NO ES FECHA, COMPARAR DÍA
        # ----------------------------------------------------

        if fecha_disp is None:

            dia_limpio = limpiar_texto(
                dia
            )

            equivalencias = {

                "lunes": "lunes",
                "monday": "lunes",

                "martes": "martes",
                "tuesday": "martes",

                "miercoles": "miercoles",
                "wednesday": "miercoles",

                "jueves": "jueves",
                "thursday": "jueves",

                "viernes": "viernes",
                "friday": "viernes",

                "sabado": "sabado",
                "saturday": "sabado",

                "domingo": "domingo",
                "sunday": "domingo"
            }

            dia_normalizado = equivalencias.get(
                dia_limpio,
                dia_limpio
            )

            if dia_normalizado != dia_semana:
                continue

        else:

            if fecha_disp != fecha_normalizada:
                continue

        # ----------------------------------------------------
        # HORARIOS
        # ----------------------------------------------------

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

    partidos["fecha_dt"] = partidos[
        "fecha"
    ].apply(convertir_fecha)

    partidos["inicio_min"] = partidos[
        "hora_inicio"
    ].apply(hora_a_minutos)

    partidos["fin_min"] = partidos[
        "hora_fin"
    ].apply(hora_a_minutos)

    partidos = partidos[
        partidos["fecha_dt"].notna()
    ].copy()

    columnas_orden = [
        "fecha_dt",
        "inicio_min"
    ]

    if "escenario" in partidos.columns:
        columnas_orden.append(
            "escenario"
        )

    if "id_partido" in partidos.columns:
        columnas_orden.append(
            "id_partido"
        )

    partidos = partidos.sort_values(
        by=columnas_orden
    )

    return partidos.reset_index(
        drop=True
    )


# ============================================================
# REGISTRO DE ASIGNACIÓN
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
            "SI"
            if sustitucion
            else "NO"
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

    partidos = preparar_partidos(
        datos
    )

    asignaciones = []
    alertas = []

    if (
        arbitros.empty
        or partidos.empty
    ):

        return (
            pd.DataFrame(),
            pd.DataFrame()
        )

    # --------------------------------------------------------
    # ÍNDICE DE DISPONIBILIDAD
    # --------------------------------------------------------

    disponibilidad_por_arbitro = {

        aid: grupo.copy()

        for aid, grupo
        in disponibilidad.groupby(
            "id_arbitro"
        )
    }

    # --------------------------------------------------------
    # ESTADO
    # --------------------------------------------------------

    carga_dia = defaultdict(int)

    carga_semana = defaultdict(int)

    historial = defaultdict(list)

    # --------------------------------------------------------
    # CANDIDATOS
    # --------------------------------------------------------

    def candidatos(
        partido,
        funcion,
        categoria_requerida
    ):

        resultado = []

        fecha = partido[
            "fecha_dt"
        ]

        inicio = partido[
            "inicio_min"
        ]

        fin = partido[
            "fin_min"
        ]

        if (
            pd.isna(fecha)
            or inicio is None
            or fin is None
        ):

            return resultado

        for _, arb in arbitros.iterrows():

            aid = arb.get(
                "id_arbitro"
            )

            rol = arb.get(
                "rol_arbitral",
                ""
            )

            # ------------------------------------------------
            # FUNCIÓN
            # ------------------------------------------------

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

            # ------------------------------------------------
            # CATEGORÍA
            # ------------------------------------------------

            if not categoria_superior_o_igual(
                categoria,
                categoria_requerida
            ):

                continue

            # ------------------------------------------------
            # DISPONIBILIDAD
            # ------------------------------------------------

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

            # ------------------------------------------------
            # CONFLICTOS
            # ------------------------------------------------

            conflicto = False

            historial_arb = historial.get(
                aid,
                []
            )

            for anterior in historial_arb:

                if (
                    anterior["fecha"]
                    != fecha
                ):

                    continue

                # Solapamiento
                if (
                    inicio < anterior["fin"]
                    and
                    fin > anterior["inicio"]
                ):

                    conflicto = True
                    break

                # Partidos consecutivos
                if (
                    anterior["fin"]
                    == inicio
                ):

                    mismo_escenario = (

                        limpiar_texto(
                            anterior[
                                "escenario"
                            ]
                        )

                        ==

                        limpiar_texto(
                            partido[
                                "escenario"
                            ]
                        )
                    )

                    if not mismo_escenario:

                        conflicto = True
                        break

                    # No puede tener campo
                    # y mesa en el mismo partido
                    if (
                        anterior[
                            "id_partido"
                        ]
                        ==
                        partido[
                            "id_partido"
                        ]
                    ):

                        conflicto = True
                        break

            if conflicto:
                continue

            # ------------------------------------------------
            # CARGA
            # ------------------------------------------------

            clave_dia = (
                aid,
                fecha.date()
            )

            campos_dia = carga_dia[
                clave_dia
            ]

            campos_semana = carga_semana[
                aid
            ]

            if (
                funcion == "CAMPO"
                and
                campos_semana
                >= MAX_CAMPO_SEMANA
            ):

                continue

            exceso_diario = (
                funcion == "CAMPO"
                and
                campos_dia
                >= MAX_CAMPO_DIA
            )

            # ------------------------------------------------
            # PUNTUACIÓN
            # ------------------------------------------------

            diferencia_categoria = (

                categoria_numero(
                    categoria
                )

                -

                categoria_numero(
                    categoria_requerida
                )
            )

            numero_asignaciones = len(
                historial_arb
            )

            puntuacion = 0

            # Categoría exacta
            puntuacion += (
                diferencia_categoria
                * 100
            )

            # Balance
            puntuacion += (
                numero_asignaciones
                * 10
            )

            # Exceso diario
            if exceso_diario:

                puntuacion += 1000

            # Híbridos penalizados
            if es_hibrido(rol):

                puntuacion += 5

            resultado.append({

                "arbitro": arb,

                "puntuacion":
                    puntuacion,

                "exceso_diario":
                    exceso_diario

            })

        resultado.sort(
            key=lambda x:
                x["puntuacion"]
        )

        return resultado

    # --------------------------------------------------------
    # ASIGNAR FUNCIÓN
    # --------------------------------------------------------

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

            # ------------------------------------------------
            # SIN CANDIDATO
            # ------------------------------------------------

            if not candidatos_disponibles:

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
                            f"{partido.get('hora_inicio')} "
                            f"- "
                            f"{partido.get('hora_fin')}"
                        ),

                    "evento":
                        partido.get(
                            "evento"
                        ),

                    "escenario":
                        partido.get(
                            "escenario"
                        ),

                    "tipo":
                        funcion,

                    "severidad":
                        "CRÍTICA",

                    "categoria_requerida":
                        categoria_req,

                    "mensaje":
                        (
                            f"No existe personal disponible "
                            f"para {funcion.lower()} con "
                            f"categoría {categoria_req}."
                        )
                })

                continue

            # ------------------------------------------------
            # SELECCIÓN
            # ------------------------------------------------

            seleccionado = (
                candidatos_disponibles[0]
            )

            arb = seleccionado[
                "arbitro"
            ]

            aid = arb.get(
                "id_arbitro"
            )

            categoria_utilizada = (

                arb.get(
                    "categoria_campo"
                )

                if funcion == "CAMPO"

                else

                arb.get(
                    "categoria_mesa"
                )
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

            asignados_partido.append(
                registro
            )

            # ------------------------------------------------
            # HISTORIAL
            # ------------------------------------------------

            historial[
                aid
            ].append({

                "id_partido":
                    partido.get(
                        "id_partido"
                    ),

                "fecha":
                    partido[
                        "fecha_dt"
                    ],

                "inicio":
                    partido[
                        "inicio_min"
                    ],

                "fin":
                    partido[
                        "fin_min"
                    ],

                "escenario":
                    partido.get(
                        "escenario"
                    ),

                "funcion":
                    funcion
            })

            # ------------------------------------------------
            # CARGA
            # ------------------------------------------------

            if funcion == "CAMPO":

                clave_dia = (

                    aid,

                    partido[
                        "fecha_dt"
                    ].date()
                )

                carga_dia[
                    clave_dia
                ] += 1

                carga_semana[
                    aid
                ] += 1

                # ------------------------------------------------
                # ALERTA DE EXCESO DIARIO
                # ------------------------------------------------

                if (
                    carga_dia[
                        clave_dia
                    ]
                    >
                    MAX_CAMPO_DIA
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
                                f"{partido.get('hora_inicio')} "
                                f"- "
                                f"{partido.get('hora_fin')}"
                            ),

                        "evento":
                            partido.get(
                                "evento"
                            ),

                        "escenario":
                            partido.get(
                                "escenario"
                            ),

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
                                f"supera la carga recomendada "
                                f"de {MAX_CAMPO_DIA} partidos "
                                f"de campo en el día."
                            )
                    })

        return asignados_partido

    # ========================================================
    # PROCESAR PARTIDOS
    # ========================================================

    for _, partido in partidos.iterrows():

        # ----------------------------------------------------
        # CAMPO
        # ----------------------------------------------------

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
            min(
                cantidad_campo,
                3
            ) + 1
        ):

            categoria = partido.get(
                f"cat_req_arb_{i}"
            )

            if (
                pd.notna(categoria)
                and
                limpiar_texto(
                    categoria
                )
                not in [
                    "",
                    "n/a",
                    "na"
                ]
            ):

                categorias_campo.append(
                    str(
                        categoria
                    ).strip()
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

        # ----------------------------------------------------
        # MESA
        # ----------------------------------------------------

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
            min(
                cantidad_mesa,
                2
            ) + 1
        ):

            categoria = partido.get(
                f"cat_req_mesa_{i}"
            )

            if (
                pd.notna(categoria)
                and
                limpiar_texto(
                    categoria
                )
                not in [
                    "",
                    "n/a",
                    "na"
                ]
            ):

                categorias_mesa.append(
                    str(
                        categoria
                    ).strip()
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

    # ========================================================
    # RESULTADOS
    # ========================================================

    df_asignaciones = pd.DataFrame(
        asignaciones
    )

    df_alertas = pd.DataFrame(
        alertas
    )

    return (
        df_asignaciones,
        df_alertas
    )


# ============================================================
# CARGAR EXCEL
# ============================================================

@st.cache_data(show_spinner=False)
def cargar_excel_archivo(
    archivo
):

    excel = pd.ExcelFile(
        archivo
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
            +
            ", ".join(faltantes)
        )

    datos = {

        "arbitros":
            pd.read_excel(
                archivo,
                sheet_name="Arbitros"
            ),

        "disponibilidad_arbitros":
            pd.read_excel(
                archivo,
                sheet_name="Disponibilidad_Arbitros"
            ),

        "config_eventos":
            pd.read_excel(
                archivo,
                sheet_name="Config_Eventos"
            ),

        "programacion_partidos":
            pd.read_excel(
                archivo,
                sheet_name="Programacion_Partidos"
            )
    }

    return datos


# ============================================================
# GENERAR EXCEL
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

        datos[
            "arbitros"
        ].to_excel(
            writer,
            sheet_name="Arbitros",
            index=False
        )

        datos[
            "disponibilidad_arbitros"
        ].to_excel(
            writer,
            sheet_name="Disponibilidad",
            index=False
        )

        datos[
            "config_eventos"
        ].to_excel(
            writer,
            sheet_name="Config_Eventos",
            index=False
        )

        datos[
            "programacion_partidos"
        ].to_excel(
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

    return (
        df.to_csv(
            index=False,
            encoding="utf-8-sig"
        )
        .encode(
            "utf-8-sig"
        )
    )


# ============================================================
# GRÁFICO PROFESIONAL PARA PDF
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
        alertas[
            "severidad"
        ]
        .value_counts()
    )

    conteo.plot(
        kind="bar",
        ax=ax
    )

    ax.set_title(
        "Alertas por nivel de severidad"
    )

    ax.set_xlabel(
        "Severidad"
    )

    ax.set_ylabel(
        "Cantidad"
    )

    plt.tight_layout()

    return fig


# ============================================================
# GRÁFICO FUNCIONES
# ============================================================

def grafico_funciones(
    asignaciones
):

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
        asignaciones[
            "funcion_asignada"
        ]
        .value_counts()
    )

    conteo.plot(
        kind="bar",
        ax=ax
    )

    ax.set_title(
        "Asignaciones por función"
    )

    ax.set_xlabel(
        "Función"
    )

    ax.set_ylabel(
        "Cantidad"
    )

    plt.tight_layout()

    return fig


# ============================================================
# GRÁFICO DE CARGA
# ============================================================

def grafico_carga(
    asignaciones
):

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

    campo = asignaciones[
        asignaciones[
            "funcion_asignada"
        ] == "CAMPO"
    ]

    if campo.empty:

        ax.text(
            0.5,
            0.5,
            "No existen asignaciones de campo"
        )

        ax.axis("off")

        return fig

    conteo = (
        campo[
            "nombre_completo"
        ]
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

    ax.set_xlabel(
        "Partidos"
    )

    ax.set_ylabel(
        "Árbitro"
    )

    plt.tight_layout()

    return fig


# ============================================================
# PDF
# ============================================================

def generar_pdf_resumen(
    datos,
    asignaciones,
    alertas
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
        "Titulo",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=12
    )

    subtitulo = ParagraphStyle(
        "Subtitulo",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor(
            "#273746"
        ),
        spaceBefore=10,
        spaceAfter=7
    )

    normal = ParagraphStyle(
        "NormalCustom",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12
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
            "Sistema de Programación de Árbitros "
            "de Baloncesto",
            subtitulo
        )
    )

    total_partidos = len(
        datos[
            "programacion_partidos"
        ]
    )

    total_arbitros = len(
        datos[
            "arbitros"
        ]
    )

    total_asignaciones = len(
        asignaciones
    )

    total_alertas = len(
        alertas
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
            "Alertas",
            str(total_alertas)
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
                colors.HexColor(
                    "#273746"
                )
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

    elementos.append(
        tabla
    )

    elementos.append(
        Spacer(1, 10)
    )

    # ========================================================
    # GRÁFICO SOLO PARA PDF
    # ========================================================

    fig1 = grafico_alertas(
        alertas
    )

    imagen1 = io.BytesIO()

    fig1.savefig(
        imagen1,
        format="png",
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig1)

    imagen1.seek(0)

    elementos.append(
        Image(
            imagen1,
            width=16 * cm,
            height=8 * cm
        )
    )

    elementos.append(
        PageBreak()
    )

    # ========================================================
    # ALERTAS
    # ========================================================

    elementos.append(
        Paragraph(
            "Informe de alertas",
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

        datos_alertas = [

            [
                "Partido",
                "Fecha",
                "Tipo",
                "Severidad",
                "Mensaje"
            ]
        ]

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
                        "mensaje",
                        ""
                    )
                )
            ])

        tabla_alertas = Table(
            datos_alertas,
            repeatRows=1,
            colWidths=[
                1.6 * cm,
                2.3 * cm,
                1.8 * cm,
                2.2 * cm,
                9 * cm
            ]
        )

        estilo_alertas = [

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor(
                    "#273746"
                )
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
                7
            )
        ]

        for fila_idx in range(
            1,
            len(datos_alertas)
        ):

            severidad = str(
                datos_alertas[
                    fila_idx
                ][3]
            )

            if severidad == "CRÍTICA":

                estilo_alertas.append(
                    (
                        "BACKGROUND",
                        (3, fila_idx),
                        (3, fila_idx),
                        colors.HexColor(
                            "#f5b7b1"
                        )
                    )
                )

            elif severidad == "MEDIA":

                estilo_alertas.append(
                    (
                        "BACKGROUND",
                        (3, fila_idx),
                        (3, fila_idx),
                        colors.HexColor(
                            "#f9e79f"
                        )
                    )
                )

        tabla_alertas.setStyle(
            TableStyle(
                estilo_alertas
            )
        )

        elementos.append(
            tabla_alertas
        )

    elementos.append(
        PageBreak()
    )

    # ========================================================
    # PROGRAMACIÓN
    # ========================================================

    elementos.append(
        Paragraph(
            "Programación semanal",
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

            "fecha",
            "hora_inicio",
            "hora_fin",
            "evento",
            "escenario",
            "categoria_partido",
            "nombre_completo",
            "funcion_asignada"
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

        tabla = Table(
            tabla_prog,
            repeatRows=1,
            colWidths=[
                2 * cm,
                1.5 * cm,
                1.5 * cm,
                3.2 * cm,
                3 * cm,
                2.2 * cm,
                4 * cm,
                2.2 * cm
            ][:len(disponibles)]
        )

        tabla.setStyle(
            TableStyle([

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#273746"
                    )
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
                    6
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
            tabla
        )

    doc.build(
        elementos
    )

    return buffer.getvalue()


# ============================================================
# GRÁFICOS SIMPLES DE LA APP
# ============================================================

def grafico_simple_barras(
    serie,
    titulo,
    max_items=8
):

    if (
        serie is None
        or len(serie) == 0
    ):

        st.caption(
            "Sin datos para mostrar."
        )

        return

    serie = (
        serie
        .head(max_items)
        .sort_values()
    )

    max_valor = max(
        float(serie.max()),
        1
    )

    st.markdown(
        f"""
        <div style="
            font-size:14px;
            font-weight:600;
            color:#273746;
            margin-bottom:8px;
        ">
            {titulo}
        </div>
        """,
        unsafe_allow_html=True
    )

    for etiqueta, valor in serie.items():

        porcentaje = (
            float(valor)
            /
            max_valor
            *
            100
        )

        st.markdown(
            f"""
            <div style="
                margin-bottom:6px;
                font-size:11px;
                color:#333333;
            ">

                <div style="
                    display:flex;
                    justify-content:space-between;
                ">

                    <span>
                        {etiqueta}
                    </span>

                    <b>
                        {int(valor)}
                    </b>

                </div>

                <div style="
                    background:#d9dde0;
                    height:7px;
                    border-radius:4px;
                    margin-top:2px;
                ">

                    <div style="
                        background:#273746;
                        width:{porcentaje:.1f}%;
                        height:7px;
                        border-radius:4px;
                    ">
                    </div>

                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# PORTADA
# CORREGIDA: NO USA HTML PARA EL TÍTULO
# ============================================================

st.markdown(
    '<div class="app-header-line"></div>',
    unsafe_allow_html=True
)

st.title(
    "🏀 Basketball Referees Scheduler"
)

st.caption(
    "Sistema inteligente de programación, "
    "asignación y control de árbitros."
)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "## 🏀 Menú"
    )

    archivo = st.file_uploader(
        "Cargar base de datos",
        type=[
            "xlsx",
            "xls"
        ],
        key="excel_upload"
    )

    st.markdown("---")

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

    st.markdown("---")

    st.caption(
        "Sistema de asignación automática"
    )

    st.caption(
        "Baloncesto · Análisis de datos"
    )


# ============================================================
# VALIDAR ARCHIVO
# ============================================================

if archivo is None:

    st.info(
        "👈 Carga el archivo Excel normalizado "
        "desde la barra lateral para iniciar "
        "el procesamiento automático."
    )

    st.markdown(
        "### Estructura esperada"
    )

    st.write(
        "El archivo debe contener las hojas:"
    )

    st.markdown(
        """
        - `Arbitros`
        - `Disponibilidad_Arbitros`
        - `Config_Eventos`
        - `Programacion_Partidos`
        """
    )

    st.markdown(
        "**Flujo:** "
        "Carga → Validación → Cruce → "
        "Asignación → Alertas → Informes"
    )

    st.stop()


# ============================================================
# PROCESAMIENTO
# ============================================================

try:

    with st.spinner(
        "Procesando base de datos..."
    ):

        datos = cargar_excel_archivo(
            archivo
        )

        (
            asignaciones,
            alertas
        ) = ejecutar_asignacion(
            datos
        )

except Exception as error:

    st.error(
        "❌ Se produjo un error al procesar "
        "el archivo."
    )

    st.exception(
        error
    )

    st.stop()


# ============================================================
# MÉTRICAS
# ============================================================

total_arbitros = len(
    datos[
        "arbitros"
    ]
)

total_partidos = len(
    datos[
        "programacion_partidos"
    ]
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

    alertas_criticas = len(
        alertas[
            alertas[
                "severidad"
            ]
            == "CRÍTICA"
        ]
    )

    alertas_medias = len(
        alertas[
            alertas[
                "severidad"
            ]
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

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-title">
                    Árbitros
                </div>

                <div class="kpi-value">
                    {total_arbitros}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-title">
                    Partidos
                </div>

                <div class="kpi-value">
                    {total_partidos}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-title">
                    Asignaciones
                </div>

                <div class="kpi-value">
                    {total_asignaciones}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

    with c4:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-title">
                    Alertas críticas
                </div>

                <div class="kpi-value">
                    {alertas_criticas}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

    with c5:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-title">
                    Alertas medias
                </div>

                <div class="kpi-value">
                    {alertas_medias}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        "### Estado general"
    )

    if total_alertas == 0:

        st.success(
            "🟢 Programación generada sin alertas."
        )

    elif alertas_criticas > 0:

        st.error(
            f"🔴 Existen {alertas_criticas} "
            "alertas críticas que requieren revisión."
        )

    else:

        st.warning(
            f"🟡 Se generaron {total_alertas} "
            "alertas durante la programación."
        )

    # ========================================================
    # GRÁFICOS SIMPLES
    # ========================================================

    col1, col2 = st.columns(2)

    with col1:

        if not asignaciones.empty:

            serie = (
                asignaciones[
                    "funcion_asignada"
                ]
                .value_counts()
            )

            grafico_simple_barras(
                serie,
                "Asignaciones por función"
            )

    with col2:

        if not alertas.empty:

            serie = (
                alertas[
                    "severidad"
                ]
                .value_counts()
            )

            grafico_simple_barras(
                serie,
                "Alertas por severidad"
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
            asignaciones[
                columnas
            ],
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
        datos[
            "arbitros"
        ],
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

        st.markdown(
            "### Detalle"
        )

        for _, alerta in alertas.iterrows():

            severidad = alerta.get(
                "severidad",
                ""
            )

            if severidad == "CRÍTICA":

                clase = (
                    "alert-critical"
                )

                icono = "🔴"

            elif severidad == "MEDIA":

                clase = (
                    "alert-medium"
                )

                icono = "🟡"

            else:

                clase = (
                    "alert-low"
                )

                icono = "🟢"

            st.markdown(
                f"""
                <div class="{clase}">

                    <b>
                        {icono}
                        {severidad}
                    </b>

                    <br>

                    Partido:
                    {alerta.get("id_partido", "")}

                    <br>

                    Fecha:
                    {alerta.get("fecha", "")}

                    <br>

                    Tipo:
                    {alerta.get("tipo", "")}

                    <br>

                    {alerta.get("mensaje", "")}

                </div>
                """,
                unsafe_allow_html=True
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
            ]
            == "CAMPO"
        ]

        mesa = asignaciones[
            asignaciones[
                "funcion_asignada"
            ]
            == "MESA"
        ]

        col1, col2 = st.columns(2)

        with col1:

            if not campo.empty:

                grafico_simple_barras(
                    campo[
                        "nombre_completo"
                    ].value_counts(),
                    "Carga de campo por árbitro",
                    max_items=10
                )

            else:

                st.caption(
                    "No existen asignaciones de campo."
                )

        with col2:

            if not mesa.empty:

                grafico_simple_barras(
                    mesa[
                        "nombre_completo"
                    ].value_counts(),
                    "Carga de mesa por oficial",
                    max_items=10
                )

            else:

                st.caption(
                    "No existen asignaciones de mesa."
                )

        st.markdown(
            "### Sustituciones de categoría"
        )

        sustituciones = (
            asignaciones[
                asignaciones[
                    "sustitucion_categoria"
                ]
                == "SI"
            ]
        )

        if sustituciones.empty:

            st.success(
                "No fue necesario utilizar "
                "sustituciones de categoría superior."
            )

        else:

            st.warning(
                f"Se realizaron "
                f"{len(sustituciones)} "
                "sustituciones de categoría superior."
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
        "Todos los informes se generan automáticamente "
        "a partir de la programación calculada."
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
    # PDF
    # ========================================================

    pdf_bytes = generar_pdf_resumen(
        datos,
        asignaciones,
        alertas
    )

    st.download_button(
        label="📕 Descargar informe PDF",
        data=pdf_bytes,
        file_name=(
            "informe_programacion_arbitros.pdf"
        ),
        mime="application/pdf",
        use_container_width=True
    )

    st.success(
        "Los gráficos profesionales se generan "
        "únicamente dentro del informe PDF. "
        "La aplicación utiliza visualizaciones "
        "ligeras para mejorar el rendimiento."
    )


# ============================================================
# PIE DE PÁGINA
# ============================================================

st.markdown(
    """
    <div style="
        margin-top:30px;
        padding:12px;
        text-align:center;
        color:#7f8c8d;
        font-size:11px;
        border-top:1px solid #dfe4e8;
    ">

        Basketball Referees Scheduler ·
        Sistema de programación y análisis de árbitros

    </div>
    """,
    unsafe_allow_html=True
)