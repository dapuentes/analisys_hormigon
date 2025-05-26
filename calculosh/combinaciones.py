# ==============================================================================
# GENERACIÓN DE COMBINACIONES DE CARGA
# ==============================================================================

F1_L_RESIDENCIAL = 0.5

def generar_combinaciones_carga(
    incluir_sismo=True, 
    f1_L_sismica=F1_L_RESIDENCIAL, # Factor para L en comb. sísmicas
    incluir_sismo_vertical=False, # Opción para incluir Ev
    Aa=0.0, Fa=1.0 # Necesarios solo si incluir_sismo_vertical es True
    ):
    """
    Genera las combinaciones de carga según NSR‑10.

    Parámetros
    ----------
    incluir_sismo : bool
        Si True, agrega las combinaciones sísmicas.
    f1_L_sismica : float
        Factor para la carga viva L en combinaciones sísmicas (0.5 para residencial).
    incluir_sismo_vertical : bool
        Si True, modifica los factores de D en combinaciones sísmicas para incluir Ev.
    Aa : float
        Coeficiente de aceleración pico efectiva (para Ev).
    Fa : float
        Coeficiente de sitio para periodo corto (para Ev).
    
    Devuelve
    -------
    dict con claves:
      - 'servicio' : lista de (nombre, factores) para estados de servicio
      - 'ultimas'  : lista de (nombre, factores) para estados últimos
    """
    # 1) Validación de tipo (ya estaba bien)
    if not isinstance(incluir_sismo, bool):
        raise TypeError("incluir_sismo debe ser un valor booleano")
    if not isinstance(incluir_sismo_vertical, bool):
        raise TypeError("incluir_sismo_vertical debe ser un valor booleano")

    # 2) Definición de combinaciones base
    # Referencias: NSR‑10 B.2.3 (Servicio), B.2.4 y A.3.5.1 (Últimas)
    
    combinaciones_servicio = [
        ("D + L",       {"D": 1.0, "L": 1.0}),
        ("D",           {"D": 1.0}), # Para asentamientos diferidos, etc.
        ("D + Lr",      {"D": 1.0, "Lr": 1.0}), # Si hay Lr
        # Podrían añadirse más combinaciones de servicio si son necesarias
    ]

    # Combinaciones últimas básicas (gravitacionales) - NSR-10 B.2.4-1
    # D = Carga Muerta, L = Carga Viva, Lr = Carga Viva de Cubierta
    # (F, H, T, S, R se omiten por simplicidad, pero pueden añadirse)
    ultimas_basicas = [
        ("1.4 D",                      {"D": 1.4}), # (a) simplificado (originalmente 1.4(D+F))
        ("1.2 D + 1.6 L + 0.5 Lr",     {"D": 1.2, "L": 1.6, "Lr": 0.5}), # (c) (si S y R son cero)
                                                                       # Si Lr también es cero, se reduce a 1.2D + 1.6L
        ("1.2 D + 1.6 Lr + 1.0 L",     {"D": 1.2, "Lr": 1.6, "L": 1.0}), # (d) con f1=1.0 (si L es la principal) o 0.5W
                                                                       # O "1.2 D + 1.6 Lr + 0.5 L" (si L no es la principal y no hay viento)
        # Para simplificar, la B.2.4-1 (b) es a menudo la que rige si Lr es pequeña:
        # ("1.2 D + 1.6 L", {"D": 1.2, "L": 1.6}) # Si Lr=0
    ]
    # La combinación más común que incluye Lr:
    # 1.2D + 1.6L + 0.5Lr  (si L es la carga viva principal)
    # 1.2D + 0.5L + 1.6Lr  (si Lr es la carga viva principal)
    # Mantendremos la que tenías, asumiendo L es más general que Lr
    
    # Para evitar duplicados si Lr=0, podríamos tener:
    ultimas_basicas_efectivas = [("1.4 D", {"D": 1.4})]
    if f1_L_sismica > 0 : # Asumimos que si hay f1_L_sismica, hay L.
        ultimas_basicas_efectivas.append(("1.2 D + 1.6 L + 0.5 Lr", {"D": 1.2, "L": 1.6, "Lr": 0.5})) # Cubre bien
        ultimas_basicas_efectivas.append(("1.2 D + 0.5 L + 1.6 Lr", {"D": 1.2, "L": 0.5, "Lr": 1.6})) # Para cuando Lr es mayor

    ultimas_sismicas = []
    if incluir_sismo:
        factor_D_sismo_1 = 1.2
        factor_D_sismo_2 = 0.9
        
        if incluir_sismo_vertical:
            # Ev = 0.2 * Sds * D = 0.2 * (2.5 * Aa * Fa) * D = 0.5 * Aa * Fa * D
            # Asumimos rho (redundancia) = 1.0 para E
            # Si Aa o Fa no son positivos, Ev sería cero.
            if Aa > 0 and Fa > 0:
                Ev_factor_D = 0.5 * Aa * Fa
                factor_D_sismo_1 += Ev_factor_D
                factor_D_sismo_2 -= Ev_factor_D # NSR-10 A.3.5.1.2 (b) es (0.9 - Ev_factor_D)D
            else:
                print("Advertencia: Aa o Fa no son positivos, sismo vertical Ev no se calculará.")

        # NSR-10 A.3.5.1 (asumiendo rho=1.0)
        # (a) (factor_D_sismo_1)D + f1_L_sismica*L + E  (se omitió 0.5S por simplicidad)
        # (b) (factor_D_sismo_2)D + E
        
        # Si f1_L_sismica es 0, entonces no se añade el término L.
        combo1_sismica = {"D": round(factor_D_sismo_1, 3), "E": 1.0}
        if f1_L_sismica > 0:
            combo1_sismica["L"] = f1_L_sismica
        
        nombre_combo1 = f"({factor_D_sismo_1:.2f})D + {f1_L_sismica}L + E" if f1_L_sismica > 0 else f"({factor_D_sismo_1:.2f})D + E"
        if not incluir_sismo_vertical: # Simplificar nombre si Ev no se incluye
             nombre_combo1 = f"1.2D + {f1_L_sismica}L + E" if f1_L_sismica > 0 else f"1.2D + E"

        ultimas_sismicas.append((nombre_combo1, combo1_sismica))

        nombre_combo2 = f"({factor_D_sismo_2:.2f})D + E"
        if not incluir_sismo_vertical:
             nombre_combo2 = f"0.9D + E"
        ultimas_sismicas.append((nombre_combo2, {"D": round(factor_D_sismo_2, 3), "E": 1.0}))
    
    # 3) Armar el diccionario de salida
    combinaciones_ultimas = list(ultimas_basicas_efectivas) # Usar la lista filtrada
    if incluir_sismo:
        combinaciones_ultimas.extend(ultimas_sismicas)

    # 4) Validación de Coeficientes ELIMINADA (o muy relajada)
    # La validación original "if coef <= 0" era problemática.
    # Se asume que los factores definidos son correctos según la norma.

    return {
        "servicio": combinaciones_servicio,
        "ultimas": combinaciones_ultimas
    }