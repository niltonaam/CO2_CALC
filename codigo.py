import streamlit as st
import math
import textwrap
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
import io
import requests
import base64

# ================================================================
# CONFIGURACIÓN GENERAL Y ESTILOS
# ================================================================

st.set_page_config(page_title="Calculadora de Emisiones en Transporte Forestal", layout="wide", initial_sidebar_state="collapsed")

# Estilos CSS personalizados
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }
    
    /* Compactar padding general de la aplicación */
    .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
    }

    div[data-testid="stVerticalBlock"] {
        gap: 0.5rem !important;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 0.75rem !important;
    }
    
    .stApp {
        background-color: #f4fafd;
        color: #161d1f;
    }
    
    .stTextInput > div > div > input, 
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stSelectbox > div > div > div {
        background-color: #ffffff;
        border: 1px solid #c1c8c2;
        border-radius: 0.25rem;
        color: #161d1f !important;
        padding-top: 0.25rem !important;
        padding-bottom: 0.25rem !important;
    }
    
    .stTextInput label p,
    .stNumberInput label p,
    .stDateInput label p,
    .stSelectbox label p,
    .stCheckbox label p,
    .stSlider label p {
        color: #161d1f !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        margin-bottom: 0.1rem !important;
    }

    .stButton > button {
        background-color: #1b4332 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 0.25rem !important;
        font-weight: 600 !important;
        padding: 0.4rem 1rem !important;
        transition: all 0.3s ease !important;
        width: 100%;
    }
    
    .stButton > button:hover {
        background-color: #012d1d !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        transform: translateY(-2px) !important;
    }
    
    .stDownloadButton > button {
        background-color: #a1f4c8 !important;
        color: #1b724f !important;
        border: 1px solid #1b724f !important;
        border-radius: 0.25rem !important;
        font-weight: 600 !important;
        padding: 0.4rem 1rem !important;
        transition: all 0.3s ease !important;
        width: 100%;
    }
    
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        border-bottom: 1px solid #dde4e6;
        padding-bottom: 0.2rem;
        margin-bottom: 0.5rem;
    }
    
    .section-header h2 {
        font-size: 1.1rem;
        font-weight: 600;
        color: #012d1d;
        margin: 0;
    }
    
    .section-container {
        background-color: #ffffff;
        border: 1px solid #c1c8c2;
        border-radius: 0.5rem;
        padding: 0.85rem 1rem;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        margin-bottom: 0.5rem;
    }    
    .chart-clickable {
        transition: transform 0.2s ease, filter 0.2s ease;
    }
    .chart-clickable:hover {
        transform: scale(1.02);
        filter: brightness(0.96);
    }</style>
""", unsafe_allow_html=True)

COR_AZUL_OSCURO = "#0B1F3A"
COR_AZUL = "#1E3A8A"
COR_VERDE = "#0F766E"
COR_AMARILLO = "#B45309"
COR_ROJO = "#B91C1C"
COR_VIOLETA = "#7C3AED"
COR_TEXTO = "#0F172A"
COR_TEXTO_SUAVE = "#475569"
COR_CO2 = "#1E3A8A"
COR_CH4 = "#15803D"
COR_N2O = "#B45309"

FE_IPCC_TJ = {
    "diésel": {"CO2": 74100.0, "CH4": 3.9, "N2O": 3.9},
    "biodiésel": {"CO2": 0.0, "CH4": 3.9, "N2O": 3.9},
    "gnl": {"CO2": 56100.0, "CH4": 16.0, "N2O": 3.2},
    "eléctrico": {"CO2": 0.0, "CH4": 0.0, "N2O": 0.0},
}

TJ_POR_L = 43.0 / 1_000_000
GWP_CH4 = 28.0
GWP_N2O = 265.0

# ================================================================
# LÓGICA DE CÁLCULO
# ================================================================

def calcular_emisiones_ipcc(consumo_total_litros, combustible):
    fe = FE_IPCC_TJ.get(combustible, FE_IPCC_TJ["diésel"])
    energia_tj = consumo_total_litros * TJ_POR_L
    co2 = energia_tj * fe["CO2"]
    ch4 = energia_tj * fe["CH4"]
    n2o = energia_tj * fe["N2O"]
    co2e_ch4 = ch4 * GWP_CH4
    co2e_n2o = n2o * GWP_N2O
    co2e_total = co2 + co2e_ch4 + co2e_n2o
    return co2, ch4, n2o, co2e_total, co2e_ch4, co2e_n2o, energia_tj

def clasificar_emision(emis_kg_tkm):
    emis_g_tkm = emis_kg_tkm * 1000
    if emis_g_tkm < 50:
        return "A", "Eficiencia alta", "Operación con desempeño superior para transporte carretero de cargas.", COR_VERDE, "Óptima", "check_circle"
    if emis_g_tkm < 80:
        return "B", "Eficiencia adecuada", "Operación dentro de una franja técnicamente aceptable.", COR_AZUL, "Buena", "info"
    if emis_g_tkm < 120:
        return "C", "Eficiencia intermedia", "Existe una oportunidad relevante para optimizar carga, ruta o consumo.", COR_AMARILLO, "Regular", "warning"
    return "D", "Eficiencia crítica", "Se recomienda revisar consumo, retorno vacío, ocupación y tecnología vehicular.", COR_ROJO, "Crítica", "error"

def calcular_score(emis_kg_tkm):
    emis_g_tkm = emis_kg_tkm * 1000
    score = 100 - ((emis_g_tkm - 30) * 1.15)
    return max(0, min(100, score))

def generar_diagnostico(r):
    participacion_co2 = (r["CO2"] / r["CO2e"] * 100) if r["CO2e"] > 0 else 0
    emis_g_tkm = r["emis_kg_tkm"] * 1000
    texto = f"""
    La operación presentó una emisión total de {r["CO2e"]:.2f} kg CO₂e,
    con una intensidad logística de {emis_g_tkm:.1f} g CO₂e/t.km.
    El CO₂ representa aproximadamente {participacion_co2:.1f}%
    de las emisiones equivalentes, indicando predominio de la combustión energética.

    La distancia total considerada fue de {r["dist_total"]:.1f} km,
    con un consumo agregado de {r["cons_total_L"]:.2f} L.
    El consumo medio operativo fue de {r["consumo_l_100km"]:.2f} L/100 km.

    La clasificación obtenida fue {r["clase_letra"]} · {r["clase_nombre"]}.
    {r["recomendacion"]}
    """
    return texto

# ================================================================
# INTERFAZ GRÁFICA STREAMLIT
# ================================================================

# Encabezado principal
st.title("Calculadora de Emisiones en Transporte Forestal")
st.caption("Ingrese los datos operativos de la carga y el vehículo para estimar la huella de carbono y evaluar la eficiencia logística.")

col_left, col_right = st.columns([7, 5], gap="large")

with col_left:
    # 1. Identificación de la Operación
    with st.container(border=True):
        st.subheader("1. Identificación de la Operación", divider="green")
        
        # Nombre del Proyecto y Fecha de Operaciones uno al lado del otro
        col_nf1, col_nf2 = st.columns(2)
        with col_nf1:
            nombre = st.text_input("Nombre / Encargado", placeholder="Ej. Juan Carlos")
        with col_nf2:
            fecha = st.date_input("Fecha de Operación", value=datetime.today())

        empresa = st.text_input("Cliente / Empresa", placeholder="Ej. UTEC")
        
        # Producto y Código NCM uno al lado del otro
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            producto_manual = st.text_input("Producto", placeholder="Ej. Madera en trozas / Pino")
        with col_p2:
            ncm_code = st.text_input("Código NCM", placeholder="Ej. 44032000")
            desc_ncm = ""
            cap_ncm = ""
            if ncm_code.strip():
                clean_code = ncm_code.strip().replace(".", "")
                cap_code = clean_code[:2] if len(clean_code) >= 2 else ""
                
                # Obtener Capítulo (primeros 2 dígitos) y descripción específica NCM
                try:
                    if cap_code:
                        r_cap = requests.get(f"https://brasilapi.com.br/api/ncm/v1/{cap_code}", timeout=3)
                        if r_cap.status_code == 200:
                            cap_ncm = r_cap.json().get("descricao", "")
                    
                    if len(clean_code) >= 4:
                        r_ncm = requests.get(f"https://brasilapi.com.br/api/ncm/v1?search={clean_code[:4]}", timeout=3)
                        if r_ncm.status_code == 200:
                            items = r_ncm.json()
                            for item in items:
                                item_code = item.get("codigo", "").replace(".", "")
                                if item_code == clean_code:
                                    desc_ncm = item.get("descricao", "")
                                    break
                            if not desc_ncm and items:
                                desc_ncm = items[0].get("descricao", "")
                except Exception:
                    desc_ncm = "Error de conexión API"
                    
                info_msg = ""
                if cap_code and cap_ncm:
                    info_msg += f"**Capítulo {cap_code}:** {cap_ncm}\n\n"
                if desc_ncm:
                    info_msg += f"**NCM:** {desc_ncm}"
                elif not cap_ncm:
                    info_msg = f"**NCM:** {ncm_code}"

                if info_msg:
                    st.info(info_msg)

        # Origen y Destino uno al lado del otro
        col_od1, col_od2 = st.columns(2)
        with col_od1:
            origen = st.text_input("Origen", placeholder="Ej. Rivera")
        with col_od2:
            destino = st.text_input("Destino", placeholder="Ej. Muelle Fray Bentos")

        # Asignar producto definitivo (usar producto manual si existe, o la descripción/código NCM como fallback)
        if producto_manual.strip():
            producto = producto_manual.strip()
        elif desc_ncm:
            producto = desc_ncm
        else:
            producto = ncm_code

    # 2. Parámetros Técnicos
    if "num_trajetos" not in st.session_state:
        st.session_state.num_trajetos = 1

    def agregar_trajeto():
        st.session_state.num_trajetos += 1

    def eliminar_trajeto():
        if st.session_state.num_trajetos > 1:
            st.session_state.num_trajetos -= 1

    with st.container(border=True):
        st.subheader("2. Parámetros Técnicos del Transporte", divider="green")
        
        c1, c2 = st.columns(2)
        with c1:
            vehiculo = st.selectbox("Tipo de Vehículo", ["Camión Maderero (3 Ejes)", "Tráiler Articulado", "Camión Grúa Forestal", "Liviano", "Mediano", "Pesado"])
            combustible = st.selectbox("Tipo de Combustible", ["diésel", "biodiésel", "gnl", "eléctrico"])
            carga = st.number_input("Carga Útil (toneladas)", min_value=0.0, value=30.0, step=0.1)
            fill = st.slider("Factor de Carga (%)", min_value=10, max_value=100, value=100, step=5)
        with c2:
            euro = st.selectbox("Norma Euro", ["III", "IV", "V", "VI"])
            vel = st.number_input("Velocidad Promedio (km/h)", min_value=0.0, value=75.0, step=1.0)
            consumo = st.number_input("Consumo Promedio (L/km)", min_value=0.0, value=0.38, step=0.01)

        st.markdown("**Trajetos de la Operación:**")
        
        trajetos_input = []
        for idx in range(st.session_state.num_trajetos):
            st.caption(f"📍 **Trayecto {idx + 1}**")
            t_col1, t_col2, t_col3 = st.columns([2.5, 2, 1.5], vertical_alignment="bottom")
            with t_col1:
                t_nombre = st.text_input(
                    "Descripción / Tramo", 
                    value=f"Trayecto {idx + 1}", 
                    key=f"t_name_{idx}",
                    placeholder="Ej. Origen -> Acopio"
                )
            with t_col2:
                t_dist = st.number_input(
                    "Distancia (km)", 
                    min_value=0.0, 
                    value=390.0 if idx == 0 else 50.0, 
                    step=1.0, 
                    key=f"t_dist_{idx}"
                )
            with t_col3:
                t_ret = st.checkbox(
                    "Retorna vacío", 
                    value=True, 
                    key=f"t_ret_{idx}"
                )
            
            t_dist_total = t_dist * 2 if t_ret else t_dist
            trajetos_input.append({
                "nombre": t_nombre,
                "dist_ida": t_dist,
                "retorna": t_ret,
                "dist_total": t_dist_total
            })

        btn_t1, btn_t2 = st.columns(2)
        with btn_t1:
            st.button("➕ Agregar Trayecto", on_click=agregar_trajeto, use_container_width=True)
        with btn_t2:
            if st.session_state.num_trajetos > 1:
                st.button("🗑️ Eliminar Último Trayecto", on_click=eliminar_trajeto, use_container_width=True)

    # Campo opcional: Interpretación Técnica (Análisis, justificaciones y medidas de mitigación)
    with st.container(border=True):
        st.subheader("Observaciones e Interpretación Técnica", divider="green")
        user_interpretacion = st.text_area(
            "Análisis, justificaciones y medidas de mitigación (Opcional)",
            placeholder="Ingrese aquí análisis operativo, observaciones o acciones de mitigación contempladas...",
            height=100
        )

    # Botón principal de cálculo
    calc_pressed = st.button("🚀 Calcular Emisiones", type="primary", use_container_width=True)

with col_right:
    if calc_pressed:
        dist_total_acumulada = sum(t["dist_total"] for t in trajetos_input)
        dist_ida_acumulada = sum(t["dist_ida"] for t in trajetos_input)

        if not nombre.strip() or not empresa.strip() or dist_total_acumulada <= 0 or carga <= 0:
            st.error("⚠️ Por favor, complete los campos obligatorios correctamente (Nombre, Empresa, Distancia Total > 0, Carga > 0).")
        else:
            dist_total = dist_total_acumulada
            cons_total = dist_total * consumo

            co2, ch4, n2o, co2e, co2e_ch4, co2e_n2o, energia_tj = calcular_emisiones_ipcc(cons_total, combustible)
            carga_efectiva = carga * (fill / 100)
            tkm = carga_efectiva * dist_total
            emis_kg_tkm = co2e / tkm if tkm > 0 else 0
            emis_g_tkm = emis_kg_tkm * 1000

            clase_letra, clase_nombre, recomendacion, color_clase, efi_texto, efi_icon = clasificar_emision(emis_kg_tkm)
            score = calcular_score(emis_kg_tkm)
            consumo_l_100km = (cons_total / dist_total) * 100 if dist_total > 0 else 0

            st.session_state.r = {
                "nombre": nombre, "empresa": empresa, "producto": producto, "origen": origen, "destino": destino, "fecha": str(fecha),
                "vehiculo": vehiculo, "euro": euro, "comb": combustible,
                "trajetos": trajetos_input,
                "user_interpretacion": user_interpretacion.strip(),
                "dist_ida": dist_ida_acumulada, "dist_total": dist_total, "retorna": any(t["retorna"] for t in trajetos_input),
                "consumo": consumo, "cons_total_L": cons_total,
                "energia_TJ": energia_tj, "carga_nominal": carga, "carga_efectiva": carga_efectiva,
                "tkm": tkm, "CO2": co2, "CH4": ch4, "N2O": n2o, "CO2e": co2e,
                "CO2e_CH4": co2e_ch4, "CO2e_N2O": co2e_n2o, "emis_kg_tkm": emis_kg_tkm,
                "emis_g_tkm": emis_g_tkm, "clase_letra": clase_letra, "clase_nombre": clase_nombre,
                "recomendacion": recomendacion, "color_clase": color_clase, "score": score,
                "consumo_l_100km": consumo_l_100km, "efi_texto": efi_texto, "efi_icon": efi_icon
            }
            st.session_state.r["diagnostico"] = generar_diagnostico(st.session_state.r)

    with st.container(border=True):
        st.subheader("3. Interpretación Técnica", divider="green")
        
        if "r" in st.session_state:
            r = st.session_state.r
            
            # KPI principal
            st.metric(
                label="EMISIONES TOTALES (CO2e)",
                value=f"{r['CO2e']:,.0f} kg",
                delta=f"Clasificación: {r['clase_letra']} - {r['clase_nombre']}"
            )
            
            st.divider()
            
            # Cuadrícula de Métricas
            m1, m2 = st.columns(2)
            with m1:
                st.metric("CO₂ Emitido", f"{r['CO2']:,.0f} kg")
                st.metric("Consumo Total", f"{r['cons_total_L']:.1f} L")
            with m2:
                st.metric("Emisión Específica", f"{r['emis_g_tkm']:.1f} g/t.km")
                st.metric("Score Ambiental", f"{r['score']:.0f} / 100")
                
            st.divider()

            # Gráfico de desglose y distribución de gases (CO2, CH4 en CO2e, N2O en CO2e)
            # Modal Pop-up para ampliar gráficos
            @st.dialog("🔍 Vista Ampliada de Gráficos de Emisión", width="large")
            def popup_graficos(r_data):
                st.subheader("Desglose y Distribución de Gases (CO₂e)")
                col_pop1, col_pie_pop = st.columns(2)
                
                with col_pop1:
                    st.write("##### Cantidad Absoluta (kg CO₂e)")
                    df_gases_pop = pd.DataFrame({
                        "Gas": ["CO₂", "CH₄", "N₂O"],
                        "kg CO₂e": [r_data["CO2"], r_data["CO2e_CH4"], r_data["CO2e_N2O"]]
                    })
                    st.bar_chart(df_gases_pop, x="Gas", y="kg CO₂e", color="#0F766E", height=350)
                    
                with col_pie_pop:
                    st.write("##### Porcentaje Relativo (%)")
                    fig_p, ax_p = plt.subplots(figsize=(5, 4))
                    fig_p.patch.set_alpha(0.0)
                    ax_p.set_facecolor('none')
                    
                    labels = ['CO₂', 'CH₄', 'N₂O']
                    values = [r_data["CO2"], r_data["CO2e_CH4"], r_data["CO2e_N2O"]]
                    colors = ['#0F766E', '#15803D', '#B45309']
                    
                    nonzero = [(v, l, c) for v, l, c in zip(values, labels, colors) if v > 0]
                    if nonzero:
                        v_vals, l_labs, c_cols = zip(*nonzero)
                        total_v = sum(v_vals)
                        display_labels = [f"{l} ({v/total_v*100:.1f}%)" for v, l in zip(v_vals, l_labs)]
                        
                        wedges, texts, autotexts = ax_p.pie(
                            v_vals, 
                            colors=c_cols, 
                            autopct=lambda p: f'{p:.1f}%' if p >= 3.0 else '',
                            startangle=140,
                            pctdistance=0.6,
                            textprops=dict(color="white", size=10, weight="bold")
                        )
                        ax_p.legend(
                            wedges, 
                            display_labels,
                            loc="center left",
                            bbox_to_anchor=(1.0, 0.5),
                            fontsize=10,
                            frameon=False
                        )
                    else:
                        ax_p.text(0.5, 0.5, "Sin emisiones", ha='center', va='center', color="#0F172A")
                        
                    ax_p.axis('equal')
                    st.pyplot(fig_p, use_container_width=True, transparent=True)
                    plt.close(fig_p)

            st.write("**Desglose y Distribución de Gases (CO₂e):**")
            st.caption("💡 *Haga clic sobre el gráfico para ampliarlo en un pop-up*")

            # Generar figura combinada clicable
            fig_comb, (ax1_comb, ax2_comb) = plt.subplots(1, 2, figsize=(6.5, 2.1), gridspec_kw={'width_ratios': [1.1, 0.9]})
            fig_comb.patch.set_alpha(0.0)

            # Subplot 1: Bar chart
            ax1_comb.set_facecolor('none')
            gases_list = ['CO₂', 'CH₄', 'N₂O']
            vals_list = [r["CO2"], r["CO2e_CH4"], r["CO2e_N2O"]]
            ax1_comb.bar(gases_list, vals_list, color='#0F766E', width=0.45)
            ax1_comb.set_title("Desglose (kg CO₂e)", fontsize=8.5, color="#414844", loc="left", pad=3)
            ax1_comb.tick_params(colors='#0F172A', labelsize=8)
            ax1_comb.spines['top'].set_visible(False)
            ax1_comb.spines['right'].set_visible(False)
            ax1_comb.spines['left'].set_color('#dde4e6')
            ax1_comb.spines['bottom'].set_color('#dde4e6')
            ax1_comb.yaxis.grid(True, linestyle='--', alpha=0.3, color='#717973')
            ax1_comb.set_axisbelow(True)

            # Subplot 2: Pie chart
            ax2_comb.set_facecolor('none')
            labels_pie = ['CO₂', 'CH₄', 'N₂O']
            colors_pie = ['#0F766E', '#15803D', '#B45309']
            nonzero_comb = [(v, l, c) for v, l, c in zip(vals_list, labels_pie, colors_pie) if v > 0]

            if nonzero_comb:
                v_vals_c, l_labs_c, c_cols_c = zip(*nonzero_comb)
                total_v_c = sum(v_vals_c)
                display_labels_c = [f"{l} ({v/total_v_c*100:.1f}%)" if (v/total_v_c*100) >= 1.0 else f"{l}" for v, l in zip(v_vals_c, l_labs_c)]
                wedges_c, texts_c, autotexts_c = ax2_comb.pie(
                    v_vals_c, 
                    colors=c_cols_c, 
                    autopct=lambda p: f'{p:.1f}%' if p >= 5.0 else '',
                    startangle=140,
                    pctdistance=0.55,
                    textprops=dict(color="white", size=8, weight="bold")
                )
                ax2_comb.legend(wedges_c, display_labels_c, loc="center left", bbox_to_anchor=(0.95, 0.5), fontsize=8, frameon=False)
            else:
                ax2_comb.text(0.5, 0.5, "Sin emisiones", ha='center', va='center', color="#0F172A")

            ax2_comb.axis('equal')
            ax2_comb.set_title("Distribución (%)", fontsize=8.5, color="#414844", loc="left", pad=3)

            fig_comb.subplots_adjust(top=0.9, bottom=0.1, left=0.05, right=0.95, wspace=0.35)
            
            buf_comb = io.BytesIO()
            fig_comb.savefig(buf_comb, format='png', bbox_inches='tight', transparent=True, dpi=130)
            plt.close(fig_comb)

            img_b64_comb = base64.b64encode(buf_comb.getvalue()).decode('utf-8')

            st.markdown(f"""
            <style>
            div.st-key-chart_click_btn button {{
                background-image: url('data:image/png;base64,{img_b64_comb}') !important;
                background-size: contain !important;
                background-repeat: no-repeat !important;
                background-position: center !important;
                height: 190px !important;
                width: 100% !important;
                border: 1px solid #dde4e6 !important;
                border-radius: 6px !important;
                background-color: transparent !important;
                color: transparent !important;
                cursor: pointer !important;
                box-shadow: none !important;
                padding: 0 !important;
                margin: 0 !important;
                transition: transform 0.2s ease, border-color 0.2s ease !important;
            }}
            div.st-key-chart_click_btn button:hover {{
                border-color: #0F766E !important;
                transform: scale(1.01) !important;
                background-color: rgba(232, 239, 241, 0.3) !important;
            }}
            </style>
            """, unsafe_allow_html=True)

            if st.button("Ampliar Gráfico", key="chart_click_btn", use_container_width=True):
                popup_graficos(r)

            st.divider()
            
            # Benchmark / Límite de Industria
            pct_limit = min(1.0, r['CO2e'] / 1500.0)
            below_limit = max(0, 1500 - r['CO2e'])
            pct_below = (below_limit / 1500) * 100 if below_limit > 0 else 0
            
            st.write("**Límite de Industria Estandarizado (1,500 kg CO2e):**")
            st.progress(pct_limit)
            if below_limit > 0:
                st.success(f"Operación **{pct_below:.0f}% por debajo** del límite de referencia.")
            else:
                st.warning("La operación supera el límite estandarizado de referencia.")

            with st.expander("Metodología & Diagnóstico Técnico IPCC", expanded=True):
                st.markdown(f"**Eficiencia Tier 1:** {r['efi_texto']}")
                st.write(r["diagnostico"])

            # Mostrar la Interpretación Técnica / Justificaciones ingresadas por el usuario
            if r.get("user_interpretacion"):
                st.info(f"**Análisis y Medidas de Mitigación:**\n\n{r['user_interpretacion']}")
            
            # Generación PDF
            buffer = io.BytesIO()
            with PdfPages(buffer) as pdf:
                fig1, ax = plt.subplots(figsize=(8.27, 11.69))
                fig1.patch.set_facecolor("#FFFFFF")
                ax.set_facecolor("#FFFFFF")
                ax.axis("off")
                
                # Encabezado principal
                ax.add_patch(plt.Rectangle((0.04, 0.90), 0.92, 0.08, transform=ax.transAxes, facecolor=COR_AZUL_OSCURO, edgecolor="none"))
                ax.text(0.07, 0.95, "REPORTE DE EMISIONES Y EFICIENCIA LOGÍSTICA", fontsize=14, fontweight="bold", color="white", transform=ax.transAxes)
                ax.text(0.07, 0.92, f"Cliente: {r['empresa']}  |  Proyecto / Encargado: {r['nombre']}  |  Fecha: {r['fecha']}", fontsize=9, color="#DDEAFE", transform=ax.transAxes)
                
                # 1. Datos Operativos y Trajetos
                ax.text(0.05, 0.86, "1. Datos Generales y Trajetos de la Operación", fontsize=11, fontweight="bold", color=COR_AZUL_OSCURO, transform=ax.transAxes)
                ax.add_patch(plt.Rectangle((0.05, 0.74), 0.90, 0.11, transform=ax.transAxes, facecolor="#F8FAFC", edgecolor="#CBD5E1", linewidth=1))
                
                info_left = f"• Origen / Destino: {r['origen']} -> {r['destino']}\n• Producto / NCM: {r['producto']}\n• Vehículo: {r['vehiculo']}"
                info_right = f"• Combustible: {r['comb'].capitalize()}\n• Norma Euro: Euro {r['euro']}\n• Distancia Total: {r['dist_total']:.1f} km"
                
                ax.text(0.07, 0.835, info_left, fontsize=8.5, color="#334155", va="top", transform=ax.transAxes, linespacing=1.3)
                ax.text(0.52, 0.835, info_right, fontsize=8.5, color="#334155", va="top", transform=ax.transAxes, linespacing=1.3)
                
                # Detalle de Trajetos en el PDF
                trajetos_str = "Trajetos: " + " | ".join([f"{t['nombre']} ({t['dist_ida']}km" + (" + retorno)" if t['retorna'] else ")") for t in r.get('trajetos', [])])
                ax.text(0.07, 0.755, textwrap.shorten(trajetos_str, width=105, placeholder="..."), fontsize=8, color="#0F766E", transform=ax.transAxes)

                # 2. Resumen de Emisiones (KPIs)
                ax.text(0.05, 0.705, "2. Resultados e Interpretación Técnica", fontsize=11, fontweight="bold", color=COR_AZUL_OSCURO, transform=ax.transAxes)
                
                kpis = [
                    ("Emisiones CO₂e", f"{r['CO2e']:,.0f} kg", "#0F766E"),
                    ("Emisión Específica", f"{r['emis_g_tkm']:.1f} g/t.km", "#1E3A8A"),
                    ("Consumo Total", f"{r['cons_total_L']:.1f} L", "#0F172A"),
                    ("Score Ambiental", f"{r['score']:.0f} / 100", "#B45309")
                ]
                
                for i, (title, val, color) in enumerate(kpis):
                    x_pos = 0.05 + i * 0.23
                    ax.add_patch(plt.Rectangle((x_pos, 0.62), 0.21, 0.065, transform=ax.transAxes, facecolor="#F1F5F9", edgecolor="#CBD5E1", linewidth=1))
                    ax.text(x_pos + 0.105, 0.66, title, fontsize=7.5, color="#64748B", ha="center", transform=ax.transAxes)
                    ax.text(x_pos + 0.105, 0.633, val, fontsize=10.5, fontweight="bold", color=color, ha="center", transform=ax.transAxes)

                # 3. Desglose de Gases
                ax.text(0.05, 0.585, "Desglose por Gas de Efecto Invernadero:", fontsize=9.5, fontweight="bold", color="#334155", transform=ax.transAxes)
                desglose_txt = f"• CO₂ directo: {r['CO2']:,.1f} kg   |   • CH₄ (en CO₂e): {r['CO2e_CH4']:.1f} kg   |   • N₂O (en CO₂e): {r['CO2e_N2O']:.1f} kg"
                ax.text(0.05, 0.565, desglose_txt, fontsize=8.5, color="#0F766E", fontweight="bold", transform=ax.transAxes)

                # 4. Diagnóstico Técnico IPCC
                ax.text(0.05, 0.53, "Diagnóstico Técnico IPCC Tier 1:", fontsize=9.5, fontweight="bold", color="#334155", transform=ax.transAxes)
                y_diag = 0.51
                for line in textwrap.wrap(r["diagnostico"].strip(), width=95):
                    ax.text(0.05, y_diag, line, fontsize=8.5, color="#475569", transform=ax.transAxes)
                    y_diag -= 0.018

                # 5. Análisis, Justificaciones y Medidas de Mitigación del Usuario
                if r.get("user_interpretacion"):
                    y_user = y_diag - 0.015
                    ax.text(0.05, y_user, "Análisis, Justificaciones y Medidas de Mitigación (Usuario):", fontsize=9.5, fontweight="bold", color="#0F766E", transform=ax.transAxes)
                    y_user -= 0.02
                    
                    user_lines = textwrap.wrap(r["user_interpretacion"], width=90)
                    box_height = len(user_lines) * 0.018 + 0.02
                    ax.add_patch(plt.Rectangle((0.05, y_user - box_height + 0.012), 0.90, box_height, transform=ax.transAxes, facecolor="#ECFDF5", edgecolor="#A7F3D0", linewidth=1))
                    
                    for line in user_lines:
                        ax.text(0.07, y_user, line, fontsize=8.5, color="#065F46", transform=ax.transAxes)
                        y_user -= 0.018
                    
                pdf.savefig(fig1, bbox_inches="tight")
                plt.close(fig1)
                
            pdf_bytes = buffer.getvalue()
            
            st.download_button(
                label="📄 Descargar Reporte PDF",
                data=pdf_bytes,
                file_name=f"reporte_emisiones_{r['empresa']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.info("💡 Complete los datos de la operación y presione **Calcular Emisiones** para generar el reporte de resultados.")