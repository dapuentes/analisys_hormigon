# Conversión
CM_TO_MM = 10.0
KNM_TO_NMM = 1e6   # kN·m → N·mm
KN_TO_N = 1e3      # kN → N

def cm_to_mm(x_cm):
    return x_cm * CM_TO_MM

def knm_to_nmm(Mu_kNm):
    return Mu_kNm * KNM_TO_NMM

def kn_to_n(valor_kn):
    """Convierte kilonewtons a newtons."""
    return valor_kn * 1000

def cm_to_m(valor_cm):
    """Convierte centímetros a metros."""
    return valor_cm / 100

def mp_to_n_mm2(valor_mp):
    """Convierte megapascales a N/mm² (equivalente)."""
    return valor_mp  # 1 MPa = 1 N/mm²

def mm_to_cm(valor_mm):
    """Convierte milímetros a centímetros."""
    return valor_mm / 10

def n_to_kn(valor_n):
    """Convierte newtons a kilonewtons."""
    return valor_n / 1000

def nmm_to_knm(valor_nmm):
    """Convierte N·mm a kN·m."""
    return valor_nmm / 1e6  # 1 kN·m = 1e6 N·mm

def m_to_cm(valor_m):
    """Convierte metros a centímetros."""
    return valor_m * 100

def m_to_mm(valor_m):
    """Convierte metros a milímetros."""
    return valor_m * 1000

def mm_to_m(valor_mm):
    """Convierte milímetros a metros."""
    return valor_mm / 1000

def cm2_to_mm2(valor_cm2):
    """Convierte centímetros cuadrados a milímetros cuadrados."""
    return valor_cm2 * 100  # 1 cm² = 100 mm²

def mm2_to_cm2(valor_mm2):
    """Convierte milímetros cuadrados a centímetros cuadrados."""
    return valor_mm2 / 100  # 1 mm² = 0.01 cm²


