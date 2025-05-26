# ==============================================================================
# DISEÑO DE VIGAS A FLEXIÓN Y CORTANTE (INCLUYE REQUISITOS DMO NSR-10)
# ==============================================================================
import numpy as np
from unidades import *
from validate_positive import validate_positive

PHI_FLEXION_VIGA = 0.90
PHI_CORTANTE_VIGA = 0.75
ES_MPA = 200000.0 # Módulo de elasticidad del acero
LAMBDA_CONCRETO_VIGA = 1.0 # Para concreto de peso normal

def _beta1_viga(fc_MPa):
    """Calcula beta1 según NSR-10 C.10.2.7.3"""
    if fc_MPa <= 28.0:
        return 0.85
    else:
        beta = 0.85 - 0.05 * ((fc_MPa - 28.0) / 7.0)
        return max(beta, 0.65)

def calcular_peralte_efectivo_viga(h_cm, rec_libre_cm, diam_estribo_mm, diam_barra_long_mm):
    """Calcula el peralte efectivo 'd' en mm para vigas."""
    h_mm = cm_to_mm(h_cm)
    rec_libre_mm = cm_to_mm(rec_libre_cm)
    d_mm = h_mm - rec_libre_mm - diam_estribo_mm - (diam_barra_long_mm / 2.0)
    if d_mm <= 0:
        raise ValueError("Peralte efectivo 'd' calculado es negativo o cero. Revise dimensiones y recubrimientos.")
    return d_mm

def diseno_viga_flexion_simple(
    b_cm, h_cm, rec_libre_cm,
    diam_estribo_mm, diam_barra_long_mm,
    fc_MPa, fy_MPa, Mu_kNm
):
    """
    Diseño a flexión de viga rectangular.
    Retorna un diccionario con As_req_cm2 y otros detalles.
    """
    # Validación de parámetros:
    # diam_estribo_mm puede ser 0 (para losas), así que no se incluye en validate_positive.
    # Se valida que sea no negativo por separado.
    validate_positive(b_cm=b_cm, h_cm=h_cm, rec_libre_cm=rec_libre_cm,
                      # diam_estribo_mm NO SE VALIDA AQUÍ COMO > 0
                      diam_barra_long_mm=diam_barra_long_mm,
                      fc_MPa=fc_MPa, fy_MPa=fy_MPa)
    
    if not isinstance(diam_estribo_mm, (int, float)) or diam_estribo_mm < 0:
        raise ValueError(f"'diam_estribo_mm' debe ser un número no negativo, se recibió: {diam_estribo_mm}")

    if Mu_kNm < 0: Mu_kNm = abs(Mu_kNm)
    if Mu_kNm == 0: Mu_kNm = 1e-6

    b_mm = cm_to_mm(b_cm)
    try:
        # calcular_peralte_efectivo_viga maneja diam_estribo_mm = 0 correctamente
        d_mm = calcular_peralte_efectivo_viga(h_cm, rec_libre_cm, diam_estribo_mm, diam_barra_long_mm)
    except ValueError as e:
        return {"status": "Error", "mensaje": str(e), "As_req_cm2": 0, "rho_calculado": 0, "d_mm": 0} # Estructura de error consistente

    Mu_Nmm = knm_to_nmm(Mu_kNm)
    
    k_rn_val = 0 # Inicializar por si d_mm es cero y no se calcula k
    if d_mm > 0: # Evitar división por cero si d_mm fuera cero (aunque calcular_peralte_efectivo_viga ya lo valida)
        k_rn_val = Mu_Nmm / (PHI_FLEXION_VIGA * b_mm * d_mm**2)
    else: # d_mm es cero o negativo
        return {
            "status": "Error",
            "mensaje": "Peralte efectivo 'd' es cero o negativo después del cálculo.",
            "As_req_cm2": float('inf'), "rho_calculado": float('inf'), "d_mm": d_mm
        }

    # Renombrar 'k' para evitar posible conflicto con 'k_rn_val' si se usara 'k' para otra cosa.
    # Usaremos k_rn = k_rn_val
    
    discriminante = 1.0 - (2.0 * k_rn_val) / (0.85 * fc_MPa)
    if discriminante < 0:
        return {
            "status": "Error",
            "mensaje": f"Momento Mu ({Mu_kNm:.1f} kNm) excede capacidad (k_Rn={k_rn_val:.2f} MPa). Aumentar sección.",
            "As_req_cm2": float('inf'), "rho_calculado": float('inf'), "d_mm": d_mm
        }
        
    rho_req = (0.85 * fc_MPa / fy_MPa) * (1.0 - np.sqrt(discriminante))
    As_req_mm2 = rho_req * b_mm * d_mm

    rho_min1 = 0.25 * np.sqrt(fc_MPa) / fy_MPa if fy_MPa > 0 else 0
    rho_min2 = 1.4 / fy_MPa if fy_MPa > 0 else 0
    rho_min = max(rho_min1, rho_min2)
    As_min_mm2 = rho_min * b_mm * d_mm
    
    As_final_mm2 = max(As_req_mm2, As_min_mm2)
    status_flex = "OK"
    mensaje_detallado = "Cálculo de flexión completado."
    if As_final_mm2 == As_min_mm2 and As_req_mm2 < As_min_mm2:
        status_flex = "Cuantía Mínima Controla"
        mensaje_detallado = "Cuantía mínima controla el diseño a flexión."
    
    rho_final_calculado = As_final_mm2 / (b_mm * d_mm) if (b_mm * d_mm) > 0 else 0

    return {
        "status": status_flex,
        "As_req_cm2": mm2_to_cm2(As_final_mm2),
        "rho_calculado": rho_final_calculado,
        "d_mm": d_mm, # Devolver d_mm para que la función de losa pueda usarlo
        "mensaje": mensaje_detallado
    }

def diseno_viga_cortante_estandar(
    b_cm, h_cm, rec_libre_cm,
    diam_estribo_mm, diam_barra_long_mm,
    fc_MPa, fy_MPa_estribos, Vu_kN
):
    """
    Diseño a cortante estándar de viga rectangular (NSR-10 C.11).
    Retorna un diccionario con Av_s_req_mm2_por_m y espaciamiento.
    """
    validate_positive(b_cm=b_cm, h_cm=h_cm, rec_libre_cm=rec_libre_cm, diam_estribo_mm=diam_estribo_mm,
                      diam_barra_long_mm=diam_barra_long_mm, fc_MPa=fc_MPa, fy_MPa_estribos=fy_MPa_estribos)
    if Vu_kN < 0: Vu_kN = abs(Vu_kN)

    b_mm = cm_to_mm(b_cm)
    try:
        d_mm = calcular_peralte_efectivo_viga(h_cm, rec_libre_cm, diam_estribo_mm, diam_barra_long_mm)
    except ValueError as e:
        return {"status": "Error", "mensaje": str(e)}
    Vu_N = kn_to_n(Vu_kN)

    Vc_N = 0.17 * LAMBDA_CONCRETO_VIGA * np.sqrt(fc_MPa) * b_mm * d_mm
    phi_Vc_N = PHI_CORTANTE_VIGA * Vc_N

    Av_s_final_mm2_per_mm = 0.0
    s_rec_mm = None
    status_cort = "No requerido por cálculo (Vu <= 0.5*phi*Vc)"
    
    if Vu_N > 0.5 * phi_Vc_N:
        Vs_req_N = max(0, (Vu_N / PHI_CORTANTE_VIGA) - Vc_N)
        
        Vs_max_N = 0.66 * LAMBDA_CONCRETO_VIGA * np.sqrt(fc_MPa) * b_mm * d_mm
        if Vs_req_N > Vs_max_N:
            return {
                "status": "Error",
                "mensaje": f"Vs_req ({n_to_kn(Vs_req_N):.1f} kN) excede Vs_max ({n_to_kn(Vs_max_N):.1f} kN). Redimensionar.",
                "Av_s_req_mm2_por_m": float('inf'), "s_rec_mm": None
            }

        Av_s_req_mm2_per_mm = 0.0
        if Vs_req_N > 0:
            Av_s_req_mm2_per_mm = Vs_req_N / (fy_MPa_estribos * d_mm)
        
        Av_s_min1 = 0.062 * np.sqrt(fc_MPa) * b_mm / fy_MPa_estribos
        Av_s_min2 = 0.35 * b_mm / fy_MPa_estribos
        Av_s_min_mm2_per_mm = max(Av_s_min1, Av_s_min2)
        
        Av_s_final_mm2_per_mm = max(Av_s_req_mm2_per_mm, Av_s_min_mm2_per_mm)
        status_cort = "OK"
        if Av_s_final_mm2_per_mm == Av_s_min_mm2_per_mm and Av_s_req_mm2_per_mm < Av_s_min_mm2_per_mm:
            status_cort = "Mínimo por norma controla (Vu > 0.5*phi*Vc)"
        
        # Espaciamiento máximo
        s_max_1 = d_mm / 2.0
        if Vs_req_N > (0.33 * LAMBDA_CONCRETO_VIGA * np.sqrt(fc_MPa) * b_mm * d_mm):
            s_max_1 = d_mm / 4.0
        s_max_2 = 600.0 # mm
        s_max_mm = min(s_max_1, s_max_2)

        if Av_s_final_mm2_per_mm > 1e-9:
            Area_una_rama_estribo = np.pi * (diam_estribo_mm / 2.0)**2
            Av_mm2_prov = 2 * Area_una_rama_estribo # Asumiendo estribo de 2 ramas
            s_calc_mm = Av_mm2_prov / Av_s_final_mm2_per_mm
            s_rec_mm = min(s_calc_mm, s_max_mm)
            s_rec_mm = np.floor(s_rec_mm / 25.0) * 25.0 # Redondear a múltiplo de 2.5cm
            if s_rec_mm < 50: s_rec_mm = 50
    
    return {
        "status": status_cort,
        "Av_s_req_mm2_por_m": Av_s_final_mm2_per_mm * 1000, # mm²/m
        "s_rec_mm": s_rec_mm,
        "Vc_kN": n_to_kn(Vc_N),
        "phi_Vc_kN": n_to_kn(phi_Vc_N),
        "diam_estribo_usado_mm": diam_estribo_mm,
        "d_mm": d_mm,
        "mensaje": "Cálculo de cortante estándar completado."
    }

def diseno_viga_dmo(
    b_cm, h_cm, rec_libre_cm, diam_estribo_mm, diam_barra_long_principal_mm,
    fc_MPa, fy_MPa_long, fy_MPa_estribos,
    Mu_neg_ext_kNm, Mu_pos_kNm, Mu_neg_int_kNm, # Momentos de análisis
    ln_m, # Luz libre de la viga
    Vu_grav_ext_kN, Vu_grav_int_kN # Cortante isostático por cargas gravitacionales en apoyos
):
    """
    Diseño completo de viga de pórtico DMO (NSR-10 C.21.3).
    """
    validate_positive(b_cm=b_cm, h_cm=h_cm, rec_libre_cm=rec_libre_cm, diam_estribo_mm=diam_estribo_mm,
                      diam_barra_long_principal_mm=diam_barra_long_principal_mm, fc_MPa=fc_MPa,
                      fy_MPa_long=fy_MPa_long, fy_MPa_estribos=fy_MPa_estribos, ln_m=ln_m)

    b_mm = cm_to_mm(b_cm)
    h_mm = cm_to_mm(h_cm)
    
    try:
        d_mm = calcular_peralte_efectivo_viga(h_cm, rec_libre_cm, diam_estribo_mm, diam_barra_long_principal_mm)
    except ValueError as e:
        return {"status": "Error", "mensaje_global": str(e)}

    # 1. Verificaciones Geométricas (NSR-10 C.21.3.1)
    if ln_m < 4 * (d_mm / 1000.0): # ln/d > 4
        # Este chequeo es para pórticos especiales DES (C.21.6.1.1), no DMO. DMO es menos restrictivo.
        # Para DMO (C.21.3.1), b_w >= 0.3h y b_w >= 250mm son de secciones C.21.6.3.1 (DES)
        # C.21.3.1 no impone mínimos absolutos de b o h, sino relaciones y que b <= ancho apoyo + distancias.
        # Por ahora, no se implementan estos chequeos complejos de ancho de apoyo.
        pass 
    if b_cm < 20: # Recomendación general, no estrictamente de C.21.3.1 para DMO pero buena práctica
        # st.warning("Se recomienda un ancho de viga bw >= 20cm para facilitar el armado.")
        pass


    # 2. Diseño por Flexión y Verificación de Cuantías (NSR-10 C.21.3.2)
    flex_neg_ext = diseno_viga_flexion_simple(b_cm, h_cm, rec_libre_cm, diam_estribo_mm, diam_barra_long_principal_mm, fc_MPa, fy_MPa_long, Mu_neg_ext_kNm)
    flex_pos = diseno_viga_flexion_simple(b_cm, h_cm, rec_libre_cm, diam_estribo_mm, diam_barra_long_principal_mm, fc_MPa, fy_MPa_long, Mu_pos_kNm)
    flex_neg_int = diseno_viga_flexion_simple(b_cm, h_cm, rec_libre_cm, diam_estribo_mm, diam_barra_long_principal_mm, fc_MPa, fy_MPa_long, Mu_neg_int_kNm)

    if any(f['status'] == "Error" for f in [flex_neg_ext, flex_pos, flex_neg_int]):
        return {"status": "Error", "mensaje_global": "Error en diseño a flexión. " + flex_neg_ext.get('mensaje', '') + flex_pos.get('mensaje', '') + flex_neg_int.get('mensaje', '')}

    rho_max_dmo = 0.025
    cuantias_ok = True
    for flex_res in [flex_neg_ext, flex_pos, flex_neg_int]:
        if flex_res['rho_calculado'] > rho_max_dmo:
            cuantias_ok = False
            break
    
    mensaje_cuantia = f"Cuantías calculadas: Ext={flex_neg_ext['rho_calculado']:.4f}, Pos={flex_pos['rho_calculado']:.4f}, Int={flex_neg_int['rho_calculado']:.4f}. "
    if not cuantias_ok:
        mensaje_cuantia += f"ADVERTENCIA: Alguna cuantía excede el máximo para DMO de {rho_max_dmo:.3f}."
    else:
        mensaje_cuantia += f"OK: Cuantías dentro del límite DMO ({rho_max_dmo:.3f})."

    # Requisito de momento positivo en la cara del nudo (C.21.3.2.2)
    # Mn_pos_cara >= 0.5 * Mn_neg_cara
    # Esto implica que As_pos_cara >= 0.5 * As_neg_cara (aproximadamente)
    # Se asume que Mu_pos_kNm ya considera el momento mínimo en la cara si es aplicable.
    # O se podría verificar As_req_pos_cm2 vs 0.5 * As_req_neg_ext/int_cm2

    # 3. Diseño por Cortante (NSR-10 C.21.3.4)
    # Cortante probable Ve
    # Mpr = Momento probable de la viga en la cara del nudo, con fy -> 1.25fy y phi=1.0
    # Para calcular Mpr real, se necesita el As provisto y d.
    # Simplificación: Mpr_aprox = 1.25 * Mu_analisis (o Mu que da As_req)
    # Esto asume que el Mu de análisis está cerca de la capacidad phi*Mn con fy.
    # Phi se cancelaría Mpr = 1.25 * (Mu_analisis / PHI_FLEXION_VIGA)
    
    # Mpr = phi_nominal * As_provisto * 1.25 * fy * (d - a/2)
    # Es complejo sin definir el acero provisto exacto.
    # Una aproximación común es Mpr ~ 1.25 * Mu_diseno_al_limite_de_As
    # O Mpr = 1.25 * Mu_cara_analisis / PHI_FLEXION_VIGA
    Mpr_ext_kNm = 1.25 * Mu_neg_ext_kNm / PHI_FLEXION_VIGA
    Mpr_int_kNm = 1.25 * Mu_neg_int_kNm / PHI_FLEXION_VIGA
    
    Ve_ext_kN = (Mpr_ext_kNm / ln_m) + Vu_grav_ext_kN # Suma de cortante por capacidad y gravitacional
    Ve_int_kN = (Mpr_int_kNm / ln_m) + Vu_grav_int_kN # En el otro extremo

    # Vc = 0 para DMO cuando se diseña para Ve (NSR-10 C.21.3.4.2)
    Vc_N_dmo = 0
    
    # Cortante a tomar por el acero en el extremo (ej. externo)
    Vs_req_ext_N = kn_to_n(Ve_ext_kN) / PHI_CORTANTE_VIGA - Vc_N_dmo # Vc es 0
    Vs_req_ext_N = max(0, Vs_req_ext_N)
    
    # Cortante a tomar por el acero en el otro extremo (ej. interno)
    Vs_req_int_N = kn_to_n(Ve_int_kN) / PHI_CORTANTE_VIGA - Vc_N_dmo # Vc es 0
    Vs_req_int_N = max(0, Vs_req_int_N)

    # Verificar Vs_max
    Vs_max_N = 0.66 * LAMBDA_CONCRETO_VIGA * np.sqrt(fc_MPa) * b_mm * d_mm
    if Vs_req_ext_N > Vs_max_N or Vs_req_int_N > Vs_max_N:
        return {
            "status": "Error", 
            "mensaje_global": f"Vs requerido ({n_to_kn(max(Vs_req_ext_N, Vs_req_int_N)):.1f} kN) excede Vs_max ({n_to_kn(Vs_max_N):.1f} kN). Redimensionar viga.",
             # Incluir otros resultados parciales para depuración
            "As_req_neg_ext_cm2": mm2_to_cm2(flex_neg_ext['As_req_cm2']),
            "As_req_pos_cm2": mm2_to_cm2(flex_pos['As_req_cm2']),
            "As_req_neg_int_cm2": mm2_to_cm2(flex_neg_int['As_req_cm2']),
            "mensaje_cuantia": mensaje_cuantia
        }

    # 4. Refuerzo Transversal para Confinamiento y Cortante (NSR-10 C.21.3.3)
    lo_mm = 2 * h_mm # Longitud de la zona confinada desde la cara del nudo

    # Espaciamiento en Zona Confinada (so)
    # C.21.3.3.2: el primero a s0/2, no más de 50mm. Luego s0.
    # s0 es el menor de: d/4, 8*db_long_min, 24*db_estribo, 300mm
    # Asumir db_long_min = diam_barra_long_principal_mm para simplificar
    s_conf_1 = d_mm / 4.0
    s_conf_2 = 8 * diam_barra_long_principal_mm
    s_conf_3 = 24 * diam_estribo_mm
    s_conf_4 = 300.0 # mm
    so_max_norma_mm = min(s_conf_1, s_conf_2, s_conf_3, s_conf_4)
    
    # Espaciamiento requerido por cortante Vs (el mayor de Ve_ext y Ve_int)
    Vs_req_max_N = max(Vs_req_ext_N, Vs_req_int_N)
    s_req_por_vs_mm = float('inf')
    Av_mm2_prov = 2 * (np.pi * (diam_estribo_mm / 2.0)**2) # Estribo 2 ramas

    if Vs_req_max_N > 0:
        s_req_por_vs_mm = (Av_mm2_prov * fy_MPa_estribos * d_mm) / Vs_req_max_N
        
    # El espaciamiento en zona confinada es el menor del de confinamiento y el de cortante
    s_final_confinado_mm = min(so_max_norma_mm, s_req_por_vs_mm)
    s_final_confinado_mm = np.floor(s_final_confinado_mm / 10.0) * 10.0 # Redondear hacia abajo a múltiplo de 10mm
    if s_final_confinado_mm < 50: s_final_confinado_mm = 50 # Mínimo práctico

    # Espaciamiento en Zona Central (fuera de lo) (NSR-10 C.21.3.3.4)
    # El refuerzo debe satisfacer C.11 y no ser mayor que d/2
    # Usamos la función de cortante estándar para el Vu_gravitacional en el centro (o el max gravitacional)
    # Aquí, por simplicidad, usaremos el mayor cortante gravitacional (Vu_grav_ext o Vu_grav_int) para el centro
    # O, si se conoce el Vu en el centro, usar ese. Para un caso general, usamos el máximo gravitacional como conservador.
    Vu_central_aprox_kN = max(abs(Vu_grav_ext_kN), abs(Vu_grav_int_kN)) # Podría ser menor en el centro de la luz
    
    res_cort_central_std = diseno_viga_cortante_estandar(
        b_cm, h_cm, rec_libre_cm, diam_estribo_mm, diam_barra_long_principal_mm,
        fc_MPa, fy_MPa_estribos, Vu_central_aprox_kN
    )
    s_calc_central_std_mm = res_cort_central_std.get('s_rec_mm', d_mm / 2.0) # s_rec_mm o d/2 si no requiere
    if s_calc_central_std_mm is None: s_calc_central_std_mm = d_mm / 2.0 # Si no se requiere por cálculo

    s_max_central_norma_mm = d_mm / 2.0
    s_final_central_mm = min(s_calc_central_std_mm, s_max_central_norma_mm)
    s_final_central_mm = np.floor(s_final_central_mm / 25.0) * 25.0 # Redondear a múltiplo de 2.5cm
    if s_final_central_mm < 50: s_final_central_mm = 50


    return {
        "status": "OK",
        "mensaje_global": "Diseño DMO de viga completado.",
        "flexion_neg_ext": {"As_req_cm2": flex_neg_ext['As_req_cm2'], "rho": flex_neg_ext['rho_calculado']},
        "flexion_pos": {"As_req_cm2": flex_pos['As_req_cm2'], "rho": flex_pos['rho_calculado']},
        "flexion_neg_int": {"As_req_cm2": flex_neg_int['As_req_cm2'], "rho": flex_neg_int['rho_calculado']},
        "mensaje_cuantia": mensaje_cuantia,
        "cortante_diseno_Ve_ext_kN": round(Ve_ext_kN, 2),
        "cortante_diseno_Ve_int_kN": round(Ve_int_kN, 2),
        "Vs_requerido_max_kN": round(n_to_kn(Vs_req_max_N), 2),
        "longitud_confinamiento_lo_cm": round(mm_to_cm(lo_mm), 1),
        "estribos_diam_mm": diam_estribo_mm,
        "espaciamiento_zona_confinada_cm": round(mm_to_cm(s_final_confinado_mm), 1),
        "espaciamiento_zona_central_cm": round(mm_to_cm(s_final_central_mm), 1),
        "d_usado_cm": round(mm_to_cm(d_mm),1)
    }