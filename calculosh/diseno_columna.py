# ==============================================================================
# DISEÑO DE COLUMNA RECTANGULAR - FLEXOCOMPRESIÓN BIAXIAL
# ==============================================================================
import numpy as np
import matplotlib.pyplot as plt
from validate_positive import validate_positive
from unidades import *

# --- Constantes ---
ES_MPA = 200000.0
EPSILON_CU = 0.003

# --- Funciones Auxiliares ---
def _beta1(fc_MPa):
    """Calcula beta1 según NSR-10 C.10.2.7.3"""
    validate_positive(fc_MPa=fc_MPa)
    if fc_MPa <= 28.0:
        return 0.85
    else:
        beta = 0.85 - 0.05 * ((fc_MPa - 28.0) / 7.0)
        return max(beta, 0.65)

def _calcular_phi(epsilon_t):
    """Calcula phi según NSR-10 C.9.3.2 basado en deformación extrema de tracción εt"""
    # Límites de deformación para phi (NSR-10 Figura R.9.3.2)
    epsilon_ty = 0.002  # Límite conservador (fy=420 MPa / Es)
    epsilon_limit = 0.005 # Límite para phi=0.90

    if epsilon_t <= epsilon_ty:
        return 0.65  # Controlado por compresión
    elif epsilon_t < epsilon_limit:
        # Transición lineal entre (epsilon_ty, 0.65) y (epsilon_limit, 0.90)
        return 0.65 + 0.25 * (epsilon_t - epsilon_ty) / (epsilon_limit - epsilon_ty)
    else:
        return 0.90  # Controlado por tracción

def _generar_posicion_barras(b_mm, h_mm, rec_libre_mm, diam_estribo_mm, diam_barra_mm, nx_barras, ny_barras):
    """
    Genera coordenadas (xi, yi) y área (Asi) de cada barra.
    Asume distribución uniforme en caras.
    nx_barras: Número de barras en la cara paralela al eje Y (lado b).
    ny_barras: Número de barras en la cara paralela al eje X (lado h), *excluyendo esquinas*.
    Origen: Centroide de la sección.
    """
    if nx_barras < 2 or ny_barras < 0:
        raise ValueError("nx_barras debe ser >= 2, ny_barras >= 0")
    
    num_barras_total = 2 * nx_barras + 2 * ny_barras
    if num_barras_total < 4:
         raise ValueError("Número total de barras debe ser al menos 4")

    area_una_barra = np.pi * (diam_barra_mm / 2.0)**2
    barras = []

    # Coordenadas del centroide de las barras respecto al borde
    centroide_barra_x = rec_libre_mm + diam_estribo_mm + diam_barra_mm / 2.0
    centroide_barra_y = rec_libre_mm + diam_estribo_mm + diam_barra_mm / 2.0

    # Coordenadas respecto al centroide de la sección
    coord_x_ext = b_mm / 2.0 - centroide_barra_x
    coord_y_ext = h_mm / 2.0 - centroide_barra_y

    # Barras en caras superior e inferior (paralelas a eje X)
    for i in range(nx_barras):
        x = -coord_x_ext + i * (2 * coord_x_ext) / (nx_barras - 1) if nx_barras > 1 else 0
        # Barra inferior
        barras.append({'x': x, 'y': -coord_y_ext, 'area': area_una_barra})
        # Barra superior
        barras.append({'x': x, 'y': coord_y_ext, 'area': area_una_barra})

    # Barras en caras laterales (intermedias, excluyendo esquinas ya contadas)
    if ny_barras > 0:
         for i in range(ny_barras):
             # Espaciamiento uniforme entre las barras de esquina
             y = -coord_y_ext + (i + 1) * (2 * coord_y_ext) / (ny_barras + 1)
             # Barra izquierda
             barras.append({'x': -coord_x_ext, 'y': y, 'area': area_una_barra})
             # Barra derecha
             barras.append({'x': coord_x_ext, 'y': y, 'area': area_una_barra})
             
    # Asegurar que el número total coincida (puede haber duplicados en esquinas si nx=2)
    # Simplificación: eliminar duplicados basados en coordenadas cercanas
    coords = np.array([[b['x'], b['y']] for b in barras])
    _, unique_indices = np.unique(np.round(coords, 1), axis=0, return_index=True)
    barras_final = [barras[i] for i in sorted(unique_indices)]

    if len(barras_final) != num_barras_total:
         print(f"Advertencia: Número de barras únicas ({len(barras_final)}) difiere del esperado ({num_barras_total}). Revisar nx/ny.")
         # Podría ser necesario ajustar lógica si se quiere un número exacto fijo.

    return barras_final

# --- Función Principal de Cálculo ---
def calcular_diagrama_interaccion_columna(
    b_cm, h_cm, rec_libre_cm,
    diam_estribo_mm, diam_barra_long_mm,
    nx_barras, ny_barras, # Número barras cara 'b' y cara 'h' (sin esquinas)
    fc_MPa, fy_MPa,
    num_puntos_c=30, num_puntos_theta=36):
    """
    Calcula puntos (phi*Pn, phi*Mnx, phi*Mny) de la superficie de interacción
    usando el método iterativo fundamental.
    Retorna un diccionario con los puntos calculados y los parámetros usados.
    """
    # 1) Validaciones
    validate_positive(b_cm=b_cm, h_cm=h_cm, rec_libre_cm=rec_libre_cm, diam_estribo_mm=diam_estribo_mm,
                      diam_barra_long_mm=diam_barra_long_mm, fc_MPa=fc_MPa, fy_MPa=fy_MPa)
    
    # 2) Conversión a mm y cálculo de beta1
    b_mm = cm_to_mm(b_cm)
    h_mm = cm_to_mm(h_cm)
    beta_1 = _beta1(fc_MPa)
    
    # 3) Generar posiciones y áreas del acero
    try:
        barras = _generar_posicion_barras(b_mm, h_mm, cm_to_mm(rec_libre_cm), diam_estribo_mm, diam_barra_long_mm, nx_barras, ny_barras)
        As_total_mm2 = sum(b['area'] for b in barras)
        rho_g = As_total_mm2 / (b_mm * h_mm)
        if not (0.01 <= rho_g <= 0.06): # NSR-10 C.10.9.1 (hasta 8%)
            # Podría ser 0.06 en zonas sísmicas DMI/DES - C.21.4.3.1
             raise ValueError(f"Cuantía total {rho_g:.3f} fuera de límites [0.01, 0.06].")
        print(f"Refuerzo: {len(barras)} barras, As_total = {As_total_mm2:.0f} mm², ρ = {rho_g:.3f}")
    except ValueError as e:
        return {"status": "Error", "mensaje": f"Error en definición de refuerzo: {e}"}

    # 4) Rangos de iteración
    # Profundidad del eje neutro 'c'. Desde casi 0 hasta un poco más allá de h (para cubrir tensión pura)
    # Ajustar el límite superior puede ser necesario para capturar bien la zona de tensión.
    c_values = np.linspace(1e-3, max(h_mm, b_mm) * 1.5, num_puntos_c)
    # Ángulo del eje neutro theta (0 a 360 grados)
    theta_values = np.linspace(0, 2 * np.pi, num_puntos_theta, endpoint=False)

    # 5) Almacenar resultados
    resultados = [] # Lista de tuplas (phiPn_N, phiMnx_Nmm, phiMny_Nmm)

    # --- Inicio del Bucle Iterativo ---
    for c_mm in c_values:
        a_mm = beta_1 * c_mm # Profundidad bloque compresión (perpendicular al eje neutro)
        if a_mm < 1e-3: continue # Ignorar si bloque es muy pequeño

        for theta_rad in theta_values:
            # theta define la orientación del eje neutro.
            # 0 rad: Eje neutro horizontal, compresión arriba. Flexión alrededor de X.
            # pi/2 rad: Eje neutro vertical, compresión izquierda. Flexión alrededor de Y.

            Pn_N = 0.0
            Mnx_Nmm = 0.0
            Mny_Nmm = 0.0
            epsilon_t_max = -float('inf') # Para encontrar la deformación máxima en tracción

            # A) Contribución del Concreto (Simplificación: rectangular)
            # El cálculo exacto requiere integrar sobre el área comprimida (polígono)
            # Simplificación 1: Usar bloque rectangular equivalente normal al eje de flexión dominante.
            # Simplificación 2: Interpolar entre uniaxial X y Y (aproximación más gruesa)
            # Aquí usaremos una aproximación basada en la proyección 'a' y el ancho 'b' o 'h'
            # Esto es MENOS preciso para theta intermedio.

            # Cálculo aproximado de Cc y su centroide (REQUIERE MEJORA PARA PRECISIÓN)
            # Usaremos una aproximación muy simple: asumimos bloque rectangular 'a' x 'b_efectivo'
            # Esto no captura bien la forma real del bloque para theta inclinado.
            # Centroide del bloque también aproximado.
            if abs(np.cos(theta_rad)) > abs(np.sin(theta_rad)): # Más cercano a flexión alrededor de X
                 comp_depth = min(a_mm, h_mm) # 'a' limitado por la altura
                 comp_width = b_mm
                 comp_area = comp_depth * comp_width
                 centroid_y = h_mm / 2.0 - comp_depth / 2.0 # Centroide del bloque (respecto al centroide sección)
                 centroid_x = 0.0
            else: # Más cercano a flexión alrededor de Y
                 comp_depth = min(a_mm, b_mm) # 'a' limitado por el ancho
                 comp_width = h_mm
                 comp_area = comp_depth * comp_width
                 centroid_x = b_mm / 2.0 - comp_depth / 2.0 # Centroide del bloque (respecto al centroide sección)
                 centroid_y = 0.0
            
            Cc_N = 0.85 * fc_MPa * comp_area
            # Restar área acero en compresión (aproximado)
            area_acero_comp = 0
            for barra in barras:
                 # Distancia perpendicular de la barra al eje neutro
                 # Ecuación línea eje neutro: x*cos(theta) + y*sin(theta) = h/2 - c (si c se mide desde arriba)
                 # O y' = c (en sistema coordenado rotado)
                 # Simplificado: usar distancia 'd_barra' desde fibra más comprimida
                 # d_barra depende de theta y coordenadas (xi, yi)
                 # d_barra = (h_mm/2.0 - barra['y'])*abs(np.cos(theta_rad)) + (b_mm/2.0 - barra['x'])*abs(np.sin(theta_rad)) # No es exacto
                 # Usaremos distancia vertical/horizontal como aproximación
                 dist_y_comp_fib = h_mm/2.0 - barra['y'] # Distancia desde fibra superior
                 # dist_x_comp_fib = b_mm/2.0 - barra['x'] # Distancia desde fibra izquierda
                 # d_prima = dist_y_comp_fib # Asumir flexión X
                 
                 # Distancia de la barra a la fibra más comprimida (proyectada normal a EN)
                 # d_barra_perp = ? Es complejo. Usaremos y_i como aproximación para eps_t
                 
                 # Si la barra está dentro de 'a' (aproximado), restar su área
                 # if d_prima < a_mm: # Muy simplificado
                 #    area_acero_comp += barra['area'] 
            # Cc_N -= 0.85 * fc_MPa * area_acero_comp # Corrección por acero desplazado


            Pn_N += Cc_N
            Mnx_Nmm += Cc_N * centroid_y # Momento de Cc respecto a eje X centroidal
            Mny_Nmm += Cc_N * centroid_x # Momento de Cc respecto a eje Y centroidal


            # B) Contribución del Acero
            for barra in barras:
                # Calcular deformación basada en distancia a eje neutro 'c'
                # Distancia 'y_prime' de la barra al eje neutro, perpendicular a este.
                # Es más fácil calcular deformación basada en la distancia a la fibra más comprimida (d_barra)
                # y la profundidad 'c'
                
                # Aproximación: Calcular deformación basada en la distancia Y de la barra (como si fuera flexión uniaxial X)
                # Esto es una simplificación importante para theta != 0 o pi/2
                distancia_y_desde_centro = barra['y']
                distancia_desde_fibra_comp = h_mm / 2.0 - distancia_y_desde_centro
                
                epsilon_s = EPSILON_CU * (c_mm - distancia_desde_fibra_comp) / c_mm if c_mm > 1e-6 else (EPSILON_CU if distancia_desde_fibra_comp < 1e-6 else -EPSILON_CU)
                
                # Limitar tensión/compresión por fluencia
                fs_MPa = max(-fy_MPa, min(fy_MPa, ES_MPA * epsilon_s))
                
                Fs_N = barra['area'] * fs_MPa
                
                Pn_N += Fs_N
                Mnx_Nmm += Fs_N * barra['y'] # Momento respecto a eje X centroidal
                Mny_Nmm += Fs_N * barra['x'] # Momento respecto a eje Y centroidal

                # Rastrear deformación máxima en tracción (para phi)
                # La barra más traccionada es la más lejana al EN en el lado opuesto a la compresión
                # Aproximación: Usar la barra con y más negativa (para theta cercano a 0)
                if epsilon_s < 0: # Si está en tracción
                     epsilon_t_max = max(epsilon_t_max, abs(epsilon_s))

            # C) Calcular phi y almacenar punto
            if epsilon_t_max < 0: epsilon_t_max = 0 # Si todo está en compresión, epsilon_t = 0
            phi = _calcular_phi(epsilon_t_max)

            # D) Chequeo Pn max (NSR-10 C.10.3.6) - Asumiendo estribos
            Po = (0.85 * fc_MPa * (b_mm * h_mm - As_total_mm2) + fy_MPa * As_total_mm2) if As_total_mm2 > 0 else (0.85 * fc_MPa * b_mm * h_mm)
            Pn_max_norma = 0.80 * (0.65 * Po) # 0.80 * phi * Po (con phi=0.65 para estribos)

            # Almacenar el punto (phi*Pn, phi*Mnx, phi*Mny)
            # Solo guardar puntos válidos (P >= 0 y P <= Pn_max_norma)
            # if Pn_N >= 0 and phi * Pn_N <= Pn_max_norma: # Aplicar límite máximo
            if Pn_N >= 0: # Guardar todos los puntos P>=0 por ahora
                resultados.append((phi * Pn_N, phi * Mnx_Nmm, phi * Mny_Nmm))
            # else: # Considerar puntos en tensión pura si es necesario
                # if Pn_N < 0: resultados.append((phi * Pn_N, phi * Mnx_Nmm, phi * Mny_Nmm))
                
    # --- Fin del Bucle Iterativo ---

    if not resultados:
         return {"status": "Error", "mensaje": "No se generaron puntos válidos en el diagrama."}

    # 6) Formatear salida
    P_N_array, Mnx_Nmm_array, Mny_Nmm_array = zip(*resultados)
    
    return {
        "status": "OK",
        "mensaje": f"Diagrama calculado con {len(resultados)} puntos. Aproximación de bloque de compresión usada.",
        "P_N": np.array(P_N_array),
        "Mx_Nmm": np.array(Mnx_Nmm_array),
        "My_Nmm": np.array(Mny_Nmm_array),
        # Incluir parámetros usados para referencia
        "params": {
            "b_cm": b_cm, "h_cm": h_cm, "rec_libre_cm": rec_libre_cm,
            "diam_estribo_mm": diam_estribo_mm, "diam_barra_long_mm": diam_barra_long_mm,
            "nx_barras": nx_barras, "ny_barras": ny_barras, "num_barras_total": len(barras),
            "fc_MPa": fc_MPa, "fy_MPa": fy_MPa,
            "rho_g": rho_g
        }
    }


# --- Función para graficar (sin cambios respecto a tu versión original) ---
def graficar_diagrama_interaccion(datos: dict, titulo: str = "Diagrama P–M Biaxial", ax=None):
    """Grafica el diagrama 3D P-Mx-My."""
    # Verificar si hay datos válidos
    if datos.get("status") != "OK" or "P_N" not in datos or len(datos["P_N"]) == 0:
        print("No hay datos válidos para graficar.")
        # Podría mostrar un gráfico vacío o un mensaje
        if ax is None:
            fig = plt.figure(figsize=(8, 8))
            ax = fig.add_subplot(111, projection='3d')
        ax.text(0, 0, 0, "No hay datos válidos", color='red', ha='center', va='center')
        ax.set_xlabel('Mx (kN·m)'); ax.set_ylabel('My (kN·m)'); ax.set_zlabel('P (kN)')
        ax.set_title(titulo + " - Error")
        if ax is None: plt.show()
        return

    P_kN = n_to_kn(datos["P_N"])   # Convertir a kN
    Mx_kNm = nmm_to_knm(datos["Mx_Nmm"]) # Convertir a kN·m
    My_kNm = nmm_to_knm(datos["My_Nmm"]) # Convertir a kN·m

    own_ax = ax is None
    if own_ax:
        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(111, projection='3d')

    # Filtrar solo puntos con P >= 0 para visualización típica
    mask_comp = P_kN >= -1e-6 # Tolerancia pequeña
    sc = ax.scatter(Mx_kNm[mask_comp], My_kNm[mask_comp], P_kN[mask_comp], s=3, c=P_kN[mask_comp], cmap='viridis', alpha=0.8)
    
    # Añadir colorbar si se está creando el eje aquí
    if own_ax:
         fig.colorbar(sc, ax=ax, label='φ·P (kN)', shrink=0.6)

    ax.set_xlabel('φ·Mx (kN·m)')
    ax.set_ylabel('φ·My (kN·m)')
    ax.set_zlabel('φ·P (kN)')
    ax.set_title(titulo)

    # Opcional: Añadir plano P=0
    max_M_plot = max(np.abs(Mx_kNm).max(), np.abs(My_kNm).max()) * 1.1
    x_plane = np.linspace(-max_M_plot, max_M_plot, 2)
    y_plane = np.linspace(-max_M_plot, max_M_plot, 2)
    X_plane, Y_plane = np.meshgrid(x_plane, y_plane)
    Z_plane = np.zeros_like(X_plane)
    # ax.plot_surface(X_plane, Y_plane, Z_plane, alpha=0.1, color='gray') # Puede ocultar puntos

    # Ajustar límites si es necesario
    ax.set_xlim(-max_M_plot, max_M_plot)
    ax.set_ylim(-max_M_plot, max_M_plot)
    ax.set_zlim(0, P_kN.max() * 1.1 if P_kN.max() > 0 else 1)

    if own_ax:
        plt.tight_layout()
        # plt.show() # No mostrar automáticamente si se usa en Streamlit
    
    # Retornar la figura para que Streamlit la use
    if own_ax: return fig
    else: return ax # Si se pasó un eje, retornar el eje modificado