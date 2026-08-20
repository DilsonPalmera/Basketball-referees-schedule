import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------------------------------------

st.set_page_config(
    page_title="Asignador de Árbitros de Baloncesto",
    page_icon="🏀",
    layout="wide"
)

# ---------------------------------------------------------
# ENCABEZADO
# ---------------------------------------------------------

st.title("🏀 Asignador de Árbitros de Baloncesto")
st.subheader("Sistema de gestión y programación de jornadas arbitrales")

st.markdown("""
Esta aplicación permitirá gestionar árbitros, jornadas y partidos,
para posteriormente realizar asignaciones de manera organizada,
equilibrada y eficiente.
""")

st.divider()

# ---------------------------------------------------------
# MENÚ LATERAL
# ---------------------------------------------------------

st.sidebar.title("⚙️ Menú principal")

opcion = st.sidebar.radio(
    "Seleccione una opción:",
    [
        "Inicio",
        "Árbitros",
        "Jornadas",
        "Partidos",
        "Asignaciones"
    ]
)

# ---------------------------------------------------------
# INICIO
# ---------------------------------------------------------

if opcion == "Inicio":

    st.header("📊 Panel principal")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Árbitros", "0")

    with col2:
        st.metric("Jornadas", "0")

    with col3:
        st.metric("Partidos", "0")

    with col4:
        st.metric("Asignaciones", "0")

    st.info(
        "🚧 El sistema se encuentra en fase inicial de desarrollo. "
        "En las siguientes versiones se incorporarán la gestión de "
        "datos y el algoritmo de asignación."
    )

# ---------------------------------------------------------
# ÁRBITROS
# ---------------------------------------------------------

elif opcion == "Árbitros":

    st.header("👨‍⚖️ Gestión de Árbitros")

    st.write(
        "En este módulo se registrarán y administrarán los árbitros "
        "disponibles para las jornadas."
    )

    st.warning("Módulo pendiente de implementación.")

# ---------------------------------------------------------
# JORNADAS
# ---------------------------------------------------------

elif opcion == "Jornadas":

    st.header("📅 Gestión de Jornadas")

    st.write(
        "Aquí se podrán crear y administrar las jornadas de "
        "competencia."
    )

    st.warning("Módulo pendiente de implementación.")

# ---------------------------------------------------------
# PARTIDOS
# ---------------------------------------------------------

elif opcion == "Partidos":

    st.header("🏀 Gestión de Partidos")

    st.write(
        "Aquí se registrarán los partidos correspondientes a "
        "cada jornada."
    )

    st.warning("Módulo pendiente de implementación.")

# ---------------------------------------------------------
# ASIGNACIONES
# ---------------------------------------------------------

elif opcion == "Asignaciones":

    st.header("🎯 Asignación de Árbitros")

    st.write(
        "Este será el módulo principal del sistema. "
        "Aquí se realizará la asignación de árbitros a los "
        "diferentes partidos."
    )

    st.warning("Algoritmo de asignación pendiente de implementación.")

# ---------------------------------------------------------
# PIE DE PÁGINA
# ---------------------------------------------------------

st.divider()

st.caption(
    "Asignador de Árbitros de Baloncesto | "
    "Proyecto Final - Análisis de Datos Junior"
)