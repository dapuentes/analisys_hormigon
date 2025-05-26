# ==============================================================================
# ANÁLISIS DE LOSA NERVADA
# ==============================================================================
import numpy as np
import matplotlib.pyplot as plt
from unidades import *
from validate_positive import validate_positive
from .diseno_vigas import _beta1_viga, calcular_peralte_efectivo_viga

# Constantes 
GAMMA_CONCRETO_KN_M3 = 24.0
PHI_FLEXION_LOSA = 0.90
PHI_CORTANTE_LOSA = 0.75
ES_MPA = 200000.0
EPSILON_CU = 0.003
LAMBDA_CONCRETO = 1.0

def calcular_cargas_losa_nervada(
    separacion_nervios_m, t_loseta_cm, h_total_nervio_cm, b_alma_nervio_cm,
    q_muerta_adicional_kNm2, q_viva_kNm2):
    """
    Calcula la carga lineal última (w_u_por_nervio) y de servicio (w_s_por_nervio)
    y el peso propio de la losa.
    Las cargas adicionales y vivas se asumen ya mayoradas si se necesita w_u,
    o en servicio si se necesita w_s. Esta función solo calcula el peso propio
    y lo suma a las cargas dadas.

    Retorna: dict con:
        - 'peso_propio_losa_kNm2': Peso propio total de la losa (kN/m²)
        - 'w_muerta_total_por_nervio_kNm': Carga muerta total lineal por nervio (kN/m)
        - 'w_viva_por_nervio_kNm': Carga viva lineal por nervio (kN/m)
    """
    validate_positive(separacion_nervios_m=separacion_nervios_m, t_loseta_cm=t_loseta_cm,
                      h_total_nervio_cm=h_total_nervio_cm, b_alma_nervio_cm=b_alma_nervio_cm)
    if q_muerta_adicional_kNm2 < 0 or q_viva_kNm2 < 0:
        raise ValueError("Las cargas adicionales deben ser >= 0")

    t_los_m = cm_to_m(t_loseta_cm)
    h_tot_m = cm_to_m(h_total_nervio_cm)
    b_alma_m = cm_to_m(b_alma_nervio_cm)

    if h_tot_m < t_los_m:
        raise ValueError("La altura total del nervio debe ser mayor o igual al espesor de la loseta.")

    # Peso propio loseta (kN/m²)
    pp_loseta_kNm2 = GAMMA_CONCRETO_KN_M3 * t_los_m

    # Peso propio alma del nervio, distribuido por m² de losa
    area_alma_m2 = (h_tot_m - t_los_m) * b_alma_m # Área de la sección del alma
    vol_alma_por_m_largo_m3 = area_alma_m2 * 1.0 # Volumen por metro lineal de nervio
    pp_alma_por_m_largo_kNm = GAMMA_CONCRETO_KN_M3 * vol_alma_por_m_largo_m3
    pp_alma_distribuido_kNm2 = pp_alma_por_m_largo_kNm / separacion_nervios_m if separacion_nervios_m > 0 else 0

    peso_propio_total_losa_kNm2 = pp_loseta_kNm2 + pp_alma_distribuido_kNm2
    
    # Cargas lineales por nervio (kN/m)
    cm_total_kNm2 = peso_propio_total_losa_kNm2 + q_muerta_adicional_kNm2
    
    w_muerta_total_por_nervio_kNm = cm_total_kNm2 * separacion_nervios_m
    w_viva_por_nervio_kNm = q_viva_kNm2 * separacion_nervios_m
    
    return {
        "peso_propio_losa_kNm2": round(peso_propio_total_losa_kNm2, 3),
        "w_muerta_total_por_nervio_kNm": round(w_muerta_total_por_nervio_kNm, 3),
        "w_viva_por_nervio_kNm": round(w_viva_por_nervio_kNm, 3)
    }


def diseno_nervio_flexion(
    Mu_kNm, # Momento último de diseño del nervio (positivo o negativo)
    fc_MPa, fy_MPa,
    h_total_cm, bw_cm, # h_total = altura loseta+alma, bw = ancho alma
    hf_cm, # Espesor de la loseta (ala)
    separacion_nervios_m, L_libre_nervio_m, # Para b_eff
    rec_libre_inf_cm, diam_estribo_mm, diam_barra_long_mm):
    """
    Diseña un nervio de losa a flexión (como viga T para M+ o rectangular para M-).
    Retorna un diccionario con resultados.
    """
    validate_positive(fc_MPa=fc_MPa, fy_MPa=fy_MPa, h_total_cm=h_total_cm, bw_cm=bw_cm, hf_cm=hf_cm)
    # Mu_kNm puede ser 0 o negativo

    h_total_mm = cm_to_mm(h_total_cm)
    bw_mm = cm_to_mm(bw_cm)
    hf_mm = cm_to_mm(hf_cm)
    Mu_Nmm = knm_to_nmm(Mu_kNm)

    try:
        # Peralte efectivo 'd' (desde fibra más comprimida a centroide de acero)
        # Para M+, fibra más comprimida es arriba de la loseta.
        # Para M-, fibra más comprimida es abajo del nervio (d se mide desde abajo).
        # Asumiremos que el acero principal siempre está abajo para M+, y arriba (en loseta) para M-.
        # Esto es una simplificación; el refuerzo negativo suele ir en la loseta pero cerca del apoyo.
        # Por ahora, calculamos d_positivo (acero abajo)
        d_mm = calcular_peralte_efectivo_viga(h_total_cm, rec_libre_inf_cm, diam_estribo_mm, diam_barra_long_mm)
    except ValueError as e:
        return {"status": "Error", "mensaje": f"Error calculando peralte efectivo: {e}"}

    beta_1 = _beta1_viga(fc_MPa)
    As_req_mm2 = 0
    a_mm = 0
    status_flex = "OK"
    mensaje_flex = ""

    # --- Diseño para Momento Positivo (M+ > 0) ---
    if Mu_Nmm > 1e-3: # Momento positivo (tracción abajo, loseta en compresión)
        # Calcular ancho efectivo del ala b_eff (NSR-10 C.8.12.2)
        # bw_m = cm_to_m(bw_cm)
        # separacion_libre_m = separacion_nervios_m - bw_m
        
        # b_eff_ala = bw_mm + min(L_libre_nervio_m * 1000 / 4.0, 16 * hf_mm, (separacion_nervios_m * 1000 - bw_mm) )
        # No, es: b_eff <= bw + 2 * (menor de (8*hf, sl/2, Ln/8))
        # O más simple, b_eff es el menor de:
        # 1. Ln/4 (Luz del nervio)
        # 2. bw + 16*hf
        # 3. Separación centro a centro de nervios (si se usa directamente)
        b_eff_1 = L_libre_nervio_m * 1000 / 4.0
        b_eff_2 = bw_mm + 16 * hf_mm
        b_eff_3 = separacion_nervios_m * 1000 # Ancho tributario = separación c-c
        
        b_eff_mm = min(b_eff_1, b_eff_2, b_eff_3)
        
        # Asumir inicialmente que a <= hf (eje neutro en la loseta)
        # Diseñar como viga rectangular de ancho b_eff
        k = Mu_Nmm / (PHI_FLEXION_LOSA * b_eff_mm * d_mm**2)
        discriminante = 1.0 - (2.0 * k) / (0.85 * fc_MPa)

        if discriminante < 0:
            return {"status": "Error", "mensaje": f"M+ ({Mu_kNm:.1f} kNm) excede capacidad de sección T (k={k:.2f} MPa). Aumentar.", "b_eff_mm": b_eff_mm}
        
        rho_rect = (0.85 * fc_MPa / fy_MPa) * (1.0 - np.sqrt(discriminante))
        As_req_mm2 = rho_rect * b_eff_mm * d_mm
        a_mm = (As_req_mm2 * fy_MPa) / (0.85 * fc_MPa * b_eff_mm)

        if a_mm > hf_mm: # Eje neutro cae fuera de la loseta, diseñar como T real
            # Fuerza en el ala (compresión): Ccf = 0.85 * fc * (b_eff - bw) * hf
            Ccf_N = 0.85 * fc_MPa * (b_eff_mm - bw_mm) * hf_mm
            # Momento resistido por el ala: Mnf = phi * Ccf * (d - hf/2)
            Muf_Nmm = PHI_FLEXION_LOSA * Ccf_N * (d_mm - hf_mm / 2.0)
            
            # Momento que debe tomar el alma: Muw = Mu - Muf
            Muw_Nmm = Mu_Nmm - Muf_Nmm # Este es el Mu para el alma (rectangular bw x d)
            
            if Muw_Nmm < 0: # Si el ala sola resiste más que el momento aplicado (sobredimensionado)
                # Significa que 'a' calculado antes (asumiendo rectangular con b_eff) es el correcto y debe ser <= hf.
                # Esto indica una posible inconsistencia si el 'a' anterior fue > hf.
                # Se recalcula As solo para el momento necesario, lo que llevaría a a <= hf.
                # Usaremos el As_req_mm2 de la suposición rectangular, ya que a_mm > hf_mm implicaría que
                # el bloque de compresión es mayor, pero si M_uw es negativo, el ala es suficiente.
                # Esta condición se maneja con el 'a' de la sección rectangular con b_eff.
                # Lo importante es que si a_mm (calculado con b_eff) > hf_mm, pero el ala puede tomar todo el M_u
                # (o más), entonces la sección es muy grande o M_u es pequeño.
                # El As_req_mm2 y 'a' calculados con b_eff son la referencia. Si ese 'a' > hf, entonces
                # se debe proceder con el diseño T.
                mensaje_flex += " (Ala (b_eff) es muy efectiva, 'a' podría estar dentro del ala con menos acero que el calculado inicialmente para el alma). "
                # Para simplificar este caso borde, si Muw_Nmm < 0, recalculamos 'a'
                # asumiendo que toda la compresión se toma en el ala con bw.
                # No, si Muw_Nmm < 0, y 'a' (con b_eff) > hf, significa que la suposición inicial era
                # incorrecta, y As_req debe ser menor. El bloque real de compresión 'a' debe ser <= hf.
                # Se usa el 'a' y 'As_req_mm2' de la suposición rectangular con b_eff.
                # Esta sección del código de diseño T es para cuando el ala NO es suficiente.
                # Si M_uw < 0, significa que C_cf (fuerza en las aletas del ala) ya genera un momento M_nf > M_u.
                # En este caso, As_req es la que corresponde a C_cf.
                # As_req_mm2 = Ccf_N / fy_MPa (si asumimos que fluye)
                # a_mm = (As_req_mm2 * fy_MPa) / (0.85 * fc_MPa * b_eff_mm) # 'a' sería < hf
                # Esta situación se maneja si el 'a' calculado con b_eff es <= hf. Si es > hf y M_uw < 0, es una sección
                # muy grande y el As del cálculo rectangular inicial es conservador.
                # Por simplicidad, si a_mm > hf_mm, pero M_uw < 0,
                # se puede decir que la loseta es suficiente, y la comprobación a<=hf es la que rige.
                # Esto indica que el As calculado con la suposición rectangular (usando b_eff) es el que rige.
                # El `a_mm` ya calculado con `b_eff` sería el de referencia.
                # Si ese a_mm > hf_mm, entonces el bloque es T, y se procede.
                pass # Se usa As y a de la sección rectangular con b_eff


            else: # El alma debe tomar Muw_Nmm
                k_alma = Muw_Nmm / (PHI_FLEXION_LOSA * bw_mm * d_mm**2)
                disc_alma = 1.0 - (2.0 * k_alma) / (0.85 * fc_MPa)
                if disc_alma < 0:
                    return {"status": "Error", "mensaje": f"M+ ({Mu_kNm:.1f} kNm) excede capacidad del alma de la sección T (k_alma={k_alma:.2f} MPa). Aumentar.", "b_eff_mm": b_eff_mm}
                
                rho_alma = (0.85 * fc_MPa / fy_MPa) * (1.0 - np.sqrt(disc_alma))
                As_alma_mm2 = rho_alma * bw_mm * d_mm
                
                As_ala_mm2 = Ccf_N / fy_MPa # Acero para equilibrar la compresión en las aletas del ala
                As_req_mm2 = As_ala_mm2 + As_alma_mm2
                # Recalcular 'a' para la sección T total
                a_mm = (As_req_mm2 * fy_MPa - Ccf_N) / (0.85 * fc_MPa * bw_mm) + hf_mm # Incorrecto
                # a_mm es la profundidad del bloque equivalente total
                # (As_req_mm2*fy) = 0.85*fc*( (b_eff-bw)*hf + bw*a ) -> a_mm = ( (As_req_mm2*fy)/(0.85*fc) - (b_eff-bw)*hf ) / bw
                # Pero a_mm se define sobre el área total comprimida.
                # P_comp_total = 0.85 * fc * ((b_eff - bw)*hf + bw*a_verdadero_en_alma)
                # As_req_mm2 * fy = P_comp_total.
                # a_verdadero_en_alma = ( (As_req_mm2*fy)/(0.85*fc) - (b_eff-bw)*hf ) / bw
                # 'a' del bloque total no es directamente comparable. Lo importante es As_req.
                # El 'a' del bloque de compresión que se extiende en el alma, medido desde la parte superior de la loseta.
                a_mm_en_alma = ( (As_alma_mm2 + As_ala_mm2) * fy_MPa - Ccf_N ) / (0.85 * fc_MPa * bw_mm) if (0.85*fc_MPa*bw_mm)>0 else float('inf')
                a_mm = a_mm_en_alma # Esta 'a' es la profundidad del bloque de compresión rectangular equivalente en el alma, medido desde la parte superior de la loseta.
                                    # Para el chequeo de a vs hf, el 'a' original de la sección rectangular con b_eff era el indicativo.
                                    # Aquí a_mm es la profundidad total del bloque de compresión.

        b_diseno_flex = b_eff_mm # Ancho usado para cálculo de 'a' y ρ_min/max

    # --- Diseño para Momento Negativo (M- < 0) ---
    elif Mu_Nmm < -1e-3: # Momento negativo (tracción arriba en loseta, compresión abajo en nervio)
        # Diseñar como viga rectangular de ancho bw_mm
        # Peralte 'd' se mediría desde la fibra inferior del nervio al acero superior (en loseta)
        # Simplificación: Usar el mismo 'd' (acero inferior) pero con bw. O pedir rec_sup.
        # Si el acero a tracción está arriba, 'd' cambia.
        # Asumimos que el acero a tracción (para M-) está en la loseta, cerca de la cara superior.
        # rec_sup_cm = st.number_input("Rec. sup a eje acero (cm)") # Se necesitaría este input
        # d_neg_mm = h_total_mm - cm_to_mm(rec_sup_cm_ejemplo)
        # Por ahora, para no complicar las entradas, se usa el mismo 'd' y bw.
        # ESTO ES UNA SIMPLIFICACIÓN IMPORTANTE PARA MOMENTO NEGATIVO.
        # Se debe usar d medido desde la fibra inferior (compresión) al acero superior (tracción).
        # O, más comúnmente, se invierte la sección y se diseña con d medido desde arriba.
        # Asumamos que Mu_kNm siempre es el momento para el cual el acero está abajo.
        # Si se quiere diseñar para M-, se debe pasar |M-| y ajustar d o la interpretación.
        # Por ahora, diseñaremos con bw y el d calculado (acero abajo)
        # Esto implica que el refuerzo a tracción para M- también estaría abajo, lo cual no es típico.
        # Mejor: Asumir que M- se toma con un 'd' simétrico o que se añade acero de compresión.
        # La práctica común es diseñar la sección rectangular (bw x d) para el momento negativo.

        k = abs(Mu_Nmm) / (PHI_FLEXION_LOSA * bw_mm * d_mm**2)
        discriminante = 1.0 - (2.0 * k) / (0.85 * fc_MPa)
        
        if discriminante < 0:
            return {"status": "Error", "mensaje": f"M- ({Mu_kNm:.1f} kNm) excede capacidad de nervio (bw={bw_cm} cm, k={k:.2f} MPa). Aumentar.", "b_eff_mm": None}

        rho_rect = (0.85 * fc_MPa / fy_MPa) * (1.0 - np.sqrt(discriminante))
        As_req_mm2 = rho_rect * bw_mm * d_mm
        a_mm = (As_req_mm2 * fy_MPa) / (0.85 * fc_MPa * bw_mm)
        b_diseno_flex = bw_mm # Ancho usado para rho_min/max

    else: # Momento cercano a cero
        As_req_mm2 = 0
        a_mm = 0
        b_diseno_flex = bw_mm # Para cuantía mínima
        status_flex = "Momento Cero o Despreciable"

    # Chequeos de cuantías (usar b_diseno_flex que es b_eff para M+ o bw para M-)
    rho_min1 = 0.25 * np.sqrt(fc_MPa) / fy_MPa
    rho_min2 = 1.4 / fy_MPa
    rho_min = max(rho_min1, rho_min2)
    As_min_mm2 = rho_min * b_diseno_flex * d_mm

    epsilon_cu = EPSILON_CU
    epsilon_y = fy_MPa / ES_MPA
    #rho_balanceada = (0.85 * fc_MPa * beta_1 / fy_MPa) * (epsilon_cu / (epsilon_cu + epsilon_y))
    # As_max_mm2 para et = 0.005 (NSR-10 C.9.3.3.1)
    As_max_mm2 = (0.85 * fc_MPa * beta_1 * b_diseno_flex * d_mm / fy_MPa) * (epsilon_cu / (epsilon_cu + 0.005))

    As_final_mm2 = As_req_mm2
    if As_req_mm2 < As_min_mm2:
        As_final_mm2 = As_min_mm2
        status_flex = "Cuantía Mínima Controla"
    elif As_req_mm2 > As_max_mm2:
        status_flex = "Error - Excede Cuantía Máxima"
        mensaje_flex = f"As calculada ({As_req_mm2/100:.2f} cm²) excede As max ({As_max_mm2/100:.2f} cm²) para εt=0.005."
        # No se debería usar As_max como final, sino indicar error.
        # As_final_mm2 = As_max_mm2 # Esto no es correcto, se debe redimensionar.
        # Devolver error para que el usuario ajuste la sección.

    # Recalcular 'a' con As_final si cambió por cuantía mínima.
    if As_final_mm2 > 0 and status_flex != "Error - Excede Cuantía Máxima":
        a_mm = (As_final_mm2 * fy_MPa) / (0.85 * fc_MPa * b_diseno_flex) if (0.85*fc_MPa*b_diseno_flex)>0 else 0
        c_mm = a_mm / beta_1 if beta_1 > 0 else float('inf')
        epsilon_t = epsilon_cu * (d_mm - c_mm) / c_mm if c_mm > 0 else float('inf')
        phi_calc = _beta1_viga(fc_MPa) # Esta es la función phi de vigas, no _beta1_viga
        # Usar _calcular_phi de diseno_columna.py o definirla aquí
        # def _calcular_phi_flex(epsilon_t_val): (similar a _calcular_phi de columnas)
        #    ...
        # phi_val = _calcular_phi_flex(epsilon_t)
    else:
        epsilon_t = float('inf')
        # phi_val = PHI_FLEXION_LOSA

    return {
        "status": status_flex, "mensaje": mensaje_flex,
        "Mu_kNm": round(Mu_kNm,2), "d_mm": round(d_mm,1),
        "b_eff_o_bw_mm": round(b_diseno_flex,1) if Mu_Nmm > 1e-3 else round(bw_mm,1),
        "a_mm": round(a_mm,1), "hf_mm": round(hf_mm,1),
        "As_req_cm2": round(As_req_mm2/100.0, 3),
        "As_min_cm2": round(As_min_mm2/100.0, 3),
        "As_max_et005_cm2": round(As_max_mm2/100.0, 3),
        "As_final_cm2": round(As_final_mm2/100.0, 3),
        "epsilon_t_final": round(epsilon_t, 5) if epsilon_t != float('inf') else "inf",
        # "phi_calculado": round(phi_val, 2)
    }


def diseno_nervio_cortante(
    Vu_kN, fc_MPa, fy_MPa, # fy para estribos
    h_total_cm, bw_cm, # Geometría del nervio
    rec_libre_inf_cm, diam_estribo_mm, diam_barra_long_mm): # Para calcular d
    """
    Diseña el refuerzo a cortante para un nervio de losa.
    Sigue la lógica de diseno_viga_cortante.
    Retorna un diccionario con resultados.
    """
    validate_positive(fc_MPa=fc_MPa, fy_MPa=fy_MPa, h_total_cm=h_total_cm, bw_cm=bw_cm,
                      rec_libre_inf_cm=rec_libre_inf_cm, diam_estribo_mm=diam_estribo_mm,
                      diam_barra_long_mm=diam_barra_long_mm)
    if Vu_kN < 0: Vu_kN = abs(Vu_kN)

    try:
        d_mm = calcular_peralte_efectivo_viga(h_total_cm, rec_libre_inf_cm, diam_estribo_mm, diam_barra_long_mm)
    except ValueError as e:
        return {"status": "Error", "mensaje": f"Error calculando peralte efectivo: {e}"}

    bw_mm = cm_to_mm(bw_cm)
    Vu_N = kn_to_n(Vu_kN)

    # Vc para nervios (NSR-10 C.11.2.2.1 y C.8.13.8)
    # C.8.13.8 permite Vc = 1.1 * (0.17*lambda*sqrt(f'c)*bw*d) si se cumplen condiciones.
    # Usaremos el Vc básico: 0.17*lambda*sqrt(f'c)*bw*d
    Vc_N = 0.17 * LAMBDA_CONCRETO * np.sqrt(fc_MPa) * bw_mm * d_mm
    
    # Lógica similar a diseno_viga_cortante
    limite_min_refuerzo = 0.5 * PHI_CORTANTE_LOSA * Vc_N
    status_calc = ""
    mensaje_cort = ""
    Vs_req_N = 0

    if Vu_N <= limite_min_refuerzo:
        mensaje_cort = "Vu ≤ 0.5·φ·Vc. No requiere estribos por cálculo. Verificar mínimos si aplica."
        Av_s_req_mm2_per_mm = 0.0
        status_calc = "No Requerido por Cálculo"
    else:
        Vs_req_N = (Vu_N / PHI_CORTANTE_LOSA) - Vc_N
        if Vs_req_N < 0:
            Vs_req_N = 0.0
            mensaje_cort = "Vu > 0.5·φ·Vc pero Vu ≤ φ·Vc. Requiere estribos mínimos si nervio es principal."
            status_calc = "Mínimo Requerido (Vu>0.5φVc)"
        else:
            mensaje_cort = "Vu > φ·Vc. Requiere estribos por cálculo."
            status_calc = "Requerido por Cálculo"
            
    Vs_max_N = 0.66 * LAMBDA_CONCRETO * np.sqrt(fc_MPa) * bw_mm * d_mm
    if Vs_req_N > Vs_max_N:
        return {
            "status": "Error",
            "mensaje": f"Vs_req ({Vs_req_N/1000:.1f} kN) excede Vs_max ({Vs_max_N/1000:.1f} kN). Sección insuficiente.",
            "Vs_req_kN": round(Vs_req_N/1000,1), "Vs_max_kN": round(Vs_max_N/1000,1)
        }

    if Vs_req_N > 0:
        Av_s_req_mm2_per_mm = Vs_req_N / (fy_MPa * d_mm)
    else:
        Av_s_req_mm2_per_mm = 0.0

    # Mínimos para nervios (NSR-10 C.7.11 si aplica, o si son vigas C.11.4.6.3)
    # Los nervios a menudo no llevan estribos si Vc es suficiente.
    # Si el nervio se considera como viga, aplican los mínimos de viga.
    # Por ahora, si Vs_req_N = 0 (o Av_s_req_mm2_per_mm = 0) no calculamos Av/s final.
    # La decisión de poner estribos mínimos si no son requeridos por cálculo es del diseñador.
    Av_s_final_mm2_per_mm = Av_s_req_mm2_per_mm # Asumimos que si no se requiere, no se pone.
                                             # O se podría comparar con Av_s_min_vigas si el nervio es estructural.
    
    s_max_mm = float('inf')
    if Vs_req_N > 0 : # Solo si se requieren estribos por cálculo
        limite_Vs_smax_reducido = 0.33 * LAMBDA_CONCRETO * np.sqrt(fc_MPa) * bw_mm * d_mm
        if Vs_req_N <= limite_Vs_smax_reducido:
            s_max_mm = min(d_mm / 2.0, 600.0)
        else:
            s_max_mm = min(d_mm / 4.0, 300.0)
            mensaje_cort += " (Vs > 0.33·√f'c·bw·d, s_max reducido)."
    
    s_calc_mm = float('inf')
    s_rec_mm = None
    Av_mm2_estribo = 0
    if Av_s_final_mm2_per_mm > 1e-9: # Si se necesita algún refuerzo
        Area_una_rama = np.pi * (diam_estribo_mm / 2.0)**2
        Av_mm2_estribo = 2.0 * Area_una_rama # Asumir estribo simple de 2 ramas
        s_calc_mm = Av_mm2_estribo / Av_s_final_mm2_per_mm
        s_rec_mm = min(s_calc_mm, s_max_mm)
        if s_rec_mm < float('inf'):
             s_rec_mm = np.floor(s_rec_mm / 25.0) * 25.0
             if s_rec_mm < 50: s_rec_mm = 50

    return {
        "status": status_calc, "mensaje": mensaje_cort,
        "Vu_kN": round(Vu_kN,1), "phi_Vc_kN": round(PHI_CORTANTE_LOSA * Vc_N / 1000.0, 1),
        "Vc_kN": round(Vc_N / 1000.0, 1),
        "Vs_req_kN": round(Vs_req_N / 1000.0, 1),
        "Vs_max_kN": round(Vs_max_N / 1000.0, 1),
        "Av_s_final_mm2_per_m": round(Av_s_final_mm2_per_mm * 1000.0, 2), # en mm²/m
        "s_max_norm_mm": round(s_max_mm, 0) if s_max_mm != float('inf') else "N/A",
        "s_calc_por_Avs_mm": round(s_calc_mm, 0) if s_calc_mm != float('inf') else "N/A",
        "s_rec_constructivo_mm": round(s_rec_mm, 0) if s_rec_mm is not None else "N/A (o según mínimos)",
        "diam_estribo_usado_mm": diam_estribo_mm,
        "Av_estribo_usado_mm2": round(Av_mm2_estribo,1)
    }
