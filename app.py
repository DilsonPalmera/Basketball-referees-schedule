import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from datetime import datetime, time
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether
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
# CSS - DISEÑO VISUAL
# ============================================================

st.markdown(
    """
    <style>

    /* Fondo general */
    .stApp {
        background-color: #f4f6f9;
    }

    /* Barra lateral */
    section[data-testid="stSidebar"] {
        background-color: #172554;
    }

    section[data-testid="stSidebar"] * {
        color: white;
    }

    /* Título principal */
    .titulo-principal {
        font-size: 36px;
        font-weight: 800;
        color: #172554;
        margin-bottom: 0px;
    }

    .subtitulo {
        font-size: 16px;
        color: #64748b;
        margin-top: 0px;
    }

    /* Tarjetas KPI */
    .kpi {
        background-color: white;
        padding: 18px;
        border-radius: 12px;
        border-left: 6px solid #2563eb;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.08);
    }

    .kpi-titulo {
        font-size: 13px;
        color: #64748b;
        font-weight: 600;
    }

    .kpi-valor {
        font-size: 28px;
        font-weight: 800;
        color: #172554;
    }

    /* Semáforo */
    .semaforo {
        padding: 20px;
        border-radius: 14px;
        text-align: center;
        font-size: 22px;
        font-weight: 800;
        margin-bottom: 20px;
    }

    .verde {
        background-color: #dcfce7;
        color: #166534;
        border: 2px solid #22c55e;
    }

    .amarillo {
        background-color: #fef9c3;
        color: #854d0e;
        border: 2px solid #eab308;
    }

    .rojo {
        background-color: #fee2e2;
        color: #991b1b;
        border: 2px solid #ef4444;
    }

    /* Alertas */
    .alerta-critica {
        background-color: #fee2e2;
        padding: 12px;
        border-radius: 8px;
        border-left: 5px solid #dc2626;
        color: #7f1d1d;
    }

    .alerta-advertencia {
        background-color: #fef3c7;
        padding: 12px;
        border-radius: 8px;
        border-left: 5px solid #f59e0b;
        color: #78350f;
    }

    .alerta-info {
        background-color: #dbeafe;
        padding: 12px;
        border-radius: 8px;
        border-left: 5px solid #2563eb;
        color: #1e3a8a;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# CONSTANTES
# ============================================================

HOJAS_REQUERIDAS = [
    "Arbitros",
    "Disponibilidad_Arbitros",
    "Config_Eventos",
    "Programacion_Partidos"
]

JERARQUIA_CAMPO = {
    "1ra": 1,
    "2da": 2,
    "3ra": 3
}

JERARQUIA_MESA = {
    "1ra": 1,
    "2da": 2
}

MAX_CAMPO_DIARIO = 2
MAX_CAMPO_SEMANAL = 14


# ============================================================
# FUNCIONES DE TEXTO Y FECHA
# ============================================================

def limpiar_texto(valor):

    if pd.isna(valor):
        return ""

    return str(valor).strip().lower()


def convertir_hora(valor):

    if pd.isna(valor):
        return None

    if isinstance(valor, time):
        return valor

    if isinstance(valor, datetime):
        return valor.time()

    try:
        return pd.to_datetime(str(valor)).time()
    except Exception:
        return None


def hora_a_minutos(valor):

    if valor is None:
        return None

    return valor.hour * 60 + valor.minute


def formatear_hora(valor):

    if valor is None:
        return ""

    if isinstance(valor, time):
        return valor.strftime("%H:%M")

    try:
        return pd.to_datetime(valor).strftime("%H:%M")
    except Exception:
        return str(valor)


def formatear_fecha(valor):

    try:
        return pd.to_datetime(valor).strftime("%d/%m/%Y")
    except Exception:
        return str(valor)


def solapamiento_horario(
    inicio_1,
    fin_1,
    inicio_2,
    fin_2
):

    if None in [
        inicio_1,
        fin_1,
        inicio_2,
        fin_2
    ]:
        return False

    return (
        inicio_1 < fin_2
        and inicio_2 < fin_1
    )


# ============================================================
# CARGA DEL EXCEL
# ============================================================

def normalizar_columnas(df):

    df = df.copy()

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    return df


def cargar_excel(archivo):

    excel = pd.ExcelFile(archivo)

    faltantes = [
        hoja
        for hoja in HOJAS_REQUERIDAS
        if hoja not in excel.sheet_names
    ]

    if faltantes:

        raise ValueError(
            "Faltan las hojas: "
            + ", ".join(faltantes)
        )

    dfs = {}

    for hoja in HOJAS_REQUERIDAS:

        dfs[hoja] = normalizar_columnas(
            pd.read_excel(
                archivo,
                sheet_name=hoja
            )
        )

    return (
        dfs["Arbitros"],
        dfs["Disponibilidad_Arbitros"],
        dfs["Config_Eventos"],
        dfs["Programacion_Partidos"]
    )


# ============================================================
# VALIDACIÓN
# ============================================================

def validar_datos(
    df_arbitros,
    df_disponibilidad,
    df_config,
    df_partidos
):

    requerimientos = {

        "Arbitros": {
            "id_arbitro",
            "nombre_completo",
            "documento_identidad",
            "email",
            "numero_celular",
            "rol_arbitral",
            "categoria_campo",
            "categoria_mesa"
        },

        "Disponibilidad_Arbitros": {
            "id_disponibilidad",
            "id_arbitro",
            "dia",
            "hora_inicio",
            "hora_fin"
        },

        "Config_Eventos": {
            "id_config_evento",
            "evento",
            "escenario",
            "rama",
            "categoria",
            "cant_arbitros_campo",
            "cat_req_arb_1",
            "cat_req_arb_2",
            "cat_req_arb_3",
            "cant_oficiales_mesa",
            "cat_req_mesa_1",
            "cat_req_mesa_2"
        },

        "Programacion_Partidos": {
            "id_partido",
            "id_config_evento",
            "evento",
            "escenario",
            "rama",
            "categoria",
            "fecha",
            "dia",
            "hora_inicio",
            "hora_fin",
            "duracion_min",
            "cant_arbitros_campo",
            "cat_req_arb_1",
            "cat_req_arb_2",
            "cat_req_arb_3",
            "cant_oficiales_mesa",
            "cat_req_mesa_1",
            "cat_req_mesa_2"
        }
    }

    errores = []

    datos = [
        ("Arbitros", df_arbitros),
        ("Disponibilidad_Arbitros", df_disponibilidad),
        ("Config_Eventos", df_config),
        ("Programacion_Partidos", df_partidos)
    ]

    for nombre, df in datos:

        faltantes = (
            requerimientos[nombre]
            - set(df.columns)
        )

        if faltantes:

            errores.append(
                f"{nombre}: faltan "
                + ", ".join(
                    sorted(faltantes)
                )
            )

    return errores


# ============================================================
# PREPARACIÓN
# ============================================================

def preparar_datos(
    df_arbitros,
    df_disponibilidad,
    df_config,
    df_partidos
):

    df_arbitros = df_arbitros.copy()
    df_disponibilidad = df_disponibilidad.copy()
    df_config = df_config.copy()
    df_partidos = df_partidos.copy()

    df_partidos["fecha"] = pd.to_datetime(
        df_partidos["fecha"],
        errors="coerce"
    )

    df_partidos["hora_inicio_obj"] = (
        df_partidos["hora_inicio"]
        .apply(convertir_hora)
    )

    df_partidos["hora_fin_obj"] = (
        df_partidos["hora_fin"]
        .apply(convertir_hora)
    )

    df_disponibilidad["hora_inicio_obj"] = (
        df_disponibilidad["hora_inicio"]
        .apply(convertir_hora)
    )

    df_disponibilidad["hora_fin_obj"] = (
        df_disponibilidad["hora_fin"]
        .apply(convertir_hora)
    )

    return (
        df_arbitros,
        df_disponibilidad,
        df_config,
        df_partidos
    )


# ============================================================
# ROLES
# ============================================================

def es_campo(rol):

    rol = limpiar_texto(rol)

    return (
        "campo" in rol
        or "hibrido" in rol
        or "híbrido" in rol
    )


def es_mesa(rol):

    rol = limpiar_texto(rol)

    return (
        "mesa" in rol
        or "hibrido" in rol
        or "híbrido" in rol
    )


# ============================================================
# CATEGORÍAS
# ============================================================

def categoria_compatible(
    categoria_arbitro,
    categoria_requerida,
    tipo
):

    disponible = limpiar_texto(
        categoria_arbitro
    )

    requerida = limpiar_texto(
        categoria_requerida
    )

    jerarquia = (
        JERARQUIA_CAMPO
        if tipo == "campo"
        else JERARQUIA_MESA
    )

    if (
        disponible not in jerarquia
        or requerida not in jerarquia
    ):
        return False

    return (
        jerarquia[disponible]
        <= jerarquia[requerida]
    )


# ============================================================
# DISPONIBILIDAD
# ============================================================

def esta_disponible(
    id_arbitro,
    dia,
    hora_inicio,
    hora_fin,
    df_disponibilidad
):

    registros = df_disponibilidad[
        df_disponibilidad["id_arbitro"]
        == id_arbitro
    ]

    dia_buscado = limpiar_texto(dia)

    for _, registro in registros.iterrows():

        if (
            limpiar_texto(
                registro["dia"]
            )
            != dia_buscado
        ):
            continue

        inicio = registro[
            "hora_inicio_obj"
        ]

        fin = registro[
            "hora_fin_obj"
        ]

        if (
            inicio is not None
            and fin is not None
            and hora_inicio >= inicio
            and hora_fin <= fin
        ):
            return True

    return False


# ============================================================
# CONFLICTOS Y DESPLAZAMIENTO
# ============================================================

def tiene_conflicto(
    id_arbitro,
    fecha,
    hora_inicio,
    hora_fin,
    escenario,
    asignaciones
):

    for asignacion in asignaciones:

        if asignacion[
            "id_arbitro"
        ] != id_arbitro:

            continue

        if asignacion[
            "fecha"
        ] != fecha:

            continue

        # Conflicto directo
        if solapamiento_horario(
            hora_inicio,
            hora_fin,
            asignacion["hora_inicio"],
            asignacion["hora_fin"]
        ):

            return True, "Solapamiento horario"

        # Cambio de escenario inmediatamente después
        if (
            asignacion["hora_fin"]
            == hora_inicio
        ):

            if (
                limpiar_texto(
                    asignacion["escenario"]
                )
                != limpiar_texto(
                    escenario
                )
            ):

                return (
                    True,
                    "Cambio de escenario sin "
                    "tiempo de desplazamiento"
                )

        # Cambio de escenario inmediatamente antes
        if (
            asignacion["hora_inicio"]
            == hora_fin
        ):

            if (
                limpiar_texto(
                    asignacion["escenario"]
                )
                != limpiar_texto(
                    escenario
                )
            ):

                return (
                    True,
                    "Cambio de escenario sin "
                    "tiempo de desplazamiento"
                )

    return False, ""


# ============================================================
# CARGA
# ============================================================

def calcular_carga(
    id_arbitro,
    fecha,
    asignaciones
):

    total = 0
    campo_dia = 0
    campo_semana = 0

    for asignacion in asignaciones:

        if (
            asignacion["id_arbitro"]
            != id_arbitro
        ):
            continue

        total += 1

        if (
            asignacion["tipo_asignacion"]
            == "Árbitro de campo"
        ):

            campo_semana += 1

            if (
                asignacion["fecha"]
                == fecha
            ):

                campo_dia += 1

    return (
        total,
        campo_dia,
        campo_semana
    )


# ============================================================
# CANDIDATOS
# ============================================================

def obtener_candidatos(
    partido,
    categoria_requerida,
    tipo,
    df_arbitros,
    df_disponibilidad,
    asignaciones
):

    candidatos = []

    for _, arbitro in df_arbitros.iterrows():

        rol = arbitro[
            "rol_arbitral"
        ]

        if tipo == "campo":

            if not es_campo(rol):
                continue

            categoria = arbitro[
                "categoria_campo"
            ]

        else:

            if not es_mesa(rol):
                continue

            categoria = arbitro[
                "categoria_mesa"
            ]

        if not categoria_compatible(
            categoria,
            categoria_requerida,
            tipo
        ):
            continue

        if not esta_disponible(
            arbitro["id_arbitro"],
            partido["dia"],
            partido["hora_inicio_obj"],
            partido["hora_fin_obj"],
            df_disponibilidad
        ):
            continue

        conflicto, _ = tiene_conflicto(
            arbitro["id_arbitro"],
            partido["fecha"],
            partido["hora_inicio_obj"],
            partido["hora_fin_obj"],
            partido["escenario"],
            asignaciones
        )

        if conflicto:
            continue

        (
            carga_total,
            campo_dia,
            campo_semana
        ) = calcular_carga(
            arbitro["id_arbitro"],
            partido["fecha"],
            asignaciones
        )

        if (
            tipo == "campo"
            and campo_semana >= MAX_CAMPO_SEMANAL
        ):
            continue

        candidatos.append(
            {
                "arbitro": arbitro,
                "categoria": categoria,
                "carga_total": carga_total,
                "campo_dia": campo_dia,
                "campo_semana": campo_semana
            }
        )

    return candidatos


# ============================================================
# SELECCIÓN
# ============================================================

def seleccionar_candidato(
    candidatos,
    categoria_requerida,
    tipo
):

    if not candidatos:
        return None

    jerarquia = (
        JERARQUIA_CAMPO
        if tipo == "campo"
        else JERARQUIA_MESA
    )

    requerida = limpiar_texto(
        categoria_requerida
    )

    for candidato in candidatos:

        candidato["nivel_sustitucion"] = (
            jerarquia[
                limpiar_texto(
                    candidato["categoria"]
                )
            ]
            -
            jerarquia[requerida]
        )

    candidatos.sort(
        key=lambda x: (
            x["nivel_sustitucion"],
            x["campo_dia"],
            x["campo_semana"],
            x["carga_total"]
        )
    )

    return candidatos[0]


# ============================================================
# GENERACIÓN DE PROGRAMACIÓN
# ============================================================

def generar_programacion(
    df_arbitros,
    df_disponibilidad,
    df_partidos
):

    asignaciones = []
    alertas = []

    partidos = df_partidos.sort_values(
        by=[
            "fecha",
            "hora_inicio_obj",
            "escenario"
        ]
    )

    for _, partido in partidos.iterrows():

        # ====================================================
        # CAMPO
        # ====================================================

        cantidad_campo = int(
            partido[
                "cant_arbitros_campo"
            ]
        )

        req_campo = [
            partido["cat_req_arb_1"],
            partido["cat_req_arb_2"],
            partido["cat_req_arb_3"]
        ]

        req_campo = [
            x for x in req_campo
            if limpiar_texto(x)
            not in ["", "n/a", "nan", "none"]
        ]

        for posicion in range(
            cantidad_campo
        ):

            categoria_requerida = (
                req_campo[posicion]
                if posicion < len(req_campo)
                else req_campo[-1]
            )

            candidatos = obtener_candidatos(
                partido,
                categoria_requerida,
                "campo",
                df_arbitros,
                df_disponibilidad,
                asignaciones
            )

            candidato = seleccionar_candidato(
                candidatos,
                categoria_requerida,
                "campo"
            )

            if candidato is None:

                nombre = "SIN ASIGNAR"
                id_arbitro = None
                categoria_real = ""
                estado = "Pendiente"

                alertas.append({
                    "tipo": "CRÍTICA",
                    "id_partido": partido["id_partido"],
                    "fecha": partido["fecha"],
                    "evento": partido["evento"],
                    "escenario": partido["escenario"],
                    "funcion": "Árbitro de campo",
                    "posicion": posicion + 1,
                    "requerimiento": categoria_requerida,
                    "detalle":
                        "No existe un árbitro "
                        "disponible y compatible."
                })

            else:

                arbitro = candidato["arbitro"]

                nombre = arbitro[
                    "nombre_completo"
                ]

                id_arbitro = arbitro[
                    "id_arbitro"
                ]

                categoria_real = candidato[
                    "categoria"
                ]

                estado = "Asignado"

                if (
                    limpiar_texto(
                        categoria_real
                    )
                    != limpiar_texto(
                        categoria_requerida
                    )
                ):

                    alertas.append({
                        "tipo": "INFORMATIVA",
                        "id_partido":
                            partido["id_partido"],
                        "fecha":
                            partido["fecha"],
                        "evento":
                            partido["evento"],
                        "escenario":
                            partido["escenario"],
                        "funcion":
                            "Árbitro de campo",
                        "posicion":
                            posicion + 1,
                        "requerimiento":
                            categoria_requerida,
                        "detalle":
                            f"Sustitución: "
                            f"{categoria_real} "
                            f"cubre "
                            f"{categoria_requerida}."
                    })

            asignaciones.append({
                "id_partido":
                    partido["id_partido"],
                "fecha":
                    partido["fecha"],
                "dia":
                    partido["dia"],
                "hora_inicio":
                    partido["hora_inicio_obj"],
                "hora_fin":
                    partido["hora_fin_obj"],
                "evento":
                    partido["evento"],
                "escenario":
                    partido["escenario"],
                "rama":
                    partido["rama"],
                "categoria":
                    partido["categoria"],
                "tipo_asignacion":
                    "Árbitro de campo",
                "posicion":
                    posicion + 1,
                "categoria_requerida":
                    categoria_requerida,
                "categoria_asignada":
                    categoria_real,
                "id_arbitro":
                    id_arbitro,
                "nombre_arbitro":
                    nombre,
                "estado":
                    estado
            })

        # ====================================================
        # MESA
        # ====================================================

        cantidad_mesa = int(
            partido[
                "cant_oficiales_mesa"
            ]
        )

        req_mesa = [
            partido["cat_req_mesa_1"],
            partido["cat_req_mesa_2"]
        ]

        req_mesa = [
            x for x in req_mesa
            if limpiar_texto(x)
            not in ["", "n/a", "nan", "none"]
        ]

        for posicion in range(
            cantidad_mesa
        ):

            categoria_requerida = (
                req_mesa[posicion]
                if posicion < len(req_mesa)
                else req_mesa[-1]
            )

            candidatos = obtener_candidatos(
                partido,
                categoria_requerida,
                "mesa",
                df_arbitros,
                df_disponibilidad,
                asignaciones
            )

            candidato = seleccionar_candidato(
                candidatos,
                categoria_requerida,
                "mesa"
            )

            if candidato is None:

                nombre = "SIN ASIGNAR"
                id_arbitro = None
                categoria_real = ""
                estado = "Pendiente"

                alertas.append({
                    "tipo": "CRÍTICA",
                    "id_partido":
                        partido["id_partido"],
                    "fecha":
                        partido["fecha"],
                    "evento":
                        partido["evento"],
                    "escenario":
                        partido["escenario"],
                    "funcion":
                        "Oficial de mesa",
                    "posicion":
                        posicion + 1,
                    "requerimiento":
                        categoria_requerida,
                    "detalle":
                        "No existe un oficial "
                        "de mesa disponible "
                        "y compatible."
                })

            else:

                arbitro = candidato["arbitro"]

                nombre = arbitro[
                    "nombre_completo"
                ]

                id_arbitro = arbitro[
                    "id_arbitro"
                ]

                categoria_real = candidato[
                    "categoria"
                ]

                estado = "Asignado"

                if (
                    limpiar_texto(
                        categoria_real
                    )
                    != limpiar_texto(
                        categoria_requerida
                    )
                ):

                    alertas.append({
                        "tipo":
                            "INFORMATIVA",
                        "id_partido":
                            partido["id_partido"],
                        "fecha":
                            partido["fecha"],
                        "evento":
                            partido["evento"],
                        "escenario":
                            partido["escenario"],
                        "funcion":
                            "Oficial de mesa",
                        "posicion":
                            posicion + 1,
                        "requerimiento":
                            categoria_requerida,
                        "detalle":
                            f"Sustitución: "
                            f"{categoria_real} "
                            f"cubre "
                            f"{categoria_requerida}."
                    })

            asignaciones.append({
                "id_partido":
                    partido["id_partido"],
                "fecha":
                    partido["fecha"],
                "dia":
                    partido["dia"],
                "hora_inicio":
                    partido["hora_inicio_obj"],
                "hora_fin":
                    partido["hora_fin_obj"],
                "evento":
                    partido["evento"],
                "escenario":
                    partido["escenario"],
                "rama":
                    partido["rama"],
                "categoria":
                    partido["categoria"],
                "tipo_asignacion":
                    "Oficial de mesa",
                "posicion":
                    posicion + 1,
                "categoria_requerida":
                    categoria_requerida,
                "categoria_asignada":
                    categoria_real,
                "id_arbitro":
                    id_arbitro,
                "nombre_arbitro":
                    nombre,
                "estado":
                    estado
            })

    df_asignaciones = pd.DataFrame(
        asignaciones
    )

    # ========================================================
    # CARGA DIARIA
    # ========================================================

    if not df_asignaciones.empty:

        campo = df_asignaciones[
            (
                df_asignaciones[
                    "tipo_asignacion"
                ]
                == "Árbitro de campo"
            )
            &
            (
                df_asignaciones[
                    "estado"
                ]
                == "Asignado"
            )
        ]

        carga = (
            campo.groupby(
                [
                    "fecha",
                    "id_arbitro",
                    "nombre_arbitro"
                ]
            )
            .size()
            .reset_index(
                name="partidos_campo"
            )
        )

        for _, fila in carga.iterrows():

            if (
                fila["partidos_campo"]
                > MAX_CAMPO_DIARIO
            ):

                alertas.append({
                    "tipo":
                        "ADVERTENCIA",
                    "id_partido":
                        "",
                    "fecha":
                        fila["fecha"],
                    "evento":
                        "",
                    "escenario":
                        "",
                    "funcion":
                        "Árbitro de campo",
                    "posicion":
                        "",
                    "requerimiento":
                        "",
                    "detalle":
                        f"{fila['nombre_arbitro']} "
                        f"fue asignado a "
                        f"{fila['partidos_campo']} "
                        f"partidos de campo "
                        f"en el día."
                })

    return (
        df_asignaciones,
        pd.DataFrame(alertas)
    )


# ============================================================
# ESTADO GENERAL
# ============================================================

def estado_programacion(
    df_asignaciones,
    df_alertas
):

    if df_asignaciones.empty:
        return (
            "rojo",
            "🔴 SIN PROGRAMACIÓN"
        )

    total = len(
        df_asignaciones
    )

    asignados = len(
        df_asignaciones[
            df_asignaciones[
                "estado"
            ] == "Asignado"
        ]
    )

    cobertura = (
        asignados / total * 100
        if total > 0
        else 0
    )

    criticas = 0

    if not df_alertas.empty:

        criticas = len(
            df_alertas[
                df_alertas["tipo"]
                == "CRÍTICA"
            ]
        )

    if criticas > 0 or cobertura < 95:

        return (
            "rojo",
            "🔴 ESTADO CRÍTICO"
        )

    if (
        cobertura < 100
        or (
            not df_alertas.empty
            and len(
                df_alertas[
                    df_alertas["tipo"]
                    == "ADVERTENCIA"
                ]
            ) > 0
        )
    ):

        return (
            "amarillo",
            "🟡 REQUIERE REVISIÓN"
        )

    return (
        "verde",
        "🟢 PROGRAMACIÓN ÓPTIMA"
    )


# ============================================================
# EXCEL
# ============================================================

def generar_excel(
    df_programacion,
    df_alertas
):

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df_programacion.to_excel(
            writer,
            sheet_name="Programacion",
            index=False
        )

        if not df_alertas.empty:

            df_alertas.to_excel(
                writer,
                sheet_name="Alertas",
                index=False
            )

        resumen = pd.DataFrame({
            "Indicador": [
                "Asignaciones",
                "Asignaciones realizadas",
                "Pendientes"
            ],
            "Valor": [
                len(df_programacion),
                len(
                    df_programacion[
                        df_programacion[
                            "estado"
                        ] == "Asignado"
                    ]
                ),
                len(
                    df_programacion[
                        df_programacion[
                            "estado"
                        ] != "Asignado"
                    ]
                )
            ]
        })

        resumen.to_excel(
            writer,
            sheet_name="Resumen",
            index=False
        )

    output.seek(0)

    return output


# ============================================================
# PDF - ESTILOS
# ============================================================

def estilos_pdf():

    estilos = getSampleStyleSheet()

    estilos.add(
        ParagraphStyle(
            name="TituloProyecto",
            parent=estilos["Title"],
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#172554"
            )
        )
    )

    estilos.add(
        ParagraphStyle(
            name="SubtituloProyecto",
            parent=estilos["Normal"],
            fontSize=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#64748B"
            )
        )
    )

    estilos.add(
        ParagraphStyle(
            name="Seccion",
            parent=estilos["Heading2"],
            fontSize=14,
            textColor=colors.HexColor(
                "#1D4ED8"
            ),
            spaceBefore=10,
            spaceAfter=8
        )
    )

    return estilos


# ============================================================
# PDF - RESUMEN EJECUTIVO
# ============================================================

def generar_pdf_resumen(
    df_arbitros,
    df_partidos,
    df_programacion,
    df_alertas
):

    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    estilos = estilos_pdf()

    elementos = []

    total_asignaciones = len(
        df_programacion
    )

    asignadas = len(
        df_programacion[
            df_programacion[
                "estado"
            ] == "Asignado"
        ]
    )

    pendientes = (
        total_asignaciones
        - asignadas
    )

    cobertura = (
        asignadas / total_asignaciones * 100
        if total_asignaciones
        else 0
    )

    criticas = 0
    advertencias = 0
    informativas = 0

    if not df_alertas.empty:

        criticas = len(
            df_alertas[
                df_alertas["tipo"]
                == "CRÍTICA"
            ]
        )

        advertencias = len(
            df_alertas[
                df_alertas["tipo"]
                == "ADVERTENCIA"
            ]
        )

        informativas = len(
            df_alertas[
                df_alertas["tipo"]
                == "INFORMATIVA"
            ]
        )

    elementos.append(
        Paragraph(
            "🏀 PROGRAMACIÓN ARBITRAL",
            estilos["TituloProyecto"]
        )
    )

    elementos.append(
        Paragraph(
            "Resumen Ejecutivo",
            estilos["SubtituloProyecto"]
        )
    )

    elementos.append(Spacer(1, 15))

    indicadores = [
        ["Árbitros", len(df_arbitros)],
        ["Partidos", len(df_partidos)],
        ["Asignaciones", total_asignaciones],
        ["Cobertura", f"{cobertura:.1f}%"],
        ["Críticas", criticas],
        ["Advertencias", advertencias]
    ]

    tabla = Table(
        [
            [
                "Indicador",
                "Valor"
            ]
        ]
        + indicadores,
        colWidths=[8 * cm, 7 * cm]
    )

    tabla.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#172554")
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
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#CBD5E1")
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#F8FAFC")
                ]
            ),
            (
                "ALIGN",
                (1, 1),
                (1, -1),
                "CENTER"
            )
        ])
    )

    elementos.append(tabla)

    elementos.append(
        Spacer(1, 15)
    )

    if criticas > 0:

        estado = "CRÍTICO"
        color = "#DC2626"

    elif advertencias > 0 or cobertura < 100:

        estado = "REQUIERE REVISIÓN"
        color = "#CA8A04"

    else:

        estado = "ÓPTIMO"
        color = "#16A34A"

    estado_tabla = Table(
        [
            [
                Paragraph(
                    f"<b>ESTADO GENERAL: "
                    f"{estado}</b>",
                    estilos["Normal"]
                )
            ]
        ],
        colWidths=[15 * cm]
    )

    estado_tabla.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.HexColor(color)
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, -1),
                colors.white
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                12
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                12
            )
        ])
    )

    elementos.append(
        estado_tabla
    )

    elementos.append(
        Spacer(1, 15)
    )

    elementos.append(
        Paragraph(
            "Hallazgos principales",
            estilos["Seccion"]
        )
    )

    hallazgos = [
        f"Se programaron {len(df_partidos)} partidos.",
        f"Se generaron {total_asignaciones} posiciones de personal.",
        f"La cobertura alcanzó {cobertura:.1f}%.",
        f"Quedaron {pendientes} posiciones sin asignar."
    ]

    for hallazgo in hallazgos:

        elementos.append(
            Paragraph(
                "• " + hallazgo,
                estilos["Normal"]
            )
        )

    elementos.append(
        Spacer(1, 15)
    )

    elementos.append(
        Paragraph(
            "Distribución de alertas",
            estilos["Seccion"]
        )
    )

    tabla_alertas = Table(
        [
            [
                "Tipo",
                "Cantidad"
            ],
            [
                "Críticas",
                criticas
            ],
            [
                "Advertencias",
                advertencias
            ],
            [
                "Informativas",
                informativas
            ]
        ],
        colWidths=[
            10 * cm,
            5 * cm
        ]
    )

    tabla_alertas.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#172554")
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
                0.5,
                colors.HexColor("#CBD5E1")
            ),
            (
                "ALIGN",
                (1, 1),
                (1, -1),
                "CENTER"
            )
        ])
    )

    elementos.append(
        tabla_alertas
    )

    doc.build(elementos)

    output.seek(0)

    return output


# ============================================================
# PDF - PROGRAMACIÓN
# ============================================================

def generar_pdf_programacion(
    df_programacion
):

    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(letter),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm
    )

    estilos = estilos_pdf()

    elementos = []

    elementos.append(
        Paragraph(
            "🏀 INFORME DE PROGRAMACIÓN ARBITRAL",
            estilos["TituloProyecto"]
        )
    )

    elementos.append(
        Spacer(1, 10)
    )

    columnas = [
        "Fecha",
        "Hora",
        "Escenario",
        "Evento",
        "Categoría",
        "Función",
        "Pos.",
        "Árbitro",
        "Req.",
        "Asign.",
        "Estado"
    ]

    datos = [columnas]

    for _, fila in df_programacion.iterrows():

        datos.append([
            formatear_fecha(
                fila["fecha"]
            ),
            (
                f"{formatear_hora(fila['hora_inicio'])}"
                f" - "
                f"{formatear_hora(fila['hora_fin'])}"
            ),
            str(
                fila["escenario"]
            ),
            str(
                fila["evento"]
            ),
            str(
                fila["categoria"]
            ),
            str(
                fila["tipo_asignacion"]
            ).replace(
                "Árbitro de campo",
                "Campo"
            ).replace(
                "Oficial de mesa",
                "Mesa"
            ),
            str(
                fila["posicion"]
            ),
            str(
                fila["nombre_arbitro"]
            ),
            str(
                fila["categoria_requerida"]
            ),
            str(
                fila["categoria_asignada"]
            ),
            str(
                fila["estado"]
            )
        ])

    tabla = Table(
        datos,
        repeatRows=1,
        colWidths=[
            2.0 * cm,
            2.5 * cm,
            3.0 * cm,
            4.0 * cm,
            2.0 * cm,
            2.0 * cm,
            1.0 * cm,
            4.0 * cm,
            1.5 * cm,
            1.5 * cm,
            2.0 * cm
        ]
    )

    estilo = [
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#172554")
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
            colors.HexColor("#CBD5E1")
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE"
        )
    ]

    for fila in range(
        1,
        len(datos)
    ):

        estado = datos[fila][-1]
        categoria_asignada = datos[fila][-2]
        categoria_req = datos[fila][-3]

        if estado == "Pendiente":

            estilo.append(
                (
                    "BACKGROUND",
                    (0, fila),
                    (-1, fila),
                    colors.HexColor("#FEE2E2")
                )
            )

        elif (
            categoria_asignada
            != categoria_req
            and categoria_asignada
        ):

            estilo.append(
                (
                    "BACKGROUND",
                    (0, fila),
                    (-1, fila),
                    colors.HexColor("#DBEAFE")
                )
            )

    tabla.setStyle(
        TableStyle(estilo)
    )

    elementos.append(tabla)

    doc.build(elementos)

    output.seek(0)

    return output


# ============================================================
# PDF - ALERTAS
# ============================================================

def generar_pdf_alertas(
    df_alertas
):

    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(letter),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm
    )

    estilos = estilos_pdf()

    elementos = []

    elementos.append(
        Paragraph(
            "🚨 INFORME DE ALERTAS",
            estilos["TituloProyecto"]
        )
    )

    elementos.append(
        Spacer(1, 10)
    )

    if df_alertas.empty:

        elementos.append(
            Paragraph(
                "No se generaron alertas.",
                estilos["Normal"]
            )
        )

    else:

        datos = [[
            "Nivel",
            "Partido",
            "Fecha",
            "Evento",
            "Escenario",
            "Función",
            "Pos.",
            "Requerimiento",
            "Detalle"
        ]]

        for _, fila in df_alertas.iterrows():

            datos.append([
                str(fila["tipo"]),
                str(fila["id_partido"]),
                formatear_fecha(
                    fila["fecha"]
                ),
                str(fila["evento"]),
                str(fila["escenario"]),
                str(fila["funcion"]),
                str(fila["posicion"]),
                str(fila["requerimiento"]),
                str(fila["detalle"])
            ])

        tabla = Table(
            datos,
            repeatRows=1,
            colWidths=[
                2.2 * cm,
                2.0 * cm,
                2.2 * cm,
                4 * cm,
                3 * cm,
                3 * cm,
                1 * cm,
                2.5 * cm,
                8 * cm
            ]
        )

        estilo = [
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#172554")
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
                colors.HexColor("#CBD5E1")
            )
        ]

        for fila in range(
            1,
            len(datos)
        ):

            nivel = datos[fila][0]

            if nivel == "CRÍTICA":

                color = "#FECACA"

            elif nivel == "ADVERTENCIA":

                color = "#FEF3C7"

            else:

                color = "#DBEAFE"

            estilo.append(
                (
                    "BACKGROUND",
                    (0, fila),
                    (-1, fila),
                    colors.HexColor(color)
                )
            )

        tabla.setStyle(
            TableStyle(estilo)
        )

        elementos.append(tabla)

    doc.build(elementos)

    output.seek(0)

    return output


# ============================================================
# EXPORTACIÓN DE TABLAS
# ============================================================

def preparar_programacion_exportacion(
    df
):

    resultado = df.copy()

    if "fecha" in resultado:

        resultado["fecha"] = resultado[
            "fecha"
        ].apply(
            formatear_fecha
        )

    if "hora_inicio" in resultado:

        resultado["hora_inicio"] = resultado[
            "hora_inicio"
        ].apply(
            formatear_hora
        )

    if "hora_fin" in resultado:

        resultado["hora_fin"] = resultado[
            "hora_fin"
        ].apply(
            formatear_hora
        )

    columnas = [
        "id_partido",
        "fecha",
        "dia",
        "hora_inicio",
        "hora_fin",
        "evento",
        "escenario",
        "rama",
        "categoria",
        "tipo_asignacion",
        "posicion",
        "categoria_requerida",
        "categoria_asignada",
        "id_arbitro",
        "nombre_arbitro",
        "estado"
    ]

    columnas = [
        c for c in columnas
        if c in resultado.columns
    ]

    return resultado[columnas]


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <h2 style="text-align:center;">
        🏀 ASIGNADOR<br>ARBITRAL
        </h2>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown(
        "### 📂 Base de datos"
    )

    archivo = st.file_uploader(
        "Cargar archivo Excel",
        type=["xlsx", "xls"],
        help=(
            "El archivo debe contener las cuatro "
            "hojas normalizadas."
        )
    )

    st.divider()

    st.markdown(
        "### 🧭 Módulos"
    )

    modulo = st.radio(
        "Seleccione",
        [
            "📊 Dashboard",
            "👨‍⚖️ Árbitros",
            "📅 Disponibilidad",
            "🏀 Partidos",
            "🎯 Programación",
            "🚨 Alertas",
            "📄 Informes"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    st.caption(
        "Proyecto Final · Análisis de Datos Junior"
    )


# ============================================================
# ENCABEZADO
# ============================================================

st.markdown(
    '<div class="titulo-principal">'
    '🏀 Asignador de Árbitros de Baloncesto'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitulo">'
    'Sistema de programación, análisis de carga y '
    'gestión de alertas arbitrales'
    '</div>',
    unsafe_allow_html=True
)

st.divider()


# ============================================================
# SIN ARCHIVO
# ============================================================

if archivo is None:

    st.info(
        "📂 Carga el archivo Excel desde la barra lateral "
        "para iniciar automáticamente el análisis."
    )

    st.markdown(
        """
        ### 📗 Estructura requerida

        El archivo debe contener:

        - `Arbitros`
        - `Disponibilidad_Arbitros`
        - `Config_Eventos`
        - `Programacion_Partidos`

        Una vez cargado, **no necesitas presionar ningún botón**.
        La aplicación procesará automáticamente la programación.
        """
    )

    st.stop()


# ============================================================
# CARGA Y VALIDACIÓN
# ============================================================

try:

    (
        df_arbitros,
        df_disponibilidad,
        df_config,
        df_partidos
    ) = cargar_excel(
        archivo
    )

except Exception as error:

    st.error(
        f"❌ Error al cargar el Excel: {error}"
    )

    st.stop()


errores = validar_datos(
    df_arbitros,
    df_disponibilidad,
    df_config,
    df_partidos
)

if errores:

    st.error(
        "❌ La estructura del archivo presenta errores."
    )

    for error in errores:

        st.write(
            f"- {error}"
        )

    st.stop()


# ============================================================
# PREPARAR
# ============================================================

(
    df_arbitros,
    df_disponibilidad,
    df_config,
    df_partidos
) = preparar_datos(
    df_arbitros,
    df_disponibilidad,
    df_config,
    df_partidos
)


# ============================================================
# GENERACIÓN AUTOMÁTICA
# ============================================================

with st.spinner(
    "⚙️ Analizando datos y generando programación..."
):

    (
        df_programacion,
        df_alertas
    ) = generar_programacion(
        df_arbitros,
        df_disponibilidad,
        df_partidos
    )


# ============================================================
# EXPORTACIONES
# ============================================================

df_programacion_export = (
    preparar_programacion_exportacion(
        df_programacion
    )
)

df_alertas_export = (
    df_alertas.copy()
)

if not df_alertas_export.empty:

    df_alertas_export["fecha"] = (
        df_alertas_export["fecha"]
        .apply(formatear_fecha)
    )


# ============================================================
# MÉTRICAS
# ============================================================

total_posiciones = len(
    df_programacion
)

total_asignadas = len(
    df_programacion[
        df_programacion[
            "estado"
        ] == "Asignado"
    ]
)

total_pendientes = (
    total_posiciones
    - total_asignadas
)

cobertura = (
    total_asignadas
    / total_posiciones
    * 100
    if total_posiciones
    else 0
)

criticas = 0
advertencias = 0
informativas = 0

if not df_alertas.empty:

    criticas = len(
        df_alertas[
            df_alertas["tipo"]
            == "CRÍTICA"
        ]
    )

    advertencias = len(
        df_alertas[
            df_alertas["tipo"]
            == "ADVERTENCIA"
        ]
    )

    informativas = len(
        df_alertas[
            df_alertas["tipo"]
            == "INFORMATIVA"
        ]
    )


# ============================================================
# ESTADO
# ============================================================

clase_estado, texto_estado = (
    estado_programacion(
        df_programacion,
        df_alertas
    )
)

st.markdown(
    f"""
    <div class="semaforo {clase_estado}">
        {texto_estado}<br>
        <span style="font-size:16px;">
        Cobertura: {cobertura:.1f}% |
        Posiciones pendientes: {total_pendientes}
        </span>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# DASHBOARD
# ============================================================

if modulo == "📊 Dashboard":

    st.header(
        "📊 Dashboard ejecutivo"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.markdown(
            f"""
            <div class="kpi">
            <div class="kpi-titulo">
            🏀 PARTIDOS
            </div>
            <div class="kpi-valor">
            {len(df_partidos)}
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:

        st.markdown(
            f"""
            <div class="kpi">
            <div class="kpi-titulo">
            👨‍⚖️ ÁRBITROS
            </div>
            <div class="kpi-valor">
            {len(df_arbitros)}
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:

        st.markdown(
            f"""
            <div class="kpi">
            <div class="kpi-titulo">
            📈 COBERTURA
            </div>
            <div class="kpi-valor">
            {cobertura:.1f}%
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c4:

        st.markdown(
            f"""
            <div class="kpi">
            <div class="kpi-titulo">
            🚨 ALERTAS
            </div>
            <div class="kpi-valor">
            {len(df_alertas)}
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    # ========================================================
    # GRÁFICOS
    # ========================================================

    col1, col2 = st.columns(2)

    with col1:

        st.subheader(
            "🏀 Partidos por día"
        )

        partidos_dia = (
            df_partidos
            .groupby("dia")
            .size()
            .reset_index(
                name="Partidos"
            )
        )

        fig = px.bar(
            partidos_dia,
            x="dia",
            y="Partidos",
            text="Partidos",
            title="Distribución semanal"
        )

        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        st.subheader(
            "🎯 Partidos por categoría"
        )

        partidos_categoria = (
            df_partidos
            .groupby("categoria")
            .size()
            .reset_index(
                name="Partidos"
            )
        )

        fig = px.pie(
            partidos_categoria,
            names="categoria",
            values="Partidos",
            hole=0.45
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # ========================================================
    # CARGA ARBITRAL
    # ========================================================

    st.subheader(
        "⚖️ Carga de partidos de campo"
    )

    campo = df_programacion[
        (
            df_programacion[
                "tipo_asignacion"
            ]
            == "Árbitro de campo"
        )
        &
        (
            df_programacion[
                "estado"
            ]
            == "Asignado"
        )
    ]

    if not campo.empty:

        carga = (
            campo
            .groupby(
                "nombre_arbitro"
            )
            .size()
            .reset_index(
                name="Partidos"
            )
            .sort_values(
                "Partidos",
                ascending=False
            )
        )

        fig = px.bar(
            carga,
            x="nombre_arbitro",
            y="Partidos",
            text="Partidos",
            title="Partidos de campo por árbitro"
        )

        fig.update_layout(
            xaxis_tickangle=-45,
            plot_bgcolor="white",
            paper_bgcolor="white"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # ========================================================
    # ALERTAS
    # ========================================================

    st.subheader(
        "🚦 Semáforo de alertas"
    )

    a1, a2, a3 = st.columns(3)

    with a1:

        st.error(
            f"🔴 CRÍTICAS\n\n{criticas}"
        )

    with a2:

        st.warning(
            f"🟡 ADVERTENCIAS\n\n{advertencias}"
        )

    with a3:

        st.info(
            f"🔵 INFORMATIVAS\n\n{informativas}"
        )


# ============================================================
# ÁRBITROS
# ============================================================

elif modulo == "👨‍⚖️ Árbitros":

    st.header(
        "👨‍⚖️ Base de árbitros"
    )

    st.dataframe(
        df_arbitros,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# DISPONIBILIDAD
# ============================================================

elif modulo == "📅 Disponibilidad":

    st.header(
        "📅 Disponibilidad arbitral"
    )

    datos = df_disponibilidad.merge(
        df_arbitros[
            [
                "id_arbitro",
                "nombre_completo",
                "rol_arbitral",
                "categoria_campo",
                "categoria_mesa"
            ]
        ],
        on="id_arbitro",
        how="left"
    )

    datos["hora_inicio"] = (
        datos["hora_inicio_obj"]
        .apply(formatear_hora)
    )

    datos["hora_fin"] = (
        datos["hora_fin_obj"]
        .apply(formatear_hora)
    )

    st.dataframe(
        datos,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PARTIDOS
# ============================================================

elif modulo == "🏀 Partidos":

    st.header(
        "🏀 Programación original de partidos"
    )

    st.dataframe(
        df_partidos.drop(
            columns=[
                "hora_inicio_obj",
                "hora_fin_obj"
            ],
            errors="ignore"
        ),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PROGRAMACIÓN
# ============================================================

elif modulo == "🎯 Programación":

    st.header(
        "🎯 Programación semanal"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        eventos = [
            "Todos"
        ] + sorted(
            df_programacion[
                "evento"
            ]
            .dropna()
            .unique()
            .tolist()
        )

        filtro_evento = st.selectbox(
            "Evento",
            eventos
        )

    with col2:

        fechas = sorted(
            df_programacion[
                "fecha"
            ]
            .dropna()
            .unique()
        )

        filtro_fecha = st.selectbox(
            "Fecha",
            ["Todas"] + fechas
        )

    with col3:

        filtro_estado = st.selectbox(
            "Estado",
            [
                "Todos",
                "Asignado",
                "Pendiente"
            ]
        )

    resultado = (
        df_programacion_export.copy()
    )

    if filtro_evento != "Todos":

        resultado = resultado[
            resultado["evento"]
            == filtro_evento
        ]

    if filtro_fecha != "Todas":

        fecha_texto = formatear_fecha(
            filtro_fecha
        )

        resultado = resultado[
            resultado["fecha"]
            == fecha_texto
        ]

    if filtro_estado != "Todos":

        resultado = resultado[
            resultado["estado"]
            == filtro_estado
        ]

    st.dataframe(
        resultado,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader(
        "📥 Descargar programación"
    )

    csv = resultado.to_csv(
        index=False
    ).encode(
        "utf-8-sig"
    )

    st.download_button(
        "📄 Descargar CSV",
        data=csv,
        file_name="programacion_semanal.csv",
        mime="text/csv"
    )

    excel = generar_excel(
        df_programacion_export,
        df_alertas_export
    )

    st.download_button(
        "📊 Descargar Excel",
        data=excel,
        file_name="programacion_semanal.xlsx",
        mime=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    pdf = generar_pdf_programacion(
        df_programacion
    )

    st.download_button(
        "📄 Descargar PDF de programación",
        data=pdf,
        file_name="informe_programacion.pdf",
        mime="application/pdf"
    )


# ============================================================
# ALERTAS
# ============================================================

elif modulo == "🚨 Alertas":

    st.header(
        "🚨 Centro de alertas"
    )

    a1, a2, a3 = st.columns(3)

    with a1:

        st.error(
            f"🔴 CRÍTICAS: {criticas}"
        )

    with a2:

        st.warning(
            f"🟡 ADVERTENCIAS: {advertencias}"
        )

    with a3:

        st.info(
            f"🔵 INFORMATIVAS: {informativas}"
        )

    if df_alertas.empty:

        st.success(
            "🎉 No existen alertas."
        )

    else:

        for nivel, titulo in [
            (
                "CRÍTICA",
                "🔴 Alertas críticas"
            ),
            (
                "ADVERTENCIA",
                "🟡 Advertencias"
            ),
            (
                "INFORMATIVA",
                "🔵 Informativas"
            )
        ]:

            datos = df_alertas[
                df_alertas["tipo"]
                == nivel
            ]

            if not datos.empty:

                st.subheader(
                    titulo
                )

                st.dataframe(
                    datos,
                    use_container_width=True,
                    hide_index=True
                )

    st.divider()

    csv_alertas = (
        df_alertas_export
        .to_csv(index=False)
        .encode("utf-8-sig")
    )

    st.download_button(
        "📄 Descargar alertas CSV",
        data=csv_alertas,
        file_name="alertas_programacion.csv",
        mime="text/csv"
    )

    excel_alertas = generar_excel(
        df_programacion_export,
        df_alertas_export
    )

    st.download_button(
        "📊 Descargar alertas Excel",
        data=excel_alertas,
        file_name="alertas_programacion.xlsx",
        mime=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    pdf_alertas = generar_pdf_alertas(
        df_alertas
    )

    st.download_button(
        "📄 Descargar informe de alertas PDF",
        data=pdf_alertas,
        file_name="informe_alertas.pdf",
        mime="application/pdf"
    )


# ============================================================
# INFORMES
# ============================================================

elif modulo == "📄 Informes":

    st.header(
        "📄 Centro de informes"
    )

    st.markdown(
        """
        Todos los informes se generan automáticamente
        a partir de la programación calculada.
        """
    )

    # ========================================================
    # RESUMEN EJECUTIVO
    # ========================================================

    st.subheader(
        "📘 1. Resumen ejecutivo"
    )

    st.write(
        "Informe dirigido a coordinadores, "
        "directivos y responsables de la programación."
    )

    pdf_resumen = generar_pdf_resumen(
        df_arbitros,
        df_partidos,
        df_programacion,
        df_alertas
    )

    st.download_button(
        "📄 Descargar resumen ejecutivo PDF",
        data=pdf_resumen,
        file_name="resumen_ejecutivo.pdf",
        mime="application/pdf"
    )

    st.divider()

    # ========================================================
    # PROGRAMACIÓN
    # ========================================================

    st.subheader(
        "📋 2. Informe de programación"
    )

    st.write(
        "Documento operativo con el detalle de "
        "todos los árbitros y oficiales asignados."
    )

    pdf_programacion = generar_pdf_programacion(
        df_programacion
    )

    st.download_button(
        "📄 Descargar informe de programación PDF",
        data=pdf_programacion,
        file_name="informe_programacion.pdf",
        mime="application/pdf"
    )

    st.divider()

    # ========================================================
    # ALERTAS
    # ========================================================

    st.subheader(
        "🚨 3. Informe de alertas"
    )

    st.write(
        "Documento detallado con posiciones sin "
        "asignar, sustituciones y excepciones."
    )

    pdf_alertas = generar_pdf_alertas(
        df_alertas
    )

    st.download_button(
        "📄 Descargar informe de alertas PDF",
        data=pdf_alertas,
        file_name="informe_alertas.pdf",
        mime="application/pdf"
    )

    st.divider()

    # ========================================================
    # EXCEL COMPLETO
    # ========================================================

    st.subheader(
        "📊 4. Libro Excel completo"
    )

    excel_completo = generar_excel(
        df_programacion_export,
        df_alertas_export
    )

    st.download_button(
        "📊 Descargar Excel completo",
        data=excel_completo,
        file_name="informe_arbitral_completo.xlsx",
        mime=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


# ============================================================
# PIE
# ============================================================

st.divider()

st.caption(
    "🏀 Asignador de Árbitros de Baloncesto | "
    "Análisis de Datos + Automatización"
)