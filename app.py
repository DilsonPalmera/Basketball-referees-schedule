import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime, date, time, timedelta

import plotly.express as px

# PDF
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)


# ============================================================
# CONFIGURACIÓN GENERAL
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

st.markdown(
    """
    <style>

    .stApp {
        background-color: #f4f6f9;
    }

    section[data-testid="stSidebar"] {
        background-color: #111827;
        min-width: 245px;
        max-width: 245px;
    }

    section[data-testid="stSidebar"] * {
        color: #f9fafb;
    }

    .sidebar-title {
        font-size: 19px;
        font-weight: 700;
        color: white;
        margin-bottom: 2px;
    }

    .sidebar-subtitle {
        font-size: 11px;
        color: #9ca3af;
        margin-bottom: 10px;
    }

    div[role="radiogroup"] {
        gap: 1px !important;
    }

    div[role="radiogroup"] > label {
        padding: 3px 6px !important;
        margin: 0 !important;
        min-height: 29px !important;
        border-radius: 5px;
    }

    div[role="radiogroup"] > label:hover {
        background-color: #1f2937;
    }

    [data-testid="stFileUploader"] {
        background-color: #1f2937;
        border-radius: 7px;
        padding: 6px;
    }

    [data-testid="stFileUploader"] button {
        background-color: #2563eb !important;
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
    }

    [data-testid="stFileUploader"] button:hover {
        background-color: #1d4ed8 !important;
        color: white !important;
    }

    .kpi {
        background: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 7px rgba(0,0,0,0.06);
        border-left: 5px solid #2563eb;
    }

    .kpi-title {
        font-size: 12px;
        color: #6b7280;
    }

    .kpi-value {
        font-size: 27px;
        font-weight: 700;
        color: #111827;
    }

    .section-title {
        border-bottom: 2px solid #e5e7eb;
        padding-bottom: 6px;
        margin-top: 15px;
        margin-bottom: 15px;
    }

    .alert-red {
        background: #fee2e2;
        border-left: 5px solid #dc2626;
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 7px;
    }

    .alert-yellow {
        background: #fef3c7;
        border-left: 5px solid #d97706;
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 7px;
    }

    .alert-green {
        background: #dcfce7;
        border-left: 5px solid #16a34a;
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 7px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# CONSTANTES DEL MOTOR
# ============================================================

CATEGORIAS_CAMPO = {
    "1ra": 3,
    "2da": 2,
    "3ra": 1
}

CATEGORIAS_MESA = {
    "1ra": 2,
    "2da": 1
}

ROL_CAMPO = "arbitro de campo"
ROL_MESA = "oficial de mesa"
ROL_HIBRIDO = "hibrido"

MAX_CAMPO_DIA = 2
MAX_CAMPO_SEMANA = 14


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def limpiar_texto(valor):
    if pd.isna(valor):
        return ""

    return (
        str(valor)
        .strip()
        .lower()
        .replace("_", " ")
    )


def categoria_numero(valor):
    """
    Convierte 1ra, 2da, 3ra en un valor numérico.
    Un número mayor significa una categoría superior.
    """

    texto = limpiar_texto(valor)

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

    disponible = categoria_numero(categoria_disponible)
    requerida = categoria_numero(categoria_requerida)

    return disponible >= requerida


def es_hibrido(rol):
    texto = limpiar_texto(rol)

    return (
        "hibrido" in texto
        or "híbrido" in texto
    )


def es_campo(rol):
    texto = limpiar_texto(rol)

    return (
        "arbitro" in texto
        and "mesa" not in texto
        and not es_hibrido(texto)
    )


def es_mesa(rol):
    texto = limpiar_texto(rol)

    return (
        "mesa" in texto
        and not es_hibrido(texto)
    )


def valor_fecha(valor):

    if pd.isna(valor):
        return None

    try:
        return pd.to_datetime(valor).date()
    except Exception:
        return None


def minutos(valor):

    if pd.isna(valor):
        return None

    if isinstance(valor, datetime):
        return valor.hour * 60 + valor.minute

    if isinstance(valor, time):
        return valor.hour * 60 + valor.minute

    texto = str(valor).strip()

    try:
        partes = texto.split(":")
        return int(partes[0]) * 60 + int(partes[1])
    except Exception:
        return None


def intervalo_disponible(
    disponibilidad_arbitro,
    fecha,
    inicio,
    fin
):

    if disponibilidad_arbitro.empty:
        return False

    dia = fecha.strftime("%A").lower()

    nombres_dias = {
        "monday": ["lunes", "monday"],
        "tuesday": ["martes", "tuesday"],
        "wednesday": ["miercoles", "miércoles", "wednesday"],
        "thursday": ["jueves", "thursday"],
        "friday": ["viernes", "friday"],
        "saturday": ["sabado", "sábado", "saturday"],
        "sunday": ["domingo", "sunday"]
    }

    posibles = nombres_dias.get(dia, [])

    for _, fila in disponibilidad_arbitro.iterrows():

        dia_base = limpiar_texto(
            fila.get("dia", "")
        )

        if dia_base not in posibles:
            continue

        inicio_disp = minutos(
            fila.get("hora_inicio")
        )

        fin_disp = minutos(
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
# CARGA DEL EXCEL
# ============================================================

@st.cache_data(show_spinner=False)
def cargar_excel(bytes_archivo):

    archivo = io.BytesIO(bytes_archivo)

    excel = pd.ExcelFile(archivo)

    hojas = [
        "Arbitros",
        "Disponibilidad_Arbitros",
        "Config_Eventos",
        "Programacion_Partidos"
    ]

    datos = {}

    for hoja in hojas:

        if hoja not in excel.sheet_names:
            raise ValueError(
                f"No se encontró la hoja '{hoja}'."
            )

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

    salida = {}

    for nombre, df in datos.items():

        df = df.copy()

        df.columns = [
            str(c).strip().lower()
            for c in df.columns
        ]

        salida[nombre.lower()] = df

    return salida


# ============================================================
# PREPARACIÓN
# ============================================================

@st.cache_data(show_spinner=False)
def preparar_partidos(datos):

    partidos = datos[
        "programacion_partidos"
    ].copy()

    configuracion = datos[
        "config_eventos"
    ].copy()

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

    # El archivo ya contiene estos campos.
    # Por seguridad solo agregamos los que no existan.

    if "id_config_evento" in partidos.columns:

        for columna in columnas_config:

            if columna == "id_config_evento":
                continue

            if columna not in partidos.columns:

                mapa = configuracion.set_index(
                    "id_config_evento"
                )[columna]

                partidos[columna] = (
                    partidos["id_config_evento"]
                    .map(mapa)
                )

    partidos["fecha_dt"] = partidos[
        "fecha"
    ].apply(valor_fecha)

    partidos["inicio_min"] = partidos[
        "hora_inicio"
    ].apply(minutos)

    partidos["fin_min"] = partidos[
        "hora_fin"
    ].apply(minutos)

    partidos = partidos.sort_values(
        ["fecha_dt", "inicio_min", "escenario"],
        na_position="last"
    ).reset_index(drop=True)

    return partidos


# ============================================================
# ESTRUCTURA DE ASIGNACIONES
# ============================================================

def crear_registro_asignacion(
    partido,
    arbitro,
    funcion,
    categoria_requerida,
    sustitucion=False,
    categoria_utilizada=""
):

    return {
        "id_partido": partido.get("id_partido"),
        "evento": partido.get("evento"),
        "escenario": partido.get("escenario"),
        "rama": partido.get("rama"),
        "categoria_partido": partido.get("categoria"),
        "fecha": partido.get("fecha"),
        "dia": partido.get("dia"),
        "hora_inicio": partido.get("hora_inicio"),
        "hora_fin": partido.get("hora_fin"),
        "funcion": funcion,
        "id_arbitro": arbitro.get("id_arbitro"),
        "nombre_arbitro": arbitro.get("nombre_completo"),
        "rol_arbitral": arbitro.get("rol_arbitral"),
        "categoria_requerida": categoria_requerida,
        "categoria_utilizada": categoria_utilizada,
        "sustitucion": "SI" if sustitucion else "NO"
    }


# ============================================================
# MOTOR DE ASIGNACIÓN
# ============================================================

@st.cache_data(show_spinner=False)
def ejecutar_asignacion(datos):

    arbitros = datos["arbitros"].copy()
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

    # --------------------------------------------------------
    # Índice de disponibilidad
    # --------------------------------------------------------

    disponibilidad_por_arbitro = {
        aid: grupo.copy()
        for aid, grupo in disponibilidad.groupby(
            "id_arbitro"
        )
    }

    # --------------------------------------------------------
    # Estado de carga
    # --------------------------------------------------------

    carga_dia = {}
    carga_semana = {}

    # Lista de asignaciones anteriores por árbitro
    historial = {}

    # --------------------------------------------------------
    # Buscar candidatos
    # --------------------------------------------------------

    def candidatos(
        partido,
        funcion,
        categoria_requerida
    ):

        resultado = []

        fecha = partido["fecha_dt"]
        inicio = partido["inicio_min"]
        fin = partido["fin_min"]

        if fecha is None or inicio is None or fin is None:
            return resultado

        for _, arb in arbitros.iterrows():

            aid = arb.get("id_arbitro")

            rol = arb.get("rol_arbitral", "")

            categoria = (
                arb.get("categoria_campo")
                if funcion == "CAMPO"
                else arb.get("categoria_mesa")
            )

            # --------------------------------------------
            # Validar rol
            # --------------------------------------------

            puede = False

            if funcion == "CAMPO":

                puede = (
                    es_campo(rol)
                    or es_hibrido(rol)
                )

            else:

                puede = (
                    es_mesa(rol)
                    or es_hibrido(rol)
                )

            if not puede:
                continue

            # --------------------------------------------
            # Categoría
            # --------------------------------------------

            if not categoria_superior_o_igual(
                categoria,
                categoria_requerida
            ):
                continue

            # --------------------------------------------
            # Disponibilidad
            # --------------------------------------------

            disp = disponibilidad_por_arbitro.get(
                aid,
                pd.DataFrame()
            )

            if not intervalo_disponible(
                disp,
                fecha,
                inicio,
                fin
            ):
                continue

            # --------------------------------------------
            # Conflicto con otro partido
            # --------------------------------------------

            conflicto = False

            historial_arb = historial.get(
                aid,
                []
            )

            for anterior in historial_arb:

                if anterior["fecha"] != fecha:
                    continue

                # Solapamiento
                if (
                    inicio < anterior["fin"]
                    and fin > anterior["inicio"]
                ):
                    conflicto = True
                    break

                # ----------------------------------------
                # Partidos consecutivos
                # ----------------------------------------

                if anterior["fin"] == inicio:

                    mismo_escenario = (
                        limpiar_texto(
                            anterior["escenario"]
                        )
                        ==
                        limpiar_texto(
                            partido["escenario"]
                        )
                    )

                    # Si cambia de escenario y no existe
                    # tiempo entre partidos, no puede asignarse.
                    if not mismo_escenario:
                        conflicto = True
                        break

                    # Un mismo partido no puede tener
                    # campo y mesa simultáneamente.
                    if (
                        anterior["id_partido"]
                        == partido["id_partido"]
                    ):
                        conflicto = True
                        break

            if conflicto:
                continue

            # --------------------------------------------
            # Carga
            # --------------------------------------------

            clave_dia = (
                aid,
                fecha
            )

            clave_semana = aid

            campos_dia = carga_dia.get(
                clave_dia,
                0
            )

            campos_semana = carga_semana.get(
                clave_semana,
                0
            )

            # Máximo semanal
            if (
                funcion == "CAMPO"
                and campos_semana >= MAX_CAMPO_SEMANA
            ):
                continue

            # Límite diario recomendado.
            # NO eliminamos completamente al candidato:
            # posteriormente puede utilizarse como excepción.
            exceso_diario = (
                funcion == "CAMPO"
                and campos_dia >= MAX_CAMPO_DIA
            )

            # --------------------------------------------
            # Puntaje
            # --------------------------------------------

            categoria_n = categoria_numero(
                categoria
            )

            requerida_n = categoria_numero(
                categoria_requerida
            )

            diferencia_categoria = (
                categoria_n - requerida_n
            )

            numero_asignaciones = len(
                historial_arb
            )

            puntuacion = 0

            # Exactitud de categoría
            puntuacion += diferencia_categoria * 100

            # Balance de carga
            puntuacion += numero_asignaciones * 10

            # Penalización por exceso diario
            if exceso_diario:
                puntuacion += 1000

            # Penalización si es híbrido:
            # se utiliza, pero se prioriza personal
            # específico cuando existe.
            if es_hibrido(rol):
                puntuacion += 5

            resultado.append({
                "arbitro": arb,
                "puntuacion": puntuacion,
                "exceso_diario": exceso_diario
            })

        resultado.sort(
            key=lambda x: x["puntuacion"]
        )

        return resultado

    # --------------------------------------------------------
    # Función de asignación
    # --------------------------------------------------------

    def asignar_funcion(
        partido,
        funcion,
        categorias
    ):

        asignados_partido = []

        for posicion, categoria_req in enumerate(
            categorias,
            start=1
        ):

            if not categoria_req:
                continue

            candidatos_exactos = candidatos(
                partido,
                funcion,
                categoria_req
            )

            if not candidatos_exactos:

                # Buscar candidato excediendo
                # límite diario recomendado.
                candidatos_forzados = []

                fecha = partido["fecha_dt"]
                inicio = partido["inicio_min"]
                fin = partido["fin_min"]

                for _, arb in arbitros.iterrows():

                    aid = arb.get("id_arbitro")
                    rol = arb.get(
                        "rol_arbitral",
                        ""
                    )

                    categoria = (
                        arb.get("categoria_campo")
                        if funcion == "CAMPO"
                        else arb.get("categoria_mesa")
                    )

                    puede = (
                        (
                            funcion == "CAMPO"
                            and (
                                es_campo(rol)
                                or es_hibrido(rol)
                            )
                        )
                        or
                        (
                            funcion == "MESA"
                            and (
                                es_mesa(rol)
                                or es_hibrido(rol)
                            )
                        )
                    )

                    if not puede:
                        continue

                    if not categoria_superior_o_igual(
                        categoria,
                        categoria_req
                    ):
                        continue

                    disp = disponibilidad_por_arbitro.get(
                        aid,
                        pd.DataFrame()
                    )

                    if not intervalo_disponible(
                        disp,
                        fecha,
                        inicio,
                        fin
                    ):
                        continue

                    conflicto = False

                    for anterior in historial.get(
                        aid,
                        []
                    ):

                        if anterior["fecha"] != fecha:
                            continue

                        if (
                            inicio < anterior["fin"]
                            and fin > anterior["inicio"]
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
                                    partido["escenario"]
                                )
                            )

                            if not mismo_escenario:
                                conflicto = True
                                break

                            if (
                                anterior["id_partido"]
                                == partido["id_partido"]
                            ):
                                conflicto = True
                                break

                    if conflicto:
                        continue

                    campos_dia = carga_dia.get(
                        (aid, fecha),
                        0
                    )

                    campos_semana = carga_semana.get(
                        aid,
                        0
                    )

                    if (
                        funcion == "CAMPO"
                        and campos_semana >= MAX_CAMPO_SEMANA
                    ):
                        continue

                    candidatos_forzados.append({
                        "arbitro": arb,
                        "puntuacion": (
                            len(historial.get(aid, [])) * 10
                            + 500
                        )
                    })

                candidatos_forzados.sort(
                    key=lambda x: x["puntuacion"]
                )

                candidatos_exactos = candidatos_forzados

            if not candidatos_exactos:

                alertas.append({
                    "id_partido":
                        partido.get("id_partido"),
                    "fecha":
                        partido.get("fecha"),
                    "hora":
                        f"{partido.get('hora_inicio')} - "
                        f"{partido.get('hora_fin')}",
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
                            f"No existe personal disponible "
                            f"para {funcion.lower()} con categoría "
                            f"{categoria_req}."
                        )
                })

                continue

            seleccionado = candidatos_exactos[0]

            arb = seleccionado["arbitro"]

            aid = arb.get("id_arbitro")

            categoria_utilizada = (
                arb.get("categoria_campo")
                if funcion == "CAMPO"
                else arb.get("categoria_mesa")
            )

            sustitucion = (
                categoria_numero(categoria_utilizada)
                >
                categoria_numero(categoria_req)
            )

            registro = crear_registro_asignacion(
                partido,
                arb,
                funcion,
                categoria_req,
                sustitucion,
                categoria_utilizada
            )

            asignados_partido.append(
                registro
            )

            # ----------------------------------------
            # Actualizar historial
            # ----------------------------------------

            historial.setdefault(
                aid,
                []
            ).append({
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

            # ----------------------------------------
            # Actualizar carga
            # ----------------------------------------

            if funcion == "CAMPO":

                clave = (
                    aid,
                    partido["fecha_dt"]
                )

                carga_dia[clave] = (
                    carga_dia.get(clave, 0)
                    + 1
                )

                carga_semana[aid] = (
                    carga_semana.get(aid, 0)
                    + 1
                )

                if carga_dia[clave] > MAX_CAMPO_DIA:

                    alertas.append({
                        "id_partido":
                            partido.get("id_partido"),
                        "fecha":
                            partido.get("fecha"),
                        "hora":
                            f"{partido.get('hora_inicio')} - "
                            f"{partido.get('hora_fin')}",
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
                                f"El árbitro {arb.get('nombre_completo')} "
                                f"supera la carga recomendada de "
                                f"{MAX_CAMPO_DIA} partidos de campo "
                                f"en el día. Se utilizó como excepción "
                                f"por disponibilidad limitada."
                            )
                    })

            return asignados_partido

    # --------------------------------------------------------
    # Procesar partidos
    # --------------------------------------------------------

    for _, partido in partidos.iterrows():

        # --------------------------------------------
        # Categorías de campo
        # --------------------------------------------

        categorias_campo = []

        cantidad_campo = partido.get(
            "cant_arbitros_campo",
            0
        )

        try:
            cantidad_campo = int(
                cantidad_campo
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
                and limpiar_texto(categoria) != "n/a"
                and limpiar_texto(categoria) != ""
            ):
                categorias_campo.append(
                    str(categoria).strip()
                )

        # --------------------------------------------
        # Asignación campo
        # --------------------------------------------

        registros_campo = asignar_funcion(
            partido,
            "CAMPO",
            categorias_campo
        )

        asignaciones.extend(
            registros_campo
        )

        # --------------------------------------------
        # Categorías mesa
        # --------------------------------------------

        categorias_mesa = []

        cantidad_mesa = partido.get(
            "cant_oficiales_mesa",
            0
        )

        try:
            cantidad_mesa = int(
                cantidad_mesa
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
                and limpiar_texto(categoria) != "n/a"
                and limpiar_texto(categoria) != ""
            ):
                categorias_mesa.append(
                    str(categoria).strip()
                )

        # --------------------------------------------
        # Asignación mesa
        # --------------------------------------------

        registros_mesa = asignar_funcion(
            partido,
            "MESA",
            categorias_mesa
        )

        asignaciones.extend(
            registros_mesa
        )

    # --------------------------------------------------------
    # DataFrames
    # --------------------------------------------------------

    df_asignaciones = pd.DataFrame(
        asignaciones
    )

    df_alertas = pd.DataFrame(
        alertas
    )

    # --------------------------------------------------------
    # Alertas de sustitución
    # --------------------------------------------------------

    if not df_asignaciones.empty:

        sustituciones = df_asignaciones[
            df_asignaciones[
                "sustitucion"
            ] == "SI"
        ]

        for _, fila in sustituciones.iterrows():

            df_alertas.loc[
                len(df_alertas)
            ] = {
                "id_partido":
                    fila["id_partido"],
                "fecha":
                    fila["fecha"],
                "hora":
                    f"{fila['hora_inicio']} - "
                    f"{fila['hora_fin']}",
                "evento":
                    fila["evento"],
                "escenario":
                    fila["escenario"],
                "tipo":
                    "SUSTITUCIÓN",
                "severidad":
                    "MEDIA",
                "categoria_requerida":
                    fila["categoria_requerida"],
                "mensaje":
                    (
                        f"{fila['nombre_arbitro']} fue asignado "
                        f"con categoría {fila['categoria_utilizada']} "
                        f"para cubrir un requerimiento "
                        f"{fila['categoria_requerida']}."
                    )
            }

    return (
        df_asignaciones,
        df_alertas
    )


# ============================================================
# ESTADÍSTICAS
# ============================================================

@st.cache_data(show_spinner=False)
def calcular_estadisticas(
    asignaciones,
    alertas,
    partidos,
    arbitros
):

    resultado = {}

    resultado["total_partidos"] = len(
        partidos
    )

    resultado["total_arbitros"] = len(
        arbitros
    )

    resultado["total_asignaciones"] = len(
        asignaciones
    )

    resultado["total_alertas"] = len(
        alertas
    )

    if not asignaciones.empty:

        resultado["asignaciones_campo"] = len(
            asignaciones[
                asignaciones["funcion"] == "CAMPO"
            ]
        )

        resultado["asignaciones_mesa"] = len(
            asignaciones[
                asignaciones["funcion"] == "MESA"
            ]
        )

        resultado["sustituciones"] = len(
            asignaciones[
                asignaciones["sustitucion"] == "SI"
            ]
        )

        resultado["arbitros_utilizados"] = (
            asignaciones[
                "id_arbitro"
            ].nunique()
        )

    else:

        resultado["asignaciones_campo"] = 0
        resultado["asignaciones_mesa"] = 0
        resultado["sustituciones"] = 0
        resultado["arbitros_utilizados"] = 0

    return resultado


# ============================================================
# EXPORTACIÓN EXCEL
# ============================================================

def dataframe_excel(df, nombre_hoja="Datos"):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name=nombre_hoja[:31]
        )

    return output.getvalue()


# ============================================================
# EXPORTACIÓN PDF GENÉRICA
# ============================================================

def generar_pdf_tabla(
    titulo,
    subtitulo,
    df,
    orientacion="landscape"
):

    buffer = io.BytesIO()

    pagina = (
        landscape(letter)
        if orientacion == "landscape"
        else letter
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagina,
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm
    )

    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle(
        "TituloPersonalizado",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        spaceAfter=10
    )

    subtitulo_style = ParagraphStyle(
        "Subtitulo",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=9,
        textColor=colors.grey
    )

    elementos = []

    elementos.append(
        Paragraph(
            titulo,
            titulo_style
        )
    )

    elementos.append(
        Paragraph(
            subtitulo,
            subtitulo_style
        )
    )

    elementos.append(
        Spacer(1, 0.4 * cm)
    )

    if df.empty:

        elementos.append(
            Paragraph(
                "No existen registros para mostrar.",
                styles["Normal"]
            )
        )

    else:

        df_pdf = df.copy()

        # Limitar ancho del texto
        df_pdf = df_pdf.fillna("")

        datos_pdf = [
            list(df_pdf.columns)
        ]

        for _, fila in df_pdf.iterrows():

            datos_pdf.append([
                str(valor)[:45]
                for valor in fila.tolist()
            ])

        tabla = Table(
            datos_pdf,
            repeatRows=1
        )

        tabla.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1f4e78")
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
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
                    6
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
                    "MIDDLE"
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#f2f2f2")
                    ]
                )
            ])
        )

        elementos.append(tabla)

    doc.build(elementos)

    return buffer.getvalue()


# ============================================================
# PDF RESUMEN EJECUTIVO
# ============================================================

def generar_resumen_pdf(
    estadisticas,
    alertas
):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    styles = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "Titulo",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20
    )

    elementos = []

    elementos.append(
        Paragraph(
            "🏀 Resumen Ejecutivo",
            titulo
        )
    )

    elementos.append(
        Spacer(1, 0.5 * cm)
    )

    elementos.append(
        Paragraph(
            "Sistema de Programación Arbitral de Baloncesto",
            styles["Heading2"]
        )
    )

    elementos.append(
        Spacer(1, 0.3 * cm)
    )

    datos = [
        ["Indicador", "Resultado"],
        [
            "Partidos programados",
            estadisticas["total_partidos"]
        ],
        [
            "Árbitros registrados",
            estadisticas["total_arbitros"]
        ],
        [
            "Árbitros utilizados",
            estadisticas["arbitros_utilizados"]
        ],
        [
            "Asignaciones de campo",
            estadisticas["asignaciones_campo"]
        ],
        [
            "Asignaciones de mesa",
            estadisticas["asignaciones_mesa"]
        ],
        [
            "Sustituciones de categoría",
            estadisticas["sustituciones"]
        ],
        [
            "Alertas",
            estadisticas["total_alertas"]
        ]
    ]

    tabla = Table(
        datos,
        colWidths=[
            9 * cm,
            6 * cm
        ]
    )

    tabla.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#1f4e78")
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
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                9
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#f3f4f6")
                ]
            )
        ])
    )

    elementos.append(tabla)

    elementos.append(
        Spacer(1, 0.6 * cm)
    )

    if alertas.empty:

        elementos.append(
            Paragraph(
                "ESTADO OPERATIVO: SIN ALERTAS",
                styles["Heading3"]
            )
        )

    else:

        criticas = len(
            alertas[
                alertas["severidad"] == "CRÍTICA"
            ]
        )

        medias = len(
            alertas[
                alertas["severidad"] == "MEDIA"
            ]
        )

        elementos.append(
            Paragraph(
                f"Alertas críticas: {criticas}",
                styles["Normal"]
            )
        )

        elementos.append(
            Paragraph(
                f"Alertas de seguimiento: {medias}",
                styles["Normal"]
            )
        )

    doc.build(elementos)

    return buffer.getvalue()


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
        'Programación inteligente de baloncesto'
        '</div>',
        unsafe_allow_html=True
    )

    archivo = st.file_uploader(
        "📁 Cargar base de datos",
        type=["xlsx", "xls"],
        help=(
            "El archivo debe contener las hojas "
            "Arbitros, Disponibilidad_Arbitros, "
            "Config_Eventos y Programacion_Partidos."
        )
    )

    st.markdown("---")

    menu = st.radio(
        "Módulos",
        [
            "🏠 Inicio",
            "📅 Programación",
            "👨‍⚖️ Asignaciones",
            "📊 Estadísticas",
            "🚨 Alertas",
            "📚 Bases de datos"
        ],
        label_visibility="collapsed"
    )


# ============================================================
# SIN ARCHIVO
# ============================================================

if archivo is None:

    st.title(
        "🏀 Asignador Arbitral de Baloncesto"
    )

    st.info(
        "Cargue el archivo Excel desde la barra lateral "
        "para iniciar automáticamente el análisis."
    )

    st.markdown(
        """
        ### Flujo del sistema

        **Excel → Cruce de bases → Motor de asignación → 
        Validación → Alertas → Informes**

        El sistema utiliza las cuatro bases normalizadas:

        - `Arbitros`
        - `Disponibilidad_Arbitros`
        - `Config_Eventos`
        - `Programacion_Partidos`

        No es necesario presionar ningún botón de generación.
        """
    )

    st.stop()


# ============================================================
# PROCESAMIENTO AUTOMÁTICO
# ============================================================

try:

    with st.spinner(
        "🔄 Leyendo bases y calculando programación..."
    ):

        bytes_archivo = archivo.getvalue()

        datos_originales = cargar_excel(
            bytes_archivo
        )

        datos = normalizar_datos(
            datos_originales
        )

        partidos = preparar_partidos(
            datos
        )

        asignaciones, alertas = ejecutar_asignacion(
            datos
        )

        estadisticas = calcular_estadisticas(
            asignaciones,
            alertas,
            partidos,
            datos["arbitros"]
        )

except Exception as error:

    st.error(
        "❌ Se produjo un error al procesar el archivo."
    )

    st.exception(error)

    st.stop()


# ============================================================
# INICIO
# ============================================================

if menu == "🏠 Inicio":

    st.title(
        "🏀 Asignador Arbitral de Baloncesto"
    )

    st.caption(
        "Programación semanal automatizada de árbitros "
        "de campo y oficiales de mesa."
    )

    # --------------------------------------------------------
    # Semáforo
    # --------------------------------------------------------

    criticas = 0

    if not alertas.empty:

        criticas = len(
            alertas[
                alertas["severidad"] == "CRÍTICA"
            ]
        )

    if criticas > 0:

        st.error(
            f"🔴 ESTADO CRÍTICO — "
            f"{criticas} alerta(s) crítica(s)"
        )

    elif not alertas.empty:

        st.warning(
            f"🟡 ESTADO DE ATENCIÓN — "
            f"{len(alertas)} observación(es)"
        )

    else:

        st.success(
            "🟢 ESTADO OPERATIVO NORMAL"
        )

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    columnas = st.columns(5)

    indicadores = [
        (
            "Partidos",
            estadisticas["total_partidos"]
        ),
        (
            "Árbitros",
            estadisticas["total_arbitros"]
        ),
        (
            "Asignaciones",
            estadisticas["total_asignaciones"]
        ),
        (
            "Sustituciones",
            estadisticas["sustituciones"]
        ),
        (
            "Alertas",
            estadisticas["total_alertas"]
        )
    ]

    for columna, (titulo, valor) in zip(
        columnas,
        indicadores
    ):

        with columna:

            st.markdown(
                f"""
                <div class="kpi">
                    <div class="kpi-title">{titulo}</div>
                    <div class="kpi-value">{valor}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown(
        '<div class="section-title">'
        '<h3>Resumen de operación</h3>'
        '</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:

        if not asignaciones.empty:

            conteo = (
                asignaciones[
                    "funcion"
                ]
                .value_counts()
                .reset_index()
            )

            conteo.columns = [
                "Función",
                "Cantidad"
            ]

            fig = px.pie(
                conteo,
                names="Función",
                values="Cantidad",
                title="Distribución de asignaciones"
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                config={
                    "displayModeBar": False
                }
            )

    with c2:

        if not partidos.empty:

            conteo = (
                partidos[
                    "categoria"
                ]
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
                config={
                    "displayModeBar": False
                }
            )


# ============================================================
# PROGRAMACIÓN
# ============================================================

elif menu == "📅 Programación":

    st.title(
        "📅 Programación semanal"
    )

    if partidos.empty:

        st.warning(
            "No existen partidos programados."
        )

    else:

        tabla = partidos.copy()

        columnas = [
            "id_partido",
            "evento",
            "escenario",
            "rama",
            "categoria",
            "fecha",
            "dia",
            "hora_inicio",
            "hora_fin",
            "duracion_min"
        ]

        columnas = [
            c for c in columnas
            if c in tabla.columns
        ]

        tabla = tabla[columnas]

        st.dataframe(
            tabla,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Descargar")

        c1, c2 = st.columns(2)

        with c1:

            st.download_button(
                "⬇️ Descargar CSV",
                tabla.to_csv(
                    index=False
                ).encode("utf-8-sig"),
                "programacion_semanal.csv",
                "text/csv"
            )

        with c2:

            st.download_button(
                "⬇️ Descargar XLSX",
                dataframe_excel(
                    tabla,
                    "Programacion"
                ),
                "programacion_semanal.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


# ============================================================
# ASIGNACIONES
# ============================================================

elif menu == "👨‍⚖️ Asignaciones":

    st.title(
        "👨‍⚖️ Asignaciones arbitrales"
    )

    if asignaciones.empty:

        st.error(
            "No fue posible realizar ninguna asignación."
        )

    else:

        tabla = asignaciones.copy()

        st.dataframe(
            tabla,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Resumen de sustituciones")

        sustituciones = tabla[
            tabla["sustitucion"] == "SI"
        ]

        if sustituciones.empty:

            st.success(
                "No se requirieron sustituciones de categoría."
            )

        else:

            st.warning(
                f"Se realizaron "
                f"{len(sustituciones)} sustituciones "
                f"por categoría superior."
            )

            st.dataframe(
                sustituciones,
                use_container_width=True,
                hide_index=True
            )

        c1, c2 = st.columns(2)

        with c1:

            st.download_button(
                "⬇️ Asignaciones CSV",
                tabla.to_csv(
                    index=False
                ).encode("utf-8-sig"),
                "asignaciones.csv",
                "text/csv"
            )

        with c2:

            st.download_button(
                "⬇️ Asignaciones XLSX",
                dataframe_excel(
                    tabla,
                    "Asignaciones"
                ),
                "asignaciones.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


# ============================================================
# ESTADÍSTICAS
# ============================================================

elif menu == "📊 Estadísticas":

    st.title(
        "📊 Estadísticas de programación"
    )

    if asignaciones.empty:

        st.warning(
            "No existen asignaciones para analizar."
        )

    else:

        c1, c2 = st.columns(2)

        with c1:

            carga = (
                asignaciones[
                    asignaciones["funcion"] == "CAMPO"
                ]
                .groupby("nombre_arbitro")
                .size()
                .reset_index(
                    name="Partidos de campo"
                )
                .sort_values(
                    "Partidos de campo",
                    ascending=False
                )
            )

            fig = px.bar(
                carga.head(20),
                x="nombre_arbitro",
                y="Partidos de campo",
                title="Carga de árbitros de campo"
            )

            fig.update_layout(
                xaxis_tickangle=-45
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                config={
                    "displayModeBar": False
                }
            )

        with c2:

            sustituciones = (
                asignaciones[
                    asignaciones["sustitucion"] == "SI"
                ]
                .groupby(
                    "categoria_requerida"
                )
                .size()
                .reset_index(
                    name="Sustituciones"
                )
            )

            if not sustituciones.empty:

                fig = px.bar(
                    sustituciones,
                    x="categoria_requerida",
                    y="Sustituciones",
                    title="Sustituciones por categoría"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={
                        "displayModeBar": False
                    }
                )

            else:

                st.success(
                    "No existen sustituciones."
                )

        st.markdown(
            "### Utilización del personal"
        )

        utilizacion = (
            asignaciones
            .groupby(
                [
                    "id_arbitro",
                    "nombre_arbitro",
                    "funcion"
                ]
            )
            .size()
            .reset_index(
                name="Asignaciones"
            )
        )

        st.dataframe(
            utilizacion,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# ALERTAS
# ============================================================

elif menu == "🚨 Alertas":

    st.title(
        "🚨 Alertas y excepciones"
    )

    if alertas.empty:

        st.success(
            "🟢 No se detectaron alertas."
        )

    else:

        criticas = alertas[
            alertas["severidad"] == "CRÍTICA"
        ]

        medias = alertas[
            alertas["severidad"] == "MEDIA"
        ]

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "🔴 Críticas",
            len(criticas)
        )

        c2.metric(
            "🟡 Seguimiento",
            len(medias)
        )

        c3.metric(
            "Total",
            len(alertas)
        )

        st.markdown("### Detalle")

        for _, alerta in alertas.iterrows():

            if alerta["severidad"] == "CRÍTICA":

                clase = "alert-red"

                icono = "🔴"

            elif alerta["severidad"] == "MEDIA":

                clase = "alert-yellow"

                icono = "🟡"

            else:

                clase = "alert-green"

                icono = "🟢"

            st.markdown(
                f"""
                <div class="{clase}">
                    <strong>
                        {icono} {alerta['severidad']}
                    </strong><br>
                    <strong>
                        Partido:
                    </strong>
                    {alerta['id_partido']}
                    &nbsp; | &nbsp;
                    <strong>
                        Tipo:
                    </strong>
                    {alerta['tipo']}
                    <br>
                    {alerta['mensaje']}
                </div>
                """,
                unsafe_allow_html=True
            )

        st.download_button(
            "⬇️ Descargar alertas CSV",
            alertas.to_csv(
                index=False
            ).encode("utf-8-sig"),
            "alertas.csv",
            "text/csv"
        )

        st.download_button(
            "⬇️ Descargar alertas XLSX",
            dataframe_excel(
                alertas,
                "Alertas"
            ),
            "alertas.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# ============================================================
# BASES DE DATOS
# ============================================================

elif menu == "📚 Bases de datos":

    st.title(
        "📚 Bases de datos cargadas"
    )

    pestañas = st.tabs([
        "Árbitros",
        "Disponibilidad",
        "Configuración",
        "Partidos"
    ])

    nombres = [
        "arbitros",
        "disponibilidad_arbitros",
        "config_eventos",
        "programacion_partidos"
    ]

    for pestaña, nombre in zip(
        pestañas,
        nombres
    ):

        with pestaña:

            df = datos[nombre]

            st.caption(
                f"{len(df):,} registros"
            )

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "⬇️ Descargar XLSX",
                dataframe_excel(
                    df,
                    nombre[:31]
                ),
                f"{nombre}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_{nombre}"
            )


# ============================================================
# INFORMES
# ============================================================

st.sidebar.markdown("---")

with st.sidebar.expander(
    "📄 Informes",
    expanded=False
):

    resumen_pdf = generar_resumen_pdf(
        estadisticas,
        alertas
    )

    st.download_button(
        "📄 Resumen ejecutivo PDF",
        resumen_pdf,
        "resumen_ejecutivo.pdf",
        "application/pdf",
        key="pdf_resumen"
    )

    if not asignaciones.empty:

        programacion_pdf = generar_pdf_tabla(
            "Informe de Programación Arbitral",
            "Programación semanal generada automáticamente",
            asignaciones
        )

        st.download_button(
            "📄 Programación PDF",
            programacion_pdf,
            "informe_programacion.pdf",
            "application/pdf",
            key="pdf_programacion"
        )

    if not alertas.empty:

        alertas_pdf = generar_pdf_tabla(
            "Informe de Alertas",
            "Alertas y excepciones detectadas durante la asignación",
            alertas
        )

        st.download_button(
            "📄 Alertas PDF",
            alertas_pdf,
            "informe_alertas.pdf",
            "application/pdf",
            key="pdf_alertas"
        )