# ============================================================
# app.py
# PROGRAMADOR DE ÁRBITROS DE BALONCESTO
# ============================================================

import io
import re
import unicodedata
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

st.set_page_config(
    page_title="Programador de Árbitros de Baloncesto",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Reglas del sistema
MAX_CAMPO_DIA = 2
MAX_CAMPO_SEMANA = 14


# ============================================================
# ESTILOS
# ============================================================

st.markdown(
    """
    <style>

    /* ---------- SIDEBAR ---------- */

    [data-testid="stSidebar"] {
        min-width: 245px;
        max-width: 245px;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    [data-testid="stSidebar"] .stRadio > div {
        gap: 0.05rem;
    }

    [data-testid="stSidebar"] .stRadio label {
        padding-top: 0.10rem !important;
        padding-bottom: 0.10rem !important;
        margin-bottom: 0 !important;
    }

    /* ---------- BOTONES ---------- */

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 8px;
        font-weight: 600;
    }

    /* ---------- TÍTULOS ---------- */

    h1 {
        font-weight: 700;
    }

    h2, h3 {
        font-weight: 650;
    }

    /* ---------- TARJETAS ---------- */

    .metric-card {
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid rgba(120,120,120,.20);
        background: rgba(120,120,120,.06);
    }

    /* ---------- ALERTAS ---------- */

    .alerta-critica {
        padding: 12px;
        border-radius: 8px;
        background-color: #ffebee;
        border-left: 6px solid #d32f2f;
        margin-bottom: 8px;
    }

    .alerta-media {
        padding: 12px;
        border-radius: 8px;
        background-color: #fff3e0;
        border-left: 6px solid #f57c00;
        margin-bottom: 8px;
    }

    .alerta-baja {
        padding: 12px;
        border-radius: 8px;
        background-color: #e8f5e9;
        border-left: 6px solid #388e3c;
        margin-bottom: 8px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FUNCIONES DE TEXTO
# ============================================================

def limpiar_texto(valor):
    """
    Convierte texto a una forma comparable:
    - minúsculas
    - sin tildes
    - espacios normalizados
    """

    if valor is None:
        return ""

    try:
        if pd.isna(valor):
            return ""
    except Exception:
        pass

    texto = str(valor).strip().lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto


# ============================================================
# FUNCIONES DE ROLES
# ============================================================

def es_hibrido(rol):

    return "hibrid" in limpiar_texto(rol)


def es_campo(rol):

    texto = limpiar_texto(rol)

    return (
        "arbitro de campo" in texto
        and not es_hibrido(texto)
    )


def es_mesa(rol):

    texto = limpiar_texto(rol)

    return (
        (
            "oficial de mesa" in texto
            or
            "oficial mesa" in texto
        )
        and not es_hibrido(texto)
    )


# ============================================================
# CATEGORÍAS
# ============================================================

def categoria_numero(categoria):

    texto = limpiar_texto(categoria)

    if (
        "1ra" in texto
        or "primera" in texto
    ):
        return 3

    if (
        "2da" in texto
        or "segunda" in texto
    ):
        return 2

    if (
        "3ra" in texto
        or "tercera" in texto
    ):
        return 1

    return 0


def categoria_superior_o_igual(
    categoria_actual,
    categoria_requerida
):

    actual = categoria_numero(
        categoria_actual
    )

    requerida = categoria_numero(
        categoria_requerida
    )

    if requerida == 0:
        return False

    return actual >= requerida


# ============================================================
# HORARIOS
# ============================================================

def convertir_hora_minutos(valor):

    if valor is None:
        return None

    try:
        if pd.isna(valor):
            return None
    except Exception:
        pass

    if isinstance(valor, datetime):

        return (
            valor.hour * 60
            + valor.minute
        )

    if hasattr(valor, "hour") and hasattr(
        valor,
        "minute"
    ):

        return (
            valor.hour * 60
            + valor.minute
        )

    texto = str(valor).strip()

    formatos = [
        "%H:%M",
        "%H:%M:%S",
        "%I:%M %p",
        "%I:%M:%S %p",
    ]

    for formato in formatos:

        try:

            dt = datetime.strptime(
                texto,
                formato
            )

            return (
                dt.hour * 60
                + dt.minute
            )

        except ValueError:
            continue

    return None


# ============================================================
# DISPONIBILIDAD
# ============================================================

def intervalo_disponible(
    disponibilidad,
    fecha,
    inicio,
    fin
):

    if (
        disponibilidad is None
        or disponibilidad.empty
    ):
        return False

    if pd.isna(fecha):
        return False

    fecha_objetivo = pd.Timestamp(
        fecha
    ).normalize()

    for _, fila in disponibilidad.iterrows():

        dia = fila.get("dia")

        if pd.isna(dia):
            continue

        coincide = False

        # ----------------------------------------------------
        # Si DIA contiene una fecha
        # ----------------------------------------------------

        try:

            fecha_dia = pd.to_datetime(
                dia,
                errors="coerce",
                dayfirst=True
            )

            if pd.notna(fecha_dia):

                coincide = (
                    fecha_dia.normalize()
                    ==
                    fecha_objetivo
                )

        except Exception:
            pass

        # ----------------------------------------------------
        # Si DIA contiene nombre del día
        # ----------------------------------------------------

        if not coincide:

            nombre_dia = limpiar_texto(
                dia
            )

            dias = {
                "lunes": 0,
                "martes": 1,
                "miercoles": 2,
                "jueves": 3,
                "viernes": 4,
                "sabado": 5,
                "domingo": 6,
            }

            if nombre_dia in dias:

                coincide = (
                    fecha_objetivo.dayofweek
                    ==
                    dias[nombre_dia]
                )

        if not coincide:
            continue

        hora_inicio = convertir_hora_minutos(
            fila.get("hora_inicio")
        )

        hora_fin = convertir_hora_minutos(
            fila.get("hora_fin")
        )

        if (
            hora_inicio is None
            or hora_fin is None
        ):
            continue

        if (
            hora_inicio <= inicio
            and hora_fin >= fin
        ):

            return True

    return False


# ============================================================
# PREPARAR PARTIDOS
# ============================================================

def preparar_partidos(datos):

    partidos = datos[
        "programacion_partidos"
    ].copy()

    if partidos.empty:
        return partidos

    # --------------------------------------------------------
    # Fecha
    # --------------------------------------------------------

    partidos["fecha_dt"] = pd.to_datetime(
        partidos.get("fecha"),
        errors="coerce",
        dayfirst=True
    )

    # --------------------------------------------------------
    # Horarios
    # --------------------------------------------------------

    if "hora_inicio" not in partidos.columns:

        partidos["hora_inicio"] = ""

    if "hora_fin" not in partidos.columns:

        partidos["hora_fin"] = ""

    partidos["inicio_min"] = partidos[
        "hora_inicio"
    ].apply(
        convertir_hora_minutos
    )

    partidos["fin_min"] = partidos[
        "hora_fin"
    ].apply(
        convertir_hora_minutos
    )

    # --------------------------------------------------------
    # Reconstruir hora final si es necesario
    # --------------------------------------------------------

    if "duracion_min" in partidos.columns:

        for indice in partidos.index:

            inicio = partidos.at[
                indice,
                "inicio_min"
            ]

            fin = partidos.at[
                indice,
                "fin_min"
            ]

            duracion = partidos.at[
                indice,
                "duracion_min"
            ]

            if (
                inicio is not None
                and pd.isna(fin)
                and pd.notna(duracion)
            ):

                try:

                    partidos.at[
                        indice,
                        "fin_min"
                    ] = (
                        inicio
                        + int(duracion)
                    )

                except Exception:
                    pass

    # --------------------------------------------------------
    # Orden cronológico
    # --------------------------------------------------------

    columnas_orden = [
        "fecha_dt",
        "inicio_min",
        "escenario"
    ]

    columnas_orden = [
        c
        for c in columnas_orden
        if c in partidos.columns
    ]

    partidos = partidos.sort_values(
        columnas_orden,
        na_position="last"
    ).reset_index(
        drop=True
    )

    return partidos


# ============================================================
# CREAR REGISTRO DE ASIGNACIÓN
# ============================================================

def crear_registro_asignacion(
    partido,
    arbitro,
    funcion,
    categoria_requerida,
    sustitucion,
    categoria_utilizada
):

    return {

        "id_partido":
            partido.get(
                "id_partido"
            ),

        "fecha":
            partido.get(
                "fecha"
            ),

        "dia":
            partido.get(
                "dia"
            ),

        "hora_inicio":
            partido.get(
                "hora_inicio"
            ),

        "hora_fin":
            partido.get(
                "hora_fin"
            ),

        "evento":
            partido.get(
                "evento"
            ),

        "escenario":
            partido.get(
                "escenario"
            ),

        "rama":
            partido.get(
                "rama"
            ),

        "categoria":
            partido.get(
                "categoria"
            ),

        "id_arbitro":
            arbitro.get(
                "id_arbitro"
            ),

        "nombre_completo":
            arbitro.get(
                "nombre_completo"
            ),

        "documento_identidad":
            arbitro.get(
                "documento_identidad"
            ),

        "email":
            arbitro.get(
                "email"
            ),

        "numero_celular":
            arbitro.get(
                "numero_celular"
            ),

        "rol_arbitral":
            arbitro.get(
                "rol_arbitral"
            ),

        "funcion_asignada":
            funcion,

        "categoria_requerida":
            categoria_requerida,

        "categoria_utilizada":
            categoria_utilizada,

        "sustitucion_categoria":
            "SI"
            if sustitucion
            else "NO",
    }


# ============================================================
# MOTOR DE ASIGNACIÓN
# ============================================================

@st.cache_data(
    show_spinner=False
)
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

    # --------------------------------------------------------
    # Validación inicial
    # --------------------------------------------------------

    if (
        arbitros.empty
        or partidos.empty
    ):

        return (
            pd.DataFrame(),
            pd.DataFrame()
        )

    # --------------------------------------------------------
    # Índice de disponibilidad
    # --------------------------------------------------------

    disponibilidad_por_arbitro = {

        aid:
            grupo.copy()

        for aid, grupo
        in disponibilidad.groupby(
            "id_arbitro"
        )

    }

    # --------------------------------------------------------
    # Carga
    # --------------------------------------------------------

    carga_dia = {}

    carga_semana = {}

    # Historial de cada árbitro
    historial = {}

    # ========================================================
    # CONFLICTOS
    # ========================================================

    def tiene_conflicto(
        id_arbitro,
        partido
    ):

        fecha = partido[
            "fecha_dt"
        ]

        inicio = partido[
            "inicio_min"
        ]

        fin = partido[
            "fin_min"
        ]

        historial_arbitro = historial.get(
            id_arbitro,
            []
        )

        for anterior in historial_arbitro:

            if anterior[
                "fecha"
            ] != fecha:

                continue

            # ------------------------------------------------
            # Solapamiento
            # ------------------------------------------------

            if (
                inicio < anterior["fin"]
                and
                fin > anterior["inicio"]
            ):

                return True

            # ------------------------------------------------
            # Partidos consecutivos
            # ------------------------------------------------

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
                        partido.get(
                            "escenario"
                        )
                    )

                )

                # No puede desplazarse instantáneamente
                # a otro escenario.

                if not mismo_escenario:

                    return True

                # Híbrido no puede realizar
                # campo + mesa en el mismo partido.

                if (
                    anterior[
                        "id_partido"
                    ]
                    ==
                    partido.get(
                        "id_partido"
                    )
                ):

                    return True

        return False

    # ========================================================
    # BUSCAR CANDIDATOS
    # ========================================================

    def buscar_candidatos(
        partido,
        funcion,
        categoria_requerida,
        permitir_exceso_diario=False
    ):

        candidatos = []

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

            return candidatos

        for _, arbitro in arbitros.iterrows():

            id_arbitro = arbitro.get(
                "id_arbitro"
            )

            rol = arbitro.get(
                "rol_arbitral",
                ""
            )

            # ------------------------------------------------
            # Categoría según función
            # ------------------------------------------------

            if funcion == "CAMPO":

                categoria = arbitro.get(
                    "categoria_campo"
                )

            else:

                categoria = arbitro.get(
                    "categoria_mesa"
                )

            # ------------------------------------------------
            # Validar rol
            # ------------------------------------------------

            puede = False

            if funcion == "CAMPO":

                puede = (
                    es_campo(rol)
                    or
                    es_hibrido(rol)
                )

            elif funcion == "MESA":

                puede = (
                    es_mesa(rol)
                    or
                    es_hibrido(rol)
                )

            if not puede:

                continue

            # ------------------------------------------------
            # Categoría
            # ------------------------------------------------

            if not categoria_superior_o_igual(
                categoria,
                categoria_requerida
            ):

                continue

            # ------------------------------------------------
            # Disponibilidad
            # ------------------------------------------------

            disponibilidad_arbitro = (
                disponibilidad_por_arbitro.get(
                    id_arbitro,
                    pd.DataFrame()
                )
            )

            if not intervalo_disponible(
                disponibilidad_arbitro,
                fecha,
                inicio,
                fin
            ):

                continue

            # ------------------------------------------------
            # Conflictos
            # ------------------------------------------------

            if tiene_conflicto(
                id_arbitro,
                partido
            ):

                continue

            # ------------------------------------------------
            # Carga
            # ------------------------------------------------

            partidos_campo_dia = (
                carga_dia.get(
                    (
                        id_arbitro,
                        fecha
                    ),
                    0
                )
            )

            partidos_campo_semana = (
                carga_semana.get(
                    id_arbitro,
                    0
                )
            )

            # ------------------------------------------------
            # Máximo semanal
            # ------------------------------------------------

            if (
                funcion == "CAMPO"
                and
                partidos_campo_semana
                >= MAX_CAMPO_SEMANA
            ):

                continue

            # ------------------------------------------------
            # Exceso diario
            # ------------------------------------------------

            exceso_diario = (

                funcion == "CAMPO"

                and

                partidos_campo_dia
                >= MAX_CAMPO_DIA

            )

            if (
                exceso_diario
                and
                not permitir_exceso_diario
            ):

                continue

            # ------------------------------------------------
            # Puntaje
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

            cantidad_asignaciones = len(
                historial.get(
                    id_arbitro,
                    []
                )
            )

            puntuacion = 0

            # Preferir categoría exacta
            puntuacion += (
                diferencia_categoria
                * 100
            )

            # Equilibrar carga
            puntuacion += (
                cantidad_asignaciones
                * 10
            )

            # Penalizar exceso diario
            if exceso_diario:

                puntuacion += 1000

            # Preferir personal específico
            # frente a híbridos cuando sea posible
            if es_hibrido(rol):

                puntuacion += 5

            candidatos.append(
                {
                    "arbitro":
                        arbitro,

                    "puntuacion":
                        puntuacion,

                    "exceso_diario":
                        exceso_diario,
                }
            )

        candidatos.sort(
            key=lambda x:
            x["puntuacion"]
        )

        return candidatos

    # ========================================================
    # REGISTRAR ALERTA
    # ========================================================

    def registrar_alerta(
        partido,
        tipo,
        categoria,
        severidad,
        mensaje
    ):

        alertas.append(
            {

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
                    partido.get(
                        "evento"
                    ),

                "escenario":
                    partido.get(
                        "escenario"
                    ),

                "tipo":
                    tipo,

                "severidad":
                    severidad,

                "categoria_requerida":
                    categoria,

                "mensaje":
                    mensaje,

            }
        )

    # ========================================================
    # ASIGNAR UNA FUNCIÓN
    # ========================================================

    def asignar_funcion(
        partido,
        funcion,
        categorias
    ):

        asignados_partido = []

        # ----------------------------------------------------
        # IMPORTANTE:
        # este FOR debe terminar completamente.
        # NO colocar return dentro.
        # ----------------------------------------------------

        for posicion, categoria_req in enumerate(
            categorias,
            start=1
        ):

            if not categoria_req:

                continue

            # ------------------------------------------------
            # Primero buscar candidatos normales
            # ------------------------------------------------

            candidatos_disponibles = (
                buscar_candidatos(
                    partido,
                    funcion,
                    categoria_req,
                    permitir_exceso_diario=False
                )
            )

            # ------------------------------------------------
            # Política de excepción:
            # permitir superar los 2 partidos diarios
            # cuando no existe otra alternativa.
            # ------------------------------------------------

            if not candidatos_disponibles:

                candidatos_disponibles = (
                    buscar_candidatos(
                        partido,
                        funcion,
                        categoria_req,
                        permitir_exceso_diario=True
                    )
                )

            # ------------------------------------------------
            # Sin candidatos
            # ------------------------------------------------

            if not candidatos_disponibles:

                registrar_alerta(
                    partido,
                    funcion,
                    categoria_req,
                    "CRÍTICA",
                    (
                        "No existe personal disponible "
                        f"para {funcion.lower()} con "
                        f"categoría {categoria_req}."
                    )
                )

                continue

            # ------------------------------------------------
            # Seleccionar mejor candidato
            # ------------------------------------------------

            seleccionado = (
                candidatos_disponibles[0]
            )

            arbitro = (
                seleccionado[
                    "arbitro"
                ]
            )

            id_arbitro = (
                arbitro.get(
                    "id_arbitro"
                )
            )

            # ------------------------------------------------
            # Categoría utilizada
            # ------------------------------------------------

            if funcion == "CAMPO":

                categoria_utilizada = (
                    arbitro.get(
                        "categoria_campo"
                    )
                )

            else:

                categoria_utilizada = (
                    arbitro.get(
                        "categoria_mesa"
                    )
                )

            # ------------------------------------------------
            # Sustitución de categoría
            # ------------------------------------------------

            sustitucion = (

                categoria_numero(
                    categoria_utilizada
                )

                >

                categoria_numero(
                    categoria_req
                )

            )

            # ------------------------------------------------
            # Crear registro
            # ------------------------------------------------

            registro = (
                crear_registro_asignacion(
                    partido,
                    arbitro,
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
            # Actualizar historial
            # ------------------------------------------------

            historial.setdefault(
                id_arbitro,
                []
            ).append(
                {

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
                        funcion,

                }
            )

            # ------------------------------------------------
            # Actualizar carga de campo
            # ------------------------------------------------

            if funcion == "CAMPO":

                clave_dia = (
                    id_arbitro,
                    partido[
                        "fecha_dt"
                    ]
                )

                carga_dia[
                    clave_dia
                ] = (
                    carga_dia.get(
                        clave_dia,
                        0
                    )
                    + 1
                )

                carga_semana[
                    id_arbitro
                ] = (
                    carga_semana.get(
                        id_arbitro,
                        0
                    )
                    + 1
                )

                # ------------------------------------------------
                # Alerta por exceso de carga diaria
                # ------------------------------------------------

                if (
                    carga_dia[
                        clave_dia
                    ]
                    >
                    MAX_CAMPO_DIA
                ):

                    registrar_alerta(
                        partido,
                        "CARGA",
                        categoria_req,
                        "MEDIA",
                        (
                            f"El árbitro "
                            f"{arbitro.get('nombre_completo')} "
                            f"supera la carga recomendada "
                            f"de {MAX_CAMPO_DIA} partidos "
                            "de campo en el día. "
                            "Se utilizó como excepción "
                            "por disponibilidad limitada."
                        )
                    )

        # ====================================================
        # MUY IMPORTANTE:
        # return FUERA del for.
        # ====================================================

        return asignados_partido

    # ========================================================
    # PROCESAR TODOS LOS PARTIDOS
    # ========================================================

    for _, partido in partidos.iterrows():

        # ====================================================
        # ÁRBITROS DE CAMPO
        # ====================================================

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
                pd.notna(
                    categoria
                )

                and

                limpiar_texto(
                    categoria
                ) not in (
                    "",
                    "n/a"
                )
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

        # Protección adicional contra None
        asignaciones.extend(
            registros_campo or []
        )

        # ====================================================
        # OFICIALES DE MESA
        # ====================================================

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
                pd.notna(
                    categoria
                )

                and

                limpiar_texto(
                    categoria
                ) not in (
                    "",
                    "n/a"
                )
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

        # Protección adicional contra None
        asignaciones.extend(
            registros_mesa or []
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
# NORMALIZACIÓN DE COLUMNAS
# ============================================================

def normalizar_columnas(df):

    df = df.copy()

    nuevas = []

    for columna in df.columns:

        texto = limpiar_texto(
            columna
        )

        texto = texto.replace(
            " ",
            "_"
        )

        nuevas.append(
            texto
        )

    df.columns = nuevas

    return df


# ============================================================
# CARGAR EXCEL
# ============================================================

def cargar_excel(archivo):

    libro = pd.ExcelFile(
        archivo
    )

    nombres_originales = (
        libro.sheet_names
    )

    nombres_normalizados = {

        limpiar_texto(nombre):
            nombre

        for nombre
        in nombres_originales

    }

    # --------------------------------------------------------
    # Posibles nombres
    # --------------------------------------------------------

    equivalencias = {

        "arbitros": [
            "arbitros"
        ],

        "disponibilidad_arbitros": [
            "disponibilidad_arbitros"
        ],

        "config_eventos": [
            "config_eventos"
        ],

        "programacion_partidos": [
            "programacion_partidos"
        ],

    }

    datos = {}

    for clave, opciones in equivalencias.items():

        hoja_encontrada = None

        for opcion in opciones:

            opcion_normalizada = (
                limpiar_texto(
                    opcion
                )
            )

            if (
                opcion_normalizada
                in nombres_normalizados
            ):

                hoja_encontrada = (
                    nombres_normalizados[
                        opcion_normalizada
                    ]
                )

                break

        if hoja_encontrada is None:

            raise ValueError(
                f"No se encontró la hoja "
                f"'{clave}'. "
                f"Hojas encontradas: "
                f"{', '.join(nombres_originales)}"
            )

        datos[clave] = normalizar_columnas(
            pd.read_excel(
                libro,
                sheet_name=hoja_encontrada
            )
        )

    return datos


# ============================================================
# EXPORTAR CSV
# ============================================================

def exportar_csv(df):

    return df.to_csv(
        index=False,
        encoding="utf-8-sig"
    ).encode(
        "utf-8-sig"
    )


# ============================================================
# EXPORTAR XLSX
# ============================================================

def exportar_xlsx(
    df,
    nombre_hoja="Datos"
):

    salida = io.BytesIO()

    with pd.ExcelWriter(
        salida,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name=nombre_hoja[:31]
        )

    return salida.getvalue()


# ============================================================
# GENERAR PDF
# ============================================================

def generar_pdf(
    asignaciones,
    alertas,
    partidos,
    tipo="resumen"
):

    try:

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            PageBreak
        )

    except ImportError:

        return None

    salida = io.BytesIO()

    if tipo == "programacion":

        pagina = landscape(letter)

    else:

        pagina = letter

    documento = SimpleDocTemplate(
        salida,
        pagesize=pagina,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    estilos = (
        getSampleStyleSheet()
    )

    elementos = []

    # ========================================================
    # TÍTULO
    # ========================================================

    if tipo == "programacion":

        titulo = (
            "INFORME DE PROGRAMACIÓN "
            "DE ÁRBITROS"
        )

    elif tipo == "alertas":

        titulo = (
            "INFORME DE ALERTAS "
            "DE PROGRAMACIÓN"
        )

    else:

        titulo = (
            "RESUMEN EJECUTIVO - "
            "PROGRAMACIÓN DE ÁRBITROS"
        )

    elementos.append(
        Paragraph(
            titulo,
            estilos["Title"]
        )
    )

    elementos.append(
        Spacer(
            1,
            12
        )
    )

    # ========================================================
    # RESUMEN
    # ========================================================

    total_partidos = len(
        partidos
    )

    total_asignaciones = len(
        asignaciones
    )

    total_alertas = len(
        alertas
    )

    alertas_criticas = 0
    alertas_medias = 0
    alertas_bajas = 0

    if not alertas.empty:

        alertas_criticas = int(
            (
                alertas[
                    "severidad"
                ]
                ==
                "CRÍTICA"
            ).sum()
        )

        alertas_medias = int(
            (
                alertas[
                    "severidad"
                ]
                ==
                "MEDIA"
            ).sum()
        )

        alertas_bajas = int(
            (
                alertas[
                    "severidad"
                ]
                ==
                "BAJA"
            ).sum()
        )

    resumen = [

        [
            "Indicador",
            "Resultado"
        ],

        [
            "Partidos",
            str(
                total_partidos
            )
        ],

        [
            "Asignaciones",
            str(
                total_asignaciones
            )
        ],

        [
            "Alertas",
            str(
                total_alertas
            )
        ],

        [
            "Alertas críticas",
            str(
                alertas_criticas
            )
        ],

        [
            "Alertas medias",
            str(
                alertas_medias
            )
        ],

    ]

    tabla_resumen = Table(
        resumen,
        colWidths=[
            3 * inch,
            2 * inch
        ]
    )

    tabla_resumen.setStyle(
        TableStyle(
            [

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#1F4E78"
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
                    0.5,
                    colors.grey
                ),

                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "CENTER"
                ),

            ]
        )
    )

    elementos.append(
        tabla_resumen
    )

    elementos.append(
        Spacer(
            1,
            18
        )
    )

    # ========================================================
    # PROGRAMACIÓN
    # ========================================================

    if (
        tipo == "programacion"
        and not asignaciones.empty
    ):

        columnas = [
            "fecha",
            "hora_inicio",
            "hora_fin",
            "evento",
            "escenario",
            "categoria",
            "nombre_completo",
            "funcion_asignada",
            "categoria_requerida",
            "categoria_utilizada"
        ]

        columnas = [
            c
            for c in columnas
            if c in asignaciones.columns
        ]

        datos_tabla = [
            columnas
        ]

        for _, fila in asignaciones[
            columnas
        ].iterrows():

            datos_tabla.append(
                [
                    str(
                        fila.get(
                            c,
                            ""
                        )
                    )
                    for c in columnas
                ]
            )

        tabla = Table(
            datos_tabla,
            repeatRows=1
        )

        tabla.setStyle(
            TableStyle(
                [

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#1F4E78"
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
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        6
                    ),

                ]
            )
        )

        elementos.append(
            tabla
        )

    # ========================================================
    # ALERTAS
    # ========================================================

    if (
        tipo == "alertas"
        and not alertas.empty
    ):

        columnas = [
            "id_partido",
            "fecha",
            "hora",
            "evento",
            "escenario",
            "tipo",
            "severidad",
            "categoria_requerida",
            "mensaje"
        ]

        columnas = [
            c
            for c in columnas
            if c in alertas.columns
        ]

        datos_tabla = [
            columnas
        ]

        for _, fila in alertas[
            columnas
        ].iterrows():

            datos_tabla.append(
                [
                    str(
                        fila.get(
                            c,
                            ""
                        )
                    )
                    for c in columnas
                ]
            )

        tabla = Table(
            datos_tabla,
            repeatRows=1
        )

        tabla.setStyle(
            TableStyle(
                [

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#C62828"
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
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        6
                    ),

                ]
            )
        )

        elementos.append(
            tabla
        )

    documento.build(
        elementos
    )

    return salida.getvalue()


# ============================================================
# INTERFAZ
# ============================================================

st.title(
    "🏀 Programador de Árbitros de Baloncesto"
)

st.caption(
    "Motor inteligente para la programación semanal "
    "de árbitros de campo y oficiales de mesa."
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "📂 Base de datos"
    )

    archivo = st.file_uploader(
        "Cargar archivo Excel",
        type=[
            "xlsx",
            "xls"
        ],
        help=(
            "El archivo debe contener las hojas: "
            "Arbitros, Disponibilidad_Arbitros, "
            "Config_Eventos y Programacion_Partidos."
        )
    )

    st.divider()

    st.subheader(
        "📌 Módulos"
    )

    modulo = st.radio(
        "Seleccionar módulo",
        [
            "Resumen",
            "Programación",
            "Asignaciones",
            "Alertas",
            "Árbitros",
            "Partidos",
            "Configuración"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    st.caption(
        "🏀 Motor de asignación"
    )

    st.caption(
        "Versión optimizada"
    )


# ============================================================
# SIN ARCHIVO
# ============================================================

if archivo is None:

    st.info(
        "👈 Carga el archivo Excel desde la barra lateral "
        "para ejecutar automáticamente la programación."
    )

    st.markdown(
        """
        ### 📋 Estructura esperada

        El archivo debe contener cuatro hojas:

        1. **Arbitros**
        2. **Disponibilidad_Arbitros**
        3. **Config_Eventos**
        4. **Programacion_Partidos**

        Una vez cargado el archivo, el sistema realizará
        automáticamente los cruces y generará la programación.
        """
    )

    st.stop()


# ============================================================
# PROCESAMIENTO AUTOMÁTICO
# ============================================================

try:

    with st.spinner(
        "Leyendo base y calculando programación..."
    ):

        datos = cargar_excel(
            archivo
        )

        asignaciones, alertas = (
            ejecutar_asignacion(
                datos
            )
        )

        partidos = preparar_partidos(
            datos
        )

    st.success(
        "✅ Base cargada y programación calculada correctamente."
    )

except Exception as error:

    st.error(
        "❌ Se produjo un error al procesar el archivo."
    )

    st.exception(
        error
    )

    st.stop()


# ============================================================
# RESUMEN
# ============================================================

if modulo == "Resumen":

    st.subheader(
        "📊 Resumen ejecutivo"
    )

    criticas = 0
    medias = 0
    bajas = 0

    if not alertas.empty:

        criticas = int(
            (
                alertas[
                    "severidad"
                ]
                ==
                "CRÍTICA"
            ).sum()
        )

        medias = int(
            (
                alertas[
                    "severidad"
                ]
                ==
                "MEDIA"
            ).sum()
        )

        bajas = int(
            (
                alertas[
                    "severidad"
                ]
                ==
                "BAJA"
            ).sum()
        )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🏀 Partidos",
        len(partidos)
    )

    c2.metric(
        "👨‍⚖️ Asignaciones",
        len(asignaciones)
    )

    c3.metric(
        "🚨 Alertas",
        len(alertas)
    )

    c4.metric(
        "🔴 Críticas",
        criticas
    )

    st.divider()

    # ========================================================
    # SEMÁFORO
    # ========================================================

    st.subheader(
        "🚦 Estado de la programación"
    )

    if criticas == 0:

        if medias == 0:

            st.success(
                "🟢 PROGRAMACIÓN ÓPTIMA — "
                "No existen alertas críticas ni medias."
            )

        else:

            st.warning(
                f"🟠 PROGRAMACIÓN CON OBSERVACIONES — "
                f"existen {medias} alertas de carga."
            )

    else:

        st.error(
            f"🔴 PROGRAMACIÓN CON ALERTAS CRÍTICAS — "
            f"se requiere revisar {criticas} asignaciones."
        )

    # ========================================================
    # GRÁFICOS
    # ========================================================

    col1, col2 = st.columns(2)

    with col1:

        st.subheader(
            "🚨 Alertas por severidad"
        )

        datos_alertas = pd.Series(
            {
                "CRÍTICA":
                    criticas,

                "MEDIA":
                    medias,

                "BAJA":
                    bajas
            },
            name="Cantidad"
        )

        st.bar_chart(
            datos_alertas
        )

    with col2:

        st.subheader(
            "👨‍⚖️ Asignaciones por función"
        )

        if not asignaciones.empty:

            datos_funciones = (
                asignaciones[
                    "funcion_asignada"
                ]
                .value_counts()
            )

            st.bar_chart(
                datos_funciones
            )

        else:

            st.info(
                "No existen asignaciones."
            )

    # ========================================================
    # SUSTITUCIONES
    # ========================================================

    if not asignaciones.empty:

        st.subheader(
            "🔄 Sustituciones de categoría"
        )

        sustituciones = int(
            (
                asignaciones[
                    "sustitucion_categoria"
                ]
                ==
                "SI"
            ).sum()
        )

        exactas = int(
            (
                asignaciones[
                    "sustitucion_categoria"
                ]
                ==
                "NO"
            ).sum()
        )

        c1, c2 = st.columns(2)

        c1.metric(
            "Categoría exacta",
            exactas
        )

        c2.metric(
            "Sustituciones superiores",
            sustituciones
        )


# ============================================================
# PROGRAMACIÓN
# ============================================================

elif modulo == "Programación":

    st.subheader(
        "📅 Programación semanal"
    )

    if asignaciones.empty:

        st.warning(
            "No se generaron asignaciones."
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
            "categoria",
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

        vista = asignaciones[
            columnas
        ].copy()

        vista = vista.sort_values(
            [
                "fecha",
                "hora_inicio",
                "escenario"
            ],
            na_position="last"
        )

        st.dataframe(
            vista,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇️ Descargar programación CSV",
            exportar_csv(vista),
            "programacion_semanal.csv",
            "text/csv"
        )

        st.download_button(
            "⬇️ Descargar programación XLSX",
            exportar_xlsx(
                vista,
                "Programacion"
            ),
            "programacion_semanal.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# ============================================================
# ASIGNACIONES
# ============================================================

elif modulo == "Asignaciones":

    st.subheader(
        "👨‍⚖️ Detalle de asignaciones"
    )

    if asignaciones.empty:

        st.warning(
            "No existen asignaciones."
        )

    else:

        funciones = sorted(
            asignaciones[
                "funcion_asignada"
            ]
            .dropna()
            .unique()
        )

        filtro_funcion = st.multiselect(
            "Filtrar función",
            funciones
        )

        vista = (
            asignaciones.copy()
        )

        if filtro_funcion:

            vista = vista[
                vista[
                    "funcion_asignada"
                ].isin(
                    filtro_funcion
                )
            ]

        st.dataframe(
            vista,
            use_container_width=True,
            hide_index=True
        )

        c1, c2 = st.columns(2)

        with c1:

            st.download_button(
                "⬇️ Descargar CSV",
                exportar_csv(
                    vista
                ),
                "asignaciones.csv",
                "text/csv"
            )

        with c2:

            st.download_button(
                "⬇️ Descargar XLSX",
                exportar_xlsx(
                    vista,
                    "Asignaciones"
                ),
                "asignaciones.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


# ============================================================
# ALERTAS
# ============================================================

elif modulo == "Alertas":

    st.subheader(
        "🚦 Alertas de programación"
    )

    if alertas.empty:

        st.success(
            "🟢 No se generaron alertas."
        )

    else:

        criticas = int(
            (
                alertas[
                    "severidad"
                ]
                ==
                "CRÍTICA"
            ).sum()
        )

        medias = int(
            (
                alertas[
                    "severidad"
                ]
                ==
                "MEDIA"
            ).sum()
        )

        bajas = int(
            (
                alertas[
                    "severidad"
                ]
                ==
                "BAJA"
            ).sum()
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "🔴 Críticas",
            criticas
        )

        c2.metric(
            "🟠 Medias",
            medias
        )

        c3.metric(
            "🟢 Bajas",
            bajas
        )

        st.bar_chart(
            pd.Series(
                {
                    "CRÍTICA":
                        criticas,

                    "MEDIA":
                        medias,

                    "BAJA":
                        bajas
                },
                name="Alertas"
            )
        )

        # ----------------------------------------------------
        # Filtro
        # ----------------------------------------------------

        severidades = st.multiselect(
            "Filtrar severidad",
            [
                "CRÍTICA",
                "MEDIA",
                "BAJA"
            ]
        )

        vista_alertas = (
            alertas.copy()
        )

        if severidades:

            vista_alertas = (
                vista_alertas[
                    vista_alertas[
                        "severidad"
                    ].isin(
                        severidades
                    )
                ]
            )

        # ----------------------------------------------------
        # Mostrar alertas visualmente
        # ----------------------------------------------------

        for _, alerta in (
            vista_alertas.iterrows()
        ):

            severidad = alerta.get(
                "severidad",
                ""
            )

            if severidad == "CRÍTICA":

                st.error(
                    f"🔴 **{alerta.get('tipo')}** — "
                    f"Partido {alerta.get('id_partido')} | "
                    f"{alerta.get('fecha')} | "
                    f"{alerta.get('hora')}  \n"
                    f"{alerta.get('mensaje')}"
                )

            elif severidad == "MEDIA":

                st.warning(
                    f"🟠 **{alerta.get('tipo')}** — "
                    f"Partido {alerta.get('id_partido')} | "
                    f"{alerta.get('fecha')} | "
                    f"{alerta.get('hora')}  \n"
                    f"{alerta.get('mensaje')}"
                )

            else:

                st.info(
                    f"🟢 **{alerta.get('tipo')}** — "
                    f"{alerta.get('mensaje')}"
                )

        st.subheader(
            "📋 Tabla completa de alertas"
        )

        st.dataframe(
            vista_alertas,
            use_container_width=True,
            hide_index=True
        )

        c1, c2 = st.columns(2)

        with c1:

            st.download_button(
                "⬇️ Alertas CSV",
                exportar_csv(
                    vista_alertas
                ),
                "alertas.csv",
                "text/csv"
            )

        with c2:

            st.download_button(
                "⬇️ Alertas XLSX",
                exportar_xlsx(
                    vista_alertas,
                    "Alertas"
                ),
                "alertas.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


# ============================================================
# ÁRBITROS
# ============================================================

elif modulo == "Árbitros":

    st.subheader(
        "👤 Base de árbitros"
    )

    arbitros = datos[
        "arbitros"
    ].copy()

    st.metric(
        "Total de árbitros",
        len(arbitros)
    )

    st.dataframe(
        arbitros,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "⬇️ Descargar árbitros XLSX",
        exportar_xlsx(
            arbitros,
            "Arbitros"
        ),
        "arbitros.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ============================================================
# PARTIDOS
# ============================================================

elif modulo == "Partidos":

    st.subheader(
        "🏀 Partidos programados"
    )

    vista_partidos = (
        partidos.copy()
    )

    vista_partidos = (
        vista_partidos.drop(
            columns=[
                "fecha_dt",
                "inicio_min",
                "fin_min"
            ],
            errors="ignore"
        )
    )

    st.metric(
        "Total de partidos",
        len(vista_partidos)
    )

    st.dataframe(
        vista_partidos,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "⬇️ Descargar partidos XLSX",
        exportar_xlsx(
            vista_partidos,
            "Partidos"
        ),
        "partidos.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ============================================================
# CONFIGURACIÓN
# ============================================================

elif modulo == "Configuración":

    st.subheader(
        "⚙️ Configuración y reglas del motor"
    )

    st.markdown(
        f"""
        ### Reglas principales

        - 🏀 Máximo recomendado de **{MAX_CAMPO_DIA} partidos de campo diarios**.
        - 📅 Máximo de **{MAX_CAMPO_SEMANA} partidos de campo semanales**.
        - 🔄 Se permite sustitución por una categoría superior.
        - 🤝 Un árbitro híbrido puede actuar como campo o mesa.
        - 🚫 Un híbrido no puede realizar ambas funciones en el mismo partido.
        - 🔁 Se permiten partidos consecutivos en el mismo escenario.
        - 🚗 No se permite cambiar de escenario entre partidos consecutivos sin tiempo de desplazamiento.
        - ⚖️ Se busca equilibrar la carga entre árbitros.
        - 🚨 Cuando no existe personal disponible se genera una alerta crítica.
        - 🟠 Cuando se supera la carga diaria recomendada se genera una alerta de carga.
        """
    )

    st.divider()

    st.subheader(
        "📚 Hojas cargadas"
    )

    for nombre, df in datos.items():

        st.write(
            f"**{nombre}** → {len(df)} registros"
        )


# ============================================================
# EXPORTACIONES GENERALES
# ============================================================

st.divider()

st.subheader(
    "📥 Informes y exportaciones"
)

col1, col2, col3, col4 = st.columns(4)

# ------------------------------------------------------------
# CSV
# ------------------------------------------------------------

with col1:

    st.download_button(
        "CSV programación",
        exportar_csv(
            asignaciones
        ),
        "programacion_semanal.csv",
        "text/csv"
    )


# ------------------------------------------------------------
# XLSX
# ------------------------------------------------------------

with col2:

    st.download_button(
        "XLSX programación",
        exportar_xlsx(
            asignaciones,
            "Programacion"
        ),
        "programacion_semanal.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ------------------------------------------------------------
# PDF RESUMEN
# ------------------------------------------------------------

with col3:

    pdf_resumen = generar_pdf(
        asignaciones,
        alertas,
        partidos,
        tipo="resumen"
    )

    if pdf_resumen:

        st.download_button(
            "📄 Resumen ejecutivo PDF",
            pdf_resumen,
            "resumen_ejecutivo.pdf",
            "application/pdf"
        )

    else:

        st.caption(
            "PDF requiere reportlab."
        )


# ------------------------------------------------------------
# PDF PROGRAMACIÓN
# ------------------------------------------------------------

with col4:

    pdf_programacion = generar_pdf(
        asignaciones,
        alertas,
        partidos,
        tipo="programacion"
    )

    if pdf_programacion:

        st.download_button(
            "📄 Informe programación PDF",
            pdf_programacion,
            "informe_programacion.pdf",
            "application/pdf"
        )

    else:

        st.caption(
            "PDF requiere reportlab."
        )


# ============================================================
# PDF ALERTAS
# ============================================================

pdf_alertas = generar_pdf(
    asignaciones,
    alertas,
    partidos,
    tipo="alertas"
)

if pdf_alertas:

    st.download_button(
        "🚦 Descargar informe de alertas PDF",
        pdf_alertas,
        "informe_alertas.pdf",
        "application/pdf"
    )


# ============================================================
# PIE
# ============================================================

st.caption(
    "🏀 Programador de Árbitros de Baloncesto | "
    "Análisis de Datos + Motor de Asignación"
)