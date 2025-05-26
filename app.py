import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import os

try:
    from calculosh.combinaciones import generar_combinaciones_carga
    from calculosh.deflexiones import *
    from calculosh.espectro import *
    from calculosh.diseno_columna import _generar_posicion_barras, calcular_diagrama_interaccion_columna
    from calculosh.diseno_vigas import *
    from calculosh.diseno_zapatas import diseno_zapata_aislada_v2
    from calculosh.diseno_losa_maciza import diseno_losa_maciza_unidireccional
    from calculosh.irregularidades import evaluar_irregularidades # Tu función existente
    from calculosh.losa_nervada import diseno_nervio_cortante, calcular_cargas_losa_nervada, diseno_nervio_flexion
    from calculosh.diseno_escaleras import diseno_tramo_escalera_losa_inclinada
    from calculosh.reportes import generar_memoria_excel
    from calculosh.diseno_columna_cortante import diseno_columna_cortante_dmo
    from unidades import *# Importar utilidades de unidades si es necesario

    # Importar constantes si las tienes definidas separadamente
    # from config_valores import ConstantesNSR, MaterialesPredeterminados, FactoresPhi # Ejemplo
    # Si no, define algunas constantes básicas aquí o directamente donde se usen
    class ConstantesNSRPlaceholder: # Placeholder si no tienes config_valores.py
        DIAMETRO_ESTRIBO_TIPICO_MM = 9.5
        DIAMETRO_BARRA_LONG_TIPICO_MM = 15.9
        # ... otras constantes necesarias ...

except ImportError as e:
    st.error(f"Error importando módulos de 'calculosh': {e}. Asegúrate de que la carpeta y los archivos .py existan y no tengan errores de sintaxis.")
    st.stop()


# --- Configuración de la Página de Streamlit ---
st.set_page_config(
    page_title="Calculadora Estructural NSR-10",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Estado de Sesión para almacenar datos ---
if 'proyecto_configurado' not in st.session_state:
    st.session_state.proyecto_configurado = False
if 'parametros_globales' not in st.session_state:
    st.session_state.parametros_globales = {}
if 'espectro_calculado_data' not in st.session_state:
    st.session_state.espectro_calculado_data = None # Usar None para indicar que no se ha calculado
if 'resultados_fhe' not in st.session_state:
    st.session_state.resultados_fhe = None
if 'phi_A_calculado' not in st.session_state:
    st.session_state.phi_A_calculado = 1.0
if 'phi_P_calculado' not in st.session_state:
    st.session_state.phi_P_calculado = 1.0
if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now().strftime("%Y-%m-%d")
# Añadir estados para resultados de otros módulos si quieres generar reportes
if 'resultados_vigas_para_excel' not in st.session_state:
    st.session_state.resultados_vigas_para_excel = []
if 'resultados_columnas_para_excel' not in st.session_state:
    st.session_state.resultados_columnas_para_excel = []
if 'lista_vigas_reporte' not in st.session_state:
    st.session_state.lista_vigas_reporte = []
if 'lista_columnas_flex_reporte' not in st.session_state: # Para P-M-M
    st.session_state.lista_columnas_flex_reporte = []
if 'lista_columnas_cort_reporte' not in st.session_state: # Para cortante/confinamiento DMO
    st.session_state.lista_columnas_cort_reporte = []
if 'lista_zapatas_reporte' not in st.session_state:
    st.session_state.lista_zapatas_reporte = []
if 'lista_losas_macizas_reporte' not in st.session_state:
    st.session_state.lista_losas_macizas_reporte = []
if 'lista_nervios_reporte' not in st.session_state:
    st.session_state.lista_nervios_reporte = []
if 'lista_escaleras_reporte' not in st.session_state:
    st.session_state.lista_escaleras_reporte = []
if 'lista_deflexiones_reporte' not in st.session_state: # Si vas a reportar deflexiones
    st.session_state.lista_deflexiones_reporte = []

# Para la hoja de Cargas Detalladas y Criterios (puedes poblarla en la config global o una sección específica)
if 'info_cargas_criterios_reporte' not in st.session_state:
    st.session_state.info_cargas_criterios_reporte = {
        "descripcion_proyecto_detallada": "Edificio residencial multifamiliar de X niveles...",
        "normativa_referencia": "NSR-10 (Capítulos A, B, C)",
        "software_usado": "Aplicación Python Personalizada, FTOOL (para análisis de solicitaciones)",
        "cargas_muertas_tipicas": [
            {"item": "Peso propio estructura", "valor": "Calculado por elemento"},
            {"item": "Acabado de piso (ej. cerámica + mortero)", "valor": "1.2 kN/m²"},
            {"item": "Mampostería divisoria (ej. Ladrillo H10)", "valor": "1.8 kN/m² (o por ml)"},
            {"item": "Cielo raso (ej. drywall)", "valor": "0.3 kN/m²"},
            {"item": "Instalaciones", "valor": "0.25 kN/m²"}
        ],
        "cargas_vivas_tipicas": [
            {"item": "Uso residencial (apartamentos)", "valor": "1.8 kN/m² (NSR-10 B.4.2.1-1)"},
            {"item": "Corredores y escaleras (comunes)", "valor": "3.0 kN/m² (NSR-10 B.4.2.1-1)"},
            {"item": "Cubiertas (transitables/no transitables)", "valor": "Variable según uso/pendiente"}
        ],
        "criterios_dmo_aplicados": "Diseño por capacidad para cortante en vigas y columnas; confinamiento según C.21; cuantías limitadas según DMO."
    }
# Para la hoja de Irregularidades (puedes poblarla desde el módulo de irregularidades)
if 'info_irregularidades_reporte' not in st.session_state:
    st.session_state.info_irregularidades_reporte = {
        "evaluacion_planta": "Se evaluaron las irregularidades 1A, 1B, 2A, 3A, 4A según NSR-10 A.3.3.4. Se considera [Tipo X] como aplicable.",
        "evaluacion_altura": "Se evaluaron las irregularidades 1E, 2E, 3E, 4E, 5E según NSR-10 A.3.3.5. Se considera [Tipo Y] como aplicable.",
        "phi_A_seleccionado": 1.0, # Esto se actualiza desde el slider
        "phi_P_seleccionado": 1.0  # Esto se actualiza desde el slider
    }



# --- BARRA LATERAL: Entradas Globales del Proyecto ---
st.sidebar.title("Configuración del Proyecto")
st.sidebar.markdown(f"**Fecha:** {st.session_state.current_date}")

# Formulario para parámetros globales
with st.sidebar.form(key="global_config_form"):
    st.header("Parámetros Generales")
    pg_nombre_proyecto = st.text_input("Nombre del Proyecto", "Edificio Residencial Ejemplo")
    pg_localizacion = st.text_input("Localización (para referencia)", "Pereira")

    st.subheader("Materiales (NSR-10 C.3)")
    pg_fc_columnas_MPa = st.number_input("f'c Columnas (MPa)", min_value=21.0, value=28.0, step=3.5, format="%.1f")
    pg_fc_losas_vigas_MPa = st.number_input("f'c Losas y Vigas (MPa)", min_value=21.0, value=21.0, step=3.5, format="%.1f")
    pg_fc_zapatas_MPa = st.number_input("f'c Zapatas (MPa)", min_value=21.0, value=21.0, step=3.5, format="%.1f")
    # pg_fy_MPa = st.number_input("f'y Acero de Refuerzo (MPa)", value=420.0, step=10.0, format="%.0f", disabled=True) # Típicamente 420
    pg_fy_MPa = 420.0 # Dejar fijo por ahora según enunciado original
    st.info(f"f'y Acero de Refuerzo (MPa): {pg_fy_MPa}")


    st.subheader("Parámetros Sísmicos Base (NSR-10 A.2)")
    pg_Aa = st.number_input("Coeficiente Aa (Aceleración)", min_value=0.05, max_value=0.50, value=0.25, step=0.01, format="%.2f") # Actualizar a valor de Pereira
    pg_Av = st.number_input("Coeficiente Av (Velocidad)", min_value=0.05, max_value=0.50, value=0.20, step=0.01, format="%.2f") # Actualizar a valor de Pereira
    pg_suelo_tipo = st.selectbox("Tipo de Perfil de Suelo", ["A", "B", "C", "D", "E", "F"], index=3) # D por defecto
    pg_grupo_uso = st.selectbox("Grupo de Uso", ["I", "II", "III", "IV"], index=0, help="I:Normal, II:Importante, III:Esencial, IV:Esencial+")

    # R0 según el sistema estructural (Simplificado)
    sistemas_R0 = {
        "Pórticos de Concreto Reforzado DMO": 5.0,
        "Pórticos de Concreto Reforzado DES": 7.0,
        "Muros Estructurales de Concreto DMO": 4.5,
        "Muros Estructurales de Concreto DES": 5.5,
        # Añadir otros sistemas según NSR-10 Tabla A.3-1
    }
    pg_sistema_estructural_R0_desc = st.selectbox("Sistema Estructural Principal", list(sistemas_R0.keys()))
    pg_R0 = sistemas_R0[pg_sistema_estructural_R0_desc]
    st.info(f"R₀ seleccionado: {pg_R0}")

    st.subheader("Geometría General")
    pg_altura_total_edificio_m = st.number_input("Altura Total Edificio (m, desde la base)", min_value=3.0, value=15.0, step=0.5, help="Para cálculo de Ta")
    pg_num_pisos_aereos = st.number_input("Número de losas aéreas", value=4, min_value=1, step=1)
    pg_altura_tipica_entrepiso_m = st.number_input("Altura típica de entrepiso (m)", value=3.0, step=0.1)
    # pg_num_pisos_sotano_base = st.number_input("Número de sótanos en la base (para Ta)", min_value=0, value=0, step=1) # Simplificado, lo quitamos por ahora
    pg_prof_cimentacion_m = st.number_input("Profundidad cimentación desde contrapiso (m)", value=2.0, step=0.1)
    pg_q_adm_suelo_kPa = st.number_input("Capacidad Portante Admisible $q_{adm}$ (kPa)", value=200.0, step=10.0)


    submitted_global_config = st.form_submit_button("Establecer Parámetros Globales")

if submitted_global_config:
    try:
        pg_Fa, pg_Fv = obtener_Fa_Fv_NSR10(pg_suelo_tipo, pg_Aa, pg_Av)
        st.sidebar.success(f"Fa calculado: {pg_Fa:.2f}, Fv calculado: {pg_Fv:.2f}")
    except Exception as e:
        st.sidebar.error(f"Error al calcular Fa/Fv: {e}. Revise el tipo de suelo F o la implementación de la función.")
        # Usar valores por defecto si falla
        fa_defaults = {"A":0.8, "B":1.0, "C":1.2, "D":1.6, "E":2.5, "F":1.0} # Valor dummy para F
        fv_defaults = {"A":0.8, "B":1.0, "C":1.7, "D":2.4, "E":3.5, "F":1.0}
        pg_Fa = fa_defaults.get(pg_suelo_tipo, 1.2)
        pg_Fv = fv_defaults.get(pg_suelo_tipo, 1.7)
        st.sidebar.warning(f"Usando Fa={pg_Fa}, Fv={pg_Fv} (valores por defecto/ejemplo)")

    coef_importancia_map = {"I": 1.0, "II": 1.25, "III": 1.5, "IV": 1.5}
    pg_I_coef = coef_importancia_map[pg_grupo_uso]

    st.session_state.parametros_globales = {
        "nombre_proyecto": pg_nombre_proyecto, "localizacion": pg_localizacion,
        "fc_columnas_MPa": pg_fc_columnas_MPa, "fc_losas_vigas_MPa": pg_fc_losas_vigas_MPa,
        "fc_zapatas_MPa": pg_fc_zapatas_MPa, "fy_MPa": pg_fy_MPa,
        "Aa": pg_Aa, "Av": pg_Av, "suelo_tipo": pg_suelo_tipo,
        "Fa": pg_Fa, "Fv": pg_Fv,
        "grupo_uso": pg_grupo_uso, "I_coef": pg_I_coef,
        "R0": pg_R0, "sistema_estructural_R0_desc": pg_sistema_estructural_R0_desc,
        "altura_total_edificio_m": pg_altura_total_edificio_m,
        "num_pisos_aereos": pg_num_pisos_aereos, "altura_tipica_entrepiso_m": pg_altura_tipica_entrepiso_m,
        "prof_cimentacion_m": pg_prof_cimentacion_m, "q_adm_suelo_kPa": pg_q_adm_suelo_kPa,
    }
    st.session_state.proyecto_configurado = True
    # Reiniciar resultados calculados si se cambian los parámetros globales
    st.session_state.espectro_calculado_data = None
    st.session_state.resultados_fhe = None
    st.session_state.phi_A_calculado = 1.0 # Resetear irregularidades también
    st.session_state.phi_P_calculado = 1.0
    st.sidebar.success("Parámetros globales establecidos!")


# --- Título Principal y Verificación de Configuración ---
st.title("🏗️ Calculadora Estructural NSR-10")
st.markdown("Herramienta para el diseño y análisis de elementos estructurales según la Norma NSR-10")

if not st.session_state.get('proyecto_configurado', False):
    st.warning("⚠️ Por favor, configure los Parámetros Globales del Proyecto en la barra lateral primero y presione 'Establecer Parámetros Globales'.")
    st.stop()

PG = st.session_state.parametros_globales # Acceso fácil a parámetros globales

# --- Menú Lateral para Selección de Módulos ---
st.sidebar.divider()
st.sidebar.title("Seleccione un Módulo")
modulo = st.sidebar.radio(
    "Módulos disponibles:",
    ["Análisis Sísmico", # Agrupa Espectro, FHE, Irregularidades
     "Diseño de Vigas",
     "Diseño de Columnas",
     "Diseño de Zapatas",
     "Diseño de Losas Macizas", # Agrupa análisis y diseño
     "Diseño de Losa Nervada", # Agrupa análisis y diseño
     "Diseño de Escaleras",
     "Cálculo de Deflexiones",
     "Combinaciones de Carga",
     "Generar Memoria Excel (WIP)"], # Opción para reporte
    key="main_module_selection"
)

# ===============================================================================
# MÓDULO: ANÁLISIS SÍSMICO
# ===============================================================================
if modulo == "Análisis Sísmico":
    st.header("Análisis Sísmico NSR-10")
    tab_espectro, tab_fhe, tab_irregularidades = st.tabs([
        "📊 Espectro de Diseño", "🏢 Fuerza Horizontal Equivalente", "📐 Evaluación de Irregularidades"])

    # --- Pestaña Espectro de Diseño ---
    with tab_espectro:
        st.subheader("📊 Espectro de Diseño Sísmico")
        st.markdown("#### Parámetros Sísmicos Base (de Configuración Global)")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.metric("Aa", f"{PG['Aa']:.2f}")
            st.metric("Av", f"{PG['Av']:.2f}")
            st.metric("Tipo Suelo", PG['suelo_tipo'])
        with col_p2:
            st.metric("Fa", f"{PG['Fa']:.2f}")
            st.metric("Fv", f"{PG['Fv']:.2f}")
            st.metric("Grupo Uso", f"{PG['grupo_uso']} (I={PG['I_coef']:.2f})")
        st.info(f"Sistema Estructural: {PG['sistema_estructural_R0_desc']} (R₀={PG['R0']:.1f})")

        st.markdown("#### Ajuste de R por Irregularidades (NSR-10 A.3.3.3)")
        # Leer de session_state si fue definido en la pestaña de irregularidades
        phi_A = st.slider("Factor por Irregularidad en Altura (ΦA)", 0.7, 1.0, st.session_state.phi_A_calculado, 0.05, key="phi_A_espectro", help="NSR-10 Tabla A.3-3. Definir en pestaña 'Evaluación de Irregularidades'.")
        phi_P = st.slider("Factor por Irregularidad en Planta (ΦP)", 0.7, 1.0, st.session_state.phi_P_calculado, 0.05, key="phi_P_espectro", help="NSR-10 Tabla A.3-4. Definir en pestaña 'Evaluación de Irregularidades'.")
        phi_E = 1.0 # Redundancia, asumido 1.0
        R_final = PG['R0'] * phi_A * phi_P * phi_E
        st.metric("Coeficiente R final (R = R₀ × ΦA × ΦP × ΦE)", f"{R_final:.2f}")

        # Determinar TL_norma
        try:
            TL_calc = determinar_TL_norma(PG['Av'], PG['Fa'], PG['Fv'])
            st.info(f"Periodo Largo $T_L$ (calculado según NSR-10 Tabla A.2.6-1): {TL_calc:.1f} s")
        except Exception as e:
            st.error(f"Error al calcular TL: {e}"); TL_calc = 4.0; st.warning(f"Usando TL por defecto: {TL_calc:.1f} s")

        tipo_espectro_sel = st.radio("Tipo de Espectro:", ["Diseño (I/R aplicado)", "Elástico (I=1, R=1)"], index=0, horizontal=True)

        if st.button("📊 Generar Espectro"):
            try:
                tipo_param = "diseño" if tipo_espectro_sel == "Diseño (I/R aplicado)" else "elastico"
                T, Sa, info_periodos = espectro_nsr10(PG['Aa'], PG['Av'], PG['I_coef'], R_final, PG['Fa'], PG['Fv'], TL_calc, tipo_espectro=tipo_param)
                st.session_state['espectro_calculado_data'] = {"T": T, "Sa": Sa, "info_periodos": info_periodos, "R_usado": R_final if tipo_param == "diseño" else 1.0, "I_usado": PG['I_coef'] if tipo_param == "diseño" else 1.0, "tipo": tipo_param}
                st.success("Espectro calculado exitosamente.")
            except Exception as e:
                st.error(f"Error al calcular el espectro: {e}")
                if 'espectro_calculado_data' in st.session_state: st.session_state.espectro_calculado_data = None

        if st.session_state.espectro_calculado_data:
            data_esp = st.session_state.espectro_calculado_data
            st.markdown("#### Resultados del Espectro")
            info_p_text = (f"$T_0 = {data_esp['info_periodos']['T0']:.3f}$ s,  "
                           f"$T_C = {data_esp['info_periodos']['TC']:.3f}$ s,  "
                           f"$T_L = {data_esp['info_periodos']['TL_norma']:.3f}$ s")
            st.markdown(info_p_text)
            fig_espectro = graficar_espectro(T=data_esp['T'], Sa=data_esp['Sa'], info_periodos=data_esp['info_periodos'], titulo=f"Espectro NSR-10 ({data_esp['tipo'].capitalize()})", R_val=data_esp['R_usado'], I_val=data_esp['I_usado'])
            st.pyplot(fig_espectro)
            df_data_espectro = pd.DataFrame({'Periodo (s)': data_esp['T'], f'Sa_{data_esp["tipo"]} (g)': data_esp['Sa']})
            csv = df_data_espectro.to_csv(index=False, sep=";", decimal=",")
            st.download_button(label=f"Descargar datos del espectro ({data_esp['tipo']}) (CSV)", data=csv, file_name=f"espectro_nsr10_{data_esp['tipo']}.csv", mime="text/csv")


    # --- Pestaña Fuerza Horizontal Equivalente ---
    with tab_fhe:
        st.subheader("🏢 Fuerza Horizontal Equivalente (NSR-10 A.4)")
        if not st.session_state.espectro_calculado_data or st.session_state.espectro_calculado_data['tipo'] != "diseño":
            st.warning("Primero genere el Espectro de **Diseño** en la pestaña anterior.")
        else:
            data_esp_diseno = st.session_state.espectro_calculado_data
            try:
                Ta_calc = calcular_Ta_aproximado(PG['altura_total_edificio_m'], PG['sistema_estructural_R0_desc']) # Asumiendo 0 sótanos si no se pide
                st.metric(f"Periodo Fundamental Aproximado $T_a$ (NSR-10 A.4.2.2.1)", f"{Ta_calc:.3f} s")
                st.session_state['Ta_calculado'] = Ta_calc
                Sa_para_Ta = np.interp(Ta_calc, data_esp_diseno['T'], data_esp_diseno['Sa'])
                st.info(f"Para $T_a = {Ta_calc:.3f}$ s  ➔  $S_a(T_a) = {Sa_para_Ta:.4f}$ g")
            except Exception as e:
                st.error(f"Error calculando Ta: {e}")
                if 'Ta_calculado' in st.session_state: del st.session_state['Ta_calculado']

            if 'Ta_calculado' in st.session_state:
                st.markdown("---")
                peso_total_sismico_kN = st.number_input("Peso Total Sísmico Edificación W (kN)", min_value=1.0, value=5000.0, step=100.0, help="CM + %CV relevante (NSR-10 A.4.1). Obtener de análisis de cargas.")
                num_pisos_para_fhe = st.number_input("Número de pisos sobre la base (para Fx)", min_value=1, value=PG.get('num_pisos_aereos', 4), step=1)

                if st.button("🏢 Calcular Fuerza Horizontal Equivalente"):
                    try:
                        Vs_kN, df_Fx = calcular_Vs_fuerza_horizontal_equivalente(peso_total_sismico_kN, Sa_para_Ta, st.session_state['Ta_calculado'], num_pisos_para_fhe, PG['altura_tipica_entrepiso_m'])
                        st.session_state['resultados_fhe'] = {"Vs_kN": Vs_kN, "df_Fx": df_Fx, "k_dist": 1.0 + (st.session_state['Ta_calculado'] - 0.5) / 2.0 if 0.5 < st.session_state['Ta_calculado'] < 2.5 else (1.0 if st.session_state['Ta_calculado'] <= 0.5 else 2.0)}
                        st.success("Cálculo de FHE completado.")
                    except Exception as e:
                        st.error(f"Error al calcular FHE: {e}")
                        if 'resultados_fhe' in st.session_state: del st.session_state['resultados_fhe']

            if st.session_state.get('resultados_fhe'):
                res_fhe = st.session_state['resultados_fhe']
                st.metric("Cortante Sísmico Basal $V_s$", f"{res_fhe['Vs_kN']:.2f} kN")
                st.markdown("#### Distribución de Fuerzas Sísmicas $F_x$ por Nivel")
                st.dataframe(res_fhe['df_Fx'].style.format({'Altura_hi (m)': '{:.2f}', 'wi_hi^k (kN*m^k)': '{:.2f}', 'Cvx': '{:.4f}', 'Fx (kN)': '{:.2f}', 'Suma_Fx_acum (kN)': '{:.2f}'}))
                st.caption(f"Exponente k para distribución: {res_fhe['k_dist']:.3f}")
                st.caption("Fuerzas listadas desde cubierta hacia base.")

    # --- Pestaña Evaluación de Irregularidades ---
    with tab_irregularidades:
        st.subheader("📐 Evaluación de Irregularidades Estructurales (NSR-10 A.3.3)")
        st.info("Defina aquí los factores de ajuste para R (ΦA, ΦP) basados en su evaluación de las irregularidades del proyecto según NSR-10.")

        st.markdown("##### Irregularidades en Altura (NSR-10 Tabla A.3-3)")
        phi_A_eval = st.slider("Seleccione el Factor ΦA", 0.7, 1.0, st.session_state.phi_A_calculado, 0.05, key="phi_A_irr_input", help="1.0 si no hay irregularidades en altura.")

        st.markdown("##### Irregularidades en Planta (NSR-10 Tabla A.3-4)")
        phi_P_eval = st.slider("Seleccione el Factor ΦP", 0.7, 1.0, st.session_state.phi_P_calculado, 0.05, key="phi_P_irr_input", help="1.0 si no hay irregularidades en planta.")

        if st.button("💾 Guardar Factores de Irregularidad"):
            st.session_state.phi_A_calculado = phi_A_eval
            st.session_state.phi_P_calculado = phi_P_eval
            st.success("Factores ΦA y ΦP guardados. Se usarán en el cálculo del espectro de diseño.")

        st.markdown("---")
        st.write("Para una evaluación detallada, consulte las secciones A.3.3.4 y A.3.3.5 de la NSR-10.")
        # Placeholder para usar tu función 'evaluar_irregularidades' si se proporcionan los datos necesarios.

# ===============================================================================
# MÓDULO: DISEÑO DE VIGAS
# ===============================================================================
elif modulo == "Diseño de Vigas":
    st.header("Diseño de Vigas a Flexión y Cortante")
    
    fc_vigas = PG['fc_losas_vigas_MPa'] # Usar fc para losas/vigas desde globales
    fy_vigas_long = PG['fy_MPa']       # Para acero longitudinal
    fy_vigas_estrib = PG['fy_MPa']     # Para estribos (usualmente el mismo)

    st.info(f"Usando Materiales Globales: f'c = {fc_vigas} MPa, f'y Longitudinal = {fy_vigas_long} MPa, f'y Estribos = {fy_vigas_estrib} MPa")

    tipo_diseno_viga = st.radio(
        "Seleccione el Tipo de Diseño para la Viga:",
        ["Estándar (NSR-10 C.9, C.11)", "Sismorresistente (DMO - NSR-10 C.21.3)"],
        horizontal=True, key="tipo_dis_viga"
    )
    st.markdown("---")

    if tipo_diseno_viga == "Estándar (NSR-10 C.9, C.11)":
        st.subheader("Diseño Estándar de Viga")
        # Aquí mantendrías tu lógica anterior para diseño estándar o un placeholder
        # Utilizando las funciones diseno_viga_flexion_simple y diseno_viga_cortante_estandar

        col_std_flex, col_std_cort = st.tabs(["Flexión Estándar", "Cortante Estándar"])

        with col_std_flex:
            st.markdown("##### Entradas para Flexión Estándar")
            # ... (inputs para b_cm, h_cm, rec_libre_cm, diams, Mu_kNm) ...
            # Ejemplo de inputs:
            b_cm_sf = st.number_input("Ancho viga b (cm)", 25.0, key="b_sf")
            h_cm_sf = st.number_input("Altura viga h (cm)", 50.0, key="h_sf")
            rec_libre_cm_sf = st.number_input("Rec. Libre (cm)", 4.0, key="rec_sf")
            diam_est_sf = st.selectbox("Ø Estribo (mm)", [9.5, 12.7], key="est_sf", index=0)
            diam_bar_sf = st.selectbox("Ø Barra Long. (mm)", [12.7, 15.9, 19.1, 22.2, 25.4], key="bar_sf", index=1)
            Mu_sf_kNm = st.number_input("Momento Último Mu (kNm)", 100.0, key="mu_sf")

            if st.button("Calcular Flexión Estándar", key="btn_sf"):
                res_sf = diseno_viga_flexion_simple(b_cm_sf, h_cm_sf, rec_libre_cm_sf, diam_est_sf, diam_bar_sf, fc_vigas, fy_vigas_long, Mu_sf_kNm)
                if res_sf['status'] != "Error":
                    st.success(f"As requerida: {res_sf['As_req_cm2']:.2f} cm² (ρ={res_sf['rho_calculado']:.4f})")
                else:
                    st.error(res_sf['mensaje'])
        
        with col_std_cort:
            st.markdown("##### Entradas para Cortante Estándar")
            # ... (inputs para b_cm, h_cm, rec_libre_cm, diams, Vu_kN) ...
            # Ejemplo de inputs (puedes sincronizarlos con los de flexión o hacerlos independientes)
            b_cm_sc = st.number_input("Ancho viga b (cm)", 25.0, key="b_sc")
            h_cm_sc = st.number_input("Altura viga h (cm)", 50.0, key="h_sc")
            rec_libre_cm_sc = st.number_input("Rec. Libre (cm)", 4.0, key="rec_sc")
            diam_est_sc = st.selectbox("Ø Estribo a usar (mm)", [9.5, 12.7], key="est_sc", index=0)
            diam_bar_sc = st.selectbox("Ø Barra Long. (para d) (mm)", [12.7, 15.9, 19.1, 22.2, 25.4], key="bar_sc", index=1)
            Vu_sc_kN = st.number_input("Cortante Último Vu (kN)", 80.0, key="vu_sc")

            if st.button("Calcular Cortante Estándar", key="btn_sc"):
                res_sc = diseno_viga_cortante_estandar(b_cm_sc, h_cm_sc, rec_libre_cm_sc, diam_est_sc, diam_bar_sc, fc_vigas, fy_vigas_estrib, Vu_sc_kN)
                if res_sc['status'] != "Error":
                    st.success(f"Av/s requerido: {res_sc['Av_s_req_mm2_por_m']:.2f} mm²/m")
                    if res_sc['s_rec_mm'] is not None:
                        st.info(f"Espaciamiento recomendado para estribos Ø{res_sc['diam_estribo_usado_mm']}mm: {res_sc['s_rec_mm']:.0f} mm")
                    else:
                        st.info("No se requiere refuerzo por cálculo, verificar mínimos normativos.")
                else:
                    st.error(res_sc['mensaje'])


    elif tipo_diseno_viga == "Sismorresistente (DMO - NSR-10 C.21.3)":
        st.subheader("Diseño de Viga para Pórtico DMO (NSR-10 C.21.3)")
        
        with st.form(key="form_viga_dmo_inputs"):
            id_viga_reporte = st.text_input("ID Viga para Reporte (ej: V-101 EjeA N2)", key="id_viga_dmo")
            st.markdown("##### Geometría de la Viga")
            col_vg1, col_vg2, col_vg3 = st.columns(3)
            with col_vg1:
                b_v_dmo_cm = st.number_input("Ancho (b, cm)", min_value=20.0, value=30.0, step=1.0, key="b_v_dmo")
            with col_vg2:
                h_v_dmo_cm = st.number_input("Altura Total (h, cm)", min_value=25.0, value=50.0, step=1.0, key="h_v_dmo")
            with col_vg3:
                ln_v_dmo_m = st.number_input("Luz Libre ($L_n$, m)", min_value=2.0, value=5.5, step=0.1, key="ln_v_dmo")

            st.markdown("##### Recubrimientos y Diámetros de Barras")
            col_vr1, col_vr2, col_vr3 = st.columns(3)
            with col_vr1:
                rec_libre_v_dmo_cm = st.number_input("Rec. Libre a Estribo (cm)", min_value=2.5, value=4.0, step=0.5, key="rec_v_dmo")
            with col_vr2:
                diam_est_v_dmo_mm = st.selectbox("Ø Estribo (mm)", [9.5, 12.7], index=0, key="est_v_dmo")
            with col_vr3:
                diam_bar_long_v_dmo_mm = st.selectbox("Ø Barra Long. Principal (mm)", [12.7, 15.9, 19.1, 22.2, 25.4], index=1, key="barlong_v_dmo")
            
            st.markdown("##### Momentos Flectores de Diseño ($M_u$)")
            col_vm1, col_vm2, col_vm3 = st.columns(3)
            with col_vm1:
                Mu_neg_ext_v_dmo_kNm = st.number_input("$M_u$ Negativo Apoyo Ext. (kNm)", value=120.0, step=5.0, key="munegext_v_dmo")
            with col_vm2:
                Mu_pos_v_dmo_kNm = st.number_input("$M_u$ Positivo Centro Luz (kNm)", value=90.0, step=5.0, key="mupos_v_dmo")
            with col_vm3:
                Mu_neg_int_v_dmo_kNm = st.number_input("$M_u$ Negativo Apoyo Int. (kNm)", value=150.0, step=5.0, key="munegint_v_dmo")

            st.markdown("##### Cortantes Isostáticos por Cargas Gravitacionales ($V_{u,grav}$ en apoyos)")
            col_vv1, col_vv2 = st.columns(2)
            with col_vv1:
                Vu_grav_ext_v_dmo_kN = st.number_input("$V_{u,grav}$ Apoyo Ext. (kN)", value=70.0, step=5.0, key="vugravext_v_dmo", help="Cortante por cargas D y L en el apoyo externo.")
            with col_vv2:
                Vu_grav_int_v_dmo_kN = st.number_input("$V_{u,grav}$ Apoyo Int. (kN)", value=85.0, step=5.0, key="vugravint_v_dmo", help="Cortante por cargas D y L en el apoyo interno.")
            
            submitted_viga_dmo_calc = st.form_submit_button("🏗️ Diseñar Viga DMO")
        
        if submitted_viga_dmo_calc:
            if not id_viga_reporte.strip(): # Validar que el ID no esté vacío
                st.error("Por favor, ingrese un ID para la viga.")
            else:
                try:
                    # Calcular d una vez para mostrarlo y usarlo
                    d_v_dmo_cm = mm_to_cm(calcular_peralte_efectivo_viga(h_v_dmo_cm, rec_libre_v_dmo_cm, diam_est_v_dmo_mm, diam_bar_long_v_dmo_mm))
                    st.info(f"Peralte efectivo (d) calculado para la viga: {d_v_dmo_cm:.2f} cm")

                    resultados_v_dmo = diseno_viga_dmo(
                        b_cm=b_v_dmo_cm, h_cm=h_v_dmo_cm, 
                        rec_libre_cm=rec_libre_v_dmo_cm, # Pasar recubrimiento libre
                        diam_estribo_mm=diam_est_v_dmo_mm, 
                        diam_barra_long_principal_mm=diam_bar_long_v_dmo_mm,
                        fc_MPa=fc_vigas, fy_MPa_long=fy_vigas_long, fy_MPa_estribos=fy_vigas_estrib,
                        Mu_neg_ext_kNm=Mu_neg_ext_v_dmo_kNm, Mu_pos_kNm=Mu_pos_v_dmo_kNm, Mu_neg_int_kNm=Mu_neg_int_v_dmo_kNm,
                        ln_m=ln_v_dmo_m,
                        Vu_grav_ext_kN=Vu_grav_ext_v_dmo_kN, Vu_grav_int_kN=Vu_grav_int_v_dmo_kN
                    )

                    if resultados_v_dmo["status"] == "OK":
                    
                        st.success(resultados_v_dmo.get("mensaje_global", "Cálculo DMO de viga completado."))
                        st.info(resultados_v_dmo.get("mensaje_cuantia", ""))

                        st.markdown("##### Acero de Refuerzo Longitudinal ($A_s$ requerido)")
                        res_flex_ext = resultados_v_dmo.get("flexion_neg_ext", {})
                        res_flex_pos = resultados_v_dmo.get("flexion_pos", {})
                        res_flex_int = resultados_v_dmo.get("flexion_neg_int", {})
                        
                        col_as_v1, col_as_v2, col_as_v3 = st.columns(3)
                        col_as_v1.metric("As Apoyo Ext. (-)", f"{res_flex_ext.get('As_req_cm2', 'N/A'):.2f} cm²", help=f"ρ={res_flex_ext.get('rho', 'N/A'):.4f}")
                        col_as_v2.metric("As Centro Luz (+)", f"{res_flex_pos.get('As_req_cm2', 'N/A'):.2f} cm²", help=f"ρ={res_flex_pos.get('rho', 'N/A'):.4f}")
                        col_as_v3.metric("As Apoyo Int. (-)", f"{res_flex_int.get('As_req_cm2', 'N/A'):.2f} cm²", help=f"ρ={res_flex_int.get('rho', 'N/A'):.4f}")

                        st.markdown("---")
                        st.markdown("##### Acero de Refuerzo Transversal (Estribos Ø" + str(resultados_v_dmo.get('estribos_diam_mm','N/A')) + "mm)")
                        st.metric(f"Cortante de Diseño ($V_e$) Máximo en Apoyos", 
                                f"{max(resultados_v_dmo.get('cortante_diseno_Ve_ext_kN',0), resultados_v_dmo.get('cortante_diseno_Ve_int_kN',0)):.2f} kN")

                        col_s_v1, col_s_v2 = st.columns(2)
                        with col_s_v1:
                            st.markdown(f"**Zona Confinada (en apoyos, $l_o = {resultados_v_dmo.get('longitud_confinamiento_lo_cm', 'N/A')}$ cm):**")
                            st.success(f"Usar estribos @ **{resultados_v_dmo.get('espaciamiento_zona_confinada_cm', 'N/A')} cm**")
                        with col_s_v2:
                            st.markdown("**Zona Central (resto de la viga):**")
                            st.success(f"Usar estribos @ **{resultados_v_dmo.get('espaciamiento_zona_central_cm', 'N/A')} cm**")
                        
                        st.caption(f"Peralte efectivo (d) usado para el diseño: {resultados_v_dmo.get('d_usado_cm', 'N/A')} cm")

                        with st.expander("Ver detalles completos del cálculo DMO"):
                            st.json(resultados_v_dmo)
                        
                        # Guardar para memoria de cálculo
                        if 'resultados_vigas_para_excel' not in st.session_state:
                            st.session_state.resultados_vigas_para_excel = []
                        
                        # Datos a guardar para la memoria (ajusta según necesites)
                        datos_viga_para_reporte = {
                                "ID Elemento": id_viga_reporte,
                                "b (cm)": b_v_dmo_cm,
                                "h (cm)": h_v_dmo_cm,
                                "d (cm)": resultados_v_dmo.get('d_usado_cm', 'N/A'),
                                "Ln (m)": ln_v_dmo_m,
                                "f'c (MPa)": fc_vigas,
                                "fy (MPa)": fy_vigas_long, # Asumiendo el mismo para estribos por simplicidad en tabla
                                "Mu(-) Ext (kNm)": Mu_neg_ext_v_dmo_kNm,
                                "As(-) Ext (cm²)": resultados_v_dmo.get("flexion_neg_ext", {}).get('As_req_cm2', 'N/A'),
                                "ρ(-) Ext": resultados_v_dmo.get("flexion_neg_ext", {}).get('rho', 'N/A'),
                                "Mu(+) Cen (kNm)": Mu_pos_v_dmo_kNm,
                                "As(+) Cen (cm²)": resultados_v_dmo.get("flexion_pos", {}).get('As_req_cm2', 'N/A'),
                                "ρ(+) Cen": resultados_v_dmo.get("flexion_pos", {}).get('rho', 'N/A'),
                                "Mu(-) Int (kNm)": Mu_neg_int_v_dmo_kNm,
                                "As(-) Int (cm²)": resultados_v_dmo.get("flexion_neg_int", {}).get('As_req_cm2', 'N/A'),
                                "ρ(-) Int": resultados_v_dmo.get("flexion_neg_int", {}).get('rho', 'N/A'),
                                "Ve,max (kN)": max(resultados_v_dmo.get('cortante_diseno_Ve_ext_kN',0), resultados_v_dmo.get('cortante_diseno_Ve_int_kN',0)),
                                "Ø Estribo (mm)": resultados_v_dmo.get('estribos_diam_mm'),
                                "s confinado (cm)": resultados_v_dmo.get('espaciamiento_zona_confinada_cm'),
                                "s central (cm)": resultados_v_dmo.get('espaciamiento_zona_central_cm'),
                                "Lo (cm)": resultados_v_dmo.get('longitud_confinamiento_lo_cm'),
                                "Estado Diseño": "OK" # O el mensaje de cuantía
                            }
                        st.session_state.lista_vigas_reporte.append(datos_viga_para_reporte)
                        st.info(f"Resultados de viga '{id_viga_reporte}' añadidos al reporte.")
                    else:
                        # Podrías guardar un registro del intento fallido si quieres
                        datos_viga_fallida_reporte = {
                            "ID Elemento": id_viga_reporte, "b (cm)": b_v_dmo_cm, "h (cm)": h_v_dmo_cm, 
                            "Estado Diseño": "Error", "Mensaje": resultados_v_dmo.get("mensaje_global", "Error desconocido")
                        }

                except Exception as e:
                    st.error(f"Ocurrió un error en el diseño DMO de la viga: {e}")
                    import traceback
                    st.text(traceback.format_exc()) # Para depuración

# ===============================================================================
# MÓDULO: DISEÑO DE COLUMNAS
# ===============================================================================
elif modulo == "Diseño de Columnas":
    st.header("Diseño de Columnas - Diagrama de Interacción P-M-M")
    # Usar f'c y f'y de parámetros globales para columnas
    fc_col = PG['fc_columnas_MPa']
    fy_col = PG['fy_MPa']
    st.info(f"Usando Materiales Globales: f'c = {fc_col} MPa, f'y = {fy_col} MPa")

    col1, col2 = st.columns([1, 2]) # Dar más espacio a la columna de resultados/gráficos

    with col1: # Asumiendo que 'col1' es donde se ingresan los datos para el diagrama P-M-M
        st.subheader("Geometría y Refuerzo para Diagrama P-M-M")
        id_columna_reporte = st.text_input("ID Columna para Reporte (ej: C-1, C-EjeA-N1)", key="id_col_rep")
        b_cm_c = st.number_input("Ancho Columna b (cm)", min_value=20.0, value=40.0, step=5.0, key="b_col")
        h_cm_c = st.number_input("Peralte Columna h (cm)", min_value=20.0, value=50.0, step=5.0, key="h_col") # Ejemplo h>b

        st.markdown("---")
        st.markdown("##### Recubrimiento y Diámetros")
        rec_libre_cm_c = st.number_input("Recubrimiento libre (cm)", min_value=2.5, value=4.0, step=0.5, key="rec_libre_col", help="Distancia borde a estribo")

        # Selectores para diámetros
        diam_estribo_opts_mm_c = {"#3 (9.5mm)": 9.5, "#4 (12.7mm)": 12.7}
        sel_estribo_c = st.selectbox("Diámetro Estribo", list(diam_estribo_opts_mm_c.keys()), key="diam_e_col")
        diam_estribo_mm_c = diam_estribo_opts_mm_c[sel_estribo_c]

        diam_barra_opts_mm_c = {"#5 (15.9mm)": 15.9, "#6 (19.1mm)": 19.1, "#7 (22.2mm)": 22.2, "#8 (25.4mm)": 25.4, "#9 (28.7mm)": 28.7, "#10 (32.3mm)": 32.3}
        sel_barra_c = st.selectbox("Diámetro Barra Long.", list(diam_barra_opts_mm_c.keys()), index=1, key="diam_b_col") # #6 por defecto
        diam_barra_long_mm_c = diam_barra_opts_mm_c[sel_barra_c]

        st.markdown("---")
        st.markdown("##### Distribución del Refuerzo")
        nx_barras_c = st.number_input("Nº barras cara 'b' (Total en cara paralela a Y, incl. esquinas)", min_value=2, value=3, step=1, key="nx_b_col")
        ny_barras_c = st.number_input("Nº barras cara 'h' (Sólo intermedias en cara paralela a X)", min_value=0, value=1, step=1, key="ny_b_col", help="No incluir las barras de esquina (ya contadas en nx)")
        num_barras_tot_c = 2 * nx_barras_c + 2 * ny_barras_c
        st.info(f"Número total de barras: {num_barras_tot_c}")

        st.markdown("---")
        st.markdown("##### Parámetros de Cálculo (Diagrama)")
        n_c_steps = st.slider("Pasos eje neutro 'c'", 20, 60, 30, 5, key="nc_col_diag")
        n_theta_steps = st.slider("Pasos ángulo 'θ'", 24, 72, 36, 6, key="nt_col_diag")

    # Botón para generar diagrama
    if st.button("📊 Generar Diagrama de Interacción", key="btn_col_diag"):
        if not id_columna_reporte.strip():
                st.error("Por favor, ingrese un ID para la columna.")
        elif num_barras_tot_c < 4: # Asegúrate que num_barras_tot_c se calcule
                st.error("Se requieren al menos 4 barras en total.")
        else:
            try:
                with st.spinner("Calculando diagrama de interacción... Por favor espere."):
                    # Llamar a la función corregida
                    resultados_diag = calcular_diagrama_interaccion_columna(
                        b_cm=b_cm_c, h_cm=h_cm_c, rec_libre_cm=rec_libre_cm_c,
                        diam_estribo_mm=diam_estribo_mm_c, diam_barra_long_mm=diam_barra_long_mm_c,
                        nx_barras=nx_barras_c, ny_barras=ny_barras_c,
                        fc_MPa=fc_col, fy_MPa=fy_col,
                        num_puntos_c=n_c_steps, num_puntos_theta=n_theta_steps
                    )
                
                st.session_state["resultados_columna_diag"] = resultados_diag # Guardar resultados completos
                if resultados_diag.get("status") == "OK":
                    st.success(f"Diagrama para columna '{id_columna_reporte}' generado. {resultados_diag.get('mensaje', '')}")
                    # --- Guardar datos de flexo-compresión para el reporte ---
                    params_col_usados_diag = resultados_diag.get("params", {})
                    P_kN_max_phi = n_to_kn(np.max(resultados_diag["P_N"])) if "P_N" in resultados_diag else 0
                        
                    # Necesitas el área de acero total y la cuantía del refuerzo usado.
                    # La función _generar_posicion_barras es interna. As_total_mm2 y rho_g están en params_col_usados_diag
                    As_total_mm2_col = params_col_usados_diag.get('As_total_mm2', 0) # Si se guardó así
                    rho_g_col = params_col_usados_diag.get('rho_g', 0)

                    datos_col_flex_reporte = {
                        "ID Columna": id_columna_reporte,
                        "b (cm)": params_col_usados_diag.get('b_cm'),
                        "h (cm)": params_col_usados_diag.get('h_cm'),
                        "Rec. Libre (cm)": params_col_usados_diag.get('rec_libre_cm'),
                        "f'c (MPa)": params_col_usados_diag.get('fc_MPa'),
                        "fy (MPa)": params_col_usados_diag.get('fy_MPa'),
                        "Ø Barra Long. (mm)": params_col_usados_diag.get('diam_barra_long_mm'),
                        "Ø Estribo (mm)": params_col_usados_diag.get('diam_estribo_mm'),
                        "Nx Barras (cara b)": params_col_usados_diag.get('nx_barras'),
                        "Ny Barras (cara h, interm.)": params_col_usados_diag.get('ny_barras'),
                        "Nº Total Barras": params_col_usados_diag.get('num_barras_total'),
                        "As Total (cm²)": mm2_to_cm2(As_total_mm2_col) if As_total_mm2_col else "N/A",
                        "Cuantía (ρg)": f"{rho_g_col:.4f}" if rho_g_col else "N/A",
                        "φPn_max (kN)": round(P_kN_max_phi, 1),
                        # Podrías añadir φMnx_max y φMny_max si los calculas específicamente
                        "Estado Diagrama": "Generado OK"
                    }
                    st.session_state.lista_columnas_flex_reporte.append(datos_col_flex_reporte)
                    st.info(f"Datos de flexo-compresión de columna '{id_columna_reporte}' añadidos al reporte.")
                else:
                    st.error(f"Error al generar diagrama para '{id_columna_reporte}': {resultados_diag.get('mensaje', 'Error desconocido')}")

            except Exception as e:
                st.error(f"Error inesperado durante el cálculo: {e}")
                if 'resultados_columna_diag' in st.session_state: del st.session_state['resultados_columna_diag']

    # --- Mostrar Resultados y Gráficos si existen ---
    if st.session_state.get("resultados_columna_diag") and st.session_state["resultados_columna_diag"].get("status") == "OK":
        resultados_diag = st.session_state["resultados_columna_diag"]
        params_col_usados = resultados_diag.get("params", {})

        with col2:
            st.subheader("Resultados y Diseño Detallado") # Título general para la columna

            # Verificar si el diagrama P-M-M ha sido calculado y está disponible
            if st.session_state.get("resultados_columna_diag") and st.session_state["resultados_columna_diag"].get("status") == "OK":
                resultados_diag = st.session_state["resultados_columna_diag"]
                # 'params_col_usados' se obtiene de los resultados del diagrama P-M-M, generado en col1
                params_col_usados = resultados_diag.get("params", {})

                # Si params_col_usados está vacío, es porque el diagrama P-M-M no se generó correctamente o
                # la estructura de 'resultados_diag' no es la esperada.
                if not params_col_usados:
                    st.warning("No se encontraron los parámetros de la columna. Por favor, genere primero el Diagrama de Interacción en la columna izquierda.")
                else:
                    tab_diag, tab_cortante, tab_secc = st.tabs(["📈 Diagrama P-M-M", "✂️ Cortante y Confinamiento (DMO)", "🖼️ Sección Transversal"])

                    with tab_diag:
                        st.markdown("##### Vista del Diagrama de Interacción $(\phi P_n, \phi M_{nx}, \phi M_{ny})$")
                        
                        P_kN_diag = n_to_kn(resultados_diag["P_N"])
                        Mx_kNm_diag = nmm_to_knm(resultados_diag["Mx_Nmm"])
                        My_kNm_diag = nmm_to_knm(resultados_diag["My_Nmm"])
                        
                        vista_diag = st.radio("Tipo de Vista del Diagrama", ["3D", "2D (Mx-P, My-P)", "2D (Mx-My)"], horizontal=True, key="vista_diag_col_main")

                        fig_col_diag = plt.figure(figsize=(9, 7))

                        if vista_diag == "3D":
                            ax_3d = fig_col_diag.add_subplot(111, projection='3d')
                            sc = ax_3d.scatter(Mx_kNm_diag, My_kNm_diag, P_kN_diag, s=5, c=P_kN_diag, cmap='viridis', alpha=0.7)
                            fig_col_diag.colorbar(sc, ax=ax_3d, label='φ·P (kN)', shrink=0.6)
                            ax_3d.set_xlabel('φ·Mx (kN·m)')
                            ax_3d.set_ylabel('φ·My (kN·m)')
                            ax_3d.set_zlabel('φ·P (kN)')
                            ax_3d.set_title('Diagrama de Interacción P-M-M')
                        
                        elif vista_diag == "2D (Mx-P, My-P)":
                            gs = fig_col_diag.add_gridspec(1, 2)
                            ax1 = fig_col_diag.add_subplot(gs[0, 0])
                            ax2 = fig_col_diag.add_subplot(gs[0, 1])
                            
                            sc1 = ax1.scatter(Mx_kNm_diag, P_kN_diag, s=5, c=abs(My_kNm_diag), cmap='plasma', alpha=0.6)
                            fig_col_diag.colorbar(sc1, ax=ax1, label='|φ·My| (kN·m)')
                            ax1.set_xlabel('φ·Mx (kN·m)'); ax1.set_ylabel('φ·P (kN)'); ax1.set_title('Vista Mx-P'); ax1.grid(True)

                            sc2 = ax2.scatter(My_kNm_diag, P_kN_diag, s=5, c=abs(Mx_kNm_diag), cmap='plasma', alpha=0.6)
                            fig_col_diag.colorbar(sc2, ax=ax2, label='|φ·Mx| (kN·m)')
                            ax2.set_xlabel('φ·My (kN·m)'); ax2.set_ylabel('φ·P (kN)'); ax2.set_title('Vista My-P'); ax2.grid(True)
                            fig_col_diag.tight_layout()
                        
                        elif vista_diag == "2D (Mx-My)":
                            ax_2d = fig_col_diag.add_subplot(111)
                            sc_2d = ax_2d.scatter(Mx_kNm_diag, My_kNm_diag, s=5, c=P_kN_diag, cmap='viridis', alpha=0.6)
                            fig_col_diag.colorbar(sc_2d, ax=ax_2d, label='φ·P (kN)')
                            ax_2d.set_xlabel('φ·Mx (kN·m)'); ax_2d.set_ylabel('φ·My (kN·m)'); ax_2d.set_title('Vista Mx-My (Contorno)')
                            ax_2d.grid(True); ax_2d.axhline(0, color='grey', lw=0.5); ax_2d.axvline(0, color='grey', lw=0.5)
                            ax_2d.set_aspect('equal', adjustable='box')
                        
                        st.pyplot(fig_col_diag)
                        
                        df_diag = pd.DataFrame({'phi*Pn (kN)': P_kN_diag, 'phi*Mnx (kNm)': Mx_kNm_diag, 'phi*Mny (kNm)': My_kNm_diag})
                        csv_diag = df_diag.to_csv(index=False, sep=";", decimal=",")
                        st.download_button(label="Descargar Datos del Diagrama (CSV)", data=csv_diag, file_name="diagrama_interaccion_columna.csv", mime="text/csv", key="download_diag_col")

                    with tab_cortante:
                        st.subheader("Diseño por Cortante y Confinamiento (DMO)")
                        st.caption("Según NSR-10 C.21.4. El cortante de diseño ($V_e$) considera la plastificación de las vigas.")

                        # El formulario para el diseño por cortante
                        with st.form(key="cortante_col_form_v2"): # Nueva key para el form
                            st.markdown("##### Entradas para Cortante Probable y Cargas")
                            cort_col1_form, cort_col2_form = st.columns(2)
                            with cort_col1_form:
                                Mn_viga_izq_kNm_form = st.number_input("Momento Nominal Viga Izquierda ($M_{n,viga,izq}$ kNm)", min_value=0.0, value=250.0, step=10.0)
                                Mn_viga_der_kNm_form = st.number_input("Momento Nominal Viga Derecha ($M_{n,viga,der}$ kNm)", min_value=0.0, value=280.0, step=10.0)
                            with cort_col2_form:
                                L_libre_vigas_m_form = st.number_input("Luz Libre Promedio Vigas ($L_{n,vigas}$ m)", min_value=3.0, value=6.0, step=0.5)
                                
                                # Corrección para H_libre_col_m:
                                # Calcular un valor por defecto más seguro para H_libre_col_m
                                # Usamos la altura de la columna de params_col_usados (convertida a m)
                                # y le restamos un porcentaje por las vigas (ej. 10-15% de la altura típica de entrepiso por cada lado si es nudo intermedio)
                                # O simplemente la altura del entrepiso menos el peralte de la viga.
                                # Por ahora, un valor estimado más simple y robusto:
                                default_h_col_m = params_col_usados.get('h_cm', PG.get('altura_tipica_entrepiso_m', 3.0) * 100) / 100.0 # Altura total columna en m
                                # H_libre_col_m_value = default_h_col_m - 2 * (PG.get('altura_tipica_entrepiso_m', 3.0) * 0.15) # Estimación previa
                                # Una mejor estimación podría ser la altura típica de entrepiso menos un peralte típico de viga.
                                # Ejemplo: si altura_tipica_entrepiso_m = 3.0m, y viga de 0.5m, H_libre = 2.5m
                                # O permitir que el usuario lo ingrese o usar una lógica más detallada si tienes peraltes de vigas.
                                # Por ahora, lo haremos dependiente de altura_tipica_entrepiso_m menos un %
                                altura_entrepiso_global = PG.get('altura_tipica_entrepiso_m', 3.0)
                                # Estimación altura libre: altura entrepiso - 15% (aprox. peralte viga)
                                valor_estimado_H_libre = altura_entrepiso_global * 0.85 
                                H_libre_col_m_form_value = max(2.0, valor_estimado_H_libre) # Asegurar que sea >= min_value

                                H_libre_col_m_form = st.number_input("Altura Libre Columna ($H_{n,col}$ m)", 
                                                                    min_value=2.0, 
                                                                    value=H_libre_col_m_form_value, 
                                                                    step=0.1, 
                                                                    help="Altura libre de la columna entre caras de elementos de apoyo (losas/vigas).")

                            st.markdown("##### Cargas Axiales y Cortante de Análisis sobre la Columna")
                            puc_col1_form, puc_col2_form = st.columns(2)
                            with puc_col1_form:
                                Pu_kN_cort_form_val = st.number_input("Carga Axial Última ($P_u$ kN)", min_value=0.0, value=1500.0, step=50.0)
                            with puc_col2_form:
                                Vu_analisis_kN_form_val = st.number_input("Cortante del Análisis Estructural ($V_{u,análisis}$ kN)", min_value=0.0, value=80.0, step=10.0)
                            
                            # Botón de envío DENTRO del formulario
                            submitted_cortante_col_form = st.form_submit_button("✂️ Diseñar Refuerzo Transversal de Columna")

                        if submitted_cortante_col_form: # Evaluar después de que el formulario se envía
                            try:
                                res_cort_col = diseno_columna_cortante_dmo(
                                    b_col_cm=params_col_usados['b_cm'], h_col_cm=params_col_usados['h_cm'],
                                    fc_MPa=params_col_usados['fc_MPa'], fy_MPa=params_col_usados['fy_MPa'],
                                    Pu_kN=Pu_kN_cort_form_val, Vu_analisis_kN=Vu_analisis_kN_form_val,
                                    Mn_viga_izq_kNm=Mn_viga_izq_kNm_form, Mn_viga_der_kNm=Mn_viga_der_kNm_form,
                                    L_libre_vigas_m=L_libre_vigas_m_form,
                                    rec_libre_mm=cm_to_mm(params_col_usados['rec_libre_cm']),
                                    diam_estribo_mm=params_col_usados['diam_estribo_mm'],
                                    H_libre_col_m=H_libre_col_m_form
                                )
                                st.session_state['resultados_col_cortante'] = res_cort_col

                                st.markdown("##### Resultados del Diseño Transversal de Columna")
                                if res_cort_col['status'] == "OK":
                                    current_id_col_cort = st.session_state.get("id_col_para_cortante_actual", id_columna_reporte if 'id_columna_reporte' in locals() else "Col_Desconocida")
                                    st.metric("Cortante de Diseño Usado ($V_u$ o $V_e$)", f"{res_cort_col['Vu_diseno_kN']:.2f} kN")
                                    st.caption(f"Cortante por capacidad de vigas ($V_e$): {res_cort_col['Ve_capacidad_kN']:.2f} kN. {res_cort_col['mensaje_Vc']}")
                                    st.metric("Longitud de Confinamiento ($l_o$)", f"{res_cort_col['longitud_confinamiento_lo_cm']:.1f} cm")

                                    col_res_cort1, col_res_cort2 = st.columns(2)
                                    with col_res_cort1:
                                        st.success(f"**Zona Confinada (en extremos $l_o$):**\nUsar estribos Ø{res_cort_col['diam_estribo_usado_mm']} mm @ **{res_cort_col['s_final_confinado_mm']:.0f} mm**")
                                    with col_res_cort2:
                                        st.info(f"**Zona Central (fuera de $l_o$):**\nUsar estribos Ø{res_cort_col['diam_estribo_usado_mm']} mm @ **{res_cort_col['s_fuera_confinado_mm']:.0f} mm**")
                                    
                                    with st.expander("Ver detalles del cálculo de cortante"):
                                        st.json(res_cort_col)
                                    # Guardar resultados para reporte
                                    datos_col_cort_reporte = {
                                        "ID Columna": current_id_col_cort, # Usar el ID de la columna actual
                                        "Vu Diseño (kN)": res_cort_col.get('Vu_diseno_kN'),
                                        "Ve Capacidad (kN)": res_cort_col.get('Ve_capacidad_kN'),
                                        "Vc (kN)": res_cort_col.get('Vc_kN'),
                                        "Mensaje Vc": res_cort_col.get('mensaje_Vc'),
                                        "Vs Req (kN)": res_cort_col.get('Vs_req_kN'),
                                        "Lo (cm)": res_cort_col.get('longitud_confinamiento_lo_cm'),
                                        "Ash/s Req (mm²/m)": res_cort_col.get('Ash_s_req_mm2_por_m'),
                                        "s_max Confinado (mm)": res_cort_col.get('s_max_confinado_mm'),
                                        "Ø Estribo Usado (mm)": res_cort_col.get('diam_estribo_usado_mm'),
                                        "s Confinado Final (mm)": res_cort_col.get('s_final_confinado_mm'),
                                        "s Central Final (mm)": res_cort_col.get('s_fuera_confinado_mm'),
                                        "Estado Cortante": "OK"
                                    }
                                    st.session_state.lista_columnas_cort_reporte.append(datos_col_cort_reporte)
                                    st.info(f"Datos de cortante/confinamiento de columna '{current_id_col_cort}' añadidos al reporte.")
                                else:
                                    st.error(f"Error en diseño por cortante: {res_cort_col.get('mensaje', 'Desconocido')}")

                            except KeyError as ke:
                                st.error(f"Error: Falta un parámetro esperado para el diseño por cortante: {ke}. Asegúrese de generar primero el diagrama P-M-M.")
                            except Exception as e_cort:
                                st.error(f"Error en el diseño por cortante de columna: {e_cort}")
                                import traceback
                                st.text(traceback.format_exc())


                    with tab_secc:
                        st.subheader("Sección Transversal y Parámetros Usados")
                        
                        # Es importante que params_col_usados esté lleno aquí.
                        # Calcular As_total_calc_mm2 y rho_g aquí si no está en params_col_usados directamente.
                        try:
                            barras_para_seccion = _generar_posicion_barras(
                                cm_to_mm(params_col_usados['b_cm']), cm_to_mm(params_col_usados['h_cm']), 
                                cm_to_mm(params_col_usados['rec_libre_cm']), 
                                params_col_usados['diam_estribo_mm'], params_col_usados['diam_barra_long_mm'], 
                                params_col_usados['nx_barras'], params_col_usados['ny_barras']
                            )
                            As_total_calc_mm2_secc = sum(b['area'] for b in barras_para_seccion)
                            rho_g_secc = As_total_calc_mm2_secc / (cm_to_mm(params_col_usados['b_cm']) * cm_to_mm(params_col_usados['h_cm']))

                            param_df_data_col = {
                                "Parámetro": ["b (cm)", "h (cm)", "Rec. Libre (cm)", "f'c (MPa)", "f'y (MPa)", 
                                            "Ø Barra Long (mm)", "Ø Estribo (mm)", "Barras cara 'b' (nx, total)", "Barras cara 'h' (ny, intermedias)",
                                            "Nº Total Barras (Estimado)", "As total calculada (cm²)", "Cuantía (ρg)"],
                                "Valor": [
                                    f"{params_col_usados['b_cm']:.1f}", f"{params_col_usados['h_cm']:.1f}", f"{params_col_usados['rec_libre_cm']:.1f}",
                                    f"{params_col_usados['fc_MPa']:.1f}", f"{params_col_usados['fy_MPa']:.0f}",
                                    f"{params_col_usados['diam_barra_long_mm']:.1f}", f"{params_col_usados['diam_estribo_mm']:.1f}",
                                    params_col_usados['nx_barras'], params_col_usados['ny_barras'],
                                    params_col_usados.get('num_barras_total', len(barras_para_seccion)), # Usar el del cálculo de barras si existe
                                    f"{As_total_calc_mm2_secc / 100.0:.2f}",
                                    f"{rho_g_secc:.3%}" 
                                ]
                            }
                            st.dataframe(pd.DataFrame(param_df_data_col))

                            st.markdown("###### Disposición del Refuerzo (Esquemático)")
                            fig_sec_col, ax_sec_col = plt.subplots(figsize=(5, 5 * params_col_usados['h_cm'] / params_col_usados['b_cm'] if params_col_usados['b_cm'] > 0 else 5))
                            b_plot_col = params_col_usados['b_cm']
                            h_plot_col = params_col_usados['h_cm']
                            rec_plot_col = params_col_usados['rec_libre_cm']
                            d_bar_plot_col = params_col_usados['diam_barra_long_mm'] / 10.0 # a cm

                            ax_sec_col.add_patch(plt.Rectangle((0, 0), b_plot_col, h_plot_col, fill=True, color='lightgray', ec='black'))
                            # Dibujo del estribo (aproximado al recubrimiento libre)
                            ax_sec_col.add_patch(plt.Rectangle((rec_plot_col, rec_plot_col), 
                                                            b_plot_col - 2*rec_plot_col, 
                                                            h_plot_col - 2*rec_plot_col, 
                                                            fill=False, color='dimgray', linewidth=1.0, linestyle='-'))

                            for barra in barras_para_seccion:
                                x_plot_b = barra['x']/10.0 + b_plot_col/2.0
                                y_plot_b = barra['y']/10.0 + h_plot_col/2.0
                                ax_sec_col.add_patch(plt.Circle((x_plot_b, y_plot_b), radius=d_bar_plot_col/2.0, color='black'))

                            ax_sec_col.set_xlim(-b_plot_col*0.1, b_plot_col*1.1) # Ajustar límites para mejor visualización
                            ax_sec_col.set_ylim(-h_plot_col*0.1, h_plot_col*1.1)
                            ax_sec_col.set_aspect('equal', adjustable='box')
                            ax_sec_col.set_xlabel('b (cm)')
                            ax_sec_col.set_ylabel('h (cm)')
                            ax_sec_col.set_title(f"Sección {b_plot_col:.0f}x{h_plot_col:.0f} cm - {len(barras_para_seccion)}Ø{params_col_usados['diam_barra_long_mm']:.1f}mm")
                            ax_sec_col.grid(True, linestyle=':', alpha=0.5)
                            st.pyplot(fig_sec_col)
                        
                        except KeyError as ke:
                            st.error(f"Error al mostrar la sección transversal: Falta el parámetro '{ke}'. Asegúrese de generar primero el diagrama P-M-M.")
                        except Exception as e_plot:
                            st.error(f"Error al dibujar la sección transversal: {e_plot}")

            else: # Si el diagrama P-M-M no se ha calculado o falló
                if st.session_state.get("resultados_columna_diag") and st.session_state["resultados_columna_diag"].get("status") == "Error":
                    st.error(f"No se puede mostrar el diagrama de interacción ni los detalles de la sección: {st.session_state['resultados_columna_diag'].get('mensaje')}")
                else:
                    st.info("⬅️ Ingrese los datos de la columna y presione 'Generar Diagrama de Interacción' en la columna izquierda para ver los resultados y habilitar el diseño detallado.")
    #else: # Si hubo error en el cálculo del diagrama
        # if st.session_state.get("resultados_columna_diag") and st.session_state["resultados_columna_diag"].get("status") == "Error":
        #     with col2:
        #         st.error(f"No se puede mostrar el diagrama: {st.session_state['resultados_columna_diag'].get('mensaje')}")
        # pass # No mostrar nada si no hay diagrama


# ===============================================================================
# MÓDULO: DISEÑO DE ZAPATAS
# ===============================================================================
elif modulo == "Diseño de Zapatas":
    st.header("Diseño de Zapatas Aisladas (NSR-10 C.15)")
    # Usar f'c, f'y, y q_adm de parámetros globales
    fc_zap = PG['fc_zapatas_MPa']
    fy_zap = PG['fy_MPa']
    q_adm_zap_kPa = PG['q_adm_suelo_kPa']
    prof_desplante_zap_m = PG.get('prof_cimentacion_m', 2.0) # Usar valor global si existe

    st.info(f"Parámetros Globales en Uso: f'c = {fc_zap} MPa, f'y = {fy_zap} MPa, q_adm = {q_adm_zap_kPa} kPa, Prof. Desplante: {prof_desplante_zap_m} m")

    col1, col2 = st.columns([1, 2]) # Columna de inputs y columna de resultados

    with col1:
        st.subheader("Datos de Entrada")
        id_zapata_reporte = st.text_input("ID Zapata para Reporte (ej: Z-1, Z-EjeA-1)", key="id_zap_rep")
        
        st.markdown("##### Cargas de Servicio (para dimensionar B y L)")
        P_srv_kN_z = st.number_input("Carga Axial Servicio $P_{serv}$ (kN)", min_value=0.1, value=600.0, step=10.0, key="psrv_zap_v2")
        Mx_srv_kNm_z = st.number_input("Momento $M_{x,serv}$ (kNm, alrededor de eje Y)", min_value=0.0, value=30.0, step=5.0, key="mxsrv_zap_v2")
        My_srv_kNm_z = st.number_input("Momento $M_{y,serv}$ (kNm, alrededor de eje X)", min_value=0.0, value=20.0, step=5.0, key="mysrv_zap_v2")

        st.markdown("---")
        st.markdown("##### Cargas Últimas (para diseño de 'h' y acero)")
        P_ult_kN_z = st.number_input("Carga Axial Última $P_{u}$ (kN)", min_value=0.1, value= P_srv_kN_z * 1.4 if P_srv_kN_z * 1.4 > 0 else 850.0, step=10.0, key="pult_zap_v2") # Default 1.4*Pserv
        Mx_ult_kNm_z = st.number_input("Momento Último $M_{ux}$ (kNm, alrededor de eje Y)", min_value=0.0, value= Mx_srv_kNm_z * 1.4 if Mx_srv_kNm_z * 1.4 > 0 else 50.0, step=5.0, key="mxult_zap_v2")
        My_ult_kNm_z = st.number_input("Momento Último $M_{uy}$ (kNm, alrededor de eje X)", min_value=0.0, value= My_srv_kNm_z * 1.4 if My_srv_kNm_z * 1.4 > 0 else 30.0, step=5.0, key="myult_zap_v2")

        Mn_col_x = st.number_input("Momento Nominal Columna $M_{n,col}$ (kNm, alrededor de eje Y)", min_value=0.0, value=350.0, step=10.0, key="mncolx_zap", help="Momento nominal de la columna que se apoya en la zapata. Usar para el diseño de la zapata.")
        Mn_col_y = st.number_input("Momento Nominal Columna $M_{n,col}$ (kNm, alrededor de eje X)", min_value=0.0, value=300.0, step=10.0, key="mncoly_zap", help="Momento nominal de la columna que se apoya en la zapata. Usar para el diseño de la zapata.")

        st.markdown("---")
        st.markdown("##### Geometría Columna y Zapata")
        b_col_cm_z = st.number_input("Ancho Columna $b_{col}$ (cm, dim. paralela a B)", min_value=20.0, value=40.0, step=1.0, key="bcol_zap_v2")
        h_col_cm_z = st.number_input("Peralte Columna $h_{col}$ (cm, dim. paralela a L)", min_value=20.0, value=40.0, step=1.0, key="hcol_zap_v2")
        
        rec_libre_cm_z = st.number_input("Recubrimiento libre en zapata (cm)", min_value=5.0, value=7.5, step=0.5, key="rec_zap_v2", help="NSR-10 C.7.7.1.(a) para concreto vaciado contra el suelo")
        
        diam_barra_opts_mm_z = {"#4 (12.7mm)": 12.7, "#5 (15.9mm)": 15.9, "#6 (19.1mm)": 19.1, "#7 (22.2mm)": 22.2, "#8 (25.4mm)": 25.4}
        sel_barra_z = st.selectbox("Diámetro Barra Refuerzo Zapata (Ref.)", list(diam_barra_opts_mm_z.keys()), index=1, key="diam_b_zap_v2") # #5 por defecto
        diam_barra_mm_z = diam_barra_opts_mm_z[sel_barra_z]
        
        st.markdown("---")
        st.markdown("##### Parámetros de Diseño (Opcional)")
        rel_BL_deseada_z = st.number_input("Relación L/B deseada (ej: 1.0 para cuadrada, 0 para auto)", min_value=0.0, value=0.0, step=0.1, key="relBL_zap_v2", help="Si es 0, se calcula automáticamente.")
        rel_BL_param = None if rel_BL_deseada_z == 0 else rel_BL_deseada_z # Convertir 0 a None

    if st.button("👣 Diseñar Zapata", key="btn_zap_v2"):
        if not id_zapata_reporte.strip():
            st.error("Por favor, ingrese un ID para la zapata.")
        else:
            try:
                resultados_zap = diseno_zapata_aislada_v2(
                    P_servicio_kN=P_srv_kN_z, Mx_servicio_kNm=Mx_srv_kNm_z, My_servicio_kNm=My_srv_kNm_z,
                    P_ultima_kN=P_ult_kN_z, 
                    Mx_ultima_kNm=Mn_col_x,  # Usar el momento de capacidad de la columna
                    My_ultima_kNm=Mn_col_y,  # Usar el momento de capacidad de la columna
                    fc_MPa=fc_zap, fy_MPa=fy_zap, q_adm_kPa=q_adm_zap_kPa,
                    b_col_cm=b_col_cm_z, h_col_cm=h_col_cm_z,
                    rec_libre_zapata_cm=rec_libre_cm_z, diam_barra_zapata_mm=diam_barra_mm_z,
                    prof_desplante_m=prof_desplante_zap_m,
                    relacion_BL_deseada=rel_BL_param
                )
                st.session_state['resultados_zapata_actual'] = resultados_zap # Guardar para posible reporte
                
                with col2:
                    st.subheader("Resultados Diseño Zapata")
                    st.info(f"Mensaje: {resultados_zap.get('mensaje', 'Cálculo procesado.')}")

                    if resultados_zap.get('status') == "OK":
                        st.markdown("##### Dimensiones Finales")
                        dim_p = resultados_zap['dimensiones_planta']
                        col_dim1, col_dim2, col_dim3 = st.columns(3)
                        with col_dim1: st.metric("Ancho B", f"{dim_p['B_m']:.2f} m")
                        with col_dim2: st.metric("Largo L", f"{dim_p['L_m']:.2f} m")
                        with col_dim3: st.metric("Peralte h", f"{resultados_zap['peralte_final']['h_m']:.2f} m (d={resultados_zap['peralte_final']['d_prom_m']:.3f}m)")

                        st.markdown("##### Presiones de Suelo")
                        pres_s = resultados_zap['presiones_servicio']
                        pres_u = resultados_zap['presiones_ultimas']
                        st.write(f"**Servicio:** q_max={pres_s['q_max_serv_kPa']:.1f} kPa, q_min={pres_s['q_min_serv_kPa']:.1f} kPa (q_adm={pres_s['q_adm_kPa']:.1f} kPa)")
                        if pres_s['q_max_serv_kPa'] > pres_s['q_adm_kPa'] * 1.01 : st.warning("Presión máxima de servicio excede ligeramente la admisible.")
                        if pres_s['q_min_serv_kPa'] < 0 : st.warning("Posible despegue bajo cargas de servicio (q_min < 0).")
                        st.write(f"**Últimas:** q_max={pres_u['q_max_ult_kPa']:.1f} kPa, q_min={pres_u['q_min_ult_kPa']:.1f} kPa")
                        # Podría añadirse q_ult_suelo si se conoce (ej. 1.5*q_adm)
                        
                        st.markdown("##### Chequeos de Cortante (Cargas Últimas)")
                        with st.expander("Ver Detalles de Cortante", expanded=False):
                            st.write("**Cortante Unidireccional (Dirección L - voladizo en L):**")
                            cort_L = resultados_zap['chequeo_cortante_unidir_L']
                            st.write(f"  Vud = {cort_L['Vud_kN']:.1f} kN, φVc = {cort_L['phiVc_kN']:.1f} kN - {'✅ OK' if cort_L['ok'] else '❌ NO OK'}")
                            if 'nota' in cort_L: st.caption(f"  Nota: {cort_L['nota']}")
                            
                            st.write("**Cortante Unidireccional (Dirección B - voladizo en B):**")
                            cort_B = resultados_zap['chequeo_cortante_unidir_B']
                            st.write(f"  Vud = {cort_B['Vud_kN']:.1f} kN, φVc = {cort_B['phiVc_kN']:.1f} kN - {'✅ OK' if cort_B['ok'] else '❌ NO OK'}")
                            if 'nota' in cort_B: st.caption(f"  Nota: {cort_B['nota']}")

                            st.write("**Punzonamiento (Cortante Bidireccional):**")
                            punz = resultados_zap['chequeo_punzonamiento']
                            st.write(f"  Vup = {punz['Vup_kN']:.1f} kN, φVc = {punz['phiVc_kN']:.1f} kN - {'✅ OK' if punz['ok'] else '❌ NO OK'}")
                            st.caption(f"  b₀={punz['b0_cm']:.1f} cm, vc={punz['vc_MPa']:.2f} MPa (Resistencia concreto al punzonamiento)")

                        st.markdown("##### Refuerzo a Flexión (Cargas Últimas)")
                        ref = resultados_zap['refuerzo_flexion']
                        st.write(f"**Dirección L (armado paralelo a B):** As_total = {ref['dir_L_paralelo_a_B']['As_total_cm2']:.2f} cm²  ($\Rightarrow$ {ref['dir_L_paralelo_a_B']['As_cm2_per_m']:.2f} cm²/m)")
                        st.write(f"**Dirección B (armado paralelo a L):** As_total = {ref['dir_B_paralelo_a_L']['As_total_cm2']:.2f} cm²  ($\Rightarrow$ {ref['dir_B_paralelo_a_L']['As_cm2_per_m']:.2f} cm²/m)")
                        st.caption(f"As mínimo por temperatura y retracción: {ref['As_min_temp_cm2_per_m']:.2f} cm²/m (calculado con h={resultados_zap['peralte_final']['h_m']:.2f}m)")

                        # Visualización gráfica de la planta
                        fig_zap, ax_zap = plt.subplots(figsize=(6, 6 * dim_p['L_m'] / dim_p['B_m'] if dim_p['B_m'] > 0 else 6))
                        ax_zap.add_patch(plt.Rectangle((0, 0), dim_p['B_m'], dim_p['L_m'], color='lightgray', alpha=0.7, ec='black'))
                        # Columna centrada
                        x0_col = (dim_p['B_m'] - cm_to_m(b_col_cm_z)) / 2
                        y0_col = (dim_p['L_m'] - cm_to_m(h_col_cm_z)) / 2
                        ax_zap.add_patch(plt.Rectangle((x0_col, y0_col), cm_to_m(b_col_cm_z), cm_to_m(h_col_cm_z), color='dimgray', ec='black'))
                        
                        ax_zap.set_aspect('equal', 'box')
                        ax_zap.set_xlim(-0.1*dim_p['B_m'], 1.1*dim_p['B_m'])
                        ax_zap.set_ylim(-0.1*dim_p['L_m'], 1.1*dim_p['L_m'])
                        ax_zap.set_xlabel("Dimensión B (m)")
                        ax_zap.set_ylabel("Dimensión L (m)")
                        ax_zap.set_title(f"Planta Zapata: {dim_p['B_m']:.2f}m x {dim_p['L_m']:.2f}m")
                        ax_zap.grid(True, linestyle=':', alpha=0.6)
                        st.pyplot(fig_zap)

                        # --- Guardar datos para el reporte ---
                        datos_zap_reporte = {
                            "ID Zapata": id_zapata_reporte,
                            "B (m)": dim_p['B_m'],
                            "L (m)": dim_p['L_m'],
                            "h (m)": resultados_zap['peralte_final']['h_m'],
                            "d prom (m)": resultados_zap['peralte_final']['d_prom_m'],
                            "P_serv (kN)": P_srv_kN_z,
                            "Mx_serv (kNm)": My_srv_kNm_z, # Convención de la función original
                            "My_serv (kNm)": Mx_srv_kNm_z, # Convención de la función original
                            "P_ult (kN)": P_ult_kN_z,
                            "Mux_ult_diseno (kNm)": Mn_col_y, # El que se usó para diseño estructural
                            "Muy_ult_diseno (kNm)": Mn_col_x, # El que se usó para diseño estructural
                            "q_max_serv (kPa)": resultados_zap['presiones_servicio']['q_max_serv_kPa'],
                            "q_min_serv (kPa)": resultados_zap['presiones_servicio']['q_min_serv_kPa'],
                            "q_adm (kPa)": resultados_zap['presiones_servicio']['q_adm_kPa'],
                            "q_max_ult (kPa)": resultados_zap['presiones_ultimas']['q_max_ult_kPa'],
                            "q_min_ult (kPa)": resultados_zap['presiones_ultimas']['q_min_ult_kPa'],
                            "Cort_Uni_L_Vud (kN)": resultados_zap['chequeo_cortante_unidir_L']['Vud_kN'],
                            "Cort_Uni_L_phiVc (kN)": resultados_zap['chequeo_cortante_unidir_L']['phiVc_kN'],
                            "Cort_Uni_L_OK": "Sí" if resultados_zap['chequeo_cortante_unidir_L']['ok'] else "No",
                            "Cort_Uni_B_Vud (kN)": resultados_zap['chequeo_cortante_unidir_B']['Vud_kN'],
                            "Cort_Uni_B_phiVc (kN)": resultados_zap['chequeo_cortante_unidir_B']['phiVc_kN'],
                            "Cort_Uni_B_OK": "Sí" if resultados_zap['chequeo_cortante_unidir_B']['ok'] else "No",
                            "Punz_Vup (kN)": resultados_zap['chequeo_punzonamiento']['Vup_kN'],
                            "Punz_phiVc (kN)": resultados_zap['chequeo_punzonamiento']['phiVc_kN'],
                            "Punz_OK": "Sí" if resultados_zap['chequeo_punzonamiento']['ok'] else "No",
                            "As_L_cm2/m": resultados_zap['refuerzo_flexion']['dir_L_paralelo_a_B']['As_cm2_per_m'],
                            "As_B_cm2/m": resultados_zap['refuerzo_flexion']['dir_B_paralelo_a_L']['As_cm2_per_m'],
                            "As_min_temp_cm2/m": resultados_zap['refuerzo_flexion']['As_min_temp_cm2_per_m']
                        }
                        st.session_state.lista_zapatas_reporte.append(datos_zap_reporte)
                        st.info(f"Resultados de zapata '{id_zapata_reporte}' añadidos al reporte.")

                    elif resultados_zap.get('status') == "Error":
                        st.error(f"No se pudo completar el diseño. {resultados_zap.get('mensaje', '')}")
                        if 'h_propuesto_m' in resultados_zap: # Si falló en el bucle de 'h'
                            st.write("Últimos resultados de chequeo de cortante antes de detenerse:")
                            if 'cort_uni_L' in resultados_zap: st.write(f"  Cortante Uni L: Vud={resultados_zap['cort_uni_L'].get('Vud_kN','N/A'):.1f} kN, φVc={resultados_zap['cort_uni_L'].get('phiVc_kN','N/A'):.1f} kN, OK={resultados_zap['cort_uni_L'].get('ok','N/A')}")
                            if 'cort_uni_B' in resultados_zap: st.write(f"  Cortante Uni B: Vud={resultados_zap['cort_uni_B'].get('Vud_kN','N/A'):.1f} kN, φVc={resultados_zap['cort_uni_B'].get('phiVc_kN','N/A'):.1f} kN, OK={resultados_zap['cort_uni_B'].get('ok','N/A')}")
                            if 'punzonamiento' in resultados_zap: st.write(f"  Punzonamiento: Vup={resultados_zap['punzonamiento'].get('Vup_kN','N/A'):.1f} kN, φVc={resultados_zap['punzonamiento'].get('phiVc_kN','N/A'):.1f} kN, OK={resultados_zap['punzonamiento'].get('ok','N/A')}")


            except ValueError as e: # Errores de validación de inputs
                with col2: st.error(f"Error en datos de entrada: {e}")
            except Exception as e: # Otros errores inesperados
                with col2: st.error(f"Error inesperado durante el diseño de la zapata: {e}")
                # import traceback
                # st.text(traceback.format_exc()) # Para depuración



# ===============================================================================
# MÓDULO: DISEÑO DE LOSA NERVADA (Análisis y Diseño de Nervio)
# ===============================================================================
elif modulo == "Diseño de Losa Nervada":
    st.header("Diseño de Losa Nervada Unidireccional")
    fc_losa_nerv = PG['fc_losas_vigas_MPa'] # Usar fc para losas/vigas
    fy_losa_nerv = PG['fy_MPa']
    st.info(f"Usando Materiales Globales: f'c = {fc_losa_nerv} MPa, f'y = {fy_losa_nerv} MPa")

    # Guardar datos de geometría y cargas de la losa en session_state
    if 'losa_nerv_geom_cargas' not in st.session_state:
        st.session_state.losa_nerv_geom_cargas = {
            "separacion_nervios_m": 0.6, "t_loseta_cm": 5.0, "h_total_nervio_cm": 25.0,
            "b_alma_nervio_cm": 10.0, "q_muerta_adicional_kNm2": 1.5, "q_viva_kNm2": 1.8,
            "L_libre_nervio_m": 5.0, # Luz libre del nervio, importante para b_eff
            "rec_libre_inf_cm": 2.5, # Recubrimiento inferior nervio
            "diam_estribo_mm_def": 9.5, # Default #3
            "diam_barra_long_mm_def": 15.9 # Default #5
        }
    
    data_ln = st.session_state.losa_nerv_geom_cargas

    id_losa_nervada_reporte = st.text_input("ID Losa Nervada/Nervio para Reporte (ej: LosaN2-N1, Nervio EjeA)", key="id_ln_rep")

    tab_cargas_ln, tab_flex_ln, tab_cort_ln = st.tabs([
        "⚖️ Cargas por Nervio", "💪 Diseño a Flexión (Nervio)", "✂️ Diseño a Cortante (Nervio)"
    ])

    # --- Pestaña Cargas por Nervio ---
    with tab_cargas_ln:
        st.subheader("Cálculo de Cargas Lineales por Nervio")
        
        col1_cln, col2_cln = st.columns(2)
        with col1_cln:
            st.markdown("##### Geometría de la Losa Nervada")
            data_ln["separacion_nervios_m"] = st.number_input("Separación centro a centro de Nervios (m)", min_value=0.3, value=data_ln["separacion_nervios_m"], step=0.05, key="sep_ln_c")
            data_ln["t_loseta_cm"] = st.number_input("Espesor Loseta (hf) (cm)", min_value=4.0, value=data_ln["t_loseta_cm"], step=0.5, key="tlos_ln_c")
            data_ln["h_total_nervio_cm"] = st.number_input("Altura Total Nervio (h) (cm, loseta+alma)", min_value=15.0, value=data_ln["h_total_nervio_cm"], step=1.0, key="htot_ln_c")
            data_ln["b_alma_nervio_cm"] = st.number_input("Ancho Alma Nervio (bw) (cm)", min_value=8.0, value=data_ln["b_alma_nervio_cm"], step=1.0, key="balma_ln_c")
        
        with col2_cln:
            st.markdown("##### Cargas superficiales (kN/m²)")
            data_ln["q_muerta_adicional_kNm2"] = st.number_input("CM Adicional (kN/m², acabados, etc.)", min_value=0.0, value=data_ln["q_muerta_adicional_kNm2"], step=0.1, key="cm_adic_ln_c")
            data_ln["q_viva_kNm2"] = st.number_input("CV (kN/m²)", min_value=0.0, value=data_ln["q_viva_kNm2"], step=0.1, key="cv_ln_c")

        if st.button("⚖️ Calcular Cargas por Nervio", key="btn_cargas_ln"):
            if not id_losa_nervada_reporte.strip():
                st.error("Por favor, ingrese un ID para la losa nervada/nervio antes de calcular.")
            else:
                try:
                    resultados_cargas = calcular_cargas_losa_nervada(
                        data_ln["separacion_nervios_m"], data_ln["t_loseta_cm"], 
                        data_ln["h_total_nervio_cm"], data_ln["b_alma_nervio_cm"],
                        data_ln["q_muerta_adicional_kNm2"], data_ln["q_viva_kNm2"]
                    )
                    data_ln.update(resultados_cargas) # Guardar resultados en session_state
                    st.session_state.losa_nerv_geom_cargas = data_ln # Actualizar session_state

                    st.success("Cargas calculadas:")
                    st.metric("Peso Propio Losa", f"{resultados_cargas['peso_propio_losa_kNm2']:.2f} kN/m²")
                    col_w1, col_w2 = st.columns(2)
                    with col_w1:
                        st.metric("W Muerta Total por Nervio", f"{resultados_cargas['w_muerta_total_por_nervio_kNm']:.2f} kN/m")
                    with col_w2:
                        st.metric("W Viva por Nervio", f"{resultados_cargas['w_viva_por_nervio_kNm']:.2f} kN/m")
                    st.markdown("---")
                    st.markdown("**Nota:** Use estas cargas lineales con los coeficientes de momento y cortante de NSR-10 C.8.3.3 (o de un análisis estructural) para obtener $M_u$ y $V_u$ para el diseño del nervio en las siguientes pestañas.")
                    st.session_state.current_id_losa_nervada = id_losa_nervada_reporte

                except ValueError as e:
                    st.error(f"Error en datos de entrada: {e}")
                except Exception as e:
                    st.error(f"Error inesperado en cálculo de cargas: {e}")

    # --- Pestaña Diseño a Flexión del Nervio ---
    with tab_flex_ln:
        st.subheader("Diseño a Flexión del Nervio")
        st.write("Ingrese el momento último de diseño $M_u$ para el nervio (obtenido de análisis o coeficientes NSR-10).")

        col1_fln, col2_fln = st.columns(2)
        with col1_fln:
            st.markdown("##### Solicitación")
            Mu_kNm_fln = st.number_input("Momento Último $M_u$ (kNm)", value=15.0, step=0.5, key="mu_fln", help="Positivo para tracción inferior, negativo para tracción superior.")
            
            st.markdown("##### Geometría (Puede usar valores de 'Cargas por Nervio')")
            sync_geom_fln = st.checkbox("Usar geometría de pestaña 'Cargas'", value=True, key="sync_geom_fln")

            h_total_cm_fln = st.number_input("Altura Total Nervio h (cm)", value=data_ln["h_total_nervio_cm"], step=1.0, key="h_fln", disabled=sync_geom_fln)
            bw_cm_fln = st.number_input("Ancho Alma Nervio bw (cm)", value=data_ln["b_alma_nervio_cm"], step=1.0, key="bw_fln", disabled=sync_geom_fln)
            hf_cm_fln = st.number_input("Espesor Loseta hf (cm)", value=data_ln["t_loseta_cm"], step=0.5, key="hf_fln", disabled=sync_geom_fln)
            
            st.markdown("##### Parámetros Adicionales para Diseño")
            sep_nerv_m_fln = st.number_input("Separación Nervios (m, para $b_{eff}$)", value=data_ln["separacion_nervios_m"], step=0.05, key="sep_fln", disabled=sync_geom_fln and "separacion_nervios_m" in data_ln)
            L_libre_m_fln = st.number_input("Luz Libre del Nervio (m, para $b_{eff}$)", value=data_ln.get("L_libre_nervio_m",5.0), step=0.1, key="Llibre_fln")
            
            rec_libre_inf_cm_fln = st.number_input("Rec. Libre Inferior (cm)", value=data_ln.get("rec_libre_inf_cm", 2.5), step=0.5, key="rec_inf_fln")
            
            diam_estribo_opts_mm = {"#3 (9.5mm)": 9.5, "#4 (12.7mm)": 12.7, "Ninguno": 0.0}
            sel_estribo_fln = st.selectbox("Diámetro Estribo (si hay)", list(diam_estribo_opts_mm.keys()), index=2, key="diam_e_fln") # Ninguno por defecto
            diam_estribo_mm_fln = diam_estribo_opts_mm[sel_estribo_fln]

            diam_barra_opts_mm = {"#3 (9.5mm)":9.5, "#4 (12.7mm)": 12.7, "#5 (15.9mm)": 15.9, "#6 (19.1mm)": 19.1}
            sel_barra_fln = st.selectbox("Diámetro Barra Long. (Ref.)", list(diam_barra_opts_mm.keys()), index=1, key="diam_b_fln") # #4 por defecto
            diam_barra_long_mm_fln = diam_barra_opts_mm[sel_barra_fln]
            
            # Actualizar data_ln si no se sincroniza
            if not sync_geom_fln:
                data_ln["h_total_nervio_cm"] = h_total_cm_fln
                data_ln["b_alma_nervio_cm"] = bw_cm_fln
                data_ln["t_loseta_cm"] = hf_cm_fln
                data_ln["separacion_nervios_m"] = sep_nerv_m_fln
            data_ln["L_libre_nervio_m"] = L_libre_m_fln
            data_ln["rec_libre_inf_cm"] = rec_libre_inf_cm_fln
            data_ln["diam_estribo_mm_def"] = diam_estribo_mm_fln
            data_ln["diam_barra_long_mm_def"] = diam_barra_long_mm_fln
            st.session_state.losa_nerv_geom_cargas = data_ln

        if st.button("💪 Diseñar Nervio a Flexión", key="btn_flex_ln"):
            current_id_ln = st.session_state.get("current_id_losa_nervada", id_losa_nervada_reporte if 'id_losa_nervada_reporte' in locals() and id_losa_nervada_reporte.strip() else "Nervio_Desconocido")
            if current_id_ln == "Nervio_Desconocido" and id_losa_nervada_reporte.strip(): # Si se ingresó ID pero no se presionó calcular cargas
                 current_id_ln = id_losa_nervada_reporte
            elif current_id_ln == "Nervio_Desconocido":
                 st.error("Por favor, ingrese un ID para la losa nervada/nervio en la pestaña de Cargas o aquí.")
                 st.stop()
            try:
                # Usar los valores de data_ln que se actualizaron
                resultados_flex_nervio = diseno_nervio_flexion(
                    Mu_kNm=Mu_kNm_fln, fc_MPa=fc_losa_nerv, fy_MPa=fy_losa_nerv,
                    h_total_cm=data_ln["h_total_nervio_cm"], bw_cm=data_ln["b_alma_nervio_cm"],
                    hf_cm=data_ln["t_loseta_cm"],
                    separacion_nervios_m=data_ln["separacion_nervios_m"], 
                    L_libre_nervio_m=data_ln["L_libre_nervio_m"],
                    rec_libre_inf_cm=data_ln["rec_libre_inf_cm"],
                    diam_estribo_mm=data_ln["diam_estribo_mm_def"],
                    diam_barra_long_mm=data_ln["diam_barra_long_mm_def"]
                )
                with col2_fln:
                    st.markdown("##### Resultados Diseño a Flexión del Nervio")
                    st.info(f"Mensaje: {resultados_flex_nervio['mensaje']}")
                    if resultados_flex_nervio['status'] != "Error":
                        st.metric("As Final Requerida", f"{resultados_flex_nervio['As_final_cm2']:.3f} cm²")
                        st.json(resultados_flex_nervio, expanded=False) # Mostrar todos los detalles
                    else:
                        st.error(f"No se pudo completar el diseño a flexión. {resultados_flex_nervio.get('b_eff_mm','')} ")

                if resultados_flex_nervio['status'] != "Error":
                    # Guardar temporalmente los resultados de flexión para combinarlos con los de cortante
                    st.session_state.temp_flex_nervio_resultados = resultados_flex_nervio
                    st.session_state.temp_flex_nervio_inputs = { # Guardar inputs relevantes
                        "ID Elemento": current_id_ln,
                        "h_total_cm": data_ln["h_total_nervio_cm"],
                        "bw_cm": data_ln["b_alma_nervio_cm"],
                        "hf_cm": data_ln["t_loseta_cm"],
                        "L_libre_m": data_ln["L_libre_nervio_m"],
                        "sep_nervios_m": data_ln["separacion_nervios_m"],
                        "Mu_kNm": Mu_kNm_fln, # El Mu usado para este cálculo
                        "fc_MPa": fc_losa_nerv, "fy_MPa": fy_losa_nerv
                    }

            except Exception as e:
                with col2_fln: st.error(f"Error inesperado en diseño a flexión: {e}")
                # import traceback; st.text(traceback.format_exc())

    # --- Pestaña Diseño a Cortante del Nervio ---
    with tab_cort_ln:
        st.subheader("Diseño a Cortante del Nervio")
        st.write("Ingrese el cortante último de diseño $V_u$ para el nervio.")

        col1_cln_cort, col2_cln_cort = st.columns(2)
        with col1_cln_cort:
            st.markdown("##### Solicitación")
            Vu_kN_cln = st.number_input("Cortante Último $V_u$ (kN)", value=10.0, step=0.5, key="vu_cln")

            st.markdown("##### Geometría (Puede usar valores de Pestañas Anteriores)")
            sync_geom_cln_cort = st.checkbox("Usar geometría de pestaña 'Cargas'/'Flexión'", value=True, key="sync_geom_cln_cort")

            h_total_cm_cln_cort = st.number_input("Altura Total Nervio h (cm)", value=data_ln["h_total_nervio_cm"], step=1.0, key="h_cln_cort", disabled=sync_geom_cln_cort)
            bw_cm_cln_cort = st.number_input("Ancho Alma Nervio bw (cm)", value=data_ln["b_alma_nervio_cm"], step=1.0, key="bw_cln_cort", disabled=sync_geom_cln_cort)
            
            st.markdown("##### Recubrimiento y Armado (para 'd' y estribos)")
            rec_libre_inf_cm_cln_cort = st.number_input("Rec. Libre Inferior (cm)", value=data_ln["rec_libre_inf_cm"], step=0.5, key="rec_inf_cln_cort", disabled=sync_geom_cln_cort)
            
            sel_estribo_cln_cort = st.selectbox("Diámetro Estribo a Usar", list(diam_estribo_opts_mm.keys()), index=list(diam_estribo_opts_mm.keys()).index(sel_estribo_fln) if 'sel_estribo_fln' in locals() else 2, key="diam_e_cln_cort")
            diam_estribo_mm_cln_cort = diam_estribo_opts_mm[sel_estribo_cln_cort]

            sel_barra_cln_cort = st.selectbox("Diámetro Barra Long. (Ref. para d)", list(diam_barra_opts_mm.keys()), index=list(diam_barra_opts_mm.keys()).index(sel_barra_fln) if 'sel_barra_fln' in locals() else 1, key="diam_b_cln_cort")
            diam_barra_long_mm_cln_cort = diam_barra_opts_mm[sel_barra_cln_cort]

            # Actualizar data_ln si no se sincroniza
            if not sync_geom_cln_cort:
                data_ln["h_total_nervio_cm"] = h_total_cm_cln_cort
                data_ln["b_alma_nervio_cm"] = bw_cm_cln_cort
                data_ln["rec_libre_inf_cm"] = rec_libre_inf_cm_cln_cort
            # Siempre actualizar diámetros de referencia para cortante
            data_ln["diam_estribo_mm_def"] = diam_estribo_mm_cln_cort
            data_ln["diam_barra_long_mm_def"] = diam_barra_long_mm_cln_cort
            st.session_state.losa_nerv_geom_cargas = data_ln

        if st.button("✂️ Diseñar Nervio a Cortante", key="btn_cort_ln"):
            current_id_ln = st.session_state.get("current_id_losa_nervada", id_losa_nervada_reporte if 'id_losa_nervada_reporte' in locals() and id_losa_nervada_reporte.strip() else "Nervio_Desconocido")
            if current_id_ln == "Nervio_Desconocido" and id_losa_nervada_reporte.strip():
                 current_id_ln = id_losa_nervada_reporte
            elif current_id_ln == "Nervio_Desconocido":
                 st.error("Por favor, ingrese un ID para la losa nervada/nervio en la pestaña de Cargas o aquí.")
                 st.stop()

            if not st.session_state.get("temp_flex_nervio_resultados"):
                st.error("Primero diseñe el nervio a flexión en la pestaña anterior.")
            else:
                try:
                    resultados_cort_nervio = diseno_nervio_cortante(
                        Vu_kN=Vu_kN_cln, fc_MPa=fc_losa_nerv, fy_MPa=fy_losa_nerv,
                        h_total_cm=data_ln["h_total_nervio_cm"], bw_cm=data_ln["b_alma_nervio_cm"],
                        rec_libre_inf_cm=data_ln["rec_libre_inf_cm"],
                        diam_estribo_mm=data_ln["diam_estribo_mm_def"], # Este es el que se está diseñando
                        diam_barra_long_mm=data_ln["diam_barra_long_mm_def"]
                    )
                    with col2_cln_cort:
                        st.markdown("##### Resultados Diseño a Cortante del Nervio")
                        st.info(f"Mensaje: {resultados_cort_nervio['mensaje']}")
                        if resultados_cort_nervio['status'] != "Error":
                            st.metric("Av/s Final Requerido", f"{resultados_cort_nervio['Av_s_final_mm2_per_m']:.2f} mm²/m")
                            s_rec = resultados_cort_nervio.get('s_rec_constructivo_mm')
                            if s_rec and s_rec != "N/A (o según mínimos)":
                                st.success(f"Se recomienda usar estribos Ø{resultados_cort_nervio['diam_estribo_usado_mm']:.1f}mm @ {s_rec:.0f}mm")
                            else:
                                st.info("Verificar necesidad de estribos mínimos según tipo de nervio y NSR-10.")
                            st.json(resultados_cort_nervio, expanded=False)
                        else:
                            st.error("No se pudo completar el diseño a cortante.")
                    
                    # Guardar resultados de cortante junto con los de flexión
                    flex_inputs = st.session_state.temp_flex_nervio_inputs
                    flex_res = st.session_state.temp_flex_nervio_resultados
                        
                    datos_nervio_reporte = {
                            "ID Elemento": flex_inputs.get("ID Elemento", current_id_ln),
                            "h_total (cm)": flex_inputs.get("h_total_cm"),
                            "bw (cm)": flex_inputs.get("bw_cm"),
                            "hf (cm)": flex_inputs.get("hf_cm"),
                            "L_libre (m)": flex_inputs.get("L_libre_m"),
                            "S_nervios (m)": flex_inputs.get("sep_nervios_m"),
                            "fc (MPa)": flex_inputs.get("fc_MPa"),
                            "fy (MPa)": flex_inputs.get("fy_MPa"),
                            "Mu (kNm)": flex_inputs.get("Mu_kNm"),
                            "As_final (cm²)": flex_res.get("As_final_cm2"),
                            "b_eff (cm)": flex_res.get("b_eff_o_bw_cm"),
                            "epsilon_t": flex_res.get("epsilon_t_final"),
                            "Vu (kN)": Vu_kN_cln, # El Vu usado para este cálculo
                            "phiVc (kN)": resultados_cort_nervio.get("phi_Vc_kN"),
                            "Vs_req (kN)": resultados_cort_nervio.get("Vs_req_kN"),
                            "Av/s (mm²/m)": resultados_cort_nervio.get("Av_s_final_mm2_per_m"),
                            "ØEstribo (mm)": resultados_cort_nervio.get("diam_estribo_usado_mm"),
                            "s_rec (mm)": resultados_cort_nervio.get("s_rec_constructivo_mm"),
                            "Estado Flexión": flex_res.get("status"),
                            "Estado Cortante": resultados_cort_nervio.get("status")
                        }
                    st.session_state.lista_nervios_reporte.append(datos_nervio_reporte)
                    st.info(f"Resultados completos del nervio '{current_id_ln}' añadidos al reporte.")
                    
                except Exception as e:
                    with col2_cln_cort: st.error(f"Error inesperado en diseño a cortante: {e}")
                    # import traceback; st.text(traceback.format_exc())


# ===============================================================================
# MÓDULO: CÁLCULO DE DEFLEXIONES
# ===============================================================================
elif modulo == "Cálculo de Deflexiones":
    st.header("Cálculo y Verificación de Deflexiones (NSR-10 C.9.5)")
    fc_def = PG['fc_losas_vigas_MPa'] 
    Ec_MPa = 4700 * np.sqrt(fc_def) 
    st.info(f"Parámetros de Material Usados: f'c = {fc_def} MPa  ➔  Ec = {Ec_MPa:.0f} MPa")

    col1_def, col2_def = st.columns([1, 1]) 

    with col1_def:
        st.subheader("1. Geometría y Propiedades del Elemento")
        id_elemento_deflex_reporte = st.text_input("ID Elemento para Reporte de Deflexión (ej: V-101, Losa N2)", key="id_deflex_rep_v2")
        tipo_elemento_def = st.selectbox("Tipo de Elemento", 
                                         ["Viga Rectangular", "Losa Maciza Unidireccional", "Nervio de Losa (Sección T)"], 
                                         key="elem_def_tipo_v2")
        L_libre_cm_def = st.number_input("Luz Libre del Elemento $L_n$ (cm)", min_value=100.0, value=500.0, step=10.0, key="L_def_v2")

        # --- Inputs de geometría específicos al tipo de elemento ---
        if tipo_elemento_def == "Viga Rectangular" or tipo_elemento_def == "Losa Maciza Unidireccional":
            b_elem_cm_def = st.number_input("Ancho del Elemento b (cm)", min_value=10.0, value=30.0, step=1.0, key="b_rect_def_v2")
            h_elem_cm_def = st.number_input("Peralte Total del Elemento h (cm)", min_value=15.0, value=50.0, step=1.0, key="h_rect_def_v2")
            es_T_secc_def = False
            bw_alma_calc_cm = b_elem_cm_def
            hf_loseta_calc_cm = h_elem_cm_def
            b_eff_calc_cm = b_elem_cm_def
        elif tipo_elemento_def == "Nervio de Losa (Sección T)":
            st.markdown("###### Dimensiones del Nervio y Losa (para $I_g$)")
            h_total_nervio_cm_def = st.number_input("Altura Total Nervio h (cm, loseta+alma)", min_value=15.0, value=25.0, step=1.0, key="h_nerv_def_v2")
            bw_alma_cm_def = st.number_input("Ancho Alma Nervio bw (cm)", min_value=8.0, value=10.0, step=1.0, key="bw_nerv_def_v2")
            hf_loseta_cm_def = st.number_input("Espesor Loseta hf (cm)", min_value=4.0, value=5.0, step=0.5, key="hf_nerv_def_v2")
            separacion_nervios_m_def = st.number_input("Separación Centro a Centro Nervios (m)", min_value=0.3, value=0.6, step=0.05, key="sep_nerv_def_v2")
            L_libre_nervio_m_def = cm_to_m(L_libre_cm_def)
            beff1 = L_libre_nervio_m_def * 1000 / 4.0
            beff2 = cm_to_mm(bw_alma_cm_def) + 16 * cm_to_mm(hf_loseta_cm_def)
            beff3 = separacion_nervios_m_def * 1000
            b_eff_calc_mm = min(beff1, beff2, beff3)
            b_eff_calc_cm = mm_to_cm(b_eff_calc_mm)
            st.info(f"Ancho efectivo $b_{{eff}}$ calculado: {b_eff_calc_cm:.1f} cm")
            es_T_secc_def = True
            h_elem_cm_def = h_total_nervio_cm_def
            bw_alma_calc_cm = bw_alma_cm_def
            hf_loseta_calc_cm = hf_loseta_cm_def
        
        # Botón para calcular Ig, yt (o puede ser parte del botón principal)
        if st.button("Calcular Ig y yt de la Sección", key="btn_calc_ig_yt"):
            try:
                Ig_mm4, yt_mm, y_centroide_sup_mm_val = momento_inercia_bruta_T_o_Rect(
                    b_total_ala_cm=b_eff_calc_cm if es_T_secc_def else b_elem_cm_def,
                    h_total_cm=h_elem_cm_def,
                    hf_loseta_cm=hf_loseta_calc_cm if es_T_secc_def else h_elem_cm_def,
                    bw_alma_cm=bw_alma_calc_cm if es_T_secc_def else b_elem_cm_def,
                    es_seccion_T=es_T_secc_def
                )
                st.success(f"Calculado: $I_g = {Ig_mm4:,.0f} mm^4$, $y_t = {yt_mm:.1f} mm$")
                st.session_state['Ig_def_calc'] = Ig_mm4
                st.session_state['yt_def_calc'] = yt_mm
                st.session_state['y_centroide_sup_mm_def_calc'] = y_centroide_sup_mm_val # Guardar para cálculo de d
            except Exception as e:
                st.error(f"Error calculando Ig/yt: {e}")
                st.session_state['Ig_def_calc'] = None
                st.session_state['yt_def_calc'] = None
                st.session_state['y_centroide_sup_mm_def_calc'] = None


        st.markdown("##### Cargas de Servicio (NO mayoradas)")
        w_CM_kNpm_def = st.number_input("Carga Muerta Sostenida (CM) (kN/m)", min_value=0.0, value=5.0, step=0.5, key="wCM_def_v2")
        w_CV_kNpm_def = st.number_input("Carga Viva Total (CV) (kN/m)", min_value=0.0, value=8.0, step=0.5, key="wCV_def_v2")
        porc_CV_sost_def = st.slider("Porcentaje de CV Sostenida (%)", 0, 100, 25, key="cvsost_def_v2")
        
        st.markdown("##### Parámetros para Inercia Efectiva y Largo Plazo")
        tipo_apoyo_def = st.selectbox("Condición de Apoyo ($M_a$ y coef. deflexión)", 
                                      ["simples", "empotrado_empotrado", "voladizo", "empotrado_apoyado"], 
                                      key="apoyo_def_v3")
        Icr_manual_mm4_def = st.number_input("Opcional: $I_{cr}$ (Inercia fisurada, mm⁴)", value=0.0, format="%e", key="icr_def_v2", help="Si es 0, se usará aproximación NSR-10 si se fisura.")
        
        st.markdown("##### Parámetros para Deflexión a Largo Plazo")
        As_comp_cm2_def = st.number_input("Área Acero de Compresión $A_s'$ (cm²)", min_value=0.0, value=0.0, step=0.1, key="as_comp_def_v2")
        d_prima_comp_cm_def = st.number_input("Rec. a $A_s'$ desde fibra comp. $d'$ (cm)", min_value=0.0, value=4.0, step=0.5, key="dprima_def_v2")
        
        xi_tiempo_def_options = {"3 meses": 1.0, "6 meses": 1.2, "12 meses": 1.4, "5 años o más": 2.0}
        sel_xi = st.selectbox("Duración Carga Sostenida (para factor ξ)", list(xi_tiempo_def_options.keys()), index=3, key="xi_def_v2")
        xi_factor_def = xi_tiempo_def_options[sel_xi]

        if st.button("🔍 Calcular y Verificar Deflexiones", key="btn_calc_def_v3"):
            if not id_elemento_deflex_reporte.strip():
                st.error("Por favor, ingrese un ID para el elemento a verificar.")
            elif st.session_state.get('Ig_def_calc') is None or st.session_state.get('yt_def_calc') is None:
                st.error("Primero calcule Ig y yt para la sección (presione el botón 'Calcular Ig y yt').")
            else:
                Ig_val = st.session_state['Ig_def_calc']
                yt_val = st.session_state['yt_def_calc']
                y_centroide_sup_mm_val = st.session_state.get('y_centroide_sup_mm_def_calc', h_elem_cm_def * 10 / 2.0) # Fallback si no está

                w_CVsostenida_kNpm = w_CV_kNpm_def * (porc_CV_sost_def / 100.0)
                w_TotalSostenida_kNpm = w_CM_kNpm_def + w_CVsostenida_kNpm
                w_total_servicio_kNpm = w_CM_kNpm_def + w_CV_kNpm_def

                if tipo_apoyo_def == 'simples' or tipo_apoyo_def == 'empotrado_apoyado': 
                    Ma_kNm = (w_total_servicio_kNpm * (cm_to_m(L_libre_cm_def)**2)) / 8.0
                elif tipo_apoyo_def == 'empotrado_empotrado': 
                    Ma_kNm = (w_total_servicio_kNpm * (cm_to_m(L_libre_cm_def)**2)) / 12.0
                elif tipo_apoyo_def == 'voladizo': 
                    Ma_kNm = (w_total_servicio_kNpm * (cm_to_m(L_libre_cm_def)**2)) / 2.0
                else: Ma_kNm = 0

                Mcr_kNm, fisurada = calcular_Mcr_y_estado_fisuracion(Ma_kNm, fc_def, Ig_val, yt_val)
                I_efectiva_mm4 = Ig_val
                msg_Ie = f"$M_a \leq M_{{cr}}$. Sección no fisurada. Usando $I_e = I_g = {Ig_val:,.0f} mm^4$."
                if fisurada:
                    if Icr_manual_mm4_def > 0:
                        I_efectiva_mm4 = calcular_inercia_efectiva_Ie(Mcr_kNm, Ma_kNm, Ig_val, Icr_manual_mm4_def)
                        msg_Ie = f"$M_a > M_{{cr}}$. Sección fisurada. Usando $I_{{cr}}$ provisto para $I_e = {I_efectiva_mm4:,.0f} mm^4$."
                    else:
                        factor_aprox_Ie = 0.25 if "losa" in tipo_elemento_def.lower() or "nervio" in tipo_elemento_def.lower() else 0.35
                        I_efectiva_mm4 = factor_aprox_Ie * Ig_val
                        msg_Ie = f"$M_a > M_{{cr}}$. Sección fisurada. $I_{{cr}}$ no provisto. Usando $I_e \approx {factor_aprox_Ie} \cdot I_g = {I_efectiva_mm4:,.0f} mm^4$."
                
                delta_inst_CM = calcular_deflexion_instantanea(L_libre_cm_def, w_CM_kNpm_def, Ec_MPa, I_efectiva_mm4, tipo_apoyo_def)
                delta_inst_CV_total = calcular_deflexion_instantanea(L_libre_cm_def, w_CV_kNpm_def, Ec_MPa, I_efectiva_mm4, tipo_apoyo_def)
                delta_inst_CV_sostenida = calcular_deflexion_instantanea(L_libre_cm_def, w_CVsostenida_kNpm, Ec_MPa, I_efectiva_mm4, tipo_apoyo_def)
                delta_inst_total_sostenida = calcular_deflexion_instantanea(L_libre_cm_def, w_TotalSostenida_kNpm, Ec_MPa, I_efectiva_mm4, tipo_apoyo_def)
                
                b_calc_rho_prima_cm = b_eff_calc_cm if es_T_secc_def else b_elem_cm_def
                d_calc_rho_prima_mm = cm_to_mm(h_elem_cm_def) - y_centroide_sup_mm_val # d al acero inferior
                
                rho_prima_comp_val = 0.0
                if As_comp_cm2_def > 0 and b_calc_rho_prima_cm > 0 and d_calc_rho_prima_mm > 0:
                     rho_prima_comp_val = (As_comp_cm2_def * 100) / (cm_to_mm(b_calc_rho_prima_cm) * d_calc_rho_prima_mm) # As_cm2 * 100 = As_mm2
                
                delta_adicional_LP = calcular_deflexion_largo_plazo(delta_inst_total_sostenida, xi_factor_def, rho_prima_comp_val)
                delta_total_LP_sostenida = delta_inst_total_sostenida + delta_adicional_LP
                delta_inst_CV_no_sostenida = delta_inst_CV_total - delta_inst_CV_sostenida
                delta_verif_susceptible = delta_adicional_LP + delta_inst_CV_no_sostenida
                
                st.session_state.resultados_deflexion_actual = {
                    "Ma_kNm": Ma_kNm, "Mcr_kNm": Mcr_kNm, "msg_Ie": msg_Ie, "fisurada": fisurada,
                    "delta_inst_CM": delta_inst_CM, "delta_inst_CV_total": delta_inst_CV_total,
                    "delta_inst_total_sostenida": delta_inst_total_sostenida,
                    "delta_adicional_LP": delta_adicional_LP, "delta_total_LP_sostenida": delta_total_LP_sostenida,
                    "delta_verif_susceptible": delta_verif_susceptible, 
                    "id_elemento": id_elemento_deflex_reporte, "tipo_elemento": tipo_elemento_def,
                    "L_libre_cm": L_libre_cm_def, "Ec_MPa": Ec_MPa, "Ig_mm4": Ig_val, "yt_mm": yt_val,
                    "Ie_mm4": I_efectiva_mm4, "w_CM_kNpm": w_CM_kNpm_def, "w_CV_kNpm": w_CV_kNpm_def,
                    "w_CVsostenida_kNpm": w_CVsostenida_kNpm, "xi_factor": xi_factor_def, "rho_prima": rho_prima_comp_val
                }
                st.session_state.calculo_deflexion_realizado = True
                st.success(f"Cálculo de deflexiones para '{id_elemento_deflex_reporte}' completado.")


    with col2_def:
        st.subheader("2. Resultados del Análisis de Deflexión")
        
        # ESTE ES EL BLOQUE CONDICIONAL IMPORTANTE
        if st.session_state.get("calculo_deflexion_realizado", False) and "resultados_deflexion_actual" in st.session_state:
            res_def = st.session_state.resultados_deflexion_actual # res_def se define AQUÍ
            
            st.markdown(f"**Elemento:** {res_def['id_elemento']} ({res_def['tipo_elemento']})")
            st.markdown(f"**$M_a$ (CM+CV):** {res_def['Ma_kNm']:.2f} kNm, **$M_{{cr}}$:** {res_def['Mcr_kNm']:.2f} kNm")
            st.info(res_def['msg_Ie'])
            
            st.markdown("##### Deflexiones Calculadas (mm):")
            col_delta1, col_delta2 = st.columns(2)
            with col_delta1:
                st.metric("δ inst. CM", f"{res_def['delta_inst_CM']:.3f}")
                st.metric("δ inst. CV Total", f"{res_def['delta_inst_CV_total']:.3f}")
                st.metric("δ inst. Carga Sostenida", f"{res_def['delta_inst_total_sostenida']:.3f}")
            with col_delta2:
                st.metric("δ adicional Largo Plazo", f"{res_def['delta_adicional_LP']:.3f}")
                st.metric("δ Total Largo Plazo (Sost.)", f"{res_def['delta_total_LP_sostenida']:.3f}")
                st.metric("δ a Verificar (Susceptibles)", f"{res_def['delta_verif_susceptible']:.3f}")

            st.markdown("##### Verificación de Límites (NSR-10 Tabla C.9-1):")
            
            opciones_cond_limite = {
                "Elementos susceptibles a fisuración (ej. mampostería) - L/480": 'Total_diferida_susceptible_a_fisuracion',
                "Elementos NO susceptibles a fisuración (ej. acabados flexibles) - L/240": 'Total_diferida_no_susceptible_a_fisuracion'
            }
            cond_lim_sel_descripcion = st.selectbox(
                "Condición de Elementos No Estructurales para Límite Diferido:",
                list(opciones_cond_limite.keys()), 
                key="cond_no_est_def_v4" 
            )
            cond_dif = opciones_cond_limite[cond_lim_sel_descripcion]
            
            # Estas variables ahora se obtienen de res_def que está definido en este bloque
            tipo_elemento_para_verif = res_def["tipo_elemento"]
            L_libre_para_verif = res_def["L_libre_cm"]
            delta_cv_total_para_verif = res_def["delta_inst_CV_total"]
            delta_verif_susc_para_verif = res_def["delta_verif_susceptible"]

            cond_cv_inm = 'CV_inmediata_no_susceptible' 
            cumple_cv, lim_cv, n_cv = verificar_limites_deflexion_nsr10(
                delta_cv_total_para_verif, L_libre_para_verif, tipo_elemento_para_verif, cond_cv_inm
            )
            st.write(f"**Def. Inmediata por CV Total vs. L/{n_cv}**: {delta_cv_total_para_verif:.3f} mm {'✅ Cumple' if cumple_cv else '❌ NO Cumple'} (Límite: {lim_cv:.3f} mm)")
            
            cumple_dif, lim_dif, n_dif = verificar_limites_deflexion_nsr10(
                delta_verif_susc_para_verif, L_libre_para_verif, tipo_elemento_para_verif, cond_dif
            )
            st.write(f"**Def. Diferida (LP + CVnoSost) vs. L/{n_dif}**: {delta_verif_susc_para_verif:.3f} mm {'✅ Cumple' if cumple_dif else '❌ NO Cumple'} (Límite: {lim_dif:.3f} mm)")

            # --- Guardar datos para el reporte ---
            datos_deflex_reporte = {
                "ID Elemento": res_def.get("id_elemento"), "Tipo Elemento": res_def.get("tipo_elemento"),
                "Luz Libre Ln (cm)": res_def.get("L_libre_cm"), "Ec (MPa)": res_def.get("Ec_MPa"),
                "Ig (mm⁴)": res_def.get("Ig_mm4"), "yt (mm)": res_def.get("yt_mm"),
                "Mcr (kNm)": res_def.get("Mcr_kNm"), "Ma (kNm)": res_def.get("Ma_kNm"),
                "Ie (mm⁴)": res_def.get("Ie_mm4"), "w_CM (kN/m)": res_def.get("w_CM_kNpm"),
                "w_CV_total (kN/m)": res_def.get("w_CV_kNpm"), "w_CV_sost (kN/m)": res_def.get("w_CVsostenida_kNpm"),
                "Δ inst CM (mm)": res_def.get("delta_inst_CM"), "Δ inst CVtot (mm)": res_def.get("delta_inst_CV_total"),
                "Δ inst Sost (mm)": res_def.get("delta_inst_total_sostenida"), "Δ adic LP (mm)": res_def.get("delta_adicional_LP"),
                "Δ verif susc (mm)": res_def.get("delta_verif_susceptible"),
                "Límite CV (L/n)": f"L/{n_cv} ({lim_cv:.2f} mm)" if n_cv is not None else 'N/A',
                "Cumple CV": "Sí" if 'cumple_cv' in locals() and cumple_cv else ("No" if 'cumple_cv' in locals() else "N/A"),
                "Límite Dif. (L/n)": f"L/{n_dif} ({lim_dif:.2f} mm)" if n_dif is not None else 'N/A',
                "Cumple Dif.": "Sí" if 'cumple_dif' in locals() and cumple_dif else ("No" if 'cumple_dif' in locals() else "N/A"),
            }
            
            # Lógica para añadir o actualizar en la lista del reporte
            elemento_encontrado = False
            for i, item in enumerate(st.session_state.lista_deflexiones_reporte):
                if item["ID Elemento"] == res_def.get("id_elemento"):
                    st.session_state.lista_deflexiones_reporte[i] = datos_deflex_reporte
                    elemento_encontrado = True
                    st.info(f"Resultados de deflexión para '{res_def.get('id_elemento')}' actualizados en el reporte.")
                    break
            if not elemento_encontrado:
                st.session_state.lista_deflexiones_reporte.append(datos_deflex_reporte)
                st.info(f"Resultados de deflexión para '{res_def.get('id_elemento')}' añadidos al reporte.")
        
        else: # Si no se ha realizado el cálculo
            st.info("⬅️ Ingrese los datos en la columna izquierda y presione 'Calcular y Verificar Deflexiones' para ver los resultados.")



# ===============================================================================
# MÓDULO: COMBINACIONES DE CARGA
# ===============================================================================
elif modulo == "Combinaciones de Carga":
    st.header("Generación de Combinaciones de Carga (NSR-10)")

    col_cb1, col_cb2 = st.columns(2)
    with col_cb1:
        incluir_sismo_cb = st.checkbox("¿Incluir combinaciones sísmicas?", value=True, key="sismo_cb_v2")
        
        # Parámetros para factor L en sismo y sismo vertical
        # (Tomar f1 de un input o asumir residencial)
        f1_L_options = {"Residencial (L<5kPa) -> f1=0.5": 0.5, 
                        "Uso Público/Almacenamiento (L>=5kPa) -> f1=1.0": 1.0}
        f1_L_desc = st.selectbox("Condición para factor $f_1$ de Carga Viva (L) en sismo:", 
                                 list(f1_L_options.keys()), index=0, key="f1L_cb")
        f1_L_valor = f1_L_options[f1_L_desc]
        
        incluir_Ev_cb = st.checkbox("¿Incluir efecto de Sismo Vertical (Ev)?", value=False, key="ev_cb")
        
        # Aa y Fa se toman de los parámetros globales si se incluye Ev
        Aa_para_Ev = PG.get('Aa', 0.0) if incluir_Ev_cb else 0.0
        Fa_para_Ev = PG.get('Fa', 1.0) if incluir_Ev_cb else 1.0 # Fa no puede ser 0
        if incluir_Ev_cb:
            st.info(f"Para Sismo Vertical (Ev), se usarán: Aa={Aa_para_Ev}, Fa={Fa_para_Ev} (de config. global)")


    # Botón de generar se puede poner fuera de las columnas
    if st.button("🔄 Generar Combinaciones", key="btn_gen_comb_v2"):
        try:
            combinaciones = generar_combinaciones_carga(
                incluir_sismo=incluir_sismo_cb,
                f1_L_sismica=f1_L_valor,
                incluir_sismo_vertical=incluir_Ev_cb,
                Aa=Aa_para_Ev, # Se pasa Aa de parámetros globales
                Fa=Fa_para_Ev  # Se pasa Fa de parámetros globales
            )
            st.session_state['combinaciones_calculadas'] = combinaciones # Guardar para posible uso
            
            # Mostrar las combinaciones
            if 'combinaciones_calculadas' in st.session_state:
                st.subheader("Combinaciones de Servicio (NSR-10 B.2.3)")
                # Convertir a DataFrame para mejor visualización
                serv_data = []
                for nombre, factores in st.session_state['combinaciones_calculadas']["servicio"]:
                    serv_data.append({"Combinación": nombre, **factores})
                st.dataframe(pd.DataFrame(serv_data).fillna(0)) # Rellenar NaNs con 0 para mejor vista

                st.subheader("Combinaciones Últimas (NSR-10 B.2.4 / A.3.5)")
                ult_data = []
                for nombre, factores in st.session_state['combinaciones_calculadas']["ultimas"]:
                    ult_data.append({"Combinación": nombre, **factores})
                st.dataframe(pd.DataFrame(ult_data).fillna(0))

        except Exception as e:
            st.error(f"Error al generar combinaciones: {str(e)}")
    
    # Sección para aplicar a cargas base (como la tenías antes)
    if st.session_state.get('combinaciones_calculadas'):
        st.markdown("---")
        st.subheader("Aplicar a Cargas Base (Ejemplo)")
        cargas_base_col1, cargas_base_col2, cargas_base_col3 = st.columns(3)
        with cargas_base_col1:
            CM_base = st.number_input("CM (D) Base", value=100.0, step=10.0, key="cm_base_cb")
            CV_base = st.number_input("CV (L) Base", value=50.0, step=10.0, key="cv_base_cb")
        with cargas_base_col2:
            CV_cub_base = st.number_input("CV Cubierta (Lr) Base", value=10.0, step=5.0, key="cvlr_base_cb")
            Sismo_E_base = st.number_input("Sismo (E) Base", value=30.0, step=5.0, key="sismoE_base_cb")
        
        if st.button("📈 Aplicar Factores a Cargas Base", key="btn_aplicar_comb"):
            resultados_aplicados_servicio = []
            for nombre, factores in st.session_state['combinaciones_calculadas']["servicio"]:
                valor_comb = (factores.get("D", 0) * CM_base +
                              factores.get("L", 0) * CV_base +
                              factores.get("Lr", 0) * CV_cub_base)
                resultados_aplicados_servicio.append({"Combinación Servicio": nombre, "Valor Resultante": f"{valor_comb:.2f}"})
            
            resultados_aplicados_ultimas = []
            for nombre, factores in st.session_state['combinaciones_calculadas']["ultimas"]:
                valor_comb = (factores.get("D", 0) * CM_base +
                              factores.get("L", 0) * CV_base +
                              factores.get("Lr", 0) * CV_cub_base +
                              factores.get("E", 0) * Sismo_E_base) # Asume E es solo una dirección
                resultados_aplicados_ultimas.append({"Combinación Última": nombre, "Valor Resultante": f"{valor_comb:.2f}"})

            st.write("##### Cargas de Servicio Aplicadas:")
            st.dataframe(pd.DataFrame(resultados_aplicados_servicio))
            st.write("##### Cargas Últimas Aplicadas:")
            st.dataframe(pd.DataFrame(resultados_aplicados_ultimas))

elif modulo == "Diseño de Losas Macizas":
    st.header("Diseño de Losas Macizas Unidireccionales")
    
    fc_losas = PG['fc_losas_vigas_MPa'] # Corrección: PG['fc_losas_vigas_MPa'] o el nombre correcto de tu clave global
    fy_losas = PG['fy_MPa']
    st.info(f"Usando Materiales Globales: f'c = {fc_losas} MPa, f'y = {fy_losas} MPa")
    
    with st.form("form_losa_maciza"):
        id_losa_reporte = st.text_input("ID Losa para Reporte (ej: Losa N2 Tipo 1)", key="id_losa_rep")
        st.markdown("##### Geometría y Cargas")
        col_losa1, col_losa2, col_losa3 = st.columns(3)
        with col_losa1:
            h_losa_cm_input = st.number_input("Espesor de la losa (h, cm)", min_value=10.0, value=15.0, step=1.0, key="h_losa_cm_input")
        with col_losa2:
            Mu_losa_kNm_input = st.number_input("Momento Último por metro ($M_u$, kNm/m)", min_value=0.0, value=15.0, step=1.0, key="Mu_losa_kNm_input") # Permitir Mu=0
        with col_losa3:
            rec_libre_losa_cm_input = st.number_input("Recubrimiento libre (cm)", min_value=2.0, value=2.5, step=0.5, key="rec_libre_losa_cm_input")

        st.markdown("##### Diámetro de Barra a Utilizar")
        diam_barra_losa_mm_input = st.selectbox("Diámetro de barra principal (mm)", [9.5, 12.7, 15.9], index=1, key="diam_barra_losa_mm_input")

        submitted_losa = st.form_submit_button("🔨 Diseñar Losa")

    if submitted_losa:
        if not id_losa_reporte.strip():
            st.error("Por favor, ingrese un ID para la losa.")
        else:
            try:
                resultados_losa = diseno_losa_maciza_unidireccional(
                    h_losa_cm=h_losa_cm_input, 
                    fc_MPa=fc_losas, 
                    fy_MPa=fy_losas,
                    rec_libre_cm=rec_libre_losa_cm_input, 
                    Mu_kNm_por_m=Mu_losa_kNm_input,
                    diam_barra_ppal_mm=diam_barra_losa_mm_input
                )
                
                # Guardar para posible reporte (opcional)
                # if 'resultados_losas_para_excel' not in st.session_state:
                #     st.session_state.resultados_losas_para_excel = []
                # st.session_state.resultados_losas_para_excel.append(resultados_losa)

                if resultados_losa["status"] == "OK":
                    st.success(resultados_losa.get("mensaje", "Diseño de Losa completado."))
                    st.info(resultados_losa['mensaje_espesor'])

                    st.markdown("##### Resultados del Refuerzo")
                    col_res_losa1, col_res_losa2 = st.columns(2)
                    with col_res_losa1:
                        st.markdown("###### Acero Principal")
                        st.metric(f"As requerido", f"{resultados_losa['As_req_ppal_cm2_por_m']} cm²/m")
                        # CORRECCIÓN AQUÍ:
                        st.success(f"Usar barra Ø{resultados_losa['diam_barra_ppal_usada_mm']} mm @ **{resultados_losa['espaciamiento_ppal_cm']} cm**")
                    with col_res_losa2:
                        st.markdown("###### Acero de Repartición y Temperatura")
                        st.metric(f"As requerido", f"{resultados_losa['As_req_temp_cm2_por_m']} cm²/m")
                        # CORRECCIÓN AQUÍ:
                        st.success(f"Usar barra Ø{resultados_losa['diam_barra_temp_usada_mm']} mm @ **{resultados_losa['espaciamiento_temp_cm']} cm**")
                    
                    with st.expander("Ver detalles completos del cálculo de la losa"):
                        st.json(resultados_losa)

                    # --- Guardar datos para el reporte ---
                    datos_losa_reporte = {
                        "ID Losa": id_losa_reporte,
                        "h (cm)": h_losa_cm_input,
                        "f'c (MPa)": fc_losas,
                        "fy (MPa)": fy_losas,
                        "Rec. Libre (cm)": rec_libre_losa_cm_input,
                        "Mu (kNm/m)": Mu_losa_kNm_input,
                        "d efectivo (cm)": resultados_losa.get('d_efectivo_ppal_cm', 'N/A'),
                        "As Ppal (cm²/m)": resultados_losa.get('As_req_ppal_cm2_por_m'),
                        "Ø Ppal (mm)": resultados_losa.get('diam_barra_ppal_usada_mm'),
                        "s Ppal (cm)": resultados_losa.get('espaciamiento_ppal_cm'),
                        "As Temp (cm²/m)": resultados_losa.get('As_req_temp_cm2_por_m'),
                        "Ø Temp (mm)": resultados_losa.get('diam_barra_temp_usada_mm'),
                        "s Temp (cm)": resultados_losa.get('espaciamiento_temp_cm'),
                        "Verif. Espesor": resultados_losa.get('mensaje_espesor')
                    }
                    st.session_state.lista_losas_macizas_reporte.append(datos_losa_reporte)
                    st.info(f"Resultados de losa maciza '{id_losa_reporte}' añadidos al reporte.")
                else:
                    # Mostrar el mensaje de error que viene de la función de diseño
                    st.error(f"Ocurrió un error en el diseño de la losa: {resultados_losa.get('mensaje', 'Error desconocido.')}")
                    # También puedes mostrar el diccionario completo de error para depurar
                    with st.expander("Detalles del error"):
                        st.json(resultados_losa)


            except Exception as e:
                st.error(f"Ocurrió un error inesperado en la aplicación al diseñar la losa: {e}")
                import traceback
                st.text(traceback.format_exc())

elif modulo == "Diseño de Escaleras":
    st.header("Diseño de Tramos de Escalera (Como Losa Inclinada)")

    fc_esc = PG['fc_losas_vigas_MPa'] # Usar f'c para losas
    fy_esc = PG['fy_MPa']
    st.info(f"Usando Materiales Globales: f'c = {fc_esc} MPa, f'y = {fy_esc} MPa")

    with st.form("form_escalera_diseno"):
        id_escalera_reporte = st.text_input("ID Tramo Escalera para Reporte (ej: Escalera1)", key="id_esc_rep")
        st.markdown("##### Geometría del Tramo de Escalera")
        col_geom_esc1, col_geom_esc2, col_geom_esc3 = st.columns(3)
        with col_geom_esc1:
            huella_cm_esc = st.number_input("Huella (cm)", min_value=25.0, value=28.0, step=0.5, help="Ancho del paso horizontal.")
        with col_geom_esc2:
            contrahuella_cm_esc = st.number_input("Contrahuella (cm)", min_value=15.0, value=17.5, step=0.5, help="Altura vertical del paso.")
        with col_geom_esc3:
            num_pasos_esc = st.number_input("Número de pasos en el tramo", min_value=3, value=10, step=1)

        col_geom_esc4, col_geom_esc5 = st.columns(2)
        with col_geom_esc4:
            ancho_tramo_m_esc = st.number_input("Ancho del tramo (m)", min_value=0.8, value=1.2, step=0.1)
        with col_geom_esc5:
            espesor_garganta_cm_esc = st.number_input("Espesor garganta losa (cm)", min_value=10.0, value=15.0, step=1.0, help="Espesor de la parte estructural inclinada.")

        st.markdown("##### Cargas de Diseño (sobre área proyectada horizontal)")
        col_cargas_esc1, col_cargas_esc2 = st.columns(2)
        with col_cargas_esc1:
            cm_adic_kNm2_esc = st.number_input("CM Adicional (acabados, etc.) (kN/m²)", min_value=0.0, value=1.0, step=0.1)
        with col_cargas_esc2:
            cv_kNm2_esc = st.number_input("CV (kN/m²)", min_value=2.0, value=3.0, step=0.1, help="NSR-10 B.4.2.1-1: Escaleras y corredores de evacuación para ocupación residencial: 3.0 kN/m²") # Residencial general es 1.8, pero escaleras suelen ser más.

        st.markdown("##### Refuerzo")
        col_ref_esc1, col_ref_esc2 = st.columns(2)
        with col_ref_esc1:
            rec_libre_cm_esc = st.number_input("Recubrimiento libre (cm)", min_value=2.0, value=2.5, step=0.5)
        with col_ref_esc2:
            diam_barra_ppal_esc_mm = st.selectbox("Diámetro barra principal (mm)", [9.5, 12.7, 15.9], index=1) # #4 (1/2")

        submitted_escalera = st.form_submit_button("🪜 Diseñar Tramo de Escalera")

    if submitted_escalera:
        if not id_escalera_reporte.strip(): # Reemplaza 'id_escalera_reporte' con la variable de tu input de ID
            st.error("Por favor, ingrese un ID para el tramo de escalera.")
        else:
            try:
                resultados_esc = diseno_tramo_escalera_losa_inclinada(
                    huella_cm=huella_cm_esc, contrahuella_cm=contrahuella_cm_esc, num_pasos=num_pasos_esc,
                    ancho_tramo_m=ancho_tramo_m_esc, espesor_losa_garganta_cm=espesor_garganta_cm_esc,
                    fc_MPa=fc_esc, fy_MPa=fy_esc,
                    carga_muerta_adic_kNm2=cm_adic_kNm2_esc, carga_viva_kNm2=cv_kNm2_esc,
                    rec_libre_cm=rec_libre_cm_esc, diam_barra_ppal_mm=diam_barra_ppal_esc_mm
                )

                if resultados_esc["status"] == "OK":
                    st.success("Diseño del tramo de escalera completado.")
                    
                    st.markdown("##### Geometría y Cargas Calculadas")
                    col_info_esc1, col_info_esc2 = st.columns(2)
                    with col_info_esc1:
                        st.metric("Longitud Horizontal Tramo", f"{resultados_esc['long_horiz_tramo_m']:.2f} m")
                        st.metric("Altura Total Tramo", f"{resultados_esc['altura_total_tramo_m']:.2f} m")
                        st.metric("Ángulo de Inclinación", f"{resultados_esc['angulo_grados']:.1f}°")
                    with col_info_esc2:
                        st.metric("Carga Última de Diseño ($w_u$)", f"{resultados_esc['carga_ultima_wu_kNm_por_m_proy']:.2f} kN/m (por metro de ancho)")
                        st.metric("Momento Último de Diseño ($M_u$)", f"{resultados_esc['momento_ultimo_Mu_kNm_por_m']:.2f} kNm (por metro de ancho)")
                    
                    st.info(f"Peralte efectivo 'd' calculado: {resultados_esc['d_efectivo_cm']:.1f} cm")

                    st.markdown("##### Refuerzo Requerido (por metro de ancho)")
                    ac_ppal = resultados_esc['acero_principal']
                    ac_temp = resultados_esc['acero_reparticion']

                    col_ref_res1, col_ref_res2 = st.columns(2)
                    with col_ref_res1:
                        st.markdown(f"**Acero Principal (Longitudinal al tramo):**")
                        st.write(f"  $A_s$ requerida: {ac_ppal['As_req_cm2_por_m']} cm²/m")
                        st.success(f"  Usar Ø{ac_ppal['diam_barra_mm']} mm @ **{ac_ppal['espaciamiento_cm']} cm**")
                    with col_ref_res2:
                        st.markdown(f"**Acero de Repartición (Transversal al tramo):**")
                        st.write(f"  $A_s$ requerida: {ac_temp['As_req_cm2_por_m']} cm²/m")
                        st.success(f"  Usar Ø{ac_temp['diam_barra_mm']} mm @ **{ac_temp['espaciamiento_cm']} cm**")
                    
                    st.warning(resultados_esc['verificacion_espesor'])

                    # Guardar para reporte (ejemplo)
                    ac_ppal_esc = resultados_esc.get('acero_principal', {})
                    ac_temp_esc = resultados_esc.get('acero_reparticion', {})
                    datos_escalera_reporte = {
                        "ID Tramo": id_escalera_reporte, # Reemplaza con tu variable de ID
                        "L_horiz (m)": resultados_esc.get('long_horiz_tramo_m'),
                        "h_garganta (cm)": espesor_garganta_cm_esc, # El input usado
                        "Ángulo (°)": resultados_esc.get('angulo_grados'),
                        "wu (kN/m)": resultados_esc.get('carga_ultima_wu_kNm_por_m_proy'),
                        "Mu (kNm/m)": resultados_esc.get('momento_ultimo_Mu_kNm_por_m'),
                        "d (cm)": resultados_esc.get('d_efectivo_cm'),
                        "As Ppal (cm²/m)": ac_ppal_esc.get('As_req_cm2_por_m'),
                        "Ref. Ppal": f"Ø{ac_ppal_esc.get('diam_barra_mm')}@{ac_ppal_esc.get('espaciamiento_cm')}cm",
                        "As Temp (cm²/m)": ac_temp_esc.get('As_req_cm2_por_m'),
                        "Ref. Temp.": f"Ø{ac_temp_esc.get('diam_barra_mm')}@{ac_temp_esc.get('espaciamiento_cm')}cm",
                        "Verif. Espesor": resultados_esc.get('verificacion_espesor')
                    }
                    st.session_state.lista_escaleras_reporte.append(datos_escalera_reporte)
                    st.info(f"Resultados del tramo de escalera '{id_escalera_reporte}' añadidos al reporte.")


                else: # Si hubo error
                    st.error(f"Error en el diseño de la escalera: {resultados_esc['mensaje']}")
                
                with st.expander("Ver todos los resultados del cálculo"):
                    st.json(resultados_esc)

            except Exception as e:
                st.error(f"Ocurrió un error inesperado en la aplicación al diseñar la escalera: {e}")
                import traceback
                st.text(traceback.format_exc())

# ===============================================================================
# MÓDULO: GENERAR MEMORIA EXCEL (Placeholder)
# ===============================================================================
elif modulo == "Generar Memoria Excel (WIP)":
    st.header("📋 Generar Memoria de Cálculo en Excel")
    st.warning("Funcionalidad en desarrollo (Work In Progress).")
    st.info("Esta sección recopilará los resultados de los módulos de diseño (Vigas, Columnas, Zapatas, etc.) almacenados durante la sesión y los exportará a un archivo Excel.")
    
    if st.button("📄 Generar Reporte Excel", key="btn_gen_excel_report"):
        if not PG: # PG = st.session_state.parametros_globales
             st.error("Configure primero los parámetros globales del proyecto.")
        else:
            # --- 1. Recopilar TODOS los datos necesarios de st.session_state ---
            datos_memoria_final = {
                "info_proyecto": {
                    "nombre_proyecto": PG.get('nombre_proyecto', 'Proyecto Sin Nombre'),
                    "localizacion": PG.get('localizacion', 'Pereira'),
                    "fecha": st.session_state.current_date,
                    "normativa_principal": "NSR-10 Colombia", # Clave más específica
                    "ingenieros_responsables": "Nombres del Grupo" # Clave más específica
                },
                "parametros_globales": PG, # f'c, fy, Aa, Av, Fa, Fv, R0, I_coef, q_adm, etc.
                
                "info_cargas_criterios": st.session_state.get('info_cargas_criterios_reporte', {}),
                "info_irregularidades": st.session_state.get('info_irregularidades_reporte', { # Pasar los phi_A, phi_P actuales
                    "phi_A_usado": st.session_state.get('phi_A_calculado', 1.0),
                    "phi_P_usado": st.session_state.get('phi_P_calculado', 1.0),
                }),

                "espectro_calculado_data": st.session_state.get('espectro_calculado_data'),
                # Asegúrate que estos se guardan en session_state desde el módulo de Análisis Sísmico
                "resultados_fhe": st.session_state.get('resultados_fhe'),
                "peso_sismico_total_usado_para_fhe": st.session_state.get('peso_total_sismico_usado_fhe'),
                "Ta_calculado_para_fhe": st.session_state.get('Ta_calculado'),
                "Sa_Ta_usado_para_fhe": st.session_state.get('Sa_Ta_usado_fhe'),
                "R_final_usado_espectro": PG.get('R0', 5.0) * st.session_state.get('phi_A_calculado', 1.0) * st.session_state.get('phi_P_calculado', 1.0),

                # Listas de resultados de diseño
                "vigas_disenadas": st.session_state.get('lista_vigas_reporte', []),
                "columnas_flexion_disenadas": st.session_state.get('lista_columnas_flex_reporte', []),
                "columnas_cortante_disenadas": st.session_state.get('lista_columnas_cort_reporte', []),
                "zapatas_disenadas": st.session_state.get('lista_zapatas_reporte', []),
                "losas_macizas_disenadas": st.session_state.get('lista_losas_macizas_reporte', []),
                "nervios_disenados": st.session_state.get('lista_nervios_reporte', []),
                "escaleras_disenadas": st.session_state.get('lista_escaleras_reporte', []),
                "deflexiones_verificadas": st.session_state.get('lista_deflexiones_reporte', []),
                
                "combinaciones_usadas": st.session_state.get('combinaciones_calculadas')
            }

            # Generar y guardar la imagen del espectro si existe
            if datos_memoria_final["espectro_calculado_data"]:
                try:
                    data_esp_rep = datos_memoria_final["espectro_calculado_data"]
                    fig_esp_rep = graficar_espectro(
                        T=data_esp_rep['T'], Sa=data_esp_rep['Sa'], 
                        info_periodos=data_esp_rep['info_periodos'],
                        titulo=f"Espectro NSR-10 ({data_esp_rep['tipo'].capitalize()})",
                        R_val=data_esp_rep['R_usado'], I_val=data_esp_rep['I_usado']
                    )
                    fig_esp_rep.savefig("espectro_plot_temp.png", dpi=200) # Guardar con buena resolución
                    plt.close(fig_esp_rep) # Cerrar la figura para liberar memoria
                    datos_memoria_final["path_imagen_espectro"] = "espectro_plot_temp.png"
                except Exception as e_img:
                    st.warning(f"No se pudo generar la imagen del espectro para el reporte: {e_img}")
                    datos_memoria_final["path_imagen_espectro"] = None
            else:
                datos_memoria_final["path_imagen_espectro"] = None
            
            # Limpiar datos None para evitar problemas con Pandas o Openpyxl
            # (Esto es opcional, _escribir_dataframe_a_hoja ya maneja pd.notna)
            # for key, value in datos_memoria_final.items():
            #     if isinstance(value, list):
            #         for item_dict in value:
            #             if isinstance(item_dict, dict):
            #                 for k_dict, v_dict in item_dict.items():
            #                     if v_dict is None: item_dict[k_dict] = "N/A"
            #     elif isinstance(value, dict):
            #          for k_dict, v_dict in value.items():
            #              if v_dict is None: value[k_dict] = "N/A"


            # --- 2. Llamar a la función de generación del reporte ---
            try:
                # from calculosh.reportes import generar_memoria_excel # Ya debería estar importada al inicio de app2.py
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                nombre_archivo_excel = f"MemoriaCalculo_{datos_memoria_final['info_proyecto']['nombre_proyecto'].replace(' ','_')}_{timestamp}.xlsx"
                
                st.info(f"Generando memoria en '{nombre_archivo_excel}'...")
                mensaje_gen = generar_memoria_excel(datos_memoria_final, nombre_archivo_excel)
                
                if "exitosamente" in mensaje_gen.lower():
                    st.success(mensaje_gen)
                    # --- 3. Ofrecer Descarga ---
                    if os.path.exists(nombre_archivo_excel):
                        with open(nombre_archivo_excel, "rb") as fp:
                            st.download_button(
                                label="📥 Descargar Memoria Excel",
                                data=fp,
                                file_name=nombre_archivo_excel,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.error("El archivo de memoria no se encontró después de intentar generarlo.")
                else:
                    st.error(f"Error durante la generación: {mensaje_gen}")

            except ImportError:
                st.error("El módulo 'calculosh/reportes.py' o la función 'generar_memoria_excel' no se pudieron importar correctamente.")
            except Exception as e:
                st.error(f"Error inesperado al intentar generar el reporte Excel: {e}")
                # import traceback
                # st.text(traceback.format_exc()) # Para depuración avanzada


# ===============================================================================
# FIN DE LOS MÓDULOS
# ===============================================================================

st.sidebar.divider()
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Proyecto:** {PG.get('nombre_proyecto', 'No definido')}")
st.sidebar.markdown(f"**Norma:** NSR-10 Colombia")
st.sidebar.markdown(f"**Fecha:** {st.session_state.current_date}")