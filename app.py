import streamlit as st
import pandas as pd

# =========================================================
# CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="Asignador de Árbitros de Baloncesto",
    page_icon="🏀",
    layout="wide"
)

# =========================================================
# TÍTULO
# =========================================================

st.title("🏀 Asignador de Árbitros de Baloncesto")
st.subheader("Sistema de gestión y programación de jornadas arbitrales")

st.markdown(
    """
    Carga un dataset de árbitros, jornadas o partidos para comenzar
    el proceso de análisis y asignación.
    """
)

st.divider()

# =========================================================
# CARGA DEL DATASET
# =========================================================

st.header("📂 Cargar dataset")

archivo = st.file_uploader(
    "Selecciona un archivo CSV o Excel",
    type=["csv", "xlsx", "xls"],
    help="Puedes cargar archivos en formato CSV o Excel."
)

if archivo is not None:

    try:

        # -------------------------------------------------
        # LECTURA DEL ARCHIVO
        # -------------------------------------------------

        if archivo.name.lower().endswith(".csv"):

            try:
                df = pd.read_csv(archivo)

            except UnicodeDecodeError:
                archivo.seek(0)
                df = pd.read_csv(archivo, encoding="latin-1")

        else:
            df = pd.read_excel(archivo)

        # -------------------------------------------------
        # INFORMACIÓN DEL DATASET
        # -------------------------------------------------

        st.success(
            f"✅ Archivo '{archivo.name}' cargado correctamente."
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Registros", f"{df.shape[0]:,}")

        with col2:
            st.metric("Columnas", df.shape[1])

        with col3:
            st.metric(
                "Valores faltantes",
                f"{df.isna().sum().sum():,}"
            )

        with col4:
            st.metric(
                "Duplicados",
                f"{df.duplicated().sum():,}"
            )

        st.divider()

        # -------------------------------------------------
        # VISTA DEL DATASET
        # -------------------------------------------------

        st.subheader("👀 Vista previa")

        st.dataframe(
            df,
            use_container_width=True,
            height=400
        )

        # -------------------------------------------------
        # INFORMACIÓN DE COLUMNAS
        # -------------------------------------------------

        st.subheader("📋 Información de las columnas")

        informacion = pd.DataFrame({
            "Columna": df.columns,
            "Tipo de dato": df.dtypes.astype(str).values,
            "Valores nulos": df.isna().sum().values,
            "Valores únicos": [
                df[col].nunique()
                for col in df.columns
            ]
        })

        st.dataframe(
            informacion,
            use_container_width=True
        )

        # -------------------------------------------------
        # ESTADÍSTICAS
        # -------------------------------------------------

        st.subheader("📊 Estadísticas descriptivas")

        st.dataframe(
            df.describe(include="all").transpose(),
            use_container_width=True
        )

        # -------------------------------------------------
        # DESCARGAR DATASET
        # -------------------------------------------------

        st.subheader("💾 Descargar dataset")

        csv = df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv,
            file_name="dataset_procesado.csv",
            mime="text/csv"
        )

    except Exception as e:

        st.error(
            f"❌ No fue posible procesar el archivo: {e}"
        )

else:

    st.info(
        "👆 Carga un archivo CSV o Excel para comenzar."
    )

# =========================================================
# PIE DE PÁGINA
# =========================================================

st.divider()

st.caption(
    "Asignador de Árbitros de Baloncesto | "
    "Proyecto Final - Análisis de Datos Junior"
)