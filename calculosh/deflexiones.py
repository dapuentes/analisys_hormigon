# ==============================================================================
# CÁLCULO DE DEFLEXIONES
# ==============================================================================
import numpy as np
from unidades import *
from validate_positive import validate_positive

LAMBDA_CONCRETO_DEF = 1.0 # Para concreto de peso normal

def momento_inercia_bruta_T_o_Rect(
    b_total_ala_cm, h_total_cm, # b_total_ala_cm es b_eff para T, o b para rectangular
    hf_loseta_cm, bw_alma_cm, # hf_loseta_cm y bw_alma_cm solo para sección T real
    es_seccion_T=True):
    """
    Calcula el momento de inercia bruto (Ig) y la distancia yt
    desde el eje neutro a la fibra extrema en tracción (para Mcr).
    Para M+, la fibra extrema en compresión está arriba.
    Retorna Ig (mm^4) y yt (mm).
    """
    validate_positive(b_total_ala_cm=b_total_ala_cm, h_total_cm=h_total_cm)
    if es_seccion_T:
        validate_positive(hf_loseta_cm=hf_loseta_cm, bw_alma_cm=bw_alma_cm)
        if hf_loseta_cm > h_total_cm:
            raise ValueError("Espesor de loseta (hf) no puede ser mayor a altura total (h).")

    b_eff_mm = cm_to_mm(b_total_ala_cm)
    h_mm = cm_to_mm(h_total_cm)
    
    if not es_seccion_T or hf_loseta_cm == h_total_cm: # Sección rectangular
        # Centroide desde la fibra superior (compresión para M+)
        y_centroide_mm = h_mm / 2.0
        Ig_mm4 = (b_eff_mm * h_mm**3) / 12.0
        # Para M+, la fibra extrema en tracción está abajo
        yt_mm = h_mm - y_centroide_mm
    else: # Sección T
        hf_mm = cm_to_mm(hf_loseta_cm)
        bw_mm = cm_to_mm(bw_alma_cm)

        # Áreas
        A_ala = b_eff_mm * hf_mm
        A_alma = bw_mm * (h_mm - hf_mm)
        A_total = A_ala + A_alma

        # Centroide y_barra desde la fibra superior (compresión para M+)
        y_centroide_ala = hf_mm / 2.0
        y_centroide_alma = hf_mm + (h_mm - hf_mm) / 2.0
        
        y_centroide_mm = (A_ala * y_centroide_ala + A_alma * y_centroide_alma) / A_total

        # Inercias respecto a sus propios centroides
        Ig_ala_propio = (b_eff_mm * hf_mm**3) / 12.0
        Ig_alma_propio = (bw_mm * (h_mm - hf_mm)**3) / 12.0

        # Teorema de Steiner (ejes paralelos)
        Ig_ala = Ig_ala_propio + A_ala * (y_centroide_mm - y_centroide_ala)**2
        Ig_alma = Ig_alma_propio + A_alma * (y_centroide_mm - y_centroide_alma)**2
        
        Ig_mm4 = Ig_ala + Ig_alma
        
        # Para M+, la fibra extrema en tracción está abajo
        yt_mm = h_mm - y_centroide_mm
        
    return Ig_mm4, yt_mm, y_centroide_mm


def calcular_Mcr_y_estado_fisuracion(
    Ma_kNm, # Momento máximo de servicio para el cual se calcula la deflexión
    fc_MPa, Ig_mm4, yt_mm # Ig y yt de la sección bruta
    ):
    """
    Calcula el momento de fisuración Mcr y determina si la sección está fisurada.
    Ma_kNm: Momento actuante de servicio (kN.m)
    fc_MPa: Resistencia del concreto (MPa)
    Ig_mm4: Inercia bruta de la sección (mm^4)
    yt_mm: Distancia del eje neutro a la fibra extrema en tracción (mm)

    Retorna: Mcr_kNm (float), fisurada (bool)
    """
    validate_positive(fc_MPa=fc_MPa, Ig_mm4=Ig_mm4, yt_mm=yt_mm)
    Ma_Nmm = knm_to_nmm(abs(Ma_kNm)) # Usar valor absoluto

    # Módulo de rotura fr (NSR-10 C.9.5.2.3, Ec. C.9-8)
    fr_MPa = 0.62 * LAMBDA_CONCRETO_DEF * np.sqrt(fc_MPa)
    
    # Momento de fisuración Mcr (NSR-10 C.9.5.2.3, Ec. C.9-7)
    Mcr_Nmm = (fr_MPa * Ig_mm4) / yt_mm if yt_mm > 0 else float('inf')
    Mcr_kNm = nmm_to_knm(Mcr_Nmm)
    
    fisurada = Ma_Nmm > Mcr_Nmm
    
    return Mcr_kNm, fisurada


def calcular_inercia_efectiva_Ie(
    Mcr_kNm, Ma_kNm, # Mcr y Ma deben estar en las mismas unidades
    Ig_mm4, Icr_mm4 # Icr es la inercia de la sección fisurada transformada
    ):
    """
    Calcula la inercia efectiva Ie según NSR-10 C.9.5.2.3 (Ec. C.9-6).
    """
    validate_positive(Ig_mm4=Ig_mm4, Icr_mm4=Icr_mm4)
    if Mcr_kNm <= 0 or Ma_kNm <= 0: # Ma puede ser 0
        return Ig_mm4 # No fisurada o sin momento

    Mcr_Ma_ratio = Mcr_kNm / Ma_kNm
    
    if Mcr_Ma_ratio >= 1.0: # No fisurada o Ma <= Mcr
        Ie_mm4 = Ig_mm4
    else: # Fisurada
        Ie_mm4 = (Mcr_Ma_ratio**3) * Ig_mm4 + (1.0 - Mcr_Ma_ratio**3) * Icr_mm4
    
    return min(Ie_mm4, Ig_mm4) # Ie no puede ser mayor que Ig


def calcular_deflexion_instantanea(
    L_cm, w_kNpm_servicio, # Carga de servicio NO mayorada (kN/m)
    Ec_MPa, I_efectiva_mm4, 
    tipo_apoyo='simples'):
    """
    Calcula la deflexión instantánea usando la I_efectiva.
    Trabajo interno: L→mm, w→N/mm, E→N/mm², I→mm⁴ → δ en mm.
    """
    validate_positive(L_cm=L_cm, Ec_MPa=Ec_MPa, I_efectiva_mm4=I_efectiva_mm4)
    if w_kNpm_servicio < 0: w_kNpm_servicio = 0 # Ignorar carga negativa

    L_mm = cm_to_mm(L_cm)
    # w_kNpm_servicio (kN/m) -> (kN/m * 1000 N/kN) / (1000 mm/m) = N/mm
    w_Npmm_servicio = w_kNpm_servicio # kN/m = N/mm
    Ec_N_mm2 = mp_to_n_mm2(Ec_MPa)

    factores_deflexion = { # Para carga uniformemente distribuida
        'simples': 5.0 / 384.0,
        'voladizo': 1.0 / 8.0, # Para carga en el extremo, o wL^4/8 para UDL
        'empotrado_empotrado': 1.0 / 384.0,
        'empotrado_apoyado': 1.0 / 185.0, # Aprox. (Varía según qué extremo es empotrado)
        # 'cont_fin1': 1/185, # Término anterior del usuario (un extremo continuo)
        # 'cont_fin2': 1/384, # Término anterior del usuario (ambos extremos continuos)
    }
    try:
        k_factor = factores_deflexion[tipo_apoyo]
    except KeyError:
        raise ValueError(f"Tipo de apoyo '{tipo_apoyo}' no reconocido. Opciones: {list(factores_deflexion.keys())}")

    delta_mm = k_factor * w_Npmm_servicio * (L_mm**4) / (Ec_N_mm2 * I_efectiva_mm4) if (Ec_N_mm2 * I_efectiva_mm4) > 0 else 0
    return delta_mm


def calcular_deflexion_largo_plazo(
    delta_inst_sostenida_mm, # Deflexión instantánea por cargas sostenidas (CM + %CVsostenida)
    xi_factor_tiempo, # Factor de la Tabla C.9-2 NSR-10 (ej. 2.0 para 5 años o más)
    rho_prima_comp=0.0 # Cuantía de refuerzo de compresión A_s' / (b*d)
    ):
    """
    Calcula la deflexión adicional a largo plazo según NSR-10 C.9.5.2.5 (Ec. C.9-9).
    """
    validate_positive(delta_inst_sostenida_mm=delta_inst_sostenida_mm if delta_inst_sostenida_mm > 0 else 1e-9, 
                      xi_factor_tiempo=xi_factor_tiempo) # Permitir delta=0
    if rho_prima_comp < 0: rho_prima_comp = 0

    lambda_delta = xi_factor_tiempo / (1.0 + 50.0 * rho_prima_comp)
    delta_adicional_lp_mm = lambda_delta * delta_inst_sostenida_mm
    return delta_adicional_lp_mm


def verificar_limites_deflexion_nsr10(
    delta_a_verificar_mm, L_cm,
    tipo_elemento, # Ej: 'Viga Rectangular', 'Losa Maciza Unidireccional', 'Nervio de Losa (Sección T)'
    condicion_carga_limite # Ej: 'CV_inmediata_no_susceptible', 'Total_diferida_susceptible', 'Total_diferida_no_susceptible'
    ):
    """
    Comprueba si la deflexión cumple con los límites de la Tabla C.9-1 de NSR-10.
    Retorna: cumple (bool), limite_aplicable_mm (float), n_factor_usado (int)
    """
    validate_positive(L_cm=L_cm)
    if delta_a_verificar_mm < 0 : delta_a_verificar_mm = 0

    L_mm = cm_to_mm(L_cm)
    n = None # Factor L/n

    # Claves simplificadas y mapeo a la Tabla C.9-1 de NSR-10
    # Las condiciones exactas de "susceptible de dañarse" deben ser evaluadas por el ingeniero.
    # "no_susceptible" se refiere a elementos que no soportan ni están ligados a elementos no estructurales
    # susceptibles de dañarse por deflexiones grandes.
    # "susceptible" se refiere a los que sí lo están.

    if tipo_elemento in ['Viga Rectangular', 'Losa Maciza Unidireccional', 'Nervio de Losa (Sección T)']:
        if condicion_carga_limite == 'CV_inmediata_no_susceptible':
            # Fila 1: Entrepisos o cubiertas que NO soporten elementos no estructurales susceptibles...
            # Deflexión a considerar: Inmediata debida a la carga viva no mayorada (L)
            n = 360
        elif condicion_carga_limite == 'Total_diferida_no_susceptible':
            # Fila 2: Entrepisos o cubiertas que NO soporten elementos no estructurales susceptibles...
            # Deflexión a considerar: La parte de la deflexión total que ocurre después de la unión
            # de los elementos no estructurales (suma de la deflexión a largo plazo por cargas
            # sostenidas y la deflexión inmediata por cualquier carga viva adicional).
            n = 240
        elif condicion_carga_limite == 'Total_diferida_susceptible_a_fisuracion': # Ej. Mampostería u otros frágiles
            # Fila 3: Entrepisos o cubiertas que SÍ soporten elementos no estructurales susceptibles...
            # Deflexión a considerar: Misma que Fila 2.
            n = 480
        elif condicion_carga_limite == 'Total_diferida_no_susceptible_a_fisuracion': # Ej. Acabados flexibles
             # Fila 4: Entrepisos o cubiertas que SÍ soporten elementos no estructurales NO susceptibles...
             # Deflexión a considerar: Misma que Fila 2.
            n = 240
        # Se podrían añadir más casos específicos de la tabla si es necesario (ej. cubiertas con contrapendiente)

    if n is None:
        raise ValueError(f"Combinación de tipo_elemento '{tipo_elemento}' y condicion_carga_limite '{condicion_carga_limite}' no reconocida o no implementada en 'verificar_limites_deflexion_nsr10'.")

    limite_mm = L_mm / n
    cumple = delta_a_verificar_mm <= limite_mm
    
    return cumple, limite_mm, n