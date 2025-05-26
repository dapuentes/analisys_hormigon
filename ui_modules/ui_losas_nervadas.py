import streamlit as st
from calculosh.losa_nervada import *


def mostrar_interfaz_losas_nervadas(PG, st_session_state):
    st.header("Diseño de Losa Nervada Unidireccional")
    fc_losa_nerv = PG['fc_losas_vigas_MPa'] # Usar fc para losas/vigas
    fy_losa_nerv = PG['fy_MPa']
    st.info(f"Usando Materiales Globales: f'c = {fc_losa_nerv} MPa, f'y = {fy_losa_nerv} MPa")

    # Guardar datos de geometría y cargas de la losa en session_state
    if 'losa_nerv_geom_cargas' not in st.session_state:
        st.session_state.losa_nerv_geom_cargas = {
            "separacion_nervios_m": 0.6, "t_loseta_cm": 5.0, "h_total_nervio_cm": 25.0,
            "b_alma_nervio_cm": 10.0, "q_muerta_adicional_kNm2": 1.5, "q_viva_kNm2": 1.8,
            "L_libre_nervio_m": 5.0, # Luz libre del nervio, importante para b_eff
            "rec_libre_inf_cm": 2.5, # Recubrimiento inferior nervio
            "diam_estribo_mm_def": 9.5, # Default #3
            "diam_barra_long_mm_def": 15.9 # Default #5
        }
    
    data_ln = st.session_state.losa_nerv_geom_cargas

    id_losa_nervada_reporte = st.text_input("ID Losa Nervada/Nervio para Reporte (ej: LosaN2-N1, Nervio EjeA)", key="id_ln_rep")

    tab_cargas_ln, tab_flex_ln, tab_cort_ln = st.tabs([
        "⚖️ Cargas por Nervio", "💪 Diseño a Flexión (Nervio)", "✂️ Diseño a Cortante (Nervio)"
    ])

    # --- Pestaña Cargas por Nervio ---
    with tab_cargas_ln:
        st.subheader("Cálculo de Cargas Lineales por Nervio")
        
        col1_cln, col2_cln = st.columns(2)
        with col1_cln:
            st.markdown("##### Geometría de la Losa Nervada")
            data_ln["separacion_nervios_m"] = st.number_input("Separación centro a centro de Nervios (m)", min_value=0.3, value=data_ln["separacion_nervios_m"], step=0.05, key="sep_ln_c")
            data_ln["t_loseta_cm"] = st.number_input("Espesor Loseta (hf) (cm)", min_value=4.0, value=data_ln["t_loseta_cm"], step=0.5, key="tlos_ln_c")
            data_ln["h_total_nervio_cm"] = st.number_input("Altura Total Nervio (h) (cm, loseta+alma)", min_value=15.0, value=data_ln["h_total_nervio_cm"], step=1.0, key="htot_ln_c")
            data_ln["b_alma_nervio_cm"] = st.number_input("Ancho Alma Nervio (bw) (cm)", min_value=8.0, value=data_ln["b_alma_nervio_cm"], step=1.0, key="balma_ln_c")
        
        with col2_cln:
            st.markdown("##### Cargas superficiales (kN/m²)")
            data_ln["q_muerta_adicional_kNm2"] = st.number_input("CM Adicional (kN/m², acabados, etc.)", min_value=0.0, value=data_ln["q_muerta_adicional_kNm2"], step=0.1, key="cm_adic_ln_c")
            data_ln["q_viva_kNm2"] = st.number_input("CV (kN/m²)", min_value=0.0, value=data_ln["q_viva_kNm2"], step=0.1, key="cv_ln_c")

        if st.button("⚖️ Calcular Cargas por Nervio", key="btn_cargas_ln"):
            if not id_losa_nervada_reporte.strip():
                st.error("Por favor, ingrese un ID para la losa nervada/nervio antes de calcular.")
            else:
                try:
                    resultados_cargas = calcular_cargas_losa_nervada(
                        data_ln["separacion_nervios_m"], data_ln["t_loseta_cm"], 
                        data_ln["h_total_nervio_cm"], data_ln["b_alma_nervio_cm"],
                        data_ln["q_muerta_adicional_kNm2"], data_ln["q_viva_kNm2"]
                    )
                    data_ln.update(resultados_cargas) # Guardar resultados en session_state
                    st.session_state.losa_nerv_geom_cargas = data_ln # Actualizar session_state

                    st.success("Cargas calculadas:")
                    st.metric("Peso Propio Losa", f"{resultados_cargas['peso_propio_losa_kNm2']:.2f} kN/m²")
                    col_w1, col_w2 = st.columns(2)
                    with col_w1:
                        st.metric("W Muerta Total por Nervio", f"{resultados_cargas['w_muerta_total_por_nervio_kNm']:.2f} kN/m")
                    with col_w2:
                        st.metric("W Viva por Nervio", f"{resultados_cargas['w_viva_por_nervio_kNm']:.2f} kN/m")
                    st.markdown("---")
                    st.markdown("**Nota:** Use estas cargas lineales con los coeficientes de momento y cortante de NSR-10 C.8.3.3 (o de un análisis estructural) para obtener $M_u$ y $V_u$ para el diseño del nervio en las siguientes pestañas.")
                    st.session_state.current_id_losa_nervada = id_losa_nervada_reporte

                except ValueError as e:
                    st.error(f"Error en datos de entrada: {e}")
                except Exception as e:
                    st.error(f"Error inesperado en cálculo de cargas: {e}")

    # --- Pestaña Diseño a Flexión del Nervio ---
    with tab_flex_ln:
        st.subheader("Diseño a Flexión del Nervio")
        st.write("Ingrese el momento último de diseño $M_u$ para el nervio (obtenido de análisis o coeficientes NSR-10).")

        col1_fln, col2_fln = st.columns(2)
        with col1_fln:
            st.markdown("##### Solicitación")
            Mu_kNm_fln = st.number_input("Momento Último $M_u$ (kNm)", value=15.0, step=0.5, key="mu_fln", help="Positivo para tracción inferior, negativo para tracción superior.")
            
            st.markdown("##### Geometría (Puede usar valores de 'Cargas por Nervio')")
            sync_geom_fln = st.checkbox("Usar geometría de pestaña 'Cargas'", value=True, key="sync_geom_fln")

            h_total_cm_fln = st.number_input("Altura Total Nervio h (cm)", value=data_ln["h_total_nervio_cm"], step=1.0, key="h_fln", disabled=sync_geom_fln)
            bw_cm_fln = st.number_input("Ancho Alma Nervio bw (cm)", value=data_ln["b_alma_nervio_cm"], step=1.0, key="bw_fln", disabled=sync_geom_fln)
            hf_cm_fln = st.number_input("Espesor Loseta hf (cm)", value=data_ln["t_loseta_cm"], step=0.5, key="hf_fln", disabled=sync_geom_fln)
            
            st.markdown("##### Parámetros Adicionales para Diseño")
            sep_nerv_m_fln = st.number_input("Separación Nervios (m, para $b_{eff}$)", value=data_ln["separacion_nervios_m"], step=0.05, key="sep_fln", disabled=sync_geom_fln and "separacion_nervios_m" in data_ln)
            L_libre_m_fln = st.number_input("Luz Libre del Nervio (m, para $b_{eff}$)", value=data_ln.get("L_libre_nervio_m",5.0), step=0.1, key="Llibre_fln")
            
            rec_libre_inf_cm_fln = st.number_input("Rec. Libre Inferior (cm)", value=data_ln.get("rec_libre_inf_cm", 2.5), step=0.5, key="rec_inf_fln")
            
            diam_estribo_opts_mm = {"#3 (9.5mm)": 9.5, "#4 (12.7mm)": 12.7, "Ninguno": 0.0}
            sel_estribo_fln = st.selectbox("Diámetro Estribo (si hay)", list(diam_estribo_opts_mm.keys()), index=2, key="diam_e_fln") # Ninguno por defecto
            diam_estribo_mm_fln = diam_estribo_opts_mm[sel_estribo_fln]

            diam_barra_opts_mm = {"#3 (9.5mm)":9.5, "#4 (12.7mm)": 12.7, "#5 (15.9mm)": 15.9, "#6 (19.1mm)": 19.1}
            sel_barra_fln = st.selectbox("Diámetro Barra Long. (Ref.)", list(diam_barra_opts_mm.keys()), index=1, key="diam_b_fln") # #4 por defecto
            diam_barra_long_mm_fln = diam_barra_opts_mm[sel_barra_fln]
            
            # Actualizar data_ln si no se sincroniza
            if not sync_geom_fln:
                data_ln["h_total_nervio_cm"] = h_total_cm_fln
                data_ln["b_alma_nervio_cm"] = bw_cm_fln
                data_ln["t_loseta_cm"] = hf_cm_fln
                data_ln["separacion_nervios_m"] = sep_nerv_m_fln
            data_ln["L_libre_nervio_m"] = L_libre_m_fln
            data_ln["rec_libre_inf_cm"] = rec_libre_inf_cm_fln
            data_ln["diam_estribo_mm_def"] = diam_estribo_mm_fln
            data_ln["diam_barra_long_mm_def"] = diam_barra_long_mm_fln
            st.session_state.losa_nerv_geom_cargas = data_ln

        if st.button("💪 Diseñar Nervio a Flexión", key="btn_flex_ln"):
            current_id_ln = st.session_state.get("current_id_losa_nervada", id_losa_nervada_reporte if 'id_losa_nervada_reporte' in locals() and id_losa_nervada_reporte.strip() else "Nervio_Desconocido")
            if current_id_ln == "Nervio_Desconocido" and id_losa_nervada_reporte.strip(): # Si se ingresó ID pero no se presionó calcular cargas
                 current_id_ln = id_losa_nervada_reporte
            elif current_id_ln == "Nervio_Desconocido":
                 st.error("Por favor, ingrese un ID para la losa nervada/nervio en la pestaña de Cargas o aquí.")
                 st.stop()
            try:
                # Usar los valores de data_ln que se actualizaron
                resultados_flex_nervio = diseno_nervio_flexion(
                    Mu_kNm=Mu_kNm_fln, fc_MPa=fc_losa_nerv, fy_MPa=fy_losa_nerv,
                    h_total_cm=data_ln["h_total_nervio_cm"], bw_cm=data_ln["b_alma_nervio_cm"],
                    hf_cm=data_ln["t_loseta_cm"],
                    separacion_nervios_m=data_ln["separacion_nervios_m"], 
                    L_libre_nervio_m=data_ln["L_libre_nervio_m"],
                    rec_libre_inf_cm=data_ln["rec_libre_inf_cm"],
                    diam_estribo_mm=data_ln["diam_estribo_mm_def"],
                    diam_barra_long_mm=data_ln["diam_barra_long_mm_def"]
                )
                with col2_fln:
                    st.markdown("##### Resultados Diseño a Flexión del Nervio")
                    st.info(f"Mensaje: {resultados_flex_nervio['mensaje']}")
                    if resultados_flex_nervio['status'] != "Error":
                        st.metric("As Final Requerida", f"{resultados_flex_nervio['As_final_cm2']:.3f} cm²")
                        st.json(resultados_flex_nervio, expanded=False) # Mostrar todos los detalles
                    else:
                        st.error(f"No se pudo completar el diseño a flexión. {resultados_flex_nervio.get('b_eff_mm','')} ")

                if resultados_flex_nervio['status'] != "Error":
                    # Guardar temporalmente los resultados de flexión para combinarlos con los de cortante
                    st.session_state.temp_flex_nervio_resultados = resultados_flex_nervio
                    st.session_state.temp_flex_nervio_inputs = { # Guardar inputs relevantes
                        "ID Elemento": current_id_ln,
                        "h_total_cm": data_ln["h_total_nervio_cm"],
                        "bw_cm": data_ln["b_alma_nervio_cm"],
                        "hf_cm": data_ln["t_loseta_cm"],
                        "L_libre_m": data_ln["L_libre_nervio_m"],
                        "sep_nervios_m": data_ln["separacion_nervios_m"],
                        "Mu_kNm": Mu_kNm_fln, # El Mu usado para este cálculo
                        "fc_MPa": fc_losa_nerv, "fy_MPa": fy_losa_nerv
                    }

            except Exception as e:
                with col2_fln: st.error(f"Error inesperado en diseño a flexión: {e}")
                # import traceback; st.text(traceback.format_exc())

    # --- Pestaña Diseño a Cortante del Nervio ---
    with tab_cort_ln:
        st.subheader("Diseño a Cortante del Nervio")
        st.write("Ingrese el cortante último de diseño $V_u$ para el nervio.")

        col1_cln_cort, col2_cln_cort = st.columns(2)
        with col1_cln_cort:
            st.markdown("##### Solicitación")
            Vu_kN_cln = st.number_input("Cortante Último $V_u$ (kN)", value=10.0, step=0.5, key="vu_cln")

            st.markdown("##### Geometría (Puede usar valores de Pestañas Anteriores)")
            sync_geom_cln_cort = st.checkbox("Usar geometría de pestaña 'Cargas'/'Flexión'", value=True, key="sync_geom_cln_cort")

            h_total_cm_cln_cort = st.number_input("Altura Total Nervio h (cm)", value=data_ln["h_total_nervio_cm"], step=1.0, key="h_cln_cort", disabled=sync_geom_cln_cort)
            bw_cm_cln_cort = st.number_input("Ancho Alma Nervio bw (cm)", value=data_ln["b_alma_nervio_cm"], step=1.0, key="bw_cln_cort", disabled=sync_geom_cln_cort)
            
            st.markdown("##### Recubrimiento y Armado (para 'd' y estribos)")
            rec_libre_inf_cm_cln_cort = st.number_input("Rec. Libre Inferior (cm)", value=data_ln["rec_libre_inf_cm"], step=0.5, key="rec_inf_cln_cort", disabled=sync_geom_cln_cort)
            
            sel_estribo_cln_cort = st.selectbox("Diámetro Estribo a Usar", list(diam_estribo_opts_mm.keys()), index=list(diam_estribo_opts_mm.keys()).index(sel_estribo_fln) if 'sel_estribo_fln' in locals() else 2, key="diam_e_cln_cort")
            diam_estribo_mm_cln_cort = diam_estribo_opts_mm[sel_estribo_cln_cort]

            sel_barra_cln_cort = st.selectbox("Diámetro Barra Long. (Ref. para d)", list(diam_barra_opts_mm.keys()), index=list(diam_barra_opts_mm.keys()).index(sel_barra_fln) if 'sel_barra_fln' in locals() else 1, key="diam_b_cln_cort")
            diam_barra_long_mm_cln_cort = diam_barra_opts_mm[sel_barra_cln_cort]

            # Actualizar data_ln si no se sincroniza
            if not sync_geom_cln_cort:
                data_ln["h_total_nervio_cm"] = h_total_cm_cln_cort
                data_ln["b_alma_nervio_cm"] = bw_cm_cln_cort
                data_ln["rec_libre_inf_cm"] = rec_libre_inf_cm_cln_cort
            # Siempre actualizar diámetros de referencia para cortante
            data_ln["diam_estribo_mm_def"] = diam_estribo_mm_cln_cort
            data_ln["diam_barra_long_mm_def"] = diam_barra_long_mm_cln_cort
            st.session_state.losa_nerv_geom_cargas = data_ln

        if st.button("✂️ Diseñar Nervio a Cortante", key="btn_cort_ln"):
            current_id_ln = st.session_state.get("current_id_losa_nervada", id_losa_nervada_reporte if 'id_losa_nervada_reporte' in locals() and id_losa_nervada_reporte.strip() else "Nervio_Desconocido")
            if current_id_ln == "Nervio_Desconocido" and id_losa_nervada_reporte.strip():
                 current_id_ln = id_losa_nervada_reporte
            elif current_id_ln == "Nervio_Desconocido":
                 st.error("Por favor, ingrese un ID para la losa nervada/nervio en la pestaña de Cargas o aquí.")
                 st.stop()

            if not st.session_state.get("temp_flex_nervio_resultados"):
                st.error("Primero diseñe el nervio a flexión en la pestaña anterior.")
            else:
                try:
                    resultados_cort_nervio = diseno_nervio_cortante(
                        Vu_kN=Vu_kN_cln, fc_MPa=fc_losa_nerv, fy_MPa=fy_losa_nerv,
                        h_total_cm=data_ln["h_total_nervio_cm"], bw_cm=data_ln["b_alma_nervio_cm"],
                        rec_libre_inf_cm=data_ln["rec_libre_inf_cm"],
                        diam_estribo_mm=data_ln["diam_estribo_mm_def"], # Este es el que se está diseñando
                        diam_barra_long_mm=data_ln["diam_barra_long_mm_def"]
                    )
                    with col2_cln_cort:
                        st.markdown("##### Resultados Diseño a Cortante del Nervio")
                        st.info(f"Mensaje: {resultados_cort_nervio['mensaje']}")
                        if resultados_cort_nervio['status'] != "Error":
                            st.metric("Av/s Final Requerido", f"{resultados_cort_nervio['Av_s_final_mm2_per_m']:.2f} mm²/m")
                            s_rec = resultados_cort_nervio.get('s_rec_constructivo_mm')
                            if s_rec and s_rec != "N/A (o según mínimos)":
                                st.success(f"Se recomienda usar estribos Ø{resultados_cort_nervio['diam_estribo_usado_mm']:.1f}mm @ {s_rec:.0f}mm")
                            else:
                                st.info("Verificar necesidad de estribos mínimos según tipo de nervio y NSR-10.")
                            st.json(resultados_cort_nervio, expanded=False)
                        else:
                            st.error("No se pudo completar el diseño a cortante.")
                    
                    # Guardar resultados de cortante junto con los de flexión
                    flex_inputs = st.session_state.temp_flex_nervio_inputs
                    flex_res = st.session_state.temp_flex_nervio_resultados
                        
                    datos_nervio_reporte = {
                            "ID Elemento": flex_inputs.get("ID Elemento", current_id_ln),
                            "h_total (cm)": flex_inputs.get("h_total_cm"),
                            "bw (cm)": flex_inputs.get("bw_cm"),
                            "hf (cm)": flex_inputs.get("hf_cm"),
                            "L_libre (m)": flex_inputs.get("L_libre_m"),
                            "S_nervios (m)": flex_inputs.get("sep_nervios_m"),
                            "fc (MPa)": flex_inputs.get("fc_MPa"),
                            "fy (MPa)": flex_inputs.get("fy_MPa"),
                            "Mu (kNm)": flex_inputs.get("Mu_kNm"),
                            "As_final (cm²)": flex_res.get("As_final_cm2"),
                            "b_eff (cm)": flex_res.get("b_eff_o_bw_cm"),
                            "epsilon_t": flex_res.get("epsilon_t_final"),
                            "Vu (kN)": Vu_kN_cln, # El Vu usado para este cálculo
                            "phiVc (kN)": resultados_cort_nervio.get("phi_Vc_kN"),
                            "Vs_req (kN)": resultados_cort_nervio.get("Vs_req_kN"),
                            "Av/s (mm²/m)": resultados_cort_nervio.get("Av_s_final_mm2_per_m"),
                            "ØEstribo (mm)": resultados_cort_nervio.get("diam_estribo_usado_mm"),
                            "s_rec (mm)": resultados_cort_nervio.get("s_rec_constructivo_mm"),
                            "Estado Flexión": flex_res.get("status"),
                            "Estado Cortante": resultados_cort_nervio.get("status")
                        }
                    st.session_state.lista_nervios_reporte.append(datos_nervio_reporte)
                    st.info(f"Resultados completos del nervio '{current_id_ln}' añadidos al reporte.")
                    
                except Exception as e:
                    with col2_cln_cort: st.error(f"Error inesperado en diseño a cortante: {e}")
                    # import traceback; st.text(traceback.format_exc())