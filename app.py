import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import os
from calculosh.espectro import obtener_Fa_Fv_NSR10
from ui_modules import (
    ui_analisis_sismico, 
    ui_vigas, 
    ui_columnas, 
    ui_zapatas,
    ui_losas_macizas,
    ui_losas_nervadas,
    ui_escaleras,
    ui_deflexiones,
    ui_combinaciones,
    ui_reportes 
)


class ConstantesNSRPlaceholder: 
    DIAMETRO_ESTRIBO_TIPICO_MM = 9.5
    DIAMETRO_BARRA_LONG_TIPICO_MM = 15.9
       



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
    ui_analisis_sismico.mostrar_interfaz_analisis_sismico(PG, st.session_state)

# ===============================================================================
# MÓDULO: DISEÑO DE VIGAS
# ===============================================================================
elif modulo == "Diseño de Vigas":
    ui_vigas.mostrar_interfaz_vigas(PG, st.session_state)

# ===============================================================================
# MÓDULO: DISEÑO DE COLUMNAS
# ===============================================================================
elif modulo == "Diseño de Columnas":
    ui_columnas.mostrar_interfaz_columnas(PG, st.session_state)


# ===============================================================================
# MÓDULO: DISEÑO DE ZAPATAS
# ===============================================================================
elif modulo == "Diseño de Zapatas":
    ui_zapatas.mostrar_interfaz_zapatas(PG, st.session_state)

# ===============================================================================
# MÓDULO: DISEÑO DE LOSA NERVADA 
# ===============================================================================
elif modulo == "Diseño de Losa Nervada":
    ui_losas_nervadas.mostrar_interfaz_losas_nervadas(PG, st.session_state)


# ===============================================================================
# MÓDULO: CÁLCULO DE DEFLEXIONES
# ===============================================================================
elif modulo == "Cálculo de Deflexiones":
    ui_deflexiones.mostrar_interfaz_deflexiones(PG, st.session_state)


# ===============================================================================
# MÓDULO: COMBINACIONES DE CARGA
# ===============================================================================
elif modulo == "Combinaciones de Carga":
    ui_combinaciones.mostrar_interfaz_combinaciones(PG, st.session_state)

elif modulo == "Diseño de Losas Macizas":
    ui_losas_macizas.mostrar_interfaz_losas_macizas(PG, st.session_state)

elif modulo == "Diseño de Escaleras":
    ui_escaleras.mostrar_interfaz_escaleras(PG, st.session_state)

# ===============================================================================
# MÓDULO: GENERAR MEMORIA EXCEL (Placeholder)
# ===============================================================================
elif modulo == "Generar Memoria Excel (WIP)":
    ui_reportes.mostrar_interfaz_reportes(PG, st.session_state)
    


# ===============================================================================
# FIN DE LOS MÓDULOS
# ===============================================================================

st.sidebar.divider()
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Proyecto:** {PG.get('nombre_proyecto', 'No definido')}")
st.sidebar.markdown(f"**Norma:** NSR-10 Colombia")
st.sidebar.markdown(f"**Fecha:** {st.session_state.current_date}")