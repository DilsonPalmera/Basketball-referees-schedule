import streamlit as st
import pandas as pd
from datetime import datetime, time
from io import BytesIO

# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Asignador de Árbitros de Baloncesto",
    page_icon="🏀",
    layout="wide"
)

st.title("🏀 Asignador de Árbitros de Baloncesto")
st.caption(
    "Sistema inteligente para la programación y asignación "
    "semanal de árbitros y oficiales de mesa."
)

# ============================================================
# CONSTANTES DEL SISTEMA
# ============================================================

HOJAS_REQUERIDAS = [
    "Arbitros",
    "Disponibilidad_Arbitros",
    "Config_Eventos",
    "Programacion_Partidos"
]

# Jerarquía de categorías.
# Un número menor representa una categoría superior.
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
# FUNCIONES DE APOYO
# ============================================================

def limpiar_texto(valor):
    """Normaliza textos para facilitar las comparaciones."""

    if pd.isna(valor):
        return ""

    return str(valor).strip().lower()


def convertir_hora(valor):
    """Convierte diferentes formatos de hora a datetime.time."""

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


def minutos_hora(valor):
    """Convierte una hora a minutos desde medianoche."""

    if valor is None:
        return None

    return valor.hour * 60 + valor.minute


def solapamiento_horario(
    inicio_1,
    fin_1,
    inicio_2,
    fin_2
):
    """Determina si dos intervalos horarios se superponen."""

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


def normalizar_columnas(df):
    """Normaliza nombres de columnas."""

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    return df


# ============================================================
# CARGA DEL EXCEL
# ============================================================

def cargar_excel(archivo):

    excel = pd.ExcelFile(archivo)

    hojas = excel.sheet_names

    faltantes = [
        hoja
        for hoja in HOJAS_REQUERIDAS
        if hoja not in hojas
    ]

    if faltantes:
        raise ValueError(
            "Faltan las siguientes hojas: "
            + ", ".join(faltantes)
        )

    df_arbitros = pd.read_excel(
        archivo,
        sheet_name="Arbitros"
    )

    df_disponibilidad = pd.read_excel(
        archivo,
        sheet_name="Disponibilidad_Arbitros"
    )

    df_config = pd.read_excel(
        archivo,
        sheet_name="Config_Eventos"
    )

    df_partidos = pd.read_excel(
        archivo,
        sheet_name="Programacion_Partidos"
    )

    return (
        normalizar_columnas(df_arbitros),
        normalizar_columnas(df_disponibilidad),
        normalizar_columnas(df_config),
        normalizar_columnas(df_partidos)
    )


# ============================================================
# VALIDACIÓN DE ESTRUCTURA
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

    estructuras = [
        ("Arbitros", df_arbitros),
        (
            "Disponibilidad_Arbitros",
            df_disponibilidad
        ),
        ("Config_Eventos", df_config),
        (
            "Programacion_Partidos",
            df_partidos
        )
    ]

    for nombre, df in estructuras:

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
# PREPARACIÓN DE DATOS
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

    # -----------------------------
    # Fechas
    # -----------------------------

    df_partidos["fecha"] = pd.to_datetime(
        df_partidos["fecha"],
        errors="coerce"
    )

    # -----------------------------
    # Horas
    # -----------------------------

    df_partidos["hora_inicio_obj"] = (
        df_partidos["hora_inicio"]
        .apply(convertir_hora)
    )

    df_partidos["hora_fin_obj"] = (
        df_partidos["hora_fin"]
        .apply(convertir_hora)
    )

    df_disponibilidad[
        "hora_inicio_obj"
    ] = (
        df_disponibilidad[
            "hora_inicio"
        ].apply(convertir_hora)
    )

    df_disponibilidad[
        "hora_fin_obj"
    ] = (
        df_disponibilidad[
            "hora_fin"
        ].apply(convertir_hora)
    )

    # -----------------------------
    # Texto
    # -----------------------------

    for df in [
        df_arbitros,
        df_disponibilidad,
        df_config,
        df_partidos
    ]:

        for columna in df.columns:

            if df[columna].dtype == "object":

                df[columna] = (
                    df[columna]
                    .astype(str)
                    .str.strip()
                )

    return (
        df_arbitros,
        df_disponibilidad,
        df_config,
        df_partidos
    )


# ============================================================
# DETERMINAR ROL
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


def es_hibrido(rol):

    rol = limpiar_texto(rol)

    return (
        "hibrido" in rol
        or "híbrido" in rol
    )


# ============================================================
# COMPATIBILIDAD DE CATEGORÍA
# ============================================================

def categoria_compatible(
    categoria_arbitro,
    categoria_requerida,
    tipo
):

    requerida = limpiar_texto(
        categoria_requerida
    )

    disponible = limpiar_texto(
        categoria_arbitro
    )

    if not requerida:
        return False

    if not disponible:
        return False

    if tipo == "campo":

        jerarquia = JERARQUIA_CAMPO

    else:

        jerarquia = JERARQUIA_MESA

    requerida = requerida.lower()
    disponible = disponible.lower()

    if (
        requerida not in jerarquia
        or disponible not in jerarquia
    ):
        return False

    # Una categoría superior puede cubrir
    # una categoría inferior.
    #
    # 1ra → 1ra, 2da, 3ra
    # 2da → 2da, 3ra
    # 3ra → 3ra

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

    dia_buscado = limpiar_texto(dia)

    registros = df_disponibilidad[
        df_disponibilidad[
            "id_arbitro"
        ] == id_arbitro
    ]

    for _, registro in registros.iterrows():

        dia_disponible = limpiar_texto(
            registro["dia"]
        )

        if dia_disponible != dia_buscado:
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
# CONFLICTO DE ASIGNACIONES
# ============================================================

def tiene_conflicto(
    id_arbitro,
    fecha,
    hora_inicio,
    hora_fin,
    escenario,
    asignaciones
):

    conflictos = []

    for asignacion in asignaciones:

        if (
            asignacion["id_arbitro"]
            != id_arbitro
        ):
            continue

        if asignacion["fecha"] != fecha:
            continue

        if solapamiento_horario(
            hora_inicio,
            hora_fin,
            asignacion["hora_inicio"],
            asignacion["hora_fin"]
        ):

            conflictos.append(
                asignacion
            )

    if conflictos:
        return True, "Solapamiento de horario"

    # --------------------------------------------------------
    # Verificación de desplazamiento
    # --------------------------------------------------------

    for asignacion in asignaciones:

        if (
            asignacion["id_arbitro"]
            != id_arbitro
        ):
            continue

        if asignacion["fecha"] != fecha:
            continue

        escenario_anterior = limpiar_texto(
            asignacion["escenario"]
        )

        escenario_nuevo = limpiar_texto(
            escenario
        )

        # Partido inmediatamente anterior
        if asignacion["hora_fin"] == hora_inicio:

            if escenario_anterior != escenario_nuevo:

                return (
                    True,
                    "Cambio de escenario sin tiempo "
                    "para desplazamiento"
                )

        # Partido inmediatamente posterior
        if asignacion["hora_inicio"] == hora_fin:

            if escenario_anterior != escenario_nuevo:

                return (
                    True,
                    "Cambio de escenario sin tiempo "
                    "para desplazamiento"
                )

    return False, ""


# ============================================================
# CARGA DE TRABAJO
# ============================================================

def calcular_carga(
    id_arbitro,
    fecha,
    tipo,
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

            if asignacion["fecha"] == fecha:

                campo_dia += 1

    return (
        total,
        campo_dia,
        campo_semana
    )


# ============================================================
# SELECCIÓN DE CANDIDATOS
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

    fecha = partido["fecha"]

    dia = partido["dia"]

    hora_inicio = partido[
        "hora_inicio_obj"
    ]

    hora_fin = partido[
        "hora_fin_obj"
    ]

    escenario = partido[
        "escenario"
    ]

    for _, arbitro in df_arbitros.iterrows():

        id_arbitro = arbitro[
            "id_arbitro"
        ]

        rol = arbitro[
            "rol_arbitral"
        ]

        # ----------------------------------------------------
        # ROL
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # CATEGORÍA
        # ----------------------------------------------------

        if not categoria_compatible(
            categoria,
            categoria_requerida,
            tipo
        ):
            continue

        # ----------------------------------------------------
        # DISPONIBILIDAD
        # ----------------------------------------------------

        if not esta_disponible(
            id_arbitro,
            dia,
            hora_inicio,
            hora_fin,
            df_disponibilidad
        ):
            continue

        # ----------------------------------------------------
        # CONFLICTOS
        # ----------------------------------------------------

        conflicto, motivo = tiene_conflicto(
            id_arbitro,
            fecha,
            hora_inicio,
            hora_fin,
            escenario,
            asignaciones
        )

        if conflicto:
            continue

        # ----------------------------------------------------
        # CARGA
        # ----------------------------------------------------

        (
            carga_total,
            campo_dia,
            campo_semana
        ) = calcular_carga(
            id_arbitro,
            fecha,
            tipo,
            asignaciones
        )

        # ----------------------------------------------------
        # LÍMITE SEMANAL
        # ----------------------------------------------------

        if tipo == "campo":

            if campo_semana >= MAX_CAMPO_SEMANAL:

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
# SELECCIÓN EQUILIBRADA
# ============================================================

def seleccionar_candidato(
    candidatos,
    categoria_requerida,
    tipo
):

    if not candidatos:
        return None

    if tipo == "campo":

        jerarquia = JERARQUIA_CAMPO

    else:

        jerarquia = JERARQUIA_MESA

    requerida = limpiar_texto(
        categoria_requerida
    )

    for candidato in candidatos:

        candidato[
            "nivel_sustitucion"
        ] = (
            jerarquia[
                limpiar_texto(
                    candidato["categoria"]
                )
            ]
            -
            jerarquia[
                requerida
            ]
        )

    # --------------------------------------------------------
    # Orden de prioridad
    #
    # 1. Menor sustitución posible
    # 2. Menor carga de campo diaria
    # 3. Menor carga semanal
    # 4. Menor carga total
    # --------------------------------------------------------

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
# GENERAR PROGRAMACIÓN
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
        # ÁRBITROS DE CAMPO
        # ====================================================

        cantidad_campo = int(
            partido[
                "cant_arbitros_campo"
            ]
        )

        requerimientos_campo = [
            partido["cat_req_arb_1"],
            partido["cat_req_arb_2"],
            partido["cat_req_arb_3"]
        ]

        requerimientos_campo = [
            categoria
            for categoria in requerimientos_campo
            if limpiar_texto(categoria)
            not in [
                "",
                "n/a",
                "nan",
                "none"
            ]
        ]

        for posicion in range(
            cantidad_campo
        ):

            if posicion < len(
                requerimientos_campo
            ):

                categoria_requerida = (
                    requerimientos_campo[
                        posicion
                    ]
                )

            else:

                categoria_requerida = (
                    requerimientos_campo[-1]
                    if requerimientos_campo
                    else ""
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

                alertas.append(
                    {
                        "tipo": "CRÍTICA",
                        "id_partido": partido[
                            "id_partido"
                        ],
                        "fecha": partido[
                            "fecha"
                        ],
                        "evento": partido[
                            "evento"
                        ],
                        "escenario": partido[
                            "escenario"
                        ],
                        "funcion": "Árbitro de campo",
                        "posicion": posicion + 1,
                        "requerimiento": categoria_requerida,
                        "detalle":
                            "No existe un árbitro "
                            "disponible y compatible "
                            "con los criterios "
                            "establecidos."
                    }
                )

            else:

                arbitro = candidato[
                    "arbitro"
                ]

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

                    alertas.append(
                        {
                            "tipo": "INFORMATIVA",
                            "id_partido":
                                partido[
                                    "id_partido"
                                ],
                            "fecha":
                                partido[
                                    "fecha"
                                ],
                            "evento":
                                partido[
                                    "evento"
                                ],
                            "escenario":
                                partido[
                                    "escenario"
                                ],
                            "funcion":
                                "Árbitro de campo",
                            "posicion":
                                posicion + 1,
                            "requerimiento":
                                categoria_requerida,
                            "detalle":
                                f"Se utilizó un árbitro "
                                f"de categoría "
                                f"{categoria_real} "
                                f"para cubrir el "
                                f"requerimiento "
                                f"{categoria_requerida}."
                        }
                    )

            registro = {
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
            }

            asignaciones.append(
                registro
            )

        # ====================================================
        # OFICIALES DE MESA
        # ====================================================

        cantidad_mesa = int(
            partido[
                "cant_oficiales_mesa"
            ]
        )

        requerimientos_mesa = [
            partido["cat_req_mesa_1"],
            partido["cat_req_mesa_2"]
        ]

        requerimientos_mesa = [
            categoria
            for categoria in requerimientos_mesa
            if limpiar_texto(categoria)
            not in [
                "",
                "n/a",
                "nan",
                "none"
            ]
        ]

        for posicion in range(
            cantidad_mesa
        ):

            if posicion < len(
                requerimientos_mesa
            ):

                categoria_requerida = (
                    requerimientos_mesa[
                        posicion
                    ]
                )

            else:

                categoria_requerida = (
                    requerimientos_mesa[-1]
                    if requerimientos_mesa
                    else ""
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

                alertas.append(
                    {
                        "tipo": "CRÍTICA",
                        "id_partido":
                            partido[
                                "id_partido"
                            ],
                        "fecha":
                            partido[
                                "fecha"
                            ],
                        "evento":
                            partido[
                                "evento"
                            ],
                        "escenario":
                            partido[
                                "escenario"
                            ],
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
                    }
                )

            else:

                arbitro = candidato[
                    "arbitro"
                ]

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

                    alertas.append(
                        {
                            "tipo":
                                "INFORMATIVA",
                            "id_partido":
                                partido[
                                    "id_partido"
                                ],
                            "fecha":
                                partido[
                                    "fecha"
                                ],
                            "evento":
                                partido[
                                    "evento"
                                ],
                            "escenario":
                                partido[
                                    "escenario"
                                ],
                            "funcion":
                                "Oficial de mesa",
                            "posicion":
                                posicion + 1,
                            "requerimiento":
                                categoria_requerida,
                            "detalle":
                                f"Se utilizó un "
                                f"oficial de mesa "
                                f"de categoría "
                                f"{categoria_real} "
                                f"para cubrir "
                                f"{categoria_requerida}."
                        }
                    )

            registro = {
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
            }

            asignaciones.append(
                registro
            )

    # ========================================================
    # ALERTAS DE CARGA DIARIA
    # ========================================================

    df_asignaciones = pd.DataFrame(
        asignaciones
    )

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

        carga_diaria = (
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

        for _, fila in carga_diaria.iterrows():

            if (
                fila["partidos_campo"]
                > MAX_CAMPO_DIARIO
            ):

                alertas.append(
                    {
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
                            f"en el mismo día. "
                            f"Se supera el límite "
                            f"recomendado de "
                            f"{MAX_CAMPO_DIARIO}."
                    }
                )

    return (
        df_asignaciones,
        pd.DataFrame(alertas)
    )


# ============================================================
# INTERFAZ
# ============================================================

st.sidebar.header("📂 Base de datos")

archivo = st.sidebar.file_uploader(
    "Cargar archivo Excel",
    type=["xlsx", "xls"]
)

if archivo is None:

    st.info(
        "👈 Carga el archivo Excel desde el menú lateral."
    )

    st.markdown(
        """
        ### El archivo debe contener:

        1. `Arbitros`
        2. `Disponibilidad_Arbitros`
        3. `Config_Eventos`
        4. `Programacion_Partidos`
        """
    )

    st.stop()


# ============================================================
# PROCESAMIENTO
# ============================================================

try:

    (
        df_arbitros,
        df_disponibilidad,
        df_config,
        df_partidos
    ) = cargar_excel(archivo)

except Exception as error:

    st.error(
        f"❌ Error al cargar el archivo: {error}"
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
        st.write(f"- {error}")

    st.stop()


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

st.success(
    "✅ Las cuatro bases fueron cargadas correctamente."
)


# ============================================================
# MÉTRICAS
# ============================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "👨‍⚖️ Árbitros",
        len(df_arbitros)
    )

with col2:
    st.metric(
        "📅 Disponibilidades",
        len(df_disponibilidad)
    )

with col3:
    st.metric(
        "🏀 Partidos",
        len(df_partidos)
    )

with col4:
    st.metric(
        "🏆 Configuraciones",
        len(df_config)
    )


st.divider()


# ============================================================
# MENÚ
# ============================================================

opcion = st.radio(
    "Seleccione un módulo",
    [
        "📊 Resumen",
        "👨‍⚖️ Árbitros",
        "📅 Disponibilidad",
        "🏀 Partidos",
        "🎯 Programación",
        "🚨 Alertas"
    ],
    horizontal=True
)


# ============================================================
# RESUMEN
# ============================================================

if opcion == "📊 Resumen":

    st.header("📊 Resumen general")

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Eventos")

        resumen_eventos = (
            df_partidos[
                "evento"
            ]
            .value_counts()
            .reset_index()
        )

        resumen_eventos.columns = [
            "Evento",
            "Partidos"
        ]

        st.dataframe(
            resumen_eventos,
            use_container_width=True,
            hide_index=True
        )

    with col2:

        st.subheader("Categorías")

        resumen_categorias = (
            df_partidos[
                "categoria"
            ]
            .value_counts()
            .reset_index()
        )

        resumen_categorias.columns = [
            "Categoría",
            "Partidos"
        ]

        st.dataframe(
            resumen_categorias,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# ÁRBITROS
# ============================================================

elif opcion == "👨‍⚖️ Árbitros":

    st.header("👨‍⚖️ Árbitros")

    st.dataframe(
        df_arbitros,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# DISPONIBILIDAD
# ============================================================

elif opcion == "📅 Disponibilidad":

    st.header("📅 Disponibilidad")

    resultado = df_disponibilidad.merge(
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

    st.dataframe(
        resultado,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PARTIDOS
# ============================================================

elif opcion == "🏀 Partidos":

    st.header("🏀 Programación de partidos")

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
        "duracion_min",
        "cant_arbitros_campo",
        "cat_req_arb_1",
        "cat_req_arb_2",
        "cat_req_arb_3",
        "cant_oficiales_mesa",
        "cat_req_mesa_1",
        "cat_req_mesa_2"
    ]

    st.dataframe(
        df_partidos[columnas],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PROGRAMACIÓN
# ============================================================

elif opcion == "🎯 Programación":

    st.header("🎯 Generación de programación semanal")

    st.markdown(
        """
        El motor considera:

        - Categoría requerida.
        - Sustitución por categoría superior.
        - Rol arbitral.
        - Árbitros híbridos.
        - Disponibilidad.
        - Conflictos horarios.
        - Escenario.
        - Desplazamiento entre escenarios.
        - Máximo recomendado de 2 partidos de campo diarios.
        - Máximo de 14 partidos de campo semanales.
        - Equilibrio de carga.
        """
    )

    if st.button(
        "🚀 Generar programación",
        type="primary"
    ):

        with st.spinner(
            "Procesando partidos y asignando personal..."
        ):

            (
                df_asignaciones,
                df_alertas
            ) = generar_programacion(
                df_arbitros,
                df_disponibilidad,
                df_partidos
            )

        st.session_state[
            "asignaciones"
        ] = df_asignaciones

        st.session_state[
            "alertas"
        ] = df_alertas

        st.success(
            "✅ Programación generada."
        )

    if "asignaciones" in st.session_state:

        df_asignaciones = st.session_state[
            "asignaciones"
        ]

        df_alertas = st.session_state[
            "alertas"
        ]

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

        pendientes = total - asignados

        cobertura = (
            asignados / total * 100
            if total
            else 0
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Asignaciones",
                total
            )

        with col2:
            st.metric(
                "Asignadas",
                asignados
            )

        with col3:
            st.metric(
                "Pendientes",
                pendientes
            )

        with col4:
            st.metric(
                "Cobertura",
                f"{cobertura:.1f}%"
            )

        st.divider()

        # ----------------------------------------------------
        # FILTROS
        # ----------------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:

            eventos = [
                "Todos"
            ] + sorted(
                df_asignaciones[
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
                df_asignaciones[
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
            df_asignaciones.copy()
        )

        if filtro_evento != "Todos":

            resultado = resultado[
                resultado["evento"]
                == filtro_evento
            ]

        if filtro_fecha != "Todas":

            resultado = resultado[
                resultado["fecha"]
                == filtro_fecha
            ]

        if filtro_estado != "Todos":

            resultado = resultado[
                resultado["estado"]
                == filtro_estado
            ]

        # ----------------------------------------------------
        # TABLA PRINCIPAL
        # ----------------------------------------------------

        st.subheader(
            "📋 Programación semanal"
        )

        columnas_informe = [
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
            "nombre_arbitro",
            "estado"
        ]

        st.dataframe(
            resultado[
                columnas_informe
            ],
            use_container_width=True,
            hide_index=True
        )

        # ----------------------------------------------------
        # DESCARGA CSV
        # ----------------------------------------------------

        csv = resultado[
            columnas_informe
        ].to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "⬇️ Descargar programación CSV",
            data=csv,
            file_name=(
                "programacion_semanal.csv"
            ),
            mime="text/csv"
        )

        # ----------------------------------------------------
        # ALERTAS RESUMEN
        # ----------------------------------------------------

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

            st.divider()

            st.subheader(
                "🚨 Resumen de alertas"
            )

            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric(
                    "Críticas",
                    criticas
                )

            with c2:
                st.metric(
                    "Advertencias",
                    advertencias
                )

            with c3:
                st.metric(
                    "Informativas",
                    informativas
                )


# ============================================================
# ALERTAS
# ============================================================

elif opcion == "🚨 Alertas":

    st.header("🚨 Alertas de la programación")

    if "alertas" not in st.session_state:

        st.info(
            "Primero genera la programación semanal."
        )

    else:

        df_alertas = st.session_state[
            "alertas"
        ]

        if df_alertas.empty:

            st.success(
                "🎉 No se generaron alertas."
            )

        else:

            criticas = df_alertas[
                df_alertas["tipo"]
                == "CRÍTICA"
            ]

            advertencias = df_alertas[
                df_alertas["tipo"]
                == "ADVERTENCIA"
            ]

            informativas = df_alertas[
                df_alertas["tipo"]
                == "INFORMATIVA"
            ]

            if not criticas.empty:

                st.error(
                    f"🔴 {len(criticas)} alertas críticas"
                )

                st.dataframe(
                    criticas,
                    use_container_width=True,
                    hide_index=True
                )

            if not advertencias.empty:

                st.warning(
                    f"🟡 {len(advertencias)} advertencias"
                )

                st.dataframe(
                    advertencias,
                    use_container_width=True,
                    hide_index=True
                )

            if not informativas.empty:

                st.info(
                    f"🔵 {len(informativas)} alertas informativas"
                )

                st.dataframe(
                    informativas,
                    use_container_width=True,
                    hide_index=True
                )

            # ------------------------------------------------
            # DESCARGA
            # ------------------------------------------------

            csv_alertas = df_alertas.to_csv(
                index=False
            ).encode("utf-8-sig")

            st.download_button(
                "⬇️ Descargar informe de alertas",
                data=csv_alertas,
                file_name="alertas_programacion.csv",
                mime="text/csv"
            )


# ============================================================
# PIE DE PÁGINA
# ============================================================

st.divider()

st.caption(
    "🏀 Asignador de Árbitros de Baloncesto | "
    "Proyecto Final - Análisis de Datos Junior"
)