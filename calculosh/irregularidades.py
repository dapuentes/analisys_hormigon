# ==============================================================================
# ANÁLISIS DE IRREGULARIDADES ESTRUCTURALES
# ==============================================================================
def evaluar_irregularidades(planta, altura, configuracion):
    """
    Evalúa irregularidades estructurales según NSR‑10.

    Parámetros
    ----------
    planta : dict
        Debe contener:
          - 'largo' (float, m)
          - 'ancho' (float, m)
          - 'retrocesos' (list of float, m)
    altura : dict
        Debe contener listas:
          - 'rigideces' (floats, kN/m)
          - 'masas'      (floats, kN·s²/m)
    configuracion : dict
        Debe contener:
          - 'torsion'                (bool)
          - 'discontinuidad_diafragma' (bool)
          - 'R_0'                    (float > 0)

    Devuelve
    -------
    dict con:
      - 'planta': {
            'irregularidades': [<etiquetas>],
            'phi_p': <factor combinado>
        }
      - 'altura': {
            'irregularidades': [<etiquetas>],
            'phi_a': <factor combinado>
        }
      - 'R_0': <valor original>,
      - 'R':   <R_0 * phi_p * phi_a>
    """
    # --- 1) Validar parámetros mínimos ---
    for key in ('largo', 'ancho', 'retrocesos'):
        if key not in planta:
            raise KeyError(f"planta debe incluir '{key}'")
    for key in ('rigideces', 'masas'):
        if key not in altura:
            raise KeyError(f"altura debe incluir '{key}'")
    if 'R_0' not in configuracion or configuracion['R_0'] <= 0:
        raise KeyError("configuracion debe incluir 'R_0' > 0")

    # --- 2) Factores de phi según NSR-10 (ejemplo de valores) ---
    FACTORES_PLANTA = {
        'torsional'         : 0.9,
        'retroceso_esquinas': 0.8,
        'discontinuidad_diaf': 0.9,
    }
    FACTORES_ALTURA = {
        'piso_flexible'    : 0.8,
        'irregularidad_masa': 0.9,
    }

    # --- 3) Detectar irregularidades en planta ---
    ip = []  # etiquetas
    # 3.1 Torsional
    if configuracion.get('torsion', False):
        ip.append('torsional')
    # 3.2 Retroceso en esquinas
    max_ret = max(planta['retrocesos']) if planta['retrocesos'] else 0.0
    dim_par = min(planta['largo'], planta['ancho'])
    if max_ret > 0.15 * dim_par:
        ip.append('retroceso_esquinas')
    # 3.3 Discontinuidad de diafragma
    if configuracion.get('discontinuidad_diafragma', False):
        ip.append('discontinuidad_diaf')

    # Combinar factores: tomar el mínimo de todos los aplicables
    if ip:
        phi_p = min(FACTORES_PLANTA[name] for name in ip)
    else:
        phi_p = 1.0

    # --- 4) Detectar irregularidades en altura ---
    ia = []
    rig = altura['rigideces']
    for i in range(1, len(rig)):
        if rig[i] < 0.7 * rig[i-1]:
            ia.append('piso_flexible')
            break
    mas = altura['masas']
    for i in range(1, len(mas)):
        if mas[i] > 1.5 * mas[i-1] or mas[i] < 0.7 * mas[i-1]:
            ia.append('irregularidad_masa')
            break

    if ia:
        phi_a = min(FACTORES_ALTURA[name] for name in ia)
    else:
        phi_a = 1.0

    # --- 5) Factor R ajustado ---
    R0 = configuracion['R_0']
    R  = R0 * phi_p * phi_a

    return {
        'planta':   {'irregularidades': ip, 'phi_p': phi_p},
        'altura':   {'irregularidades': ia, 'phi_a': phi_a},
        'R_0': R0,
        'R':   R
    }