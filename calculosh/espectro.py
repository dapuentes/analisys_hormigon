# ==============================================================================
# ESPECTRO DE DISEÑO SÍSMICO NSR-10
# y funciones auxiliares (Fa, Fv, TL_norma)
# ==============================================================================
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def obtener_Fa_Fv_NSR10(suelo_tipo, Aa_val, Av_val):
    """
    Calcula los coeficientes Fa y Fv según NSR-10 Tablas A.2.4-2 y A.2.4-3.
    Incluye interpolación lineal para valores intermedios de Aa y Av.

    Parámetros:
    suelo_tipo (str): Tipo de perfil de suelo ('A', 'B', 'C', 'D', 'E', 'F').
    Aa_val (float): Coeficiente de aceleración pico efectiva.
    Av_val (float): Coeficiente de velocidad pico efectiva.

    Retorna:
    tuple: (Fa, Fv)
    """
    if suelo_tipo == "F":
        raise ValueError("Suelo tipo F requiere estudio geotécnico específico. No se pueden determinar Fa y Fv directamente desde estas tablas.")

    # --- Coeficiente Fa (Tabla A.2.4-2) ---
    # Columnas representan: Aa <= 0.05, Aa = 0.10, Aa = 0.15, Aa = 0.20, Aa = 0.25, Aa >= 0.30
    # (Usaremos el límite superior para Aa >= 0.30, es decir, 0.30 para interpolación)
    Aa_puntos_tabla = np.array([0.05, 0.10, 0.15, 0.20, 0.25, 0.30])

    fa_data = {
        'A': np.array([0.8, 0.8, 0.8, 0.8, 0.8, 0.8]),
        'B': np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0]),
        'C': np.array([1.2, 1.2, 1.1, 1.0, 1.0, 1.0]),
        'D': np.array([1.6, 1.4, 1.2, 1.1, 1.0, 1.0]),
        'E': np.array([2.5, 1.7, 1.2, 0.9, 0.9, 0.9]), # Nota: NSR-10 dice "Véase nota (*)" - Asumimos aplicable sin modificación para interpolación
    }

    if suelo_tipo not in fa_data:
        raise ValueError(f"Tipo de suelo '{suelo_tipo}' no reconocido para Fa.")
    
    # Interpolar para Fa
    # Asegurarse que Aa_val esté dentro del rango de interpolación o en los extremos
    if Aa_val < Aa_puntos_tabla[0]: # Si Aa es menor que el primer punto, usar el valor del primer punto
        Fa = fa_data[suelo_tipo][0]
    elif Aa_val >= Aa_puntos_tabla[-1]: # Si Aa es mayor o igual al último punto, usar el valor del último punto
        Fa = fa_data[suelo_tipo][-1]
    else:
        Fa = np.interp(Aa_val, Aa_puntos_tabla, fa_data[suelo_tipo])

    # --- Coeficiente Fv (Tabla A.2.4-3) ---
    # Columnas representan: Av <= 0.05, Av = 0.10, Av = 0.15, Av = 0.20, Av = 0.25, Av >= 0.30
    # (Usaremos el límite superior para Av >= 0.30, es decir, 0.30 para interpolación)
    Av_puntos_tabla = np.array([0.05, 0.10, 0.15, 0.20, 0.25, 0.30])
    
    fv_data = {
        'A': np.array([0.8, 0.8, 0.8, 0.8, 0.8, 0.8]),
        'B': np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0]),
        'C': np.array([1.7, 1.6, 1.5, 1.4, 1.3, 1.2]),
        'D': np.array([2.4, 2.0, 1.8, 1.6, 1.5, 1.4]),
        'E': np.array([3.5, 3.2, 2.8, 2.4, 2.4, 2.4]), # Nota: NSR-10 dice "Véase nota (*)"
    }

    if suelo_tipo not in fv_data:
        raise ValueError(f"Tipo de suelo '{suelo_tipo}' no reconocido para Fv.")

    # Interpolar para Fv
    if Av_val < Av_puntos_tabla[0]:
        Fv = fv_data[suelo_tipo][0]
    elif Av_val >= Av_puntos_tabla[-1]:
        Fv = fv_data[suelo_tipo][-1]
    else:
        Fv = np.interp(Av_val, Av_puntos_tabla, fv_data[suelo_tipo])
            
    return round(Fa, 3), round(Fv, 3)


def determinar_TL_norma(Av_val, Fa_val, Fv_val):
    """
    Determina el Periodo Largo (TL) según la Tabla A.2.6-1 de la NSR-10.
    Se basa en la Zona de Amenaza Sísmica, que se infiere de Av.
    También considera S1 = Av * Fv para ZAS Alta.

    Parámetros:
    Av_val (float): Coeficiente de velocidad pico efectiva.
    Fa_val (float): Coeficiente de sitio para periodo corto.
    Fv_val (float): Coeficiente de sitio para periodo largo.
    
    Retorna:
    float: Periodo Largo TL (s)
    """
    # Definición de Zonas de Amenaza Sísmica según A.2.2
    # ZAS Baja: Av < 0.10
    # ZAS Intermedia: 0.10 <= Av < 0.20
    # ZAS Alta: Av >= 0.20
    
    if Av_val < 0.10: # ZAS Baja
        TL = 3.0  # s
    elif Av_val < 0.20: # ZAS Intermedia
        TL = 4.0  # s
    else: # ZAS Alta (Av_val >= 0.20)
        # Para ZAS Alta, TL depende de S1 = Av * Fv (Ver nota (a) de Tabla A.2.6-1)
        S1 = Av_val * Fv_val
        if S1 < 0.75:
            TL = 4.0  # s
        else: # S1 >= 0.75g
            TL = 6.0  # s
    return TL


def espectro_nsr10(Aa, Av, I, R, Fa, Fv, TL_norma, tipo_espectro="diseño"):
    """
    Genera el espectro de diseño o elástico según NSR-10 (Figura A.2-1).
    
    Parámetros:
    Aa (float): Aceleración horizontal pico efectiva.
    Av (float): Velocidad horizontal pico efectiva.
    I (float): Coeficiente de importancia (usado solo para espectro de diseño).
    R (float): Coeficiente de capacidad de disipación de energía (usado solo para espectro de diseño).
    Fa (float): Coeficiente de amplificación para periodo corto.
    Fv (float): Coeficiente de amplificación para periodo largo.
    TL_norma (float): Periodo Largo (s) según Tabla A.2.6-1 de NSR-10.
    tipo_espectro (str): "diseño" o "elastico". Si es "elastico", I y R se ignoran (efectivamente I=1, R=1).
    
    Retorna:
    tuple: (T, Sa, info_periodos)
           T: Array de periodos (s)
           Sa: Array de aceleraciones espectrales (g)
           info_periodos: dict con T0, Tc, TL_norma
    """
    if tipo_espectro.lower() == "elastico":
        I_eff = 1.0
        R_eff = 1.0
    elif tipo_espectro.lower() == "diseño":
        I_eff = I
        R_eff = R
    else:
        raise ValueError("tipo_espectro debe ser 'diseño' o 'elastico'")

    # Parámetros del espectro (NSR-10 A.2.6.2)
    if Aa * Fa == 0: # Evitar división por cero si Aa o Fa son cero (improbable pero por seguridad)
        T0 = 0 
        TC = 0
    else:
        T0 = 0.1 * Av * Fv / (Aa * Fa)
        TC = 0.48 * Av * Fv / (Aa * Fa) # Corresponde a S_M1 / S_MS * 0.48 donde S_MS=2.5*Aa*Fa y S_M1=Av*Fv
                                     # O más directamente T_C = T_S * (Av*Fv)/(Aa*Fa*2.5), donde T_S es Tc de ACI7

    # Generar array de periodos. Asegurarse de incluir puntos clave.
    # El rango de periodos puede ajustarse según TL_norma
    max_periodo_plot = max(4.0, TL_norma + 1.0) 
    T_points = sorted(list(set([0, T0, TC, TL_norma, max_periodo_plot]))) # Incluir puntos clave
    T_dense_segments = []
    for i in range(len(T_points)-1):
        if T_points[i+1] > T_points[i]: # Evitar segmentos de longitud cero
             T_dense_segments.append(np.linspace(T_points[i], T_points[i+1], 100, endpoint=(i == len(T_points)-2)))
    
    if not T_dense_segments: # Caso borde si todos los puntos clave son iguales
        T = np.linspace(0, max_periodo_plot, 400)
    else:
        T = np.unique(np.concatenate(T_dense_segments))


    Sa = np.zeros_like(T)
    
    # Calcular Sa para cada periodo según NSR-10 Figura A.2-1 y Ecuaciones A.2-1 a A.2-4
    # S_DS = 2.5 * Aa * Fa
    # S_D1 = Av * Fv
    S_MS = 2.5 * Aa * Fa # Máxima aceleración espectral considerada para diseño, modificada por el sitio (elástico)
    S_M1 = Av * Fv     # Aceleración espectral para periodo de 1s, modificada por el sitio (elástico)


    for i, t_val in enumerate(T):
        if t_val <= T0:
            # Sa_elastico = S_MS * (0.4 + 0.6 * t_val / T0) # Según ASCE 7, NSR-10 es un poco diferente en este tramo
            # NSR-10 Ecuación A.2-1 (para diseño)
            Sa_val = Aa * Fa * (0.4 + 0.6 * t_val / T0) * 2.5 # Elástico (antes de I/R)
        elif t_val <= TC:
            # Sa_elastico = S_MS
            Sa_val = Aa * Fa * 2.5 # Elástico
        elif t_val <= TL_norma:
            # Sa_elastico = S_M1 / t_val
            Sa_val = Av * Fv / t_val # Elástico
        else: # t_val > TL_norma
            # Sa_elastico = S_M1 * TL_norma / (t_val**2)
            Sa_val = (Av * Fv * TL_norma) / (t_val**2) # Elástico
            
        Sa[i] = Sa_val * I_eff / R_eff # Aplicar factores I y R para espectro de diseño

    info_periodos = {"T0": round(T0,3), "TC": round(TC,3), "TL_norma": round(TL_norma,3)}
    return T, Sa, info_periodos


def graficar_espectro(T, Sa, info_periodos, titulo="Espectro NSR-10", R_val=None, I_val=None):
    """Grafica el espectro de diseño, mostrando T0, TC, TL."""
    plt.figure(figsize=(10, 6))
    plt.plot(T, Sa, label=f"Sa (I={I_val}, R={R_val})" if R_val else "Sa Elástico")
    plt.grid(True)
    plt.xlabel('Periodo T (s)')
    plt.ylabel('Aceleración espectral Sa (g)')
    
    title_full = titulo
    if R_val and I_val:
        title_full += f" (I={I_val}, R={R_val})"
    plt.title(title_full)

    # Marcar periodos importantes
    if info_periodos:
        T0 = info_periodos["T0"]
        TC = info_periodos["TC"]
        TL_norma = info_periodos["TL_norma"]
        
        plt.axvline(x=T0, color='r', linestyle='--', alpha=0.7, label=f'T0 = {T0:.3f} s')
        plt.axvline(x=TC, color='g', linestyle='--', alpha=0.7, label=f'TC = {TC:.3f} s')
        plt.axvline(x=TL_norma, color='b', linestyle='--', alpha=0.7, label=f'TL = {TL_norma:.3f} s')
    
    plt.legend()
    # plt.savefig('espectro_diseno.png', dpi=300) # Opcional, guardar directamente
    # plt.show() # No usar plt.show() si se va a integrar con Streamlit (st.pyplot(fig))
    return plt.gcf() # Retorna la figura actual para que Streamlit la pueda usar


# --- Funciones adicionales que estaban en tu app2.py relacionadas con sismo ---
def calcular_Ta_aproximado(H_total_edificio_m, sistema_resist_sismico_desc, num_sotanos_base=0):
    """
    Calcula el periodo fundamental aproximado Ta según NSR-10 A.4.2.2.1.
    H_total_edificio_m: Altura total del edificio en metros desde la base (incluyendo sótanos si no están desligados).
    sistema_resist_sismico_desc: Descripción del sistema (ej. "Pórticos de Concreto Reforzado DMO")
    num_sotanos_base: Número de niveles de sótano en la base que están estructuralmente integrados.
    """
    # Coeficiente Ct y exponente alpha según Tabla A.4.2.2-1
    # Aquí algunos ejemplos, se pueden expandir:
    if "Pórticos de Concreto Reforzado" in sistema_resist_sismico_desc:
        Ct = 0.047
        alpha = 0.9
    elif "Pórticos de Acero" in sistema_resist_sismico_desc and "Arriostrados Concéntricamente" not in sistema_resist_sismico_desc:
        Ct = 0.072
        alpha = 0.8
    elif "Pórticos de Acero Arriostrados Concéntricamente" in sistema_resist_sismico_desc:
        Ct = 0.073
        alpha = 0.75
    elif "Muros Estructurales de Concreto" in sistema_resist_sismico_desc or "Muros de Mampostería Reforzada" in sistema_resist_sismico_desc:
        Ct = 0.049
        alpha = 0.75
    else: # Caso "Todos los demás sistemas"
        Ct = 0.049
        alpha = 0.75
        # O advertir y usar un valor por defecto:
        # print(f"Advertencia: Sistema '{sistema_resist_sismico_desc}' no mapeado directamente a Ct. Usando valores por defecto.")

    # Hn es la altura en metros desde la base hasta el nivel más alto de la estructura principal.
    # La "base" se define como el nivel en el cual las fuerzas sísmicas son resistidas por el terreno
    # o por un sótano rígido estructuralmente independiente del terreno circundante.
    # Si los sótanos están integrados y no son significativamente más rígidos que la superestructura,
    # Hn se mide desde la base de los sótanos.
    Hn = H_total_edificio_m # Asumimos que H_total_edificio_m es Hn

    # Ajuste por número de sótanos (NSR-10 A.4.2.2.1.c)
    # Este ajuste es para C_t, no para T_a directamente de esta forma.
    # El código original del usuario multiplicaba Hn por (1 - 0.1*num_sotanos_base), lo cual no es estándar.
    # La norma indica ajustar C_t si la base del edificio está a nivel del terreno y existen sótanos.
    # C_t_ajustado = C_t / (1 + 0.1 * num_sotanos_base) # Esto es si la altura Hn se mide desde el nivel del terreno.
    # Si Hn ya se mide desde la base real (fondo de sótanos), no se necesita este ajuste a Ct.
    # Por simplicidad y dado que H_total_edificio_m se define "desde la base", no aplicaremos ajuste adicional a Ct aquí.

    Ta = Ct * (Hn ** alpha)
    return round(Ta, 3)


def calcular_Vs_fuerza_horizontal_equivalente(W_total_sismico_kN, Sa_para_Ta, Ta_s, num_pisos, altura_tipica_piso_m):
    """
    Calcula el Cortante Sísmico Basal (Vs) y distribuye las fuerzas Fx por piso.
    NSR-10 A.4.3 y A.4.4.

    Parámetros:
    W_total_sismico_kN (float): Peso total sísmico de la edificación (CM + %CV relevante).
    Sa_para_Ta (float): Aceleración espectral de diseño para el periodo Ta (en g).
    Ta_s (float): Periodo fundamental de la estructura (s).
    num_pisos (int): Número de pisos sobre la base.
    altura_tipica_piso_m (float): Altura típica de entrepiso (m).

    Retorna:
    tuple: (Vs_kN, df_Fx_por_piso)
           Vs_kN: Cortante sísmico basal (kN).
           df_Fx_por_piso: DataFrame con la distribución de fuerzas por piso.
    """
    # Cortante Sísmico en la Base (Vs) - NSR-10 A.4-1
    Vs_kN = Sa_para_Ta * W_total_sismico_kN
    
    # TODO: Implementar chequeos de Vs mínimo según NSR-10 A.4.3.2 y A.4.3.3 si es necesario.
    # Vs_min1 = 0.044 * Aa * I * W_total_sismico_kN  (NSR-10 A.4-4, si aplica)
    # Vs_min2 = 0.8 * Av * Fa * I * W_total_sismico_kN / R (NSR-10 A.4-5, si aplica para ciertas zonas y R)
    # Vs_kN = max(Vs_kN, Vs_min1_aplicable, Vs_min2_aplicable)

    # Distribución Vertical de la Fuerza Sísmica (Fx) - NSR-10 A.4.4
    # Exponente k para la distribución de la carga (NSR-10 A.4.4.2)
    if Ta_s <= 0.5:
        k = 1.0
    elif Ta_s >= 2.5:
        k = 2.0
    else: # 0.5 < Ta_s < 2.5
        k = 0.75 + 0.5 * Ta_s # Según ACI 7, NSR-10 A.4.4.2 dice k = 1.0 para Ta<=0.5s y k=2.0 para Ta>=2.5s, interpolar linealmente para valores intermedios.
                              # Interpolación lineal: k = 1.0 + ( (Ta_s - 0.5) / (2.5 - 0.5) ) * (2.0 - 1.0)
                              # k = 1.0 + (Ta_s - 0.5) / 2.0
        k = 1.0 + (Ta_s - 0.5) / 2.0


    # Asumimos pesos de piso iguales para simplificar, en un caso real se deben calcular.
    # w_i = W_total_sismico_kN / num_pisos # Peso del nivel i (simplificado)
    # h_i = altura del nivel i desde la base

    pisos = np.arange(1, num_pisos + 1)
    h_i_array = pisos * altura_tipica_piso_m # Altura de cada nivel i desde la base
    
    # Para una distribución más realista, se necesitarían los pesos de cada piso (w_i)
    # Aquí asumimos w_i es proporcional a la altura o uniforme. Para simplificar, usamos w_i = W_total / N
    w_i_uniforme = W_total_sismico_kN / num_pisos
    
    sum_wi_hi_k = np.sum(w_i_uniforme * (h_i_array ** k))
    
    if sum_wi_hi_k == 0: # Evitar división por cero
        Cvx_array = np.zeros_like(h_i_array)
        if num_pisos > 0: Cvx_array[-1] = 1.0 # Aplicar toda la fuerza en el último piso si no hay otra forma
    else:
        Cvx_array = (w_i_uniforme * (h_i_array ** k)) / sum_wi_hi_k # Coeficientes de distribución vertical

    Fx_array_kN = Cvx_array * Vs_kN # Fuerza lateral en cada nivel i

    # Crear DataFrame para mostrar resultados
    # Las fuerzas se listan desde la cubierta hacia abajo (piso más alto primero)
    df_Fx_por_piso = pd.DataFrame({
        'Nivel': pisos[::-1], # Invertir para mostrar de cubierta a base
        'Altura_hi (m)': h_i_array[::-1],
        'wi_hi^k (kN*m^k)': (w_i_uniforme * (h_i_array ** k))[::-1],
        'Cvx': Cvx_array[::-1],
        'Fx (kN)': Fx_array_kN[::-1]
    })
    df_Fx_por_piso['Suma_Fx_acum (kN)'] = df_Fx_por_piso['Fx (kN)'].cumsum()

    # Chequeo rápido: la suma de Fx debe ser Vs (o muy cercano por redondeo)
    # print(f"Suma Fx: {np.sum(Fx_array_kN):.2f} kN vs Vs: {Vs_kN:.2f} kN")

    return round(Vs_kN, 2), df_Fx_por_piso