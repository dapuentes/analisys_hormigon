import streamlit as st
from calculosh.diseno_losa_maciza import diseno_losa_maciza_unidireccional

def mostrar_interfaz_losas_macizas(PG, st_session):
    st.header("Diseño de Losas Macizas Unidireccionales")
    
    fc_losas = PG['fc_losas_vigas_MPa'] # Corrección: PG['fc_losas_vigas_MPa'] o el nombre correcto de tu clave global
    fy_losas = PG['fy_MPa']
    st.info(f"Usando Materiales Globales: f'c = {fc_losas} MPa, f'y = {fy_losas} MPa")
    
    with st.form("form_losa_maciza"):
        id_losa_reporte = st.text_input("ID Losa para Reporte (ej: Losa N2 Tipo 1)", key="id_losa_rep")
        st.markdown("##### Geometría y Cargas")
        col_losa1, col_losa2, col_losa3 = st.columns(3)
        with col_losa1:
            h_losa_cm_input = st.number_input("Espesor de la losa (h, cm)", min_value=10.0, value=15.0, step=1.0, key="h_losa_cm_input")
        with col_losa2:
            Mu_losa_kNm_input = st.number_input("Momento Último por metro ($M_u$, kNm/m)", min_value=0.0, value=15.0, step=1.0, key="Mu_losa_kNm_input") # Permitir Mu=0
        with col_losa3:
            rec_libre_losa_cm_input = st.number_input("Recubrimiento libre (cm)", min_value=2.0, value=2.5, step=0.5, key="rec_libre_losa_cm_input")

        st.markdown("##### Diámetro de Barra a Utilizar")
        diam_barra_losa_mm_input = st.selectbox("Diámetro de barra principal (mm)", [9.5, 12.7, 15.9], index=1, key="diam_barra_losa_mm_input")

        submitted_losa = st.form_submit_button("🔨 Diseñar Losa")

    if submitted_losa:
        if not id_losa_reporte.strip():
            st.error("Por favor, ingrese un ID para la losa.")
        else:
            try:
                resultados_losa = diseno_losa_maciza_unidireccional(
                    h_losa_cm=h_losa_cm_input, 
                    fc_MPa=fc_losas, 
                    fy_MPa=fy_losas,
                    rec_libre_cm=rec_libre_losa_cm_input, 
                    Mu_kNm_por_m=Mu_losa_kNm_input,
                    diam_barra_ppal_mm=diam_barra_losa_mm_input
                )
                
                # Guardar para posible reporte (opcional)
                # if 'resultados_losas_para_excel' not in st.session_state:
                #     st.session_state.resultados_losas_para_excel = []
                # st.session_state.resultados_losas_para_excel.append(resultados_losa)

                if resultados_losa["status"] == "OK":
                    st.success(resultados_losa.get("mensaje", "Diseño de Losa completado."))
                    st.info(resultados_losa['mensaje_espesor'])

                    st.markdown("##### Resultados del Refuerzo")
                    col_res_losa1, col_res_losa2 = st.columns(2)
                    with col_res_losa1:
                        st.markdown("###### Acero Principal")
                        st.metric(f"As requerido", f"{resultados_losa['As_req_ppal_cm2_por_m']} cm²/m")
                        # CORRECCIÓN AQUÍ:
                        st.success(f"Usar barra Ø{resultados_losa['diam_barra_ppal_usada_mm']} mm @ **{resultados_losa['espaciamiento_ppal_cm']} cm**")
                    with col_res_losa2:
                        st.markdown("###### Acero de Repartición y Temperatura")
                        st.metric(f"As requerido", f"{resultados_losa['As_req_temp_cm2_por_m']} cm²/m")
                        # CORRECCIÓN AQUÍ:
                        st.success(f"Usar barra Ø{resultados_losa['diam_barra_temp_usada_mm']} mm @ **{resultados_losa['espaciamiento_temp_cm']} cm**")
                    
                    with st.expander("Ver detalles completos del cálculo de la losa"):
                        st.json(resultados_losa)

                    # --- Guardar datos para el reporte ---
                    datos_losa_reporte = {
                        "ID Losa": id_losa_reporte,
                        "h (cm)": h_losa_cm_input,
                        "f'c (MPa)": fc_losas,
                        "fy (MPa)": fy_losas,
                        "Rec. Libre (cm)": rec_libre_losa_cm_input,
                        "Mu (kNm/m)": Mu_losa_kNm_input,
                        "d efectivo (cm)": resultados_losa.get('d_efectivo_ppal_cm', 'N/A'),
                        "As Ppal (cm²/m)": resultados_losa.get('As_req_ppal_cm2_por_m'),
                        "Ø Ppal (mm)": resultados_losa.get('diam_barra_ppal_usada_mm'),
                        "s Ppal (cm)": resultados_losa.get('espaciamiento_ppal_cm'),
                        "As Temp (cm²/m)": resultados_losa.get('As_req_temp_cm2_por_m'),
                        "Ø Temp (mm)": resultados_losa.get('diam_barra_temp_usada_mm'),
                        "s Temp (cm)": resultados_losa.get('espaciamiento_temp_cm'),
                        "Verif. Espesor": resultados_losa.get('mensaje_espesor')
                    }
                    st.session_state.lista_losas_macizas_reporte.append(datos_losa_reporte)
                    st.info(f"Resultados de losa maciza '{id_losa_reporte}' añadidos al reporte.")
                else:
                    # Mostrar el mensaje de error que viene de la función de diseño
                    st.error(f"Ocurrió un error en el diseño de la losa: {resultados_losa.get('mensaje', 'Error desconocido.')}")
                    # También puedes mostrar el diccionario completo de error para depurar
                    with st.expander("Detalles del error"):
                        st.json(resultados_losa)


            except Exception as e:
                st.error(f"Ocurrió un error inesperado en la aplicación al diseñar la losa: {e}")
                import traceback
                st.text(traceback.format_exc())