import streamlit as st
from calculosh.diseno_vigas import (
    diseno_viga_flexion_simple, 
    diseno_viga_cortante_estandar, 
    diseno_viga_dmo, 
    calcular_peralte_efectivo_viga
)
from unidades import mm_to_cm 


def mostrar_interfaz_vigas(PG, st_session):
    st.header("Diseño de Vigas a Flexión y Cortante")
    
    fc_vigas = PG['fc_losas_vigas_MPa'] # Usar fc para losas/vigas desde globales
    fy_vigas_long = PG['fy_MPa']       # Para acero longitudinal
    fy_vigas_estrib = PG['fy_MPa']     # Para estribos (usualmente el mismo)

    st.info(f"Usando Materiales Globales: f'c = {fc_vigas} MPa, f'y Longitudinal = {fy_vigas_long} MPa, f'y Estribos = {fy_vigas_estrib} MPa")

    tipo_diseno_viga = st.radio(
        "Seleccione el Tipo de Diseño para la Viga:",
        ["Estándar (NSR-10 C.9, C.11)", "Sismorresistente (DMO - NSR-10 C.21.3)"],
        horizontal=True, key="tipo_dis_viga"
    )
    st.markdown("---")

    if tipo_diseno_viga == "Estándar (NSR-10 C.9, C.11)":
        st.subheader("Diseño Estándar de Viga")

        col_std_flex, col_std_cort = st.tabs(["Flexión Estándar", "Cortante Estándar"])

        with col_std_flex:
            st.markdown("##### Entradas para Flexión Estándar")
            b_cm_sf = st.number_input("Ancho viga b (cm)", 25.0, key="b_sf")
            h_cm_sf = st.number_input("Altura viga h (cm)", 50.0, key="h_sf")
            rec_libre_cm_sf = st.number_input("Rec. Libre (cm)", 4.0, key="rec_sf")
            diam_est_sf = st.selectbox("Ø Estribo (mm)", [9.5, 12.7], key="est_sf", index=0)
            diam_bar_sf = st.selectbox("Ø Barra Long. (mm)", [12.7, 15.9, 19.1, 22.2, 25.4], key="bar_sf", index=1)
            Mu_sf_kNm = st.number_input("Momento Último Mu (kNm)", 100.0, key="mu_sf")

            if st.button("Calcular Flexión Estándar", key="btn_sf"):
                res_sf = diseno_viga_flexion_simple(b_cm_sf, h_cm_sf, rec_libre_cm_sf, diam_est_sf, diam_bar_sf, fc_vigas, fy_vigas_long, Mu_sf_kNm)
                if res_sf['status'] != "Error":
                    st.success(f"As requerida: {res_sf['As_req_cm2']:.2f} cm² (ρ={res_sf['rho_calculado']:.4f})")
                else:
                    st.error(res_sf['mensaje'])
        
        with col_std_cort:
            st.markdown("##### Entradas para Cortante Estándar")
            b_cm_sc = st.number_input("Ancho viga b (cm)", 25.0, key="b_sc")
            h_cm_sc = st.number_input("Altura viga h (cm)", 50.0, key="h_sc")
            rec_libre_cm_sc = st.number_input("Rec. Libre (cm)", 4.0, key="rec_sc")
            diam_est_sc = st.selectbox("Ø Estribo a usar (mm)", [9.5, 12.7], key="est_sc", index=0)
            diam_bar_sc = st.selectbox("Ø Barra Long. (para d) (mm)", [12.7, 15.9, 19.1, 22.2, 25.4], key="bar_sc", index=1)
            Vu_sc_kN = st.number_input("Cortante Último Vu (kN)", 80.0, key="vu_sc")

            if st.button("Calcular Cortante Estándar", key="btn_sc"):
                res_sc = diseno_viga_cortante_estandar(b_cm_sc, h_cm_sc, rec_libre_cm_sc, diam_est_sc, diam_bar_sc, fc_vigas, fy_vigas_estrib, Vu_sc_kN)
                if res_sc['status'] != "Error":
                    st.success(f"Av/s requerido: {res_sc['Av_s_req_mm2_por_m']:.2f} mm²/m")
                    if res_sc['s_rec_mm'] is not None:
                        st.info(f"Espaciamiento recomendado para estribos Ø{res_sc['diam_estribo_usado_mm']}mm: {res_sc['s_rec_mm']:.0f} mm")
                    else:
                        st.info("No se requiere refuerzo por cálculo, verificar mínimos normativos.")
                else:
                    st.error(res_sc['mensaje'])


    elif tipo_diseno_viga == "Sismorresistente (DMO - NSR-10 C.21.3)":
        st.subheader("Diseño de Viga para Pórtico DMO (NSR-10 C.21.3)")
        
        with st.form(key="form_viga_dmo_inputs"):
            id_viga_reporte = st.text_input("ID Viga para Reporte (ej: V-101 EjeA N2)", key="id_viga_dmo")
            st.markdown("##### Geometría de la Viga")
            col_vg1, col_vg2, col_vg3 = st.columns(3)
            with col_vg1:
                b_v_dmo_cm = st.number_input("Ancho (b, cm)", min_value=20.0, value=30.0, step=1.0, key="b_v_dmo")
            with col_vg2:
                h_v_dmo_cm = st.number_input("Altura Total (h, cm)", min_value=25.0, value=50.0, step=1.0, key="h_v_dmo")
            with col_vg3:
                ln_v_dmo_m = st.number_input("Luz Libre ($L_n$, m)", min_value=2.0, value=5.5, step=0.1, key="ln_v_dmo")

            st.markdown("##### Recubrimientos y Diámetros de Barras")
            col_vr1, col_vr2, col_vr3 = st.columns(3)
            with col_vr1:
                rec_libre_v_dmo_cm = st.number_input("Rec. Libre a Estribo (cm)", min_value=2.5, value=4.0, step=0.5, key="rec_v_dmo")
            with col_vr2:
                diam_est_v_dmo_mm = st.selectbox("Ø Estribo (mm)", [9.5, 12.7], index=0, key="est_v_dmo")
            with col_vr3:
                diam_bar_long_v_dmo_mm = st.selectbox("Ø Barra Long. Principal (mm)", [12.7, 15.9, 19.1, 22.2, 25.4], index=1, key="barlong_v_dmo")
            
            st.markdown("##### Momentos Flectores de Diseño ($M_u$)")
            col_vm1, col_vm2, col_vm3 = st.columns(3)
            with col_vm1:
                Mu_neg_ext_v_dmo_kNm = st.number_input("$M_u$ Negativo Apoyo Ext. (kNm)", value=120.0, step=5.0, key="munegext_v_dmo")
            with col_vm2:
                Mu_pos_v_dmo_kNm = st.number_input("$M_u$ Positivo Centro Luz (kNm)", value=90.0, step=5.0, key="mupos_v_dmo")
            with col_vm3:
                Mu_neg_int_v_dmo_kNm = st.number_input("$M_u$ Negativo Apoyo Int. (kNm)", value=150.0, step=5.0, key="munegint_v_dmo")

            st.markdown("##### Cortantes Isostáticos por Cargas Gravitacionales ($V_{u,grav}$ en apoyos)")
            col_vv1, col_vv2 = st.columns(2)
            with col_vv1:
                Vu_grav_ext_v_dmo_kN = st.number_input("$V_{u,grav}$ Apoyo Ext. (kN)", value=70.0, step=5.0, key="vugravext_v_dmo", help="Cortante por cargas D y L en el apoyo externo.")
            with col_vv2:
                Vu_grav_int_v_dmo_kN = st.number_input("$V_{u,grav}$ Apoyo Int. (kN)", value=85.0, step=5.0, key="vugravint_v_dmo", help="Cortante por cargas D y L en el apoyo interno.")
            
            submitted_viga_dmo_calc = st.form_submit_button("🏗️ Diseñar Viga DMO")
        
        if submitted_viga_dmo_calc:
            if not id_viga_reporte.strip(): # Validar que el ID no esté vacío
                st.error("Por favor, ingrese un ID para la viga.")
            else:
                try:
                    # Calcular d una vez para mostrarlo y usarlo
                    d_v_dmo_cm = mm_to_cm(calcular_peralte_efectivo_viga(h_v_dmo_cm, rec_libre_v_dmo_cm, diam_est_v_dmo_mm, diam_bar_long_v_dmo_mm))
                    st.info(f"Peralte efectivo (d) calculado para la viga: {d_v_dmo_cm:.2f} cm")

                    resultados_v_dmo = diseno_viga_dmo(
                        b_cm=b_v_dmo_cm, h_cm=h_v_dmo_cm, 
                        rec_libre_cm=rec_libre_v_dmo_cm, # Pasar recubrimiento libre
                        diam_estribo_mm=diam_est_v_dmo_mm, 
                        diam_barra_long_principal_mm=diam_bar_long_v_dmo_mm,
                        fc_MPa=fc_vigas, fy_MPa_long=fy_vigas_long, fy_MPa_estribos=fy_vigas_estrib,
                        Mu_neg_ext_kNm=Mu_neg_ext_v_dmo_kNm, Mu_pos_kNm=Mu_pos_v_dmo_kNm, Mu_neg_int_kNm=Mu_neg_int_v_dmo_kNm,
                        ln_m=ln_v_dmo_m,
                        Vu_grav_ext_kN=Vu_grav_ext_v_dmo_kN, Vu_grav_int_kN=Vu_grav_int_v_dmo_kN
                    )

                    if resultados_v_dmo["status"] == "OK":
                    
                        st.success(resultados_v_dmo.get("mensaje_global", "Cálculo DMO de viga completado."))
                        st.info(resultados_v_dmo.get("mensaje_cuantia", ""))

                        st.markdown("##### Acero de Refuerzo Longitudinal ($A_s$ requerido)")
                        res_flex_ext = resultados_v_dmo.get("flexion_neg_ext", {})
                        res_flex_pos = resultados_v_dmo.get("flexion_pos", {})
                        res_flex_int = resultados_v_dmo.get("flexion_neg_int", {})
                        
                        col_as_v1, col_as_v2, col_as_v3 = st.columns(3)
                        col_as_v1.metric("As Apoyo Ext. (-)", f"{res_flex_ext.get('As_req_cm2', 'N/A'):.2f} cm²", help=f"ρ={res_flex_ext.get('rho', 'N/A'):.4f}")
                        col_as_v2.metric("As Centro Luz (+)", f"{res_flex_pos.get('As_req_cm2', 'N/A'):.2f} cm²", help=f"ρ={res_flex_pos.get('rho', 'N/A'):.4f}")
                        col_as_v3.metric("As Apoyo Int. (-)", f"{res_flex_int.get('As_req_cm2', 'N/A'):.2f} cm²", help=f"ρ={res_flex_int.get('rho', 'N/A'):.4f}")

                        st.markdown("---")
                        st.markdown("##### Acero de Refuerzo Transversal (Estribos Ø" + str(resultados_v_dmo.get('estribos_diam_mm','N/A')) + "mm)")
                        st.metric(f"Cortante de Diseño ($V_e$) Máximo en Apoyos", 
                                f"{max(resultados_v_dmo.get('cortante_diseno_Ve_ext_kN',0), resultados_v_dmo.get('cortante_diseno_Ve_int_kN',0)):.2f} kN")

                        col_s_v1, col_s_v2 = st.columns(2)
                        with col_s_v1:
                            st.markdown(f"**Zona Confinada (en apoyos, $l_o = {resultados_v_dmo.get('longitud_confinamiento_lo_cm', 'N/A')}$ cm):**")
                            st.success(f"Usar estribos @ **{resultados_v_dmo.get('espaciamiento_zona_confinada_cm', 'N/A')} cm**")
                        with col_s_v2:
                            st.markdown("**Zona Central (resto de la viga):**")
                            st.success(f"Usar estribos @ **{resultados_v_dmo.get('espaciamiento_zona_central_cm', 'N/A')} cm**")
                        
                        st.caption(f"Peralte efectivo (d) usado para el diseño: {resultados_v_dmo.get('d_usado_cm', 'N/A')} cm")

                        with st.expander("Ver detalles completos del cálculo DMO"):
                            st.json(resultados_v_dmo)
                        
                        # Guardar para memoria de cálculo
                        if 'resultados_vigas_para_excel' not in st.session_state:
                            st.session_state.resultados_vigas_para_excel = []
                        
                        # Datos a guardar para la memoria (ajusta según necesites)
                        datos_viga_para_reporte = {
                                "ID Elemento": id_viga_reporte,
                                "b (cm)": b_v_dmo_cm,
                                "h (cm)": h_v_dmo_cm,
                                "d (cm)": resultados_v_dmo.get('d_usado_cm', 'N/A'),
                                "Ln (m)": ln_v_dmo_m,
                                "f'c (MPa)": fc_vigas,
                                "fy (MPa)": fy_vigas_long, # Asumiendo el mismo para estribos por simplicidad en tabla
                                "Mu(-) Ext (kNm)": Mu_neg_ext_v_dmo_kNm,
                                "As(-) Ext (cm²)": resultados_v_dmo.get("flexion_neg_ext", {}).get('As_req_cm2', 'N/A'),
                                "ρ(-) Ext": resultados_v_dmo.get("flexion_neg_ext", {}).get('rho', 'N/A'),
                                "Mu(+) Cen (kNm)": Mu_pos_v_dmo_kNm,
                                "As(+) Cen (cm²)": resultados_v_dmo.get("flexion_pos", {}).get('As_req_cm2', 'N/A'),
                                "ρ(+) Cen": resultados_v_dmo.get("flexion_pos", {}).get('rho', 'N/A'),
                                "Mu(-) Int (kNm)": Mu_neg_int_v_dmo_kNm,
                                "As(-) Int (cm²)": resultados_v_dmo.get("flexion_neg_int", {}).get('As_req_cm2', 'N/A'),
                                "ρ(-) Int": resultados_v_dmo.get("flexion_neg_int", {}).get('rho', 'N/A'),
                                "Ve,max (kN)": max(resultados_v_dmo.get('cortante_diseno_Ve_ext_kN',0), resultados_v_dmo.get('cortante_diseno_Ve_int_kN',0)),
                                "Ø Estribo (mm)": resultados_v_dmo.get('estribos_diam_mm'),
                                "s confinado (cm)": resultados_v_dmo.get('espaciamiento_zona_confinada_cm'),
                                "s central (cm)": resultados_v_dmo.get('espaciamiento_zona_central_cm'),
                                "Lo (cm)": resultados_v_dmo.get('longitud_confinamiento_lo_cm'),
                                "Estado Diseño": "OK" # O el mensaje de cuantía
                            }
                        st.session_state.lista_vigas_reporte.append(datos_viga_para_reporte)
                        st.info(f"Resultados de viga '{id_viga_reporte}' añadidos al reporte.")
                    else:
                        datos_viga_fallida_reporte = {
                            "ID Elemento": id_viga_reporte, "b (cm)": b_v_dmo_cm, "h (cm)": h_v_dmo_cm, 
                            "Estado Diseño": "Error", "Mensaje": resultados_v_dmo.get("mensaje_global", "Error desconocido")
                        }

                except Exception as e:
                    st.error(f"Ocurrió un error en el diseño DMO de la viga: {e}")
                    import traceback
                    st.text(traceback.format_exc()) # Para depuración