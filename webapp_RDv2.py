import streamlit as st
import pandas as pd
import altair as alt
import math
import os

# ==========================================
#      CONFIGURACIÓN
# ==========================================

# URL del archivo CSV/Excel que sirve como base de datos histórica
GSHEET_URL = "https://drive.google.com/uc?id=15EAxTJ1UaGwsW2xRqbN-HDFa9JWNLhG7&export=download"

# Configuración de la página
st.set_page_config(page_title="Control de plano de construcción", layout="wide", page_icon="📊")

# ==========================================
#      FUNCIONES DE CARGA DE DATOS
# ==========================================

@st.cache_data(ttl=600)
def load_data():
    """
    Carga los datos desde la URL del Google Sheet (CSV).
    """
    try:
        # Leemos el CSV. Si hay líneas con errores, las saltamos para no romper la app.
        df = pd.read_csv(GSHEET_URL, on_bad_lines='skip')
        return df
    except Exception as e:
        st.error(f"Error crítico al cargar la base de datos: {e}")
        return None

# ==========================================
#      INTERFAZ DE STREAMLIT
# ==========================================

# --- CSS PERSONALIZADO PARA TABS ---
st.markdown("""
<style>
    /* Estilo general de los botones de los tabs */
    button[data-baseweb="tab"] {
        font-size: 20px !important;
        font-weight: 700 !important;
        padding-top: 10px !important;
        padding-bottom: 10px !important;
    }
    
    /* Estilo específico cuando un tab está seleccionado */
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #0068c9 !important;  /* Azul ingeniería */
        background-color: rgba(0, 104, 201, 0.1) !important; /* Fondo sutil */
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)
# -----------------------------------

# 1. Cargar datos al inicio automáticamente
if 'scan_data' not in st.session_state or st.session_state['scan_data'] is None:
    with st.spinner("Cargando base de datos histórica..."):
        st.session_state['scan_data'] = load_data()

st.title("📊 Control de Planos de Construcción y RedLines (RD) - Proyecto L4-T62-003")

# --- BARRA LATERAL ---
with st.sidebar:
    # ----------------------------------------------
    # 🖼️ INSERCIÓN DEL LOGO DE LA EMPRESA
    # ----------------------------------------------
    logo_path = "logo_CPP_Rev01.png"
    
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("### CAD PROYECTOS PERU, SAC")
    
    st.markdown("---") 
    
    st.info("Actulizado al 24.01.2026")
    st.caption("Los datos se cargan desde el registro centralizado.")

# --- LÓGICA PRINCIPAL ---

if st.session_state['scan_data'] is not None:
    df_full = st.session_state['scan_data']
    
    if df_full.empty:
        st.warning("La base de datos está vacía o no se pudo leer correctamente.")
    else:
        st.sidebar.markdown("---")
        st.sidebar.header("📂 Grupo de Análisis")
        
        # Verificar que existan las columnas necesarias antes de filtrar
        if '_Category' in df_full.columns:
            count_planos = len(df_full[df_full['_Category'] == 'Plano'])
            count_sketches = len(df_full[df_full['_Category'] == 'Sketch'])
        else:
            count_planos = 0
            count_sketches = 0
        
        grupo_seleccionado = st.sidebar.radio(
            "Seleccione el tipo de documento a analizar:",
            ["Planos", "Sketches"],
            format_func=lambda x: f"{x} ({count_planos if x == 'Planos' else count_sketches})"
        )
        
        if grupo_seleccionado == "Planos":
            df = df_full[df_full['_Category'] == 'Plano'].copy()
            titulo_seccion = "Planos Base"
        else:
            df = df_full[df_full['_Category'] == 'Sketch'].copy()
            titulo_seccion = "Sketches (SK)"

        st.markdown(f"### 🎯 Vista Actual: **{titulo_seccion}**")

        st.subheader("🔎 Filtros de Visualización (Para Matriz y Listado)")
        c1, c2, c3 = st.columns(3)
        
        all_specs = ["Todas"] + sorted(df['_Specialty'].unique().tolist())
        filtro_esp = c1.selectbox("Especialidad:", all_specs)
        busqueda = c2.text_input("Buscar archivo (contiene):")
        filtro_tipo = c3.radio("Mostrar:", ["Todo", "Solo RedLines", "Solo Originales"], horizontal=True)

        df_filtered = df.copy()
        if filtro_esp != "Todas":
            df_filtered = df_filtered[df_filtered['_Specialty'] == filtro_esp]
        if busqueda:
            df_filtered = df_filtered[df_filtered['Nombre Archivo'].str.contains(busqueda, case=False)]
        if filtro_tipo == "Solo RedLines":
            df_filtered = df_filtered[df_filtered['_IsRedLine'] == "Sí"]
        elif filtro_tipo == "Solo Originales":
            df_filtered = df_filtered[df_filtered['_IsRedLine'] == "No"]

        st.divider()

        # ==========================================
        #      DEFINICIÓN DE TABS (PESTAÑAS)
        # ==========================================
        tab1, tab2, tab3 = st.tabs([
            "📈 Resumen Ejecutivo", 
            "📊 Detalle por especialidad de Planos y Sketchs", 
            "🔍 Busqueda de plano"
        ])

        # ==============================================================================
        #      TAB 1: RESUMEN EJECUTIVO (GERENCIAL)
        # ==============================================================================
        with tab1:
            st.markdown("### 🏢 Tablero de Control Gerencial")
            st.caption("Resumen global de avance ordenado por progreso.")

            def calcular_kpis(categoria):
                subset = df_full[df_full['_Category'] == categoria].copy()
                if subset.empty: 
                    return pd.DataFrame(), pd.DataFrame(), 0

                temp = subset.groupby(['_Specialty', '_BaseName'])['_IsRedLine'].apply(
                    lambda x: "Sí" in x.values
                ).reset_index(name='HasRD')
                
                resumen = temp.groupby('_Specialty').agg(
                    Total_Docs=('HasRD', 'count'),
                    Con_RD=('HasRD', 'sum')
                ).reset_index()

                resumen['Total_Docs'] = resumen['Total_Docs'].astype(int)
                resumen['Con_RD'] = resumen['Con_RD'].astype(int)
                resumen['Sin_RD'] = resumen['Total_Docs'] - resumen['Con_RD']
                
                resumen['Pct_RD'] = 0.0
                mask = resumen['Total_Docs'] > 0
                resumen.loc[mask, 'Pct_RD'] = (resumen.loc[mask, 'Con_RD'] / resumen.loc[mask, 'Total_Docs']) * 100

                resumen = resumen.sort_values(by='Pct_RD', ascending=False)

                total_docs_all = int(resumen['Total_Docs'].sum())
                total_con_all = int(resumen['Con_RD'].sum())
                total_sin_all = total_docs_all - total_con_all
                pct_all = (total_con_all / total_docs_all * 100) if total_docs_all > 0 else 0.0
                
                row_total = pd.DataFrame([{
                    '_Specialty': 'TOTAL GENERAL',
                    'Total_Docs': total_docs_all,
                    'Con_RD': total_con_all,
                    'Sin_RD': total_sin_all,
                    'Pct_RD': pct_all
                }])
                
                df_final = pd.concat([resumen, row_total], ignore_index=True)
                df_chart = resumen.copy()
                
                return df_chart, df_final, total_docs_all

            df_chart_planos, df_table_planos, total_planos = calcular_kpis("Plano")
            df_chart_sk, df_table_sk, total_sketches = calcular_kpis("Sketch")

            def obtener_totales(df_resumen):
                if df_resumen.empty: return 0, 0, 0
                row = df_resumen.iloc[-1]
                return int(row['Con_RD']), int(row['Sin_RD']), row['Pct_RD']

            rd_planos, sin_rd_planos, pct_planos = obtener_totales(df_table_planos)
            rd_sk, sin_rd_sk, pct_sk = obtener_totales(df_table_sk)

            kpi_col1, kpi_col2 = st.columns(2)

            with kpi_col1:
                st.markdown("### 🏗️ Total Planos Obra")
                st.caption("Cantidad de Planos de Ingeniería")
                st.metric(label="Total Documentos", value=total_planos)
                st.markdown("---") 
                sub_c1, sub_c2 = st.columns(2)
                with sub_c1: st.metric("Con RD", rd_planos)
                with sub_c2: st.metric("Sin RD", sin_rd_planos)
                st.metric("% de Planos Proyecto con RD", f"{pct_planos:.1f}%")

            with kpi_col2:
                st.markdown("### 📝 Total Sketches (SK)")
                st.caption("Cantidad de Sketches/planos generados en obra bajo Alcance de HAUG")
                st.metric(label="Total Documentos", value=total_sketches)
                st.markdown("---")
                sub_c3, sub_c4 = st.columns(2)
                with sub_c3: st.metric("Con RD", rd_sk)
                with sub_c4: st.metric("Sin RD", sin_rd_sk)
                st.metric("% de Sketches con RD", f"{pct_sk:.1f}%")

            st.divider()

            def generar_grafico_altair(data, color_destacado):
                if data.empty: return None
                data_graf = data.copy()
                data_graf['Etiqueta'] = data_graf['Pct_RD'].apply(lambda x: f"{x:.1f}%")
                orden_especialidades = data_graf['_Specialty'].tolist()

                df_melted = data_graf.melt(
                    id_vars=['_Specialty', 'Etiqueta', 'Total_Docs'], 
                    value_vars=['Sin_RD', 'Con_RD'], 
                    var_name='Estado', 
                    value_name='Cantidad'
                )

                domain = ['Sin_RD', 'Con_RD']
                range_ = ['#e0e0e0', color_destacado]

                barras = alt.Chart(df_melted).mark_bar().encode(
                    x=alt.X('_Specialty', sort=orden_especialidades, axis=alt.Axis(title=None, labelAngle=-45)),
                    y=alt.Y('Cantidad', title='N° Documentos'),
                    color=alt.Color('Estado', scale=alt.Scale(domain=domain, range=range_), legend=alt.Legend(title="Estado")),
                    order=alt.Order('Estado', sort='ascending'),
                    tooltip=['_Specialty', 'Estado', 'Cantidad']
                )

                textos = alt.Chart(data_graf).mark_text(dy=-10, color='black').encode(
                    x=alt.X('_Specialty', sort=orden_especialidades),
                    y=alt.Y('Total_Docs'),
                    text=alt.Text('Etiqueta')
                )
                return (barras + textos).properties(height=320)

            c_chart1, c_chart2 = st.columns(2)
            with c_chart1:
                st.subheader("📊 % de Planos Proyecto con RD")
                chart_p = generar_grafico_altair(df_chart_planos, "#ff4b4b")
                if chart_p: st.altair_chart(chart_p, use_container_width=True)
                else: st.info("Sin datos.")

            with c_chart2:
                st.subheader("📊 % de Sketches con RD")
                chart_s = generar_grafico_altair(df_chart_sk, "#4b4bff")
                if chart_s: st.altair_chart(chart_s, use_container_width=True)
                else: st.info("Sin datos.")

            st.divider()

            st.subheader("📋 Detalle Numérico (Ordenado por % Avance)")
            col_config_kpi = {
                "_Specialty": st.column_config.TextColumn("Especialidad", width="medium"),
                "Total_Docs": st.column_config.NumberColumn("Total", format="%d", width="small"),
                "Con_RD": st.column_config.NumberColumn("Con RD", format="%d", width="small"),
                "Sin_RD": st.column_config.NumberColumn("Sin RD", format="%d", width="small"),
                "Pct_RD": st.column_config.ProgressColumn(
                    "% Avance", format="%.1f%%", min_value=0, max_value=100, width="medium"
                )
            }
            col_t1, col_t2 = st.columns(2)
            
            with col_t1:
                st.markdown("**Detalle Planos**")
                if not df_table_planos.empty:
                    height_p = (len(df_table_planos) + 1) * 35 + 3
                    st.dataframe(df_table_planos, column_config=col_config_kpi, hide_index=True, use_container_width=True, height=height_p)
                else: st.write("No hay datos.")

            with col_t2:
                st.markdown("**Detalle Sketches**")
                if not df_table_sk.empty:
                    height_s = (len(df_table_sk) + 1) * 35 + 3
                    st.dataframe(df_table_sk, column_config=col_config_kpi, hide_index=True, use_container_width=True, height=height_s)
                else: st.write("No hay datos.")

        # ==============================================================================
        #      TAB 2: MATRIZ DE CONTROL (FILTRABLE) - CON TOTALES
        # ==============================================================================
        with tab2:
            if df_filtered.empty:
                st.warning(f"No hay {grupo_seleccionado} para mostrar con los filtros actuales.")
            else:
                st.markdown(f"### 1️⃣ Panorama General ({grupo_seleccionado} Únicos)")
                st.caption("Conteo basado en la última versión disponible (Filtrado). Se incluye TOTAL GENERAL al final.")
                
                df_latest_status = df_filtered.groupby(['_Specialty', '_BaseName'])['_RDNum'].max().reset_index()
                
                pivot_global = df_latest_status.pivot_table(
                    index='_Specialty', columns='_RDNum', values='_BaseName', aggfunc='count', fill_value=0
                )
                
                new_cols = []
                for col in pivot_global.columns:
                    if col == 0: new_cols.append("Original")
                    else: new_cols.append(f"RD {col}")
                pivot_global.columns = new_cols

                if "Original" not in pivot_global.columns: pivot_global["Original"] = 0
                
                pivot_global = pivot_global.sort_values(by="Original", ascending=False).astype(int)

                total_row = pivot_global.sum()
                total_row.name = "TOTAL GENERAL"
                pivot_global = pd.concat([pivot_global, total_row.to_frame().T])

                height_pivot = (len(pivot_global) + 1) * 35 + 3
                st.dataframe(
                    pivot_global.style.background_gradient(cmap="Blues", axis=0).format("{:.0f}"), 
                    use_container_width=True, 
                    height=height_pivot
                )

                st.divider()

                st.markdown("### 2️⃣ Desglose Detallado con Descarga")
                specialties = sorted(df_filtered['_Specialty'].unique())
                for spec in specialties:
                    spec_df = df_filtered[df_filtered['_Specialty'] == spec]
                    idx = spec_df.groupby('_BaseName')['_RDNum'].transform('max') == spec_df['_RDNum']
                    spec_df_latest = spec_df[idx]

                    pivot_links = spec_df_latest.pivot_table(
                        index='_BaseName', columns='_RDNum', values='URL Descarga', aggfunc='first' 
                    )
                    link_cols = {col: ("Original" if col == 0 else f"RD {col}") for col in pivot_links.columns}
                    pivot_links.rename(columns=link_cols, inplace=True)
                    
                    with st.expander(f"📂 {spec} | {len(pivot_links)} Docs"):
                        column_config_dynamic = {"_BaseName": st.column_config.TextColumn("Nombre Base", width="medium")}
                        for col_name in pivot_links.columns:
                            column_config_dynamic[str(col_name)] = st.column_config.LinkColumn(str(col_name), display_text="⬇️", width="small")
                        
                        height_links = min((len(pivot_links) + 1) * 35 + 3, 600)
                        st.data_editor(
                            pivot_links.reset_index(),
                            column_config=column_config_dynamic,
                            hide_index=True, disabled=True, use_container_width=True, height=height_links
                        )

        # ==============================================================================
        #      TAB 3: LISTADO SIMPLE
        # ==============================================================================
        with tab3:
            st.caption(f"Listado completo ({grupo_seleccionado}).")
            st.data_editor(
                df_filtered[["Nombre Archivo", "Carpeta Ubicación", "_Specialty", "_IsRedLine", "_RDNum", "URL Descarga"]],
                column_config={
                    "URL Descarga": st.column_config.LinkColumn("Link", display_text="⬇️ Bajar", width="small"),
                    "_Specialty": st.column_config.TextColumn("Especialidad", width="medium"),
                    "Nombre Archivo": st.column_config.TextColumn("Archivo", width="large"),
                    "_IsRedLine": st.column_config.TextColumn("Es RD?", width="small"),
                    "_RDNum": st.column_config.NumberColumn("N° Rev", width="small")
                },
                hide_index=True, use_container_width=True
            )
            csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
            st.download_button(f"📥 Descargar CSV ({grupo_seleccionado})", csv, f"Reporte_{grupo_seleccionado}.csv", "text/csv", type="primary")