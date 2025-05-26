import streamlit as st
from calculosh.diseno_escaleras import diseno_tramo_escalera_losa_inclinada

def mostrar_interfaz_escaleras(PG, st_session):
    st.header("Diseño de Tramos de Escalera (Como Losa Inclinada)")

    fc_esc = PG['fc_losas_vigas_MPa'] # Usar f'c para losas
    fy_esc = PG['fy_MPa']
    st.info(f"Usando Materiales Globales: f'c = {fc_esc} MPa, f'y = {fy_esc} MPa")

    with st.form("form_escalera_diseno"):
        id_escalera_reporte = st.text_input("ID Tramo Escalera para Reporte (ej: Escalera1)", key="id_esc_rep")
        st.markdown("##### Geometría del Tramo de Escalera")
        col_geom_esc1, col_geom_esc2, col_geom_esc3 = st.columns(3)
        with col_geom_esc1:
            huella_cm_esc = st.number_input("Huella (cm)", min_value=25.0, value=28.0, step=0.5, help="Ancho del paso horizontal.")
        with col_geom_esc2:
            contrahuella_cm_esc = st.number_input("Contrahuella (cm)", min_value=15.0, value=17.5, step=0.5, help="Altura vertical del paso.")
        with col_geom_esc3:
            num_pasos_esc = st.number_input("Número de pasos en el tramo", min_value=3, value=10, step=1)

        col_geom_esc4, col_geom_esc5 = st.columns(2)
        with col_geom_esc4:
            ancho_tramo_m_esc = st.number_input("Ancho del tramo (m)", min_value=0.8, value=1.2, step=0.1)
        with col_geom_esc5:
            espesor_garganta_cm_esc = st.number_input("Espesor garganta losa (cm)", min_value=10.0, value=15.0, step=1.0, help="Espesor de la parte estructural inclinada.")

        st.markdown("##### Cargas de Diseño (sobre área proyectada horizontal)")
        col_cargas_esc1, col_cargas_esc2 = st.columns(2)
        with col_cargas_esc1:
            cm_adic_kNm2_esc = st.number_input("CM Adicional (acabados, etc.) (kN/m²)", min_value=0.0, value=1.0, step=0.1)
        with col_cargas_esc2:
            cv_kNm2_esc = st.number_input("CV (kN/m²)", min_value=2.0, value=3.0, step=0.1, help="NSR-10 B.4.2.1-1: Escaleras y corredores de evacuación para ocupación residencial: 3.0 kN/m²") # Residencial general es 1.8, pero escaleras suelen ser más.

        st.markdown("##### Refuerzo")
        col_ref_esc1, col_ref_esc2 = st.columns(2)
        with col_ref_esc1:
            rec_libre_cm_esc = st.number_input("Recubrimiento libre (cm)", min_value=2.0, value=2.5, step=0.5)
        with col_ref_esc2:
            diam_barra_ppal_esc_mm = st.selectbox("Diámetro barra principal (mm)", [9.5, 12.7, 15.9], index=1) # #4 (1/2")

        submitted_escalera = st.form_submit_button("🪜 Diseñar Tramo de Escalera")

    if submitted_escalera:
        if not id_escalera_reporte.strip(): # Reemplaza 'id_escalera_reporte' con la variable de tu input de ID
            st.error("Por favor, ingrese un ID para el tramo de escalera.")
        else:
            try:
                resultados_esc = diseno_tramo_escalera_losa_inclinada(
                    huella_cm=huella_cm_esc, contrahuella_cm=contrahuella_cm_esc, num_pasos=num_pasos_esc,
                    ancho_tramo_m=ancho_tramo_m_esc, espesor_losa_garganta_cm=espesor_garganta_cm_esc,
                    fc_MPa=fc_esc, fy_MPa=fy_esc,
                    carga_muerta_adic_kNm2=cm_adic_kNm2_esc, carga_viva_kNm2=cv_kNm2_esc,
                    rec_libre_cm=rec_libre_cm_esc, diam_barra_ppal_mm=diam_barra_ppal_esc_mm
                )

                if resultados_esc["status"] == "OK":
                    st.success("Diseño del tramo de escalera completado.")
                    
                    st.markdown("##### Geometría y Cargas Calculadas")
                    col_info_esc1, col_info_esc2 = st.columns(2)
                    with col_info_esc1:
                        st.metric("Longitud Horizontal Tramo", f"{resultados_esc['long_horiz_tramo_m']:.2f} m")
                        st.metric("Altura Total Tramo", f"{resultados_esc['altura_total_tramo_m']:.2f} m")
                        st.metric("Ángulo de Inclinación", f"{resultados_esc['angulo_grados']:.1f}°")
                    with col_info_esc2:
                        st.metric("Carga Última de Diseño ($w_u$)", f"{resultados_esc['carga_ultima_wu_kNm_por_m_proy']:.2f} kN/m (por metro de ancho)")
                        st.metric("Momento Último de Diseño ($M_u$)", f"{resultados_esc['momento_ultimo_Mu_kNm_por_m']:.2f} kNm (por metro de ancho)")
                    
                    st.info(f"Peralte efectivo 'd' calculado: {resultados_esc['d_efectivo_cm']:.1f} cm")

                    st.markdown("##### Refuerzo Requerido (por metro de ancho)")
                    ac_ppal = resultados_esc['acero_principal']
                    ac_temp = resultados_esc['acero_reparticion']

                    col_ref_res1, col_ref_res2 = st.columns(2)
                    with col_ref_res1:
                        st.markdown(f"**Acero Principal (Longitudinal al tramo):**")
                        st.write(f"  $A_s$ requerida: {ac_ppal['As_req_cm2_por_m']} cm²/m")
                        st.success(f"  Usar Ø{ac_ppal['diam_barra_mm']} mm @ **{ac_ppal['espaciamiento_cm']} cm**")
                    with col_ref_res2:
                        st.markdown(f"**Acero de Repartición (Transversal al tramo):**")
                        st.write(f"  $A_s$ requerida: {ac_temp['As_req_cm2_por_m']} cm²/m")
                        st.success(f"  Usar Ø{ac_temp['diam_barra_mm']} mm @ **{ac_temp['espaciamiento_cm']} cm**")
                    
                    st.warning(resultados_esc['verificacion_espesor'])

                    # Guardar para reporte (ejemplo)
                    ac_ppal_esc = resultados_esc.get('acero_principal', {})
                    ac_temp_esc = resultados_esc.get('acero_reparticion', {})
                    datos_escalera_reporte = {
                        "ID Tramo": id_escalera_reporte, # Reemplaza con tu variable de ID
                        "L_horiz (m)": resultados_esc.get('long_horiz_tramo_m'),
                        "h_garganta (cm)": espesor_garganta_cm_esc, # El input usado
                        "Ángulo (°)": resultados_esc.get('angulo_grados'),
                        "wu (kN/m)": resultados_esc.get('carga_ultima_wu_kNm_por_m_proy'),
                        "Mu (kNm/m)": resultados_esc.get('momento_ultimo_Mu_kNm_por_m'),
                        "d (cm)": resultados_esc.get('d_efectivo_cm'),
                        "As Ppal (cm²/m)": ac_ppal_esc.get('As_req_cm2_por_m'),
                        "Ref. Ppal": f"Ø{ac_ppal_esc.get('diam_barra_mm')}@{ac_ppal_esc.get('espaciamiento_cm')}cm",
                        "As Temp (cm²/m)": ac_temp_esc.get('As_req_cm2_por_m'),
                        "Ref. Temp.": f"Ø{ac_temp_esc.get('diam_barra_mm')}@{ac_temp_esc.get('espaciamiento_cm')}cm",
                        "Verif. Espesor": resultados_esc.get('verificacion_espesor')
                    }
                    st.session_state.lista_escaleras_reporte.append(datos_escalera_reporte)
                    st.info(f"Resultados del tramo de escalera '{id_escalera_reporte}' añadidos al reporte.")


                else: # Si hubo error
                    st.error(f"Error en el diseño de la escalera: {resultados_esc['mensaje']}")
                
                with st.expander("Ver todos los resultados del cálculo"):
                    st.json(resultados_esc)

            except Exception as e:
                st.error(f"Ocurrió un error inesperado en la aplicación al diseñar la escalera: {e}")
                import traceback
                st.text(traceback.format_exc())