# ==============================================================================
# DISEÑO DE ZAPATA AISLADA
# ==============================================================================
import numpy as np
from unidades import *
from validate_positive import validate_positive

# Asumiendo algunas constantes 
PHI_FLEXION_ZAP = 0.90
PHI_CORTANTE_ZAP = 0.75
LAMBDA_CONCRETO_ZAP = 1.0 # Para concreto de peso normal
GAMMA_CONCRETO_KN_M3 = 24.0
GAMMA_SUELO_PROMEDIO_KN_M3 = 18.0 # Promedio para relleno sobre zapata

def _calcular_presion_en_punto(coord_x_m, coord_y_m, P_ultima_kN, Mx_ultima_kNm, My_ultima_kNm, B_m, L_m):
    """
    Calcula la presión última del suelo q_u en un punto (coord_x_m, coord_y_m)
    bajo la zapata, relativo al centroide de la zapata.
    coord_x_m: Coordenada a lo largo de la dimensión B_m.
    coord_y_m: Coordenada a lo largo de la dimensión L_m.
    Retorna presión en N/m2.
    """
    if B_m <= 0 or L_m <= 0: return 0

    Area_zap_m2 = B_m * L_m
    P_u_N = P_ultima_kN * 1000.0
    Mx_u_Nm = Mx_ultima_kNm * 1000.0 # Momento alrededor del eje Y (causa variación a lo largo de L)
    My_u_Nm = My_ultima_kNm * 1000.0 # Momento alrededor del eje X (causa variación a lo largo de B)

    # Momentos de Inercia del área de la zapata
    Ix_zap_m4 = (L_m * B_m**3) / 12.0 # Para My_u_Nm
    Iy_zap_m4 = (B_m * L_m**3) / 12.0 # Para Mx_u_Nm

    q_axial_N_m2 = P_u_N / Area_zap_m2
    
    # El término de momento es M*c/I.
    # Para My (momento alrededor del eje X), la variación es con coord_x_m.
    q_flex_My_N_m2 = (My_u_Nm / Ix_zap_m4) * coord_x_m if Ix_zap_m4 > 0 else 0
    # Para Mx (momento alrededor del eje Y), la variación es con coord_y_m.
    q_flex_Mx_N_m2 = (Mx_u_Nm / Iy_zap_m4) * coord_y_m if Iy_zap_m4 > 0 else 0
    
    return q_axial_N_m2 + q_flex_My_N_m2 + q_flex_Mx_N_m2

def _beta1_zap(fc_MPa): # Copiado de diseno_vigas para evitar dependencia cruzada si es el mismo
    if fc_MPa <= 28.0: return 0.85
    else: return max(0.65, 0.85 - 0.05 * ((fc_MPa - 28.0) / 7.0))

def diseno_zapata_aislada_v2(
    # Cargas (distinguir servicio de últimas)
    P_servicio_kN, Mx_servicio_kNm, My_servicio_kNm, # Para dimensionamiento en planta
    P_ultima_kN, Mx_ultima_kNm, My_ultima_kNm,       # Para diseño de acero y chequeos de cortante
    # Propiedades de materiales y suelo
    fc_MPa, fy_MPa, q_adm_kPa,
    # Dimensiones columna y recubrimiento
    b_col_cm, h_col_cm, rec_libre_zapata_cm, diam_barra_zapata_mm,
    # Opcional: Profundidad para considerar peso propio
    prof_desplante_m=2.0,
    # Parámetros de diseño
    relacion_BL_deseada=None, # Si se quiere forzar una relación B/L
    max_iter_h=10, h_inicial_m_ratio=0.10 # Ratio L/h o B/h para h inicial
    ):
    """
    Diseño de zapata aislada rectangular según NSR‑10.
    1. Dimensiona en planta con cargas de servicio.
    2. Calcula presiones últimas.
    3. Determina peralte 'h' por cortante unidireccional y punzonamiento.
    4. Diseña refuerzo a flexión.
    Sistema interno: N, mm, MPa para cálculos de sección. m, kN para dimensiones globales.
    """
    # --- 1. Validación de Entradas ---
    validate_positive(P_servicio_kN=P_servicio_kN, P_ultima_kN=P_ultima_kN,
                      fc_MPa=fc_MPa, fy_MPa=fy_MPa, q_adm_kPa=q_adm_kPa,
                      b_col_cm=b_col_cm, h_col_cm=h_col_cm,
                      rec_libre_zapata_cm=rec_libre_zapata_cm, diam_barra_zapata_mm=diam_barra_zapata_mm)
    if P_ultima_kN < P_servicio_kN:
        return {"status": "Error", "mensaje": "P_ultima_kN no puede ser menor que P_servicio_kN."}

    # --- 2. Conversión de Unidades Iniciales y Parámetros ---
    b_col_m = cm_to_m(b_col_cm)
    h_col_m = cm_to_m(h_col_cm)
    q_adm_N_m2 = q_adm_kPa * 1000.0

    # --- 3. Dimensionamiento en Planta (con Cargas de Servicio) ---
    # Referencia: Bowles - Foundation Analysis and Design
    # Considerar excentricidades de servicio
    ex_serv_L = abs(Mx_servicio_kNm / P_servicio_kN) if P_servicio_kN else 0 # Excentricidad en dirección L (paralela a h_col_m)
    ey_serv_B = abs(My_servicio_kNm / P_servicio_kN) if P_servicio_kN else 0 # Excentricidad en dirección B (paralela a b_col_m)

    # Estimación inicial de área requerida (sin excentricidad)
    Area_req_min_m2 = P_servicio_kN / q_adm_kPa

    # Iteración para encontrar B y L (simplificada)
    # Se puede usar el método de área efectiva de Meyerhof para un cálculo más exacto.
    # Por ahora, un enfoque iterativo simple o una estimación basada en aumentar el área.
    # Bowles sugiere incrementar el área entre un 20% y 50% para excentricidades moderadas.
    # O usar B'L' = P_serv / q_adm con B' = B - 2*ey_serv_B, L' = L - 2*ex_serv_L
    
    # Método iterativo simple para B y L (puede mejorarse con optimización)
    # Se busca que q_max_servicio <= q_adm y q_min_servicio >= 0
    if relacion_BL_deseada:
        L_m = np.sqrt(Area_req_min_m2 / relacion_BL_deseada)
        B_m = L_m * relacion_BL_deseada
    else: # Asumir cuadrada inicialmente o proporcional a la columna + excentricidades
        ratio_col_exc = (h_col_m + 2 * ex_serv_L) / (b_col_m + 2 * ey_serv_B) if (b_col_m + 2 * ey_serv_B) > 0 else 1
        B_m = np.sqrt(Area_req_min_m2 * ratio_col_exc)
        L_m = Area_req_min_m2 / B_m if B_m > 0 else np.sqrt(Area_req_min_m2)
        if B_m == 0: B_m = L_m # Si B_m es 0, hacer cuadrada

    for _ in range(10): # Iterar para ajustar B y L
        Area_zap_m2 = B_m * L_m
        if Area_zap_m2 == 0: Area_zap_m2 = 1e-6 # Evitar división por cero

        # Presiones de servicio (N/m²)
        q_unif_serv_N_m2 = (P_servicio_kN * 1000) / Area_zap_m2
        q_flex_L_serv_N_m2 = (Mx_servicio_kNm * 1000 * 6) / (B_m * L_m**2) if B_m * L_m**2 >0 else 0
        q_flex_B_serv_N_m2 = (My_servicio_kNm * 1000 * 6) / (L_m * B_m**2) if L_m * B_m**2 >0 else 0
        
        q_max_serv_N_m2 = q_unif_serv_N_m2 + abs(q_flex_L_serv_N_m2) + abs(q_flex_B_serv_N_m2)
        q_min_serv_N_m2 = q_unif_serv_N_m2 - abs(q_flex_L_serv_N_m2) - abs(q_flex_B_serv_N_m2)

        if q_max_serv_N_m2 <= q_adm_N_m2 * 1.05 and q_min_serv_N_m2 >= -0.05 * q_adm_N_m2: # Tolerancia 5%
            break
        
        # Ajustar dimensiones (simple escalado)
        ratio_ajuste = np.sqrt(q_max_serv_N_m2 / q_adm_N_m2) if q_adm_N_m2 > 0 else 1.1
        B_m *= ratio_ajuste
        L_m *= ratio_ajuste
    else: # Si no converge
        # st.warning("Dimensionamiento de zapata no convergió bien, verificar presiones.")
        pass

    B_m = np.ceil(B_m * 20) / 20.0 # Redondear a múltiplos de 5 cm
    L_m = np.ceil(L_m * 20) / 20.0
    Area_zap_m2 = B_m * L_m
    
    # --- 4. Presiones Últimas de Diseño (Netas o Brutas) ---
    # q_u = P_ultima / (B*L) +/- 6*Mx_ultima / (B*L^2) +/- 6*My_ultima / (L*B^2)
    # Estas son las presiones que el suelo ejerce sobre la zapata.
    # Para el diseño de la zapata, estas son las cargas.
    q_unif_ult_N_m2 = (P_ultima_kN * 1000) / Area_zap_m2 if Area_zap_m2 > 0 else 0
    # Momentos últimos respecto al centroide de la zapata
    q_flex_L_ult_N_m2 = (Mx_ultima_kNm * 1000 * 6) / (B_m * L_m**2) if B_m * L_m**2 > 0 else 0
    q_flex_B_ult_N_m2 = (My_ultima_kNm * 1000 * 6) / (L_m * B_m**2) if L_m * B_m**2 > 0 else 0

    # Presiones en las esquinas (A, B, C, D) - Para diseño de voladizos
    # Coordenadas esquinas (m) respecto al centroide de la zapata:
    # A: (-B/2, -L/2), B: (B/2, -L/2), C: (B/2, L/2), D: (-B/2, L/2)
    q_ult_esq = [
        q_unif_ult_N_m2 - q_flex_L_ult_N_m2 - q_flex_B_ult_N_m2, # q @ (-L/2, -B/2)
        q_unif_ult_N_m2 - q_flex_L_ult_N_m2 + q_flex_B_ult_N_m2, # q @ (-L/2, +B/2)
        q_unif_ult_N_m2 + q_flex_L_ult_N_m2 + q_flex_B_ult_N_m2, # q @ (+L/2, +B/2)
        q_unif_ult_N_m2 + q_flex_L_ult_N_m2 - q_flex_B_ult_N_m2  # q @ (+L/2, -B/2)
    ]
    q_u_max_N_m2 = max(q_ult_esq)
    q_u_min_N_m2 = min(q_ult_esq)

    # Simplificación: Usar una presión promedio o la máxima para el diseño de los voladizos si la variación es pequeña.
    # O la presión en el centroide de la carga del voladizo.
    # Para este cálculo, usaremos una presión promedio para voladizos si no hay despegue,
    # o una distribución trapezoidal/triangular si hay despegue (q_u_min < 0).
    # Por ahora, simplificaremos usando q_u_promedio_voladizo = (q_u_max + q_u_borde_columna) / 2
    # O más simple, q_u_reaccion_total = P_ultima_kN / Area_zap_m2 para cortantes, y distribución lineal para momentos.

    # --- 5. Determinación del Peralte 'h' (Iterativo) ---
    h_m = max(L_m, B_m) * h_inicial_m_ratio # Estimación inicial de peralte
    h_m = max(h_m, 0.3) # Mínimo constructivo (ej. 30cm)
    
    rec_libre_zap_mm = cm_to_mm(rec_libre_zapata_cm)
    d_barra_zap_mm = diam_barra_zapata_mm

    cortante_ok = False
    iter_h = 0
    
    resultados_cortante_uni_L = {} # Para voladizo en dirección L
    resultados_cortante_uni_B = {} # Para voladizo en dirección B
    resultados_punzonamiento = {}

    while not cortante_ok and iter_h < max_iter_h:
        iter_h += 1
        h_mm = m_to_mm(h_m)
        # Peralte efectivo (promedio para ambas direcciones, o usar d_L y d_B)
        # Usar d_promedio: h - rec_libre - diam_barra (no 1.5*diam_barra, sino al centro de la parrilla)
        d_mm = h_mm - rec_libre_zap_mm - d_barra_zap_mm 
        if d_mm <= 0: # Si h es muy pequeño
            h_m += 0.05 # Incrementar h y reintentar
            if iter_h >= max_iter_h: return {"status": "Error", "mensaje": "No se pudo obtener 'd' positivo."}
            continue
        d_m = mm_to_m(d_mm)

        # --- 5a. Chequeo Cortante Unidireccional (Viga Ancha) ---
        # Dirección L (armado paralelo a B, voladizo en L)
        voladizo_total_L_m = (L_m - h_col_m) / 2.0
        seccion_critica_Vud_L_m = voladizo_total_L_m - d_m # Distancia desde borde de zapata a sección crítica de cortante

        if seccion_critica_Vud_L_m > 0:
            # Coordenadas 'y' (relativas al centroide de la zapata) para el tramo de cortante
            y_borde_zapata = L_m / 2.0
            y_seccion_critica_cortante = h_col_m / 2.0 + d_m # Distancia desde centroide a sección crítica

            # Presiones en el eje x=0 (centro de la zapata en la dirección B)
            q_a_borde_zapata_Ldir = _calcular_presion_en_punto(0, y_borde_zapata, P_ultima_kN, Mx_ultima_kNm, My_ultima_kNm, B_m, L_m)
            q_a_seccion_critica_Ldir = _calcular_presion_en_punto(0, y_seccion_critica_cortante, P_ultima_kN, Mx_ultima_kNm, My_ultima_kNm, B_m, L_m)
            
            # Fuerza cortante Vud_L (considerando el ancho B_m y la longitud del voladizo efectivo para cortante)
            # Longitud sobre la cual actúa la presión para este cortante: (L_m/2 - y_seccion_critica_cortante) = seccion_critica_Vud_L_m
            Vud_L_N = B_m * seccion_critica_Vud_L_m * (q_a_borde_zapata_Ldir + q_a_seccion_critica_Ldir) / 2.0
            phi_Vc_L_N = PHI_CORTANTE_ZAP * 0.17 * LAMBDA_CONCRETO_ZAP * np.sqrt(fc_MPa) * (B_m * 1000) * d_mm
            resultados_cortante_uni_L = {"Vud_kN": n_to_kn(Vud_L_N), "phiVc_kN": n_to_kn(phi_Vc_L_N), "ok": abs(Vud_L_N) <= abs(phi_Vc_L_N)}
        else:
            Vud_L_N = 0; phi_Vc_L_N = float('inf'); resultados_cortante_uni_L = {"Vud_kN": 0, "phiVc_kN": 0, "ok": True, "nota": "Sección crítica de cortante unidireccional (L) fuera del voladizo."}

        # Dirección B (armado paralelo a L, voladizo en B)
        voladizo_total_B_m = (B_m - b_col_m) / 2.0
        seccion_critica_Vud_B_m = voladizo_total_B_m - d_m

        if seccion_critica_Vud_B_m > 0:
            x_borde_zapata = B_m / 2.0
            x_seccion_critica_cortante = b_col_m / 2.0 + d_m

            q_a_borde_zapata_Bdir = _calcular_presion_en_punto(x_borde_zapata, 0, P_ultima_kN, Mx_ultima_kNm, My_ultima_kNm, B_m, L_m)
            q_a_seccion_critica_Bdir = _calcular_presion_en_punto(x_seccion_critica_cortante, 0, P_ultima_kN, Mx_ultima_kNm, My_ultima_kNm, B_m, L_m)
            
            Vud_B_N = L_m * seccion_critica_Vud_B_m * (q_a_borde_zapata_Bdir + q_a_seccion_critica_Bdir) / 2.0
            phi_Vc_B_N = PHI_CORTANTE_ZAP * 0.17 * LAMBDA_CONCRETO_ZAP * np.sqrt(fc_MPa) * (L_m * 1000) * d_mm
            resultados_cortante_uni_B = {"Vud_kN": n_to_kn(Vud_B_N), "phiVc_kN": n_to_kn(phi_Vc_B_N), "ok": abs(Vud_B_N) <= abs(phi_Vc_B_N)}
        else:
            Vud_B_N = 0; phi_Vc_B_N = float('inf'); resultados_cortante_uni_B = {"Vud_kN": 0, "phiVc_kN": 0, "ok": True, "nota": "Sección crítica de cortante unidireccional (B) fuera del voladizo."}


        # Dirección B (flexión alrededor del eje paralelo a L, cortante en caras paralelas a L)
        dist_crit_B = (B_m - b_col_m) / 2.0 - d_m
        if dist_crit_B > 0:
            q_prom_para_Vud_B = (P_ultima_kN*1000) / (B_m*L_m)
            Vud_B_N = q_prom_para_Vud_B * dist_crit_B * L_m
            phi_Vc_B_N = PHI_CORTANTE_ZAP * 0.17 * LAMBDA_CONCRETO_ZAP * np.sqrt(fc_MPa) * L_m * 1000 * d_mm
            resultados_cortante_uni_B = {"Vud_kN": n_to_kn(Vud_B_N), "phiVc_kN": n_to_kn(phi_Vc_B_N), "ok": Vud_B_N <= phi_Vc_B_N}
        else:
            Vud_B_N = 0; phi_Vc_B_N = float('inf'); resultados_cortante_uni_B = {"Vud_kN": 0, "phiVc_kN": 0, "ok": True, "nota": "Sección crítica fuera del voladizo."}

        # --- 5b. Chequeo Punzonamiento (Cortante Bidireccional) ---
        # Perímetro crítico b0 (NSR-10 C.11.11.1.2)
        b0_mm = 2 * ((b_col_m * 1000 + d_mm) + (h_col_m * 1000 + d_mm))
        # Fuerza cortante de punzonamiento Vup (NSR-10 C.15.5.1)
        # P_ultima_neta = P_ultima - presión promedio bajo área crítica (b_col+d)(h_col+d)
        area_crit_punz_m2 = (b_col_m + d_m) * (h_col_m + d_m)
        # Vup_N = P_ultima_kN * 1000 - (P_ultima_kN * 1000 / Area_zap_m2) * area_crit_punz_m2 if Area_zap_m2 > 0 else P_ultima_kN * 1000
        Vup_N = P_ultima_kN * 1000 * (1 - area_crit_punz_m2 / Area_zap_m2) if Area_zap_m2 > area_crit_punz_m2 else 0 # Simplificado


        # Resistencia al punzonamiento phi*Vc (NSR-10 C.11.11.2.1)
        # beta_c = max(h_col_m, b_col_m) / min(h_col_m, b_col_m) # Relación lado largo a corto de la columna
        beta_c = max(m_to_cm(h_col_m), m_to_cm(b_col_m)) / min(m_to_cm(h_col_m), m_to_cm(b_col_m)) if min(m_to_cm(h_col_m), m_to_cm(b_col_m)) > 0 else 1

        # alpha_s: 40 para columnas interiores, 30 borde, 20 esquina
        alpha_s = 40 # Asumir columna interior
        
        vc1_MPa = 0.33 * LAMBDA_CONCRETO_ZAP * np.sqrt(fc_MPa)
        vc2_MPa = 0.17 * LAMBDA_CONCRETO_ZAP * (1 + 2 / beta_c) * np.sqrt(fc_MPa)
        vc3_MPa = 0.083 * LAMBDA_CONCRETO_ZAP * (alpha_s * d_mm / b0_mm + 2) * np.sqrt(fc_MPa) if b0_mm > 0 else float('inf')
        
        vc_MPa = min(vc1_MPa, vc2_MPa, vc3_MPa)
        phi_Vc_punz_N = PHI_CORTANTE_ZAP * vc_MPa * b0_mm * d_mm
        resultados_punzonamiento = {"Vup_kN": n_to_kn(Vup_N), "phiVc_kN": n_to_kn(phi_Vc_punz_N), "ok": Vup_N <= phi_Vc_punz_N,
                                   "b0_cm": mm_to_cm(b0_mm), "vc_MPa": round(vc_MPa,2)}

        cortante_ok = resultados_cortante_uni_L["ok"] and resultados_cortante_uni_B["ok"] and resultados_punzonamiento["ok"]
        
        if not cortante_ok:
            h_m += 0.05 # Incrementar peralte 5 cm
    
    if iter_h >= max_iter_h and not cortante_ok:
        # Aunque no convergió, necesitamos valores para 'h' para el reporte de error
        # y para evitar errores de variables no definidas si se intentara continuar.
        # Las variables h_m y d_mm tendrán los valores de la última iteración.
        return {"status": "Error", "mensaje": "Peralte 'h' no convergió por cortante tras varias iteraciones.",
                "B_m": round(B_m,2), "L_m": round(L_m,2), "h_propuesto_m": round(h_m,2), "d_propuesto_m": round(mm_to_m(d_mm),3) if 'd_mm' in locals() else 'N/A',
                "chequeo_cortante_unidir_L": resultados_cortante_uni_L,
                "chequeo_cortante_unidir_B": resultados_cortante_uni_B,
                "chequeo_punzonamiento": resultados_punzonamiento
               }
    
    # Si el bucle terminó exitosamente (cortante_ok es True) o si se quiere proceder
    # con el último 'h_m' calculado aunque no sea 100% ok (lo cual no debería pasar si se retorna error arriba).
    # ASEGURAR QUE h_m y d_mm TENGAN VALORES VÁLIDOS DE LA ÚLTIMA ITERACIÓN.
    # Estas asignaciones deben estar aquí, después del bucle y de la posible salida por error de convergencia.
    h_final_m = h_m
    # 'd_mm' se asigna dentro del bucle, así que su último valor es el que corresponde a h_final_m
    # No es necesario reasignar d_mm aquí si ya tiene el valor correcto de la última iteración.
    # Solo nos aseguramos que exista, lo cual el bucle while garantiza si se ejecuta al menos una vez.
    # Y si el bucle no se ejecuta (lo cual es improbable), h_m y d_mm no estarían definidos.
    # La lógica del bucle 'while' asegura que d_mm se define.
    
    # Recalcular d_final_mm y d_final_m explícitamente con h_final_m para claridad y seguridad
    # (aunque d_mm ya debería tener el valor correcto de la última iteración si cortante_ok=True)
    h_final_mm = m_to_mm(h_final_m) # Convertir h_final_m a mm para cálculo de d_final_mm
    d_final_mm = h_final_mm - rec_libre_zap_mm - d_barra_zap_mm # d promedio
    d_final_m = mm_to_m(d_final_mm)

    # --- 6. Diseño del Refuerzo a Flexión (NSR-10 C.15.3) ---
    # Secciones críticas en la cara de la columna
    voladizo_L_m = (L_m - h_col_m) / 2.0
    if voladizo_L_m > 0:
        y_cara_col_L = h_col_m / 2.0
        y_borde_zap_L = L_m / 2.0
        
        q_u_cara_L_centro = _calcular_presion_en_punto(0, y_cara_col_L, P_ultima_kN, Mx_ultima_kNm, My_ultima_kNm, B_m, L_m)
        q_u_borde_L_centro = _calcular_presion_en_punto(0, y_borde_zap_L, P_ultima_kN, Mx_ultima_kNm, My_ultima_kNm, B_m, L_m)
        
        Mu_L_Nm_total = B_m * (voladizo_L_m**2 / 6.0) * (2 * q_u_borde_L_centro + q_u_cara_L_centro)
        Mu_L_Nmm = Mu_L_Nm_total * 1000.0
        
        # d para esta dirección (barras inferiores, d mayor)
        d_flex_L_mm = h_final_mm - rec_libre_zap_mm - d_barra_zap_mm / 2.0
        
        if (B_m * 1000 * d_flex_L_mm**2) > 0:
            k_L = Mu_L_Nmm / (PHI_FLEXION_ZAP * (B_m * 1000) * d_flex_L_mm**2)
            disc_L = 1.0 - (2.0 * k_L) / (0.85 * fc_MPa) if fc_MPa > 0 else -1
            if disc_L < 0: As_L_req_mm2 = float('inf') 
            else: rho_L = (0.85 * fc_MPa / fy_MPa) * (1.0 - np.sqrt(disc_L)); As_L_req_mm2 = rho_L * (B_m*1000) * d_flex_L_mm
        else:
            As_L_req_mm2 = float('inf') # Evitar división por cero
    else:
        As_L_req_mm2 = 0

    # Dirección B (armado paralelo a L, momento alrededor del eje Y de la zapata)
    voladizo_B_m = (B_m - b_col_m) / 2.0
    if voladizo_B_m > 0:
        x_cara_col_B = b_col_m / 2.0
        x_borde_zap_B = B_m / 2.0
        
        q_u_cara_B_centro = _calcular_presion_en_punto(x_cara_col_B, 0, P_ultima_kN, Mx_ultima_kNm, My_ultima_kNm, B_m, L_m)
        q_u_borde_B_centro = _calcular_presion_en_punto(x_borde_zap_B, 0, P_ultima_kN, Mx_ultima_kNm, My_ultima_kNm, B_m, L_m)

        Mu_B_Nm_total = L_m * (voladizo_B_m**2 / 6.0) * (2 * q_u_borde_B_centro + q_u_cara_B_centro)
        Mu_B_Nmm = Mu_B_Nm_total * 1000.0

        # d para esta dirección (barras superiores en parrilla, d menor)
        d_flex_B_mm = h_final_mm - rec_libre_zap_mm - d_barra_zap_mm - d_barra_zap_mm / 2.0

        if (L_m * 1000 * d_flex_B_mm**2) > 0:
            k_B = Mu_B_Nmm / (PHI_FLEXION_ZAP * (L_m * 1000) * d_flex_B_mm**2)
            disc_B = 1.0 - (2.0 * k_B) / (0.85 * fc_MPa) if fc_MPa > 0 else -1
            if disc_B < 0: As_B_req_mm2 = float('inf')
            else: rho_B = (0.85 * fc_MPa / fy_MPa) * (1.0 - np.sqrt(disc_B)); As_B_req_mm2 = rho_B * (L_m*1000) * d_flex_B_mm
        else:
            As_B_req_mm2 = float('inf') # Evitar división por cero
    else:
        As_B_req_mm2 = 0

    # Cuantía mínima por retracción y temperatura (NSR-10 C.7.6.1.1)
    rho_min_temp = 0.0018 if fy_MPa == 420 else (0.0020 if fy_MPa < 420 else 0.0018 * 420 / fy_MPa)
    
    As_min_L_mm2 = rho_min_temp * (B_m * 1000) * h_final_mm # Refuerzo en dirección L, distribuido en ancho B
    As_min_B_mm2 = rho_min_temp * (L_m * 1000) * h_final_mm # Refuerzo en dirección B, distribuido en ancho L

    As_L_final_mm2 = max(As_L_req_mm2 if As_L_req_mm2 != float('inf') else As_min_L_mm2, As_min_L_mm2)
    As_B_final_mm2 = max(As_B_req_mm2 if As_B_req_mm2 != float('inf') else As_min_B_mm2, As_min_B_mm2)
    
    As_L_final_mm2_per_m = As_L_final_mm2 / B_m if B_m > 0 else 0
    As_B_final_mm2_per_m = As_B_final_mm2 / L_m if L_m > 0 else 0

    return {
        "status": "OK",
        "mensaje": "Diseño de zapata completado.",
        "dimensiones_planta": {"B_m": round(B_m,2), "L_m": round(L_m,2), "Area_m2": round(Area_zap_m2,2)},
        "peralte_final": {"h_m": round(h_final_m,2), "d_prom_m": round(d_final_m,3)}, # d_prom_m usa d_final_m que es el promedio
        "presiones_servicio": {"q_max_serv_kPa": round(q_max_serv_N_m2/1000,1), "q_min_serv_kPa": round(q_min_serv_N_m2/1000,1), "q_adm_kPa": q_adm_kPa},
        "presiones_ultimas": {"q_max_ult_kPa": round(q_u_max_N_m2/1000,1), "q_min_ult_kPa": round(q_u_min_N_m2/1000,1)},
        "chequeo_cortante_unidir_L": resultados_cortante_uni_L,
        "chequeo_cortante_unidir_B": resultados_cortante_uni_B,
        "chequeo_punzonamiento": resultados_punzonamiento,
        "refuerzo_flexion": {
            "dir_L_paralelo_a_B": {"As_total_cm2": round(As_L_final_mm2/100,2), "As_cm2_per_m": round(As_L_final_mm2_per_m/100,2)},
            "dir_B_paralelo_a_L": {"As_total_cm2": round(As_B_final_mm2/100,2), "As_cm2_per_m": round(As_B_final_mm2_per_m/100,2)},
            "As_min_temp_cm2_per_m": round(rho_min_temp * h_final_mm * 1000 / 100, 2) # cm2/m
        }
    }
