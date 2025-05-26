# ==============================================================================
# DISEÑO ESTRUCTURAL DE TRAMOS DE ESCALERA (COMO LOSA INCLINADA)
# ==============================================================================
import numpy as np
from unidades import cm_to_m, m_to_cm, kn_to_n, n_to_kn, mm2_to_cm2, cm2_to_mm2, cm_to_mm, mm_to_cm
from validate_positive import validate_positive
from .diseno_vigas import diseno_viga_flexion_simple # Reutilizamos para el diseño a flexión

GAMMA_CONCRETO_KN_M3_ESC = 24.0 # Peso específico del concreto en kN/m³
PHI_FLEXION_ESC = 0.90

def diseno_tramo_escalera_losa_inclinada(
    # Geometría del tramo
    huella_cm,                # Ancho de la huella (run)
    contrahuella_cm,          # Altura de la contrahuella (rise)
    num_pasos,                # Número de pasos en el tramo
    ancho_tramo_m,            # Ancho del tramo de escalera
    espesor_losa_garganta_cm, # Espesor de la losa inclinada (garganta)
    # Materiales
    fc_MPa,
    fy_MPa,
    # Cargas (adicionales a peso propio, por m² de área horizontal proyectada)
    carga_muerta_adic_kNm2,   # Acabados, pasamanos, etc. en kN/m² (proyectado)
    carga_viva_kNm2,          # Carga viva según uso en kN/m² (proyectado)
    # Refuerzo
    rec_libre_cm,
    diam_barra_ppal_mm
):
    """
    Diseña el refuerzo para un tramo de escalera, considerado como una losa inclinada
    simplemente apoyada en sus extremos (proyección horizontal).
    El diseño se realiza por metro de ancho y luego se ajusta al ancho del tramo.
    """
    try:
        validate_positive(huella_cm=huella_cm, contrahuella_cm=contrahuella_cm, num_pasos=num_pasos,
                          ancho_tramo_m=ancho_tramo_m, espesor_losa_garganta_cm=espesor_losa_garganta_cm,
                          fc_MPa=fc_MPa, fy_MPa=fy_MPa, rec_libre_cm=rec_libre_cm,
                          diam_barra_ppal_mm=diam_barra_ppal_mm)
        if carga_muerta_adic_kNm2 < 0: carga_muerta_adic_kNm2 = 0
        if carga_viva_kNm2 < 0: carga_viva_kNm2 = 0

        # --- 1. Cálculos Geométricos ---
        long_horiz_paso_m = cm_to_m(huella_cm)
        altura_paso_m = cm_to_m(contrahuella_cm)
        
        long_horiz_tramo_m = num_pasos * long_horiz_paso_m
        altura_total_tramo_m = num_pasos * altura_paso_m
        
        long_inclinada_paso_m = np.sqrt(long_horiz_paso_m**2 + altura_paso_m**2)
        angulo_rad = np.arctan(altura_paso_m / long_horiz_paso_m)
        cos_angulo = np.cos(angulo_rad)

        if cos_angulo == 0: # Evitar división por cero si la escalera es vertical (improbable)
            raise ValueError("La escalera no puede ser completamente vertical (ángulo de 90 grados).")

        # Espesor promedio de la losa inclinada (considerando los escalones)
        # t_promedio = t_garganta / cos(angulo) + h_escalon / 2 (aproximación)
        espesor_garganta_m = cm_to_m(espesor_losa_garganta_cm)
        # Área de un escalón (triángulo) por metro de ancho de huella
        area_un_escalon_m2 = (long_horiz_paso_m * altura_paso_m) / 2.0
        # Volumen de escalones por metro de longitud horizontal de escalera, por metro de ancho
        vol_escalones_por_m_horiz_m3_m = area_un_escalon_m2 / long_horiz_paso_m
        
        # --- 2. Cálculo de Cargas por metro de ancho de escalera ---
        # Peso propio de la garganta (losa inclinada) por m² de proyección horizontal
        peso_garganta_kNm2_proy_horiz = (espesor_garganta_m / cos_angulo) * GAMMA_CONCRETO_KN_M3_ESC
        
        # Peso propio de los escalones por m² de proyección horizontal
        peso_escalones_kNm2_proy_horiz = vol_escalones_por_m_horiz_m3_m * GAMMA_CONCRETO_KN_M3_ESC
        
        carga_muerta_total_kNm2_proy_horiz = peso_garganta_kNm2_proy_horiz + peso_escalones_kNm2_proy_horiz + carga_muerta_adic_kNm2
        
        # Cargas últimas por metro de ancho (proyección horizontal)
        # Usando combinación 1.2 CM + 1.6 CV (NSR-10 B.2.4-1c)
        wu_kNm_por_m_ancho_proy_horiz = 1.2 * carga_muerta_total_kNm2_proy_horiz + 1.6 * carga_viva_kNm2
        
        # --- 3. Cálculo del Momento de Diseño ---
        # Asumiendo simplemente apoyada en la longitud horizontal proyectada
        Mu_kNm_por_m_ancho = (wu_kNm_por_m_ancho_proy_horiz * long_horiz_tramo_m**2) / 8.0
        
        # --- 4. Diseño a Flexión (Acero Principal) ---
        # Se diseña una franja de 1m de ancho.
        # El recubrimiento se toma a la fibra, la función de viga calculará 'd'.
        # Para losas, no hay estribos, así que diam_estribo_mm = 0.
        resultados_flexion_esc = diseno_viga_flexion_simple(
            b_cm=100.0,  # Ancho de diseño de 1 metro
            h_cm=espesor_losa_garganta_cm, # Usar el espesor de la garganta para 'h'
            rec_libre_cm=rec_libre_cm,
            diam_estribo_mm=0,
            diam_barra_long_mm=diam_barra_ppal_mm,
            fc_MPa=fc_MPa,
            fy_MPa=fy_MPa,
            Mu_kNm=Mu_kNm_por_m_ancho
        )

        if resultados_flexion_esc["status"] == "Error":
            raise Exception(f"Error en diseño a flexión de la escalera: {resultados_flexion_esc['mensaje']}")

        As_req_ppal_cm2_por_m = resultados_flexion_esc["As_req_cm2"]
        As_req_ppal_mm2_por_m = cm2_to_mm2(As_req_ppal_cm2_por_m)
        d_efectivo_mm_esc = resultados_flexion_esc.get("d_mm", 0)
        
        area_una_barra_ppal_mm2 = np.pi * (diam_barra_ppal_mm / 2.0)**2
        s_calculado_ppal_cm = (area_una_barra_ppal_mm2 / As_req_ppal_mm2_por_m) * 100.0 if As_req_ppal_mm2_por_m > 1e-6 else float('inf')
        
        # Espaciamiento máximo para losas (NSR-10 C.7.6.5)
        s_max_norma_ppal_cm = min(3 * espesor_losa_garganta_cm, 45.0)
        s_final_ppal_cm = min(s_calculado_ppal_cm, s_max_norma_ppal_cm)
        if As_req_ppal_mm2_por_m <= 1e-6 : s_final_ppal_cm = s_max_norma_ppal_cm


        # --- 5. Acero de Repartición (Transversal) (NSR-10 C.7.12) ---
        Ag_mm2_por_m = 1000 * cm_to_mm(espesor_losa_garganta_cm) # b_mm = 1000 mm
        rho_temp = 0.0018 if fy_MPa >= 420 else 0.0020
        As_req_temp_mm2_por_m = rho_temp * Ag_mm2_por_m
        
        diam_barra_temp_mm = 9.5 # Ejemplo: #3 (3/8")
        area_una_barra_temp_mm2 = np.pi * (diam_barra_temp_mm / 2.0)**2
        s_calculado_temp_cm = (area_una_barra_temp_mm2 / As_req_temp_mm2_por_m) * 100.0 if As_req_temp_mm2_por_m > 1e-6 else float('inf')
        
        s_max_norma_temp_cm = min(5 * espesor_losa_garganta_cm, 45.0)
        s_final_temp_cm = min(s_calculado_temp_cm, s_max_norma_temp_cm)

        # --- 6. Verificación de Espesor Mínimo (Informativo) ---
        # Para losas macizas simplemente apoyadas, h_min = L_n / 20 (NSR-10 Tabla C.9.5(a))
        # Usar L_n como la longitud horizontal proyectada
        h_min_deflex_cm = m_to_cm(long_horiz_tramo_m) / 20.0
        mensaje_h_min = f"Espesor mínimo por deflexión (aprox. L_n/20): {h_min_deflex_cm:.1f} cm. (L_n horizontal = {long_horiz_tramo_m:.2f} m)"
        if espesor_losa_garganta_cm < h_min_deflex_cm:
            mensaje_h_min += " ¡ADVERTENCIA: Espesor actual podría ser insuficiente por deflexiones!"
        else:
            mensaje_h_min += " OK respecto a L_n/20."
            
        return {
            "status": "OK",
            "long_horiz_tramo_m": round(long_horiz_tramo_m, 2),
            "altura_total_tramo_m": round(altura_total_tramo_m, 2),
            "angulo_grados": round(np.degrees(angulo_rad), 1),
            "carga_muerta_total_kNm2_proy": round(carga_muerta_total_kNm2_proy_horiz, 2),
            "carga_viva_kNm2_proy": round(carga_viva_kNm2, 2),
            "carga_ultima_wu_kNm_por_m_proy": round(wu_kNm_por_m_ancho_proy_horiz, 2),
            "momento_ultimo_Mu_kNm_por_m": round(Mu_kNm_por_m_ancho, 2),
            "d_efectivo_cm": round(mm_to_cm(d_efectivo_mm_esc), 1),
            "acero_principal": {
                "As_req_cm2_por_m": round(mm2_to_cm2(As_req_ppal_mm2_por_m), 3),
                "diam_barra_mm": diam_barra_ppal_mm,
                "espaciamiento_cm": round(s_final_ppal_cm, 1) if s_final_ppal_cm != float('inf') else "N/A (Revisar Mín.)"
            },
            "acero_reparticion": {
                "As_req_cm2_por_m": round(mm2_to_cm2(As_req_temp_mm2_por_m), 3),
                "diam_barra_mm": diam_barra_temp_mm,
                "espaciamiento_cm": round(s_final_temp_cm, 1) if s_final_temp_cm != float('inf') else "N/A (Revisar Mín.)"
            },
            "verificacion_espesor": mensaje_h_min
        }

    except ValueError as ve:
        return {"status": "Error en datos de entrada", "mensaje": str(ve)}
    except Exception as e:
        return {"status": "Error en cálculo de escalera", "mensaje": str(e)}
