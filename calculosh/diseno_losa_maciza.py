# ==============================================================================
# DISEÑO DE LOSAS MACIZAS UNIDIRECCIONALES
# ==============================================================================
import numpy as np
from unidades import *
from validate_positive import validate_positive
from .diseno_vigas import diseno_viga_flexion_simple

PHI_FLEXION_LOSA = 0.90

def diseno_losa_maciza_unidireccional(
    h_losa_cm,
    fc_MPa,
    fy_MPa,
    rec_libre_cm,
    Mu_kNm_por_m,
    diam_barra_ppal_mm
):
    """
    Diseña una losa maciza unidireccional por metro de ancho.
    Calcula el acero principal y el de temperatura/retracción.
    Retorna un diccionario con los resultados.
    """
    # Definir una estructura de retorno por defecto para errores, incluyendo todas las claves esperadas
    default_error_return = {
        "status": "Error",
        "mensaje": "Error no especificado en diseño de losa.",
        "As_req_ppal_cm2_por_m": 0, # O float('inf') si prefieres
        "espaciamiento_ppal_cm": "N/A",
        "diam_barra_ppal_usada_mm": diam_barra_ppal_mm, # Devolver el input
        "As_req_temp_cm2_por_m": 0,
        "espaciamiento_temp_cm": "N/A",
        "diam_barra_temp_usada_mm": 9.5, # Un default común
        "mensaje_espesor": "Cálculo no completado debido a error.", # Clave que faltaba
        "d_efectivo_ppal_cm": 0
    }

    try:
        validate_positive(h_losa_cm=h_losa_cm, fc_MPa=fc_MPa, fy_MPa=fy_MPa, 
                          rec_libre_cm=rec_libre_cm, diam_barra_ppal_mm=diam_barra_ppal_mm)
        if Mu_kNm_por_m < 0:
            Mu_kNm_por_m = abs(Mu_kNm_por_m)

        resultados_flexion_losa = diseno_viga_flexion_simple(
            b_cm=100.0,
            h_cm=h_losa_cm,
            rec_libre_cm=rec_libre_cm,
            diam_estribo_mm=0,
            diam_barra_long_mm=diam_barra_ppal_mm,
            fc_MPa=fc_MPa,
            fy_MPa=fy_MPa,
            Mu_kNm=Mu_kNm_por_m
        )

        if resultados_flexion_losa["status"] == "Error":
            # Usar la estructura de error por defecto y actualizar el mensaje específico
            error_return = default_error_return.copy()
            error_return["status"] = "Error en cálculo de flexión para la losa"
            error_return["mensaje"] = resultados_flexion_losa["mensaje"]
            return error_return

        As_req_ppal_cm2_por_m = resultados_flexion_losa["As_req_cm2"]
        As_req_ppal_mm2_por_m = cm2_to_mm2(As_req_ppal_cm2_por_m)
        d_efectivo_mm = resultados_flexion_losa.get("d_mm", 0) # Obtener d_mm de los resultados de flexión

        area_una_barra_ppal_mm2 = np.pi * (diam_barra_ppal_mm / 2.0)**2
        
        if As_req_ppal_mm2_por_m > 1e-6:
            s_calculado_ppal_cm = (area_una_barra_ppal_mm2 / As_req_ppal_mm2_por_m) * 100.0
        else:
            s_calculado_ppal_cm = float('inf') 
            
        s_max_norma_ppal_cm = min(3 * h_losa_cm, 45.0)
        s_final_ppal_cm = min(s_calculado_ppal_cm, s_max_norma_ppal_cm)
        
        if As_req_ppal_cm2_por_m <= cm2_to_mm2(0.0001): # Si es prácticamente cero
             s_final_ppal_cm = s_max_norma_ppal_cm

        Ag_mm2_por_m = 1000 * cm_to_mm(h_losa_cm)
        
        rho_temp = 0.0018 if fy_MPa >= 420 else 0.0020
        
        As_req_temp_mm2_por_m = rho_temp * Ag_mm2_por_m
        
        diam_barra_temp_mm = 9.5 
        area_una_barra_temp_mm2 = np.pi * (diam_barra_temp_mm / 2.0)**2
        
        if As_req_temp_mm2_por_m > 1e-6:
            s_calculado_temp_cm = (area_una_barra_temp_mm2 / As_req_temp_mm2_por_m) * 100.0
        else:
            s_calculado_temp_cm = float('inf')
            
        s_max_norma_temp_cm = min(5 * h_losa_cm, 45.0)
        s_final_temp_cm = min(s_calculado_temp_cm, s_max_norma_temp_cm)

        mensaje_h_min = ("Recordatorio: Verificar espesor mínimo de losa según Tabla C.9.5(a) "
                         "de la NSR-10 (ej. $L_n/20$ para apoyos simples, $L_n/24$ para un "
                         "extremo continuo, etc., donde $L_n$ es la luz libre).")

        return {
            "status": "OK",
            "mensaje": "Diseño de losa completado.", # Mensaje general de éxito
            "As_req_ppal_cm2_por_m": round(As_req_ppal_cm2_por_m, 3),
            "espaciamiento_ppal_cm": round(s_final_ppal_cm, 1) if s_final_ppal_cm != float('inf') else "N/A (Máx. normativo)",
            "diam_barra_ppal_usada_mm": diam_barra_ppal_mm,
            "As_req_temp_cm2_por_m": round(mm2_to_cm2(As_req_temp_mm2_por_m), 3),
            "espaciamiento_temp_cm": round(s_final_temp_cm, 1) if s_final_temp_cm != float('inf') else "N/A (Máx. normativo)",
            "diam_barra_temp_usada_mm": diam_barra_temp_mm,
            "mensaje_espesor": mensaje_h_min,
            "d_efectivo_ppal_cm": round(mm_to_cm(d_efectivo_mm), 1)
        }

    except ValueError as e:
        error_return = default_error_return.copy()
        error_return["status"] = "Error en datos de entrada para losa"
        error_return["mensaje"] = str(e)
        return error_return
    except Exception as e_gen:
        error_return = default_error_return.copy()
        error_return["status"] = "Error general en cálculo de losa"
        error_return["mensaje"] = str(e_gen)
        return error_return
