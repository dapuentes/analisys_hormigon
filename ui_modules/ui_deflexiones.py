import streamlit as st
from calculosh.deflexiones import *

def mostrar_interfaz_deflexiones(PG, st_session):
    st.header("Cálculo y Verificación de Deflexiones (NSR-10 C.9.5)")
    fc_def = PG['fc_losas_vigas_MPa'] 
    Ec_MPa = 4700 * np.sqrt(fc_def) 
    st.info(f"Parámetros de Material Usados: f'c = {fc_def} MPa  ➔  Ec = {Ec_MPa:.0f} MPa")

    col1_def, col2_def = st.columns([1, 1]) 

    with col1_def:
        st.subheader("1. Geometría y Propiedades del Elemento")
        id_elemento_deflex_reporte = st.text_input("ID Elemento para Reporte de Deflexión (ej: V-101, Losa N2)", key="id_deflex_rep_v2")
        tipo_elemento_def = st.selectbox("Tipo de Elemento", 
                                         ["Viga Rectangular", "Losa Maciza Unidireccional", "Nervio de Losa (Sección T)"], 
                                         key="elem_def_tipo_v2")
        L_libre_cm_def = st.number_input("Luz Libre del Elemento $L_n$ (cm)", min_value=100.0, value=500.0, step=10.0, key="L_def_v2")

        # --- Inputs de geometría específicos al tipo de elemento ---
        if tipo_elemento_def == "Viga Rectangular" or tipo_elemento_def == "Losa Maciza Unidireccional":
            b_elem_cm_def = st.number_input("Ancho del Elemento b (cm)", min_value=10.0, value=30.0, step=1.0, key="b_rect_def_v2")
            h_elem_cm_def = st.number_input("Peralte Total del Elemento h (cm)", min_value=15.0, value=50.0, step=1.0, key="h_rect_def_v2")
            es_T_secc_def = False
            bw_alma_calc_cm = b_elem_cm_def
            hf_loseta_calc_cm = h_elem_cm_def
            b_eff_calc_cm = b_elem_cm_def
        elif tipo_elemento_def == "Nervio de Losa (Sección T)":
            st.markdown("###### Dimensiones del Nervio y Losa (para $I_g$)")
            h_total_nervio_cm_def = st.number_input("Altura Total Nervio h (cm, loseta+alma)", min_value=15.0, value=25.0, step=1.0, key="h_nerv_def_v2")
            bw_alma_cm_def = st.number_input("Ancho Alma Nervio bw (cm)", min_value=8.0, value=10.0, step=1.0, key="bw_nerv_def_v2")
            hf_loseta_cm_def = st.number_input("Espesor Loseta hf (cm)", min_value=4.0, value=5.0, step=0.5, key="hf_nerv_def_v2")
            separacion_nervios_m_def = st.number_input("Separación Centro a Centro Nervios (m)", min_value=0.3, value=0.6, step=0.05, key="sep_nerv_def_v2")
            L_libre_nervio_m_def = cm_to_m(L_libre_cm_def)
            beff1 = L_libre_nervio_m_def * 1000 / 4.0
            beff2 = cm_to_mm(bw_alma_cm_def) + 16 * cm_to_mm(hf_loseta_cm_def)
            beff3 = separacion_nervios_m_def * 1000
            b_eff_calc_mm = min(beff1, beff2, beff3)
            b_eff_calc_cm = mm_to_cm(b_eff_calc_mm)
            st.info(f"Ancho efectivo $b_{{eff}}$ calculado: {b_eff_calc_cm:.1f} cm")
            es_T_secc_def = True
            h_elem_cm_def = h_total_nervio_cm_def
            bw_alma_calc_cm = bw_alma_cm_def
            hf_loseta_calc_cm = hf_loseta_cm_def
        
        # Botón para calcular Ig, yt (o puede ser parte del botón principal)
        if st.button("Calcular Ig y yt de la Sección", key="btn_calc_ig_yt"):
            try:
                Ig_mm4, yt_mm, y_centroide_sup_mm_val = momento_inercia_bruta_T_o_Rect(
                    b_total_ala_cm=b_eff_calc_cm if es_T_secc_def else b_elem_cm_def,
                    h_total_cm=h_elem_cm_def,
                    hf_loseta_cm=hf_loseta_calc_cm if es_T_secc_def else h_elem_cm_def,
                    bw_alma_cm=bw_alma_calc_cm if es_T_secc_def else b_elem_cm_def,
                    es_seccion_T=es_T_secc_def
                )
                st.success(f"Calculado: $I_g = {Ig_mm4:,.0f} mm^4$, $y_t = {yt_mm:.1f} mm$")
                st.session_state['Ig_def_calc'] = Ig_mm4
                st.session_state['yt_def_calc'] = yt_mm
                st.session_state['y_centroide_sup_mm_def_calc'] = y_centroide_sup_mm_val # Guardar para cálculo de d
            except Exception as e:
                st.error(f"Error calculando Ig/yt: {e}")
                st.session_state['Ig_def_calc'] = None
                st.session_state['yt_def_calc'] = None
                st.session_state['y_centroide_sup_mm_def_calc'] = None


        st.markdown("##### Cargas de Servicio (NO mayoradas)")
        w_CM_kNpm_def = st.number_input("Carga Muerta Sostenida (CM) (kN/m)", min_value=0.0, value=5.0, step=0.5, key="wCM_def_v2")
        w_CV_kNpm_def = st.number_input("Carga Viva Total (CV) (kN/m)", min_value=0.0, value=8.0, step=0.5, key="wCV_def_v2")
        porc_CV_sost_def = st.slider("Porcentaje de CV Sostenida (%)", 0, 100, 25, key="cvsost_def_v2")
        
        st.markdown("##### Parámetros para Inercia Efectiva y Largo Plazo")
        tipo_apoyo_def = st.selectbox("Condición de Apoyo ($M_a$ y coef. deflexión)", 
                                      ["simples", "empotrado_empotrado", "voladizo", "empotrado_apoyado"], 
                                      key="apoyo_def_v3")
        Icr_manual_mm4_def = st.number_input("Opcional: $I_{cr}$ (Inercia fisurada, mm⁴)", value=0.0, format="%e", key="icr_def_v2", help="Si es 0, se usará aproximación NSR-10 si se fisura.")
        
        st.markdown("##### Parámetros para Deflexión a Largo Plazo")
        As_comp_cm2_def = st.number_input("Área Acero de Compresión $A_s'$ (cm²)", min_value=0.0, value=0.0, step=0.1, key="as_comp_def_v2")
        d_prima_comp_cm_def = st.number_input("Rec. a $A_s'$ desde fibra comp. $d'$ (cm)", min_value=0.0, value=4.0, step=0.5, key="dprima_def_v2")
        
        xi_tiempo_def_options = {"3 meses": 1.0, "6 meses": 1.2, "12 meses": 1.4, "5 años o más": 2.0}
        sel_xi = st.selectbox("Duración Carga Sostenida (para factor ξ)", list(xi_tiempo_def_options.keys()), index=3, key="xi_def_v2")
        xi_factor_def = xi_tiempo_def_options[sel_xi]

        if st.button("🔍 Calcular y Verificar Deflexiones", key="btn_calc_def_v3"):
            if not id_elemento_deflex_reporte.strip():
                st.error("Por favor, ingrese un ID para el elemento a verificar.")
            elif st.session_state.get('Ig_def_calc') is None or st.session_state.get('yt_def_calc') is None:
                st.error("Primero calcule Ig y yt para la sección (presione el botón 'Calcular Ig y yt').")
            else:
                Ig_val = st.session_state['Ig_def_calc']
                yt_val = st.session_state['yt_def_calc']
                y_centroide_sup_mm_val = st.session_state.get('y_centroide_sup_mm_def_calc', h_elem_cm_def * 10 / 2.0) # Fallback si no está

                w_CVsostenida_kNpm = w_CV_kNpm_def * (porc_CV_sost_def / 100.0)
                w_TotalSostenida_kNpm = w_CM_kNpm_def + w_CVsostenida_kNpm
                w_total_servicio_kNpm = w_CM_kNpm_def + w_CV_kNpm_def

                if tipo_apoyo_def == 'simples' or tipo_apoyo_def == 'empotrado_apoyado': 
                    Ma_kNm = (w_total_servicio_kNpm * (cm_to_m(L_libre_cm_def)**2)) / 8.0
                elif tipo_apoyo_def == 'empotrado_empotrado': 
                    Ma_kNm = (w_total_servicio_kNpm * (cm_to_m(L_libre_cm_def)**2)) / 12.0
                elif tipo_apoyo_def == 'voladizo': 
                    Ma_kNm = (w_total_servicio_kNpm * (cm_to_m(L_libre_cm_def)**2)) / 2.0
                else: Ma_kNm = 0

                Mcr_kNm, fisurada = calcular_Mcr_y_estado_fisuracion(Ma_kNm, fc_def, Ig_val, yt_val)
                I_efectiva_mm4 = Ig_val
                msg_Ie = f"$M_a \leq M_{{cr}}$. Sección no fisurada. Usando $I_e = I_g = {Ig_val:,.0f} mm^4$."
                if fisurada:
                    if Icr_manual_mm4_def > 0:
                        I_efectiva_mm4 = calcular_inercia_efectiva_Ie(Mcr_kNm, Ma_kNm, Ig_val, Icr_manual_mm4_def)
                        msg_Ie = f"$M_a > M_{{cr}}$. Sección fisurada. Usando $I_{{cr}}$ provisto para $I_e = {I_efectiva_mm4:,.0f} mm^4$."
                    else:
                        factor_aprox_Ie = 0.25 if "losa" in tipo_elemento_def.lower() or "nervio" in tipo_elemento_def.lower() else 0.35
                        I_efectiva_mm4 = factor_aprox_Ie * Ig_val
                        msg_Ie = f"$M_a > M_{{cr}}$. Sección fisurada. $I_{{cr}}$ no provisto. Usando $I_e \approx {factor_aprox_Ie} \cdot I_g = {I_efectiva_mm4:,.0f} mm^4$."
                
                delta_inst_CM = calcular_deflexion_instantanea(L_libre_cm_def, w_CM_kNpm_def, Ec_MPa, I_efectiva_mm4, tipo_apoyo_def)
                delta_inst_CV_total = calcular_deflexion_instantanea(L_libre_cm_def, w_CV_kNpm_def, Ec_MPa, I_efectiva_mm4, tipo_apoyo_def)
                delta_inst_CV_sostenida = calcular_deflexion_instantanea(L_libre_cm_def, w_CVsostenida_kNpm, Ec_MPa, I_efectiva_mm4, tipo_apoyo_def)
                delta_inst_total_sostenida = calcular_deflexion_instantanea(L_libre_cm_def, w_TotalSostenida_kNpm, Ec_MPa, I_efectiva_mm4, tipo_apoyo_def)
                
                b_calc_rho_prima_cm = b_eff_calc_cm if es_T_secc_def else b_elem_cm_def
                d_calc_rho_prima_mm = cm_to_mm(h_elem_cm_def) - y_centroide_sup_mm_val # d al acero inferior
                
                rho_prima_comp_val = 0.0
                if As_comp_cm2_def > 0 and b_calc_rho_prima_cm > 0 and d_calc_rho_prima_mm > 0:
                     rho_prima_comp_val = (As_comp_cm2_def * 100) / (cm_to_mm(b_calc_rho_prima_cm) * d_calc_rho_prima_mm) # As_cm2 * 100 = As_mm2
                
                delta_adicional_LP = calcular_deflexion_largo_plazo(delta_inst_total_sostenida, xi_factor_def, rho_prima_comp_val)
                delta_total_LP_sostenida = delta_inst_total_sostenida + delta_adicional_LP
                delta_inst_CV_no_sostenida = delta_inst_CV_total - delta_inst_CV_sostenida
                delta_verif_susceptible = delta_adicional_LP + delta_inst_CV_no_sostenida
                
                st.session_state.resultados_deflexion_actual = {
                    "Ma_kNm": Ma_kNm, "Mcr_kNm": Mcr_kNm, "msg_Ie": msg_Ie, "fisurada": fisurada,
                    "delta_inst_CM": delta_inst_CM, "delta_inst_CV_total": delta_inst_CV_total,
                    "delta_inst_total_sostenida": delta_inst_total_sostenida,
                    "delta_adicional_LP": delta_adicional_LP, "delta_total_LP_sostenida": delta_total_LP_sostenida,
                    "delta_verif_susceptible": delta_verif_susceptible, 
                    "id_elemento": id_elemento_deflex_reporte, "tipo_elemento": tipo_elemento_def,
                    "L_libre_cm": L_libre_cm_def, "Ec_MPa": Ec_MPa, "Ig_mm4": Ig_val, "yt_mm": yt_val,
                    "Ie_mm4": I_efectiva_mm4, "w_CM_kNpm": w_CM_kNpm_def, "w_CV_kNpm": w_CV_kNpm_def,
                    "w_CVsostenida_kNpm": w_CVsostenida_kNpm, "xi_factor": xi_factor_def, "rho_prima": rho_prima_comp_val
                }
                st.session_state.calculo_deflexion_realizado = True
                st.success(f"Cálculo de deflexiones para '{id_elemento_deflex_reporte}' completado.")


    with col2_def:
        st.subheader("2. Resultados del Análisis de Deflexión")
        
        # ESTE ES EL BLOQUE CONDICIONAL IMPORTANTE
        if st.session_state.get("calculo_deflexion_realizado", False) and "resultados_deflexion_actual" in st.session_state:
            res_def = st.session_state.resultados_deflexion_actual # res_def se define AQUÍ
            
            st.markdown(f"**Elemento:** {res_def['id_elemento']} ({res_def['tipo_elemento']})")
            st.markdown(f"**$M_a$ (CM+CV):** {res_def['Ma_kNm']:.2f} kNm, **$M_{{cr}}$:** {res_def['Mcr_kNm']:.2f} kNm")
            st.info(res_def['msg_Ie'])
            
            st.markdown("##### Deflexiones Calculadas (mm):")
            col_delta1, col_delta2 = st.columns(2)
            with col_delta1:
                st.metric("δ inst. CM", f"{res_def['delta_inst_CM']:.3f}")
                st.metric("δ inst. CV Total", f"{res_def['delta_inst_CV_total']:.3f}")
                st.metric("δ inst. Carga Sostenida", f"{res_def['delta_inst_total_sostenida']:.3f}")
            with col_delta2:
                st.metric("δ adicional Largo Plazo", f"{res_def['delta_adicional_LP']:.3f}")
                st.metric("δ Total Largo Plazo (Sost.)", f"{res_def['delta_total_LP_sostenida']:.3f}")
                st.metric("δ a Verificar (Susceptibles)", f"{res_def['delta_verif_susceptible']:.3f}")

            st.markdown("##### Verificación de Límites (NSR-10 Tabla C.9-1):")
            
            opciones_cond_limite = {
                "Elementos susceptibles a fisuración (ej. mampostería) - L/480": 'Total_diferida_susceptible_a_fisuracion',
                "Elementos NO susceptibles a fisuración (ej. acabados flexibles) - L/240": 'Total_diferida_no_susceptible_a_fisuracion'
            }
            cond_lim_sel_descripcion = st.selectbox(
                "Condición de Elementos No Estructurales para Límite Diferido:",
                list(opciones_cond_limite.keys()), 
                key="cond_no_est_def_v4" 
            )
            cond_dif = opciones_cond_limite[cond_lim_sel_descripcion]
            
            # Estas variables ahora se obtienen de res_def que está definido en este bloque
            tipo_elemento_para_verif = res_def["tipo_elemento"]
            L_libre_para_verif = res_def["L_libre_cm"]
            delta_cv_total_para_verif = res_def["delta_inst_CV_total"]
            delta_verif_susc_para_verif = res_def["delta_verif_susceptible"]

            cond_cv_inm = 'CV_inmediata_no_susceptible' 
            cumple_cv, lim_cv, n_cv = verificar_limites_deflexion_nsr10(
                delta_cv_total_para_verif, L_libre_para_verif, tipo_elemento_para_verif, cond_cv_inm
            )
            st.write(f"**Def. Inmediata por CV Total vs. L/{n_cv}**: {delta_cv_total_para_verif:.3f} mm {'✅ Cumple' if cumple_cv else '❌ NO Cumple'} (Límite: {lim_cv:.3f} mm)")
            
            cumple_dif, lim_dif, n_dif = verificar_limites_deflexion_nsr10(
                delta_verif_susc_para_verif, L_libre_para_verif, tipo_elemento_para_verif, cond_dif
            )
            st.write(f"**Def. Diferida (LP + CVnoSost) vs. L/{n_dif}**: {delta_verif_susc_para_verif:.3f} mm {'✅ Cumple' if cumple_dif else '❌ NO Cumple'} (Límite: {lim_dif:.3f} mm)")

            # --- Guardar datos para el reporte ---
            datos_deflex_reporte = {
                "ID Elemento": res_def.get("id_elemento"), "Tipo Elemento": res_def.get("tipo_elemento"),
                "Luz Libre Ln (cm)": res_def.get("L_libre_cm"), "Ec (MPa)": res_def.get("Ec_MPa"),
                "Ig (mm⁴)": res_def.get("Ig_mm4"), "yt (mm)": res_def.get("yt_mm"),
                "Mcr (kNm)": res_def.get("Mcr_kNm"), "Ma (kNm)": res_def.get("Ma_kNm"),
                "Ie (mm⁴)": res_def.get("Ie_mm4"), "w_CM (kN/m)": res_def.get("w_CM_kNpm"),
                "w_CV_total (kN/m)": res_def.get("w_CV_kNpm"), "w_CV_sost (kN/m)": res_def.get("w_CVsostenida_kNpm"),
                "Δ inst CM (mm)": res_def.get("delta_inst_CM"), "Δ inst CVtot (mm)": res_def.get("delta_inst_CV_total"),
                "Δ inst Sost (mm)": res_def.get("delta_inst_total_sostenida"), "Δ adic LP (mm)": res_def.get("delta_adicional_LP"),
                "Δ verif susc (mm)": res_def.get("delta_verif_susceptible"),
                "Límite CV (L/n)": f"L/{n_cv} ({lim_cv:.2f} mm)" if n_cv is not None else 'N/A',
                "Cumple CV": "Sí" if 'cumple_cv' in locals() and cumple_cv else ("No" if 'cumple_cv' in locals() else "N/A"),
                "Límite Dif. (L/n)": f"L/{n_dif} ({lim_dif:.2f} mm)" if n_dif is not None else 'N/A',
                "Cumple Dif.": "Sí" if 'cumple_dif' in locals() and cumple_dif else ("No" if 'cumple_dif' in locals() else "N/A"),
            }
            
            # Lógica para añadir o actualizar en la lista del reporte
            elemento_encontrado = False
            for i, item in enumerate(st.session_state.lista_deflexiones_reporte):
                if item["ID Elemento"] == res_def.get("id_elemento"):
                    st.session_state.lista_deflexiones_reporte[i] = datos_deflex_reporte
                    elemento_encontrado = True
                    st.info(f"Resultados de deflexión para '{res_def.get('id_elemento')}' actualizados en el reporte.")
                    break
            if not elemento_encontrado:
                st.session_state.lista_deflexiones_reporte.append(datos_deflex_reporte)
                st.info(f"Resultados de deflexión para '{res_def.get('id_elemento')}' añadidos al reporte.")
        
        else: # Si no se ha realizado el cálculo
            st.info("⬅️ Ingrese los datos en la columna izquierda y presione 'Calcular y Verificar Deflexiones' para ver los resultados.")
