import streamlit as st
import matplotlib.pyplot as plt

from unidades import *
from calculosh.diseno_zapatas import diseno_zapata_aislada_v2


def mostrar_interfaz_zapatas(PG, st_session):
    st.header("Diseño de Zapatas Aisladas (NSR-10 C.15)")
    # Usar f'c, f'y, y q_adm de parámetros globales
    fc_zap = PG['fc_zapatas_MPa']
    fy_zap = PG['fy_MPa']
    q_adm_zap_kPa = PG['q_adm_suelo_kPa']
    prof_desplante_zap_m = PG.get('prof_cimentacion_m', 2.0) # Usar valor global si existe

    st.info(f"Parámetros Globales en Uso: f'c = {fc_zap} MPa, f'y = {fy_zap} MPa, q_adm = {q_adm_zap_kPa} kPa, Prof. Desplante: {prof_desplante_zap_m} m")

    col1, col2 = st.columns([1, 2]) # Columna de inputs y columna de resultados

    with col1:
        st.subheader("Datos de Entrada")
        id_zapata_reporte = st.text_input("ID Zapata para Reporte (ej: Z-1, Z-EjeA-1)", key="id_zap_rep")
        
        st.markdown("##### Cargas de Servicio (para dimensionar B y L)")
        P_srv_kN_z = st.number_input("Carga Axial Servicio $P_{serv}$ (kN)", min_value=0.1, value=600.0, step=10.0, key="psrv_zap_v2")
        Mx_srv_kNm_z = st.number_input("Momento $M_{x,serv}$ (kNm, alrededor de eje Y)", min_value=0.0, value=30.0, step=5.0, key="mxsrv_zap_v2")
        My_srv_kNm_z = st.number_input("Momento $M_{y,serv}$ (kNm, alrededor de eje X)", min_value=0.0, value=20.0, step=5.0, key="mysrv_zap_v2")

        st.markdown("---")
        st.markdown("##### Cargas Últimas (para diseño de 'h' y acero)")
        P_ult_kN_z = st.number_input("Carga Axial Última $P_{u}$ (kN)", min_value=0.1, value= P_srv_kN_z * 1.4 if P_srv_kN_z * 1.4 > 0 else 850.0, step=10.0, key="pult_zap_v2") # Default 1.4*Pserv
        Mx_ult_kNm_z = st.number_input("Momento Último $M_{ux}$ (kNm, alrededor de eje Y)", min_value=0.0, value= Mx_srv_kNm_z * 1.4 if Mx_srv_kNm_z * 1.4 > 0 else 50.0, step=5.0, key="mxult_zap_v2")
        My_ult_kNm_z = st.number_input("Momento Último $M_{uy}$ (kNm, alrededor de eje X)", min_value=0.0, value= My_srv_kNm_z * 1.4 if My_srv_kNm_z * 1.4 > 0 else 30.0, step=5.0, key="myult_zap_v2")

        Mn_col_x = st.number_input("Momento Nominal Columna $M_{n,col}$ (kNm, alrededor de eje Y)", min_value=0.0, value=350.0, step=10.0, key="mncolx_zap", help="Momento nominal de la columna que se apoya en la zapata. Usar para el diseño de la zapata.")
        Mn_col_y = st.number_input("Momento Nominal Columna $M_{n,col}$ (kNm, alrededor de eje X)", min_value=0.0, value=300.0, step=10.0, key="mncoly_zap", help="Momento nominal de la columna que se apoya en la zapata. Usar para el diseño de la zapata.")

        st.markdown("---")
        st.markdown("##### Geometría Columna y Zapata")
        b_col_cm_z = st.number_input("Ancho Columna $b_{col}$ (cm, dim. paralela a B)", min_value=20.0, value=40.0, step=1.0, key="bcol_zap_v2")
        h_col_cm_z = st.number_input("Peralte Columna $h_{col}$ (cm, dim. paralela a L)", min_value=20.0, value=40.0, step=1.0, key="hcol_zap_v2")
        
        rec_libre_cm_z = st.number_input("Recubrimiento libre en zapata (cm)", min_value=5.0, value=7.5, step=0.5, key="rec_zap_v2", help="NSR-10 C.7.7.1.(a) para concreto vaciado contra el suelo")
        
        diam_barra_opts_mm_z = {"#4 (12.7mm)": 12.7, "#5 (15.9mm)": 15.9, "#6 (19.1mm)": 19.1, "#7 (22.2mm)": 22.2, "#8 (25.4mm)": 25.4}
        sel_barra_z = st.selectbox("Diámetro Barra Refuerzo Zapata (Ref.)", list(diam_barra_opts_mm_z.keys()), index=1, key="diam_b_zap_v2") # #5 por defecto
        diam_barra_mm_z = diam_barra_opts_mm_z[sel_barra_z]
        
        st.markdown("---")
        st.markdown("##### Parámetros de Diseño (Opcional)")
        rel_BL_deseada_z = st.number_input("Relación L/B deseada (ej: 1.0 para cuadrada, 0 para auto)", min_value=0.0, value=0.0, step=0.1, key="relBL_zap_v2", help="Si es 0, se calcula automáticamente.")
        rel_BL_param = None if rel_BL_deseada_z == 0 else rel_BL_deseada_z # Convertir 0 a None

    if st.button("👣 Diseñar Zapata", key="btn_zap_v2"):
        if not id_zapata_reporte.strip():
            st.error("Por favor, ingrese un ID para la zapata.")
        else:
            try:
                resultados_zap = diseno_zapata_aislada_v2(
                    P_servicio_kN=P_srv_kN_z, Mx_servicio_kNm=Mx_srv_kNm_z, My_servicio_kNm=My_srv_kNm_z,
                    P_ultima_kN=P_ult_kN_z, 
                    Mx_ultima_kNm=Mn_col_x,  # Usar el momento de capacidad de la columna
                    My_ultima_kNm=Mn_col_y,  # Usar el momento de capacidad de la columna
                    fc_MPa=fc_zap, fy_MPa=fy_zap, q_adm_kPa=q_adm_zap_kPa,
                    b_col_cm=b_col_cm_z, h_col_cm=h_col_cm_z,
                    rec_libre_zapata_cm=rec_libre_cm_z, diam_barra_zapata_mm=diam_barra_mm_z,
                    prof_desplante_m=prof_desplante_zap_m,
                    relacion_BL_deseada=rel_BL_param
                )
                st.session_state['resultados_zapata_actual'] = resultados_zap # Guardar para posible reporte
                
                with col2:
                    st.subheader("Resultados Diseño Zapata")
                    st.info(f"Mensaje: {resultados_zap.get('mensaje', 'Cálculo procesado.')}")

                    if resultados_zap.get('status') == "OK":
                        st.markdown("##### Dimensiones Finales")
                        dim_p = resultados_zap['dimensiones_planta']
                        col_dim1, col_dim2, col_dim3 = st.columns(3)
                        with col_dim1: st.metric("Ancho B", f"{dim_p['B_m']:.2f} m")
                        with col_dim2: st.metric("Largo L", f"{dim_p['L_m']:.2f} m")
                        with col_dim3: st.metric("Peralte h", f"{resultados_zap['peralte_final']['h_m']:.2f} m (d={resultados_zap['peralte_final']['d_prom_m']:.3f}m)")

                        st.markdown("##### Presiones de Suelo")
                        pres_s = resultados_zap['presiones_servicio']
                        pres_u = resultados_zap['presiones_ultimas']
                        st.write(f"**Servicio:** q_max={pres_s['q_max_serv_kPa']:.1f} kPa, q_min={pres_s['q_min_serv_kPa']:.1f} kPa (q_adm={pres_s['q_adm_kPa']:.1f} kPa)")
                        if pres_s['q_max_serv_kPa'] > pres_s['q_adm_kPa'] * 1.01 : st.warning("Presión máxima de servicio excede ligeramente la admisible.")
                        if pres_s['q_min_serv_kPa'] < 0 : st.warning("Posible despegue bajo cargas de servicio (q_min < 0).")
                        st.write(f"**Últimas:** q_max={pres_u['q_max_ult_kPa']:.1f} kPa, q_min={pres_u['q_min_ult_kPa']:.1f} kPa")
                        # Podría añadirse q_ult_suelo si se conoce (ej. 1.5*q_adm)
                        
                        st.markdown("##### Chequeos de Cortante (Cargas Últimas)")
                        with st.expander("Ver Detalles de Cortante", expanded=False):
                            st.write("**Cortante Unidireccional (Dirección L - voladizo en L):**")
                            cort_L = resultados_zap['chequeo_cortante_unidir_L']
                            st.write(f"  Vud = {cort_L['Vud_kN']:.1f} kN, φVc = {cort_L['phiVc_kN']:.1f} kN - {'✅ OK' if cort_L['ok'] else '❌ NO OK'}")
                            if 'nota' in cort_L: st.caption(f"  Nota: {cort_L['nota']}")
                            
                            st.write("**Cortante Unidireccional (Dirección B - voladizo en B):**")
                            cort_B = resultados_zap['chequeo_cortante_unidir_B']
                            st.write(f"  Vud = {cort_B['Vud_kN']:.1f} kN, φVc = {cort_B['phiVc_kN']:.1f} kN - {'✅ OK' if cort_B['ok'] else '❌ NO OK'}")
                            if 'nota' in cort_B: st.caption(f"  Nota: {cort_B['nota']}")

                            st.write("**Punzonamiento (Cortante Bidireccional):**")
                            punz = resultados_zap['chequeo_punzonamiento']
                            st.write(f"  Vup = {punz['Vup_kN']:.1f} kN, φVc = {punz['phiVc_kN']:.1f} kN - {'✅ OK' if punz['ok'] else '❌ NO OK'}")
                            st.caption(f"  b₀={punz['b0_cm']:.1f} cm, vc={punz['vc_MPa']:.2f} MPa (Resistencia concreto al punzonamiento)")

                        st.markdown("##### Refuerzo a Flexión (Cargas Últimas)")
                        ref = resultados_zap['refuerzo_flexion']
                        st.write(f"**Dirección L (armado paralelo a B):** As_total = {ref['dir_L_paralelo_a_B']['As_total_cm2']:.2f} cm²  ($\Rightarrow$ {ref['dir_L_paralelo_a_B']['As_cm2_per_m']:.2f} cm²/m)")
                        st.write(f"**Dirección B (armado paralelo a L):** As_total = {ref['dir_B_paralelo_a_L']['As_total_cm2']:.2f} cm²  ($\Rightarrow$ {ref['dir_B_paralelo_a_L']['As_cm2_per_m']:.2f} cm²/m)")
                        st.caption(f"As mínimo por temperatura y retracción: {ref['As_min_temp_cm2_per_m']:.2f} cm²/m (calculado con h={resultados_zap['peralte_final']['h_m']:.2f}m)")

                        # Visualización gráfica de la planta
                        fig_zap, ax_zap = plt.subplots(figsize=(6, 6 * dim_p['L_m'] / dim_p['B_m'] if dim_p['B_m'] > 0 else 6))
                        ax_zap.add_patch(plt.Rectangle((0, 0), dim_p['B_m'], dim_p['L_m'], color='lightgray', alpha=0.7, ec='black'))
                        # Columna centrada
                        x0_col = (dim_p['B_m'] - cm_to_m(b_col_cm_z)) / 2
                        y0_col = (dim_p['L_m'] - cm_to_m(h_col_cm_z)) / 2
                        ax_zap.add_patch(plt.Rectangle((x0_col, y0_col), cm_to_m(b_col_cm_z), cm_to_m(h_col_cm_z), color='dimgray', ec='black'))
                        
                        ax_zap.set_aspect('equal', 'box')
                        ax_zap.set_xlim(-0.1*dim_p['B_m'], 1.1*dim_p['B_m'])
                        ax_zap.set_ylim(-0.1*dim_p['L_m'], 1.1*dim_p['L_m'])
                        ax_zap.set_xlabel("Dimensión B (m)")
                        ax_zap.set_ylabel("Dimensión L (m)")
                        ax_zap.set_title(f"Planta Zapata: {dim_p['B_m']:.2f}m x {dim_p['L_m']:.2f}m")
                        ax_zap.grid(True, linestyle=':', alpha=0.6)
                        st.pyplot(fig_zap)

                        # --- Guardar datos para el reporte ---
                        datos_zap_reporte = {
                            "ID Zapata": id_zapata_reporte,
                            "B (m)": dim_p['B_m'],
                            "L (m)": dim_p['L_m'],
                            "h (m)": resultados_zap['peralte_final']['h_m'],
                            "d prom (m)": resultados_zap['peralte_final']['d_prom_m'],
                            "P_serv (kN)": P_srv_kN_z,
                            "Mx_serv (kNm)": My_srv_kNm_z, # Convención de la función original
                            "My_serv (kNm)": Mx_srv_kNm_z, # Convención de la función original
                            "P_ult (kN)": P_ult_kN_z,
                            "Mux_ult_diseno (kNm)": Mn_col_y, # El que se usó para diseño estructural
                            "Muy_ult_diseno (kNm)": Mn_col_x, # El que se usó para diseño estructural
                            "q_max_serv (kPa)": resultados_zap['presiones_servicio']['q_max_serv_kPa'],
                            "q_min_serv (kPa)": resultados_zap['presiones_servicio']['q_min_serv_kPa'],
                            "q_adm (kPa)": resultados_zap['presiones_servicio']['q_adm_kPa'],
                            "q_max_ult (kPa)": resultados_zap['presiones_ultimas']['q_max_ult_kPa'],
                            "q_min_ult (kPa)": resultados_zap['presiones_ultimas']['q_min_ult_kPa'],
                            "Cort_Uni_L_Vud (kN)": resultados_zap['chequeo_cortante_unidir_L']['Vud_kN'],
                            "Cort_Uni_L_phiVc (kN)": resultados_zap['chequeo_cortante_unidir_L']['phiVc_kN'],
                            "Cort_Uni_L_OK": "Sí" if resultados_zap['chequeo_cortante_unidir_L']['ok'] else "No",
                            "Cort_Uni_B_Vud (kN)": resultados_zap['chequeo_cortante_unidir_B']['Vud_kN'],
                            "Cort_Uni_B_phiVc (kN)": resultados_zap['chequeo_cortante_unidir_B']['phiVc_kN'],
                            "Cort_Uni_B_OK": "Sí" if resultados_zap['chequeo_cortante_unidir_B']['ok'] else "No",
                            "Punz_Vup (kN)": resultados_zap['chequeo_punzonamiento']['Vup_kN'],
                            "Punz_phiVc (kN)": resultados_zap['chequeo_punzonamiento']['phiVc_kN'],
                            "Punz_OK": "Sí" if resultados_zap['chequeo_punzonamiento']['ok'] else "No",
                            "As_L_cm2/m": resultados_zap['refuerzo_flexion']['dir_L_paralelo_a_B']['As_cm2_per_m'],
                            "As_B_cm2/m": resultados_zap['refuerzo_flexion']['dir_B_paralelo_a_L']['As_cm2_per_m'],
                            "As_min_temp_cm2/m": resultados_zap['refuerzo_flexion']['As_min_temp_cm2_per_m']
                        }
                        st.session_state.lista_zapatas_reporte.append(datos_zap_reporte)
                        st.info(f"Resultados de zapata '{id_zapata_reporte}' añadidos al reporte.")

                    elif resultados_zap.get('status') == "Error":
                        st.error(f"No se pudo completar el diseño. {resultados_zap.get('mensaje', '')}")
                        if 'h_propuesto_m' in resultados_zap: # Si falló en el bucle de 'h'
                            st.write("Últimos resultados de chequeo de cortante antes de detenerse:")
                            if 'cort_uni_L' in resultados_zap: st.write(f"  Cortante Uni L: Vud={resultados_zap['cort_uni_L'].get('Vud_kN','N/A'):.1f} kN, φVc={resultados_zap['cort_uni_L'].get('phiVc_kN','N/A'):.1f} kN, OK={resultados_zap['cort_uni_L'].get('ok','N/A')}")
                            if 'cort_uni_B' in resultados_zap: st.write(f"  Cortante Uni B: Vud={resultados_zap['cort_uni_B'].get('Vud_kN','N/A'):.1f} kN, φVc={resultados_zap['cort_uni_B'].get('phiVc_kN','N/A'):.1f} kN, OK={resultados_zap['cort_uni_B'].get('ok','N/A')}")
                            if 'punzonamiento' in resultados_zap: st.write(f"  Punzonamiento: Vup={resultados_zap['punzonamiento'].get('Vup_kN','N/A'):.1f} kN, φVc={resultados_zap['punzonamiento'].get('phiVc_kN','N/A'):.1f} kN, OK={resultados_zap['punzonamiento'].get('ok','N/A')}")


            except ValueError as e: # Errores de validación de inputs
                with col2: st.error(f"Error en datos de entrada: {e}")
            except Exception as e: # Otros errores inesperados
                with col2: st.error(f"Error inesperado durante el diseño de la zapata: {e}")
                # import traceback
                # st.text(traceback.format_exc()) # Para depuración