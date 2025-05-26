# ==============================================================================
# DISEÑO DE COLUMNA POR CORTANTE Y CONFINAMIENTO (DMO - NSR-10 C.21)
# ==============================================================================
import numpy as np
from unidades import *
from validate_positive import validate_positive

PHI_CORTANTE_COL = 0.75

def diseno_columna_cortante_dmo(
    # Geometría y Materiales
    b_col_cm, h_col_cm, fc_MPa, fy_MPa,
    # Cargas y Solicitaciones
    Pu_kN, Vu_analisis_kN,
    # Parámetros para Diseño por Capacidad (Cortante Probable)
    Mn_viga_izq_kNm, Mn_viga_der_kNm, L_libre_vigas_m,
    # Parámetros para Confinamiento
    rec_libre_mm, diam_estribo_mm, H_libre_col_m
):
    """
    Realiza el diseño de refuerzo transversal para columnas con capacidad de
    disipación de energía moderada (DMO) según NSR-10 C.21.

    Parámetros:
    - b_col_cm, h_col_cm: Dimensiones de la columna.
    - fc_MPa, fy_MPa: Resistencia de los materiales.
    - Pu_kN: Carga axial última mayorada sobre la columna.
    - Vu_analisis_kN: Fuerza cortante obtenida del análisis estructural.
    - Mn_viga_izq_kNm, Mn_viga_der_kNm: Momentos nominales de las vigas que llegan al nudo.
    - L_libre_vigas_m: Luz libre promedio de las vigas que llegan al nudo.
    - rec_libre_mm: Recubrimiento libre al estribo.
    - diam_estribo_mm: Diámetro del estribo a utilizar.
    - H_libre_col_m: Altura libre de la columna.
    """
    validate_positive(b_col_cm=b_col_cm, h_col_cm=h_col_cm, fc_MPa=fc_MPa, fy_MPa=fy_MPa, L_libre_vigas_m=L_libre_vigas_m, H_libre_col_m=H_libre_col_m)

    b_col_mm = cm_to_mm(b_col_cm)
    h_col_mm = cm_to_mm(h_col_cm)
    Ag_mm2 = b_col_mm * h_col_mm

    # --- 1. Diseño por Cortante (NSR-10 C.21.4.5) ---
    # a) Cortante probable (Ve) por formación de rótulas en vigas
    Mpr_vigas = 1.25 * (Mn_viga_izq_kNm + Mn_viga_der_kNm)  # Suma de momentos probables en el nudo
    Ve_capacidad_kN = Mpr_vigas / L_libre_vigas_m
    
    # b) Cortante de diseño (Vu)
    # Es el menor entre el del análisis y el de capacidad
    Vu_diseno_kN = min(Vu_analisis_kN, Ve_capacidad_kN)
    
    # c) Resistencia al cortante del concreto (Vc)
    # Vc se reduce o elimina si la ductilidad aumenta o la carga axial es baja (NSR-10 C.21.4.5.2)
    # Si Pu < 0.05 * Ag * f'c, Vc = 0
    Pu_limite_N = 0.05 * Ag_mm2 * fc_MPa
    if (Pu_kN * 1000) < Pu_limite_N:
        Vc_N = 0
        mensaje_vc = "Pu < 0.05*Ag*f'c, por lo tanto Vc = 0."
    else:
        Vc_N = 0.17 * np.sqrt(fc_MPa) * b_col_mm * h_col_mm # d se aproxima a h
        mensaje_vc = "Vc calculado con la fórmula estándar."

    Vc_kN = n_to_kn(Vc_N)

    # d) Cortante que debe tomar el acero (Vs)
    Vs_req_kN = (Vu_diseno_kN / PHI_CORTANTE_COL) - Vc_kN
    Vs_req_kN = max(0, Vs_req_kN) # No puede ser negativo
    
    # --- 2. Diseño por Confinamiento (NSR-10 C.21.4.4) ---
    # Longitud de la zona confinada (lo)
    lo = max(h_col_mm, b_col_mm, H_libre_col_m * 1000 / 6.0, 450.0)

    # Área del núcleo confinado (Ach) y dimensiones (bc, hc)
    bc_mm = b_col_mm - 2 * rec_libre_mm - diam_estribo_mm
    hc_mm = h_col_mm - 2 * rec_libre_mm - diam_estribo_mm
    Ach_mm2 = bc_mm * hc_mm
    
    # Área de refuerzo transversal requerida (Ash)
    # Se usan las ecuaciones C.21-1 y C.21-2
    Ash_s_req1 = 0.3 * (Ag_mm2 / Ach_mm2 - 1) * (fc_MPa / fy_MPa) * bc_mm
    Ash_s_req2 = 0.09 * (fc_MPa / fy_MPa) * bc_mm
    Ash_s_requerido_mm2_por_mm = max(Ash_s_req1, Ash_s_req2) # Ash/s en la dirección de 'h'

    # Espaciamiento en la zona confinada (so)
    s_max_confinado1 = min(bc_mm, hc_mm) / 4.0
    s_max_confinado2 = 6 * diam_estribo_mm # Asumiendo estribo es la barra long. de menor diam.
    s_max_confinado3 = 100 # mm
    s_confinado_max_mm = min(s_max_confinado1, s_max_confinado2, s_max_confinado3)
    
    # --- 3. Determinación del Espaciamiento Final ---
    # Área de un estribo (asumiendo 2 ramas + ramas intermedias si aplica)
    # Simplificación: se calcula para 1 estribo de 2 ramas
    num_ramas = 2 # Asumir 2 ramas para el cálculo
    A_estribo_mm2 = num_ramas * (np.pi * (diam_estribo_mm / 2)**2)
    
    s_por_confinamiento_mm = A_estribo_mm2 / Ash_s_requerido_mm2_por_mm if Ash_s_requerido_mm2_por_mm > 0 else float('inf')

    # El espaciamiento en la zona confinada debe ser el menor entre el requerido por confinamiento y el espaciamiento máximo
    s_final_confinado_mm = min(s_por_confinamiento_mm, s_confinado_max_mm)
    
    # Espaciamiento fuera de la zona confinada (NSR-10 C.7.10.5.6)
    s_fuera_confinado_mm = min(2 * s_final_confinado_mm, H_libre_col_m * 1000 / 2) # Simplificado

    return {
        "status": "OK",
        "Vu_diseno_kN": round(Vu_diseno_kN, 2),
        "Ve_capacidad_kN": round(Ve_capacidad_kN, 2),
        "Vc_kN": round(Vc_kN, 2),
        "mensaje_Vc": mensaje_vc,
        "Vs_req_kN": round(Vs_req_kN, 2),
        "longitud_confinamiento_lo_cm": round(mm_to_cm(lo), 1),
        "Ash_s_req_mm2_por_m": round(Ash_s_requerido_mm2_por_mm * 1000, 2),
        "s_max_confinado_mm": round(s_confinado_max_mm, 1),
        "s_final_confinado_mm": round(np.floor(s_final_confinado_mm / 10) * 10, 0), # Redondear a 10mm
        "s_fuera_confinado_mm": round(np.floor(s_fuera_confinado_mm / 10) * 10, 0),
        "diam_estribo_usado_mm": diam_estribo_mm
    }