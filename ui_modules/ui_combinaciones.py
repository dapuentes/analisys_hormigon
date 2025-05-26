import streamlit as st
import pandas as pd
from calculosh.combinaciones import generar_combinaciones_carga

def mostrar_interfaz_combinaciones(PG, st_session):
    st.header("Generación de Combinaciones de Carga (NSR-10)")

    col_cb1, col_cb2 = st.columns(2)
    with col_cb1:
        incluir_sismo_cb = st.checkbox("¿Incluir combinaciones sísmicas?", value=True, key="sismo_cb_v2")
        
        # Parámetros para factor L en sismo y sismo vertical
        # (Tomar f1 de un input o asumir residencial)
        f1_L_options = {"Residencial (L<5kPa) -> f1=0.5": 0.5, 
                        "Uso Público/Almacenamiento (L>=5kPa) -> f1=1.0": 1.0}
        f1_L_desc = st.selectbox("Condición para factor $f_1$ de Carga Viva (L) en sismo:", 
                                 list(f1_L_options.keys()), index=0, key="f1L_cb")
        f1_L_valor = f1_L_options[f1_L_desc]
        
        incluir_Ev_cb = st.checkbox("¿Incluir efecto de Sismo Vertical (Ev)?", value=False, key="ev_cb")
        
        # Aa y Fa se toman de los parámetros globales si se incluye Ev
        Aa_para_Ev = PG.get('Aa', 0.0) if incluir_Ev_cb else 0.0
        Fa_para_Ev = PG.get('Fa', 1.0) if incluir_Ev_cb else 1.0 # Fa no puede ser 0
        if incluir_Ev_cb:
            st.info(f"Para Sismo Vertical (Ev), se usarán: Aa={Aa_para_Ev}, Fa={Fa_para_Ev} (de config. global)")


    # Botón de generar se puede poner fuera de las columnas
    if st.button("🔄 Generar Combinaciones", key="btn_gen_comb_v2"):
        try:
            combinaciones = generar_combinaciones_carga(
                incluir_sismo=incluir_sismo_cb,
                f1_L_sismica=f1_L_valor,
                incluir_sismo_vertical=incluir_Ev_cb,
                Aa=Aa_para_Ev, # Se pasa Aa de parámetros globales
                Fa=Fa_para_Ev  # Se pasa Fa de parámetros globales
            )
            st.session_state['combinaciones_calculadas'] = combinaciones # Guardar para posible uso
            
            # Mostrar las combinaciones
            if 'combinaciones_calculadas' in st.session_state:
                st.subheader("Combinaciones de Servicio (NSR-10 B.2.3)")
                # Convertir a DataFrame para mejor visualización
                serv_data = []
                for nombre, factores in st.session_state['combinaciones_calculadas']["servicio"]:
                    serv_data.append({"Combinación": nombre, **factores})
                st.dataframe(pd.DataFrame(serv_data).fillna(0)) # Rellenar NaNs con 0 para mejor vista

                st.subheader("Combinaciones Últimas (NSR-10 B.2.4 / A.3.5)")
                ult_data = []
                for nombre, factores in st.session_state['combinaciones_calculadas']["ultimas"]:
                    ult_data.append({"Combinación": nombre, **factores})
                st.dataframe(pd.DataFrame(ult_data).fillna(0))

        except Exception as e:
            st.error(f"Error al generar combinaciones: {str(e)}")
    
    # Sección para aplicar a cargas base (como la tenías antes)
    if st.session_state.get('combinaciones_calculadas'):
        st.markdown("---")
        st.subheader("Aplicar a Cargas Base (Ejemplo)")
        cargas_base_col1, cargas_base_col2, cargas_base_col3 = st.columns(3)
        with cargas_base_col1:
            CM_base = st.number_input("CM (D) Base", value=100.0, step=10.0, key="cm_base_cb")
            CV_base = st.number_input("CV (L) Base", value=50.0, step=10.0, key="cv_base_cb")
        with cargas_base_col2:
            CV_cub_base = st.number_input("CV Cubierta (Lr) Base", value=10.0, step=5.0, key="cvlr_base_cb")
            Sismo_E_base = st.number_input("Sismo (E) Base", value=30.0, step=5.0, key="sismoE_base_cb")
        
        if st.button("📈 Aplicar Factores a Cargas Base", key="btn_aplicar_comb"):
            resultados_aplicados_servicio = []
            for nombre, factores in st.session_state['combinaciones_calculadas']["servicio"]:
                valor_comb = (factores.get("D", 0) * CM_base +
                              factores.get("L", 0) * CV_base +
                              factores.get("Lr", 0) * CV_cub_base)
                resultados_aplicados_servicio.append({"Combinación Servicio": nombre, "Valor Resultante": f"{valor_comb:.2f}"})
            
            resultados_aplicados_ultimas = []
            for nombre, factores in st.session_state['combinaciones_calculadas']["ultimas"]:
                valor_comb = (factores.get("D", 0) * CM_base +
                              factores.get("L", 0) * CV_base +
                              factores.get("Lr", 0) * CV_cub_base +
                              factores.get("E", 0) * Sismo_E_base) # Asume E es solo una dirección
                resultados_aplicados_ultimas.append({"Combinación Última": nombre, "Valor Resultante": f"{valor_comb:.2f}"})

            st.write("##### Cargas de Servicio Aplicadas:")
            st.dataframe(pd.DataFrame(resultados_aplicados_servicio))
            st.write("##### Cargas Últimas Aplicadas:")
            st.dataframe(pd.DataFrame(resultados_aplicados_ultimas))