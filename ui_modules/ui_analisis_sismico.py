import streamlit as st
from calculosh.espectro import *

def mostrar_interfaz_analisis_sismico(PG, st_session):
    st.header("Análisis Sísmico NSR-10")
    tab_espectro, tab_fhe, tab_irregularidades = st.tabs([
        "📊 Espectro de Diseño", "🏢 Fuerza Horizontal Equivalente", "📐 Evaluación de Irregularidades"])

    # --- Pestaña Espectro de Diseño ---
    with tab_espectro:
        st.subheader("📊 Espectro de Diseño Sísmico")
        st.markdown("#### Parámetros Sísmicos Base (de Configuración Global)")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.metric("Aa", f"{PG['Aa']:.2f}")
            st.metric("Av", f"{PG['Av']:.2f}")
            st.metric("Tipo Suelo", PG['suelo_tipo'])
        with col_p2:
            st.metric("Fa", f"{PG['Fa']:.2f}")
            st.metric("Fv", f"{PG['Fv']:.2f}")
            st.metric("Grupo Uso", f"{PG['grupo_uso']} (I={PG['I_coef']:.2f})")
        st.info(f"Sistema Estructural: {PG['sistema_estructural_R0_desc']} (R₀={PG['R0']:.1f})")

        st.markdown("#### Ajuste de R por Irregularidades (NSR-10 A.3.3.3)")
        # Leer de session_state si fue definido en la pestaña de irregularidades
        phi_A = st.slider("Factor por Irregularidad en Altura (ΦA)", 0.7, 1.0, st.session_state.phi_A_calculado, 0.05, key="phi_A_espectro", help="NSR-10 Tabla A.3-3. Definir en pestaña 'Evaluación de Irregularidades'.")
        phi_P = st.slider("Factor por Irregularidad en Planta (ΦP)", 0.7, 1.0, st.session_state.phi_P_calculado, 0.05, key="phi_P_espectro", help="NSR-10 Tabla A.3-4. Definir en pestaña 'Evaluación de Irregularidades'.")
        phi_E = 1.0 # Redundancia, asumido 1.0
        R_final = PG['R0'] * phi_A * phi_P * phi_E
        st.metric("Coeficiente R final (R = R₀ × ΦA × ΦP × ΦE)", f"{R_final:.2f}")

        # Determinar TL_norma
        try:
            TL_calc = determinar_TL_norma(PG['Av'], PG['Fa'], PG['Fv'])
            st.info(f"Periodo Largo $T_L$ (calculado según NSR-10 Tabla A.2.6-1): {TL_calc:.1f} s")
        except Exception as e:
            st.error(f"Error al calcular TL: {e}"); TL_calc = 4.0; st.warning(f"Usando TL por defecto: {TL_calc:.1f} s")

        tipo_espectro_sel = st.radio("Tipo de Espectro:", ["Diseño (I/R aplicado)", "Elástico (I=1, R=1)"], index=0, horizontal=True)

        if st.button("📊 Generar Espectro"):
            try:
                tipo_param = "diseño" if tipo_espectro_sel == "Diseño (I/R aplicado)" else "elastico"
                T, Sa, info_periodos = espectro_nsr10(PG['Aa'], PG['Av'], PG['I_coef'], R_final, PG['Fa'], PG['Fv'], TL_calc, tipo_espectro=tipo_param)
                st.session_state['espectro_calculado_data'] = {"T": T, "Sa": Sa, "info_periodos": info_periodos, "R_usado": R_final if tipo_param == "diseño" else 1.0, "I_usado": PG['I_coef'] if tipo_param == "diseño" else 1.0, "tipo": tipo_param}
                st.success("Espectro calculado exitosamente.")
            except Exception as e:
                st.error(f"Error al calcular el espectro: {e}")
                if 'espectro_calculado_data' in st.session_state: st.session_state.espectro_calculado_data = None

        if st.session_state.espectro_calculado_data:
            data_esp = st.session_state.espectro_calculado_data
            st.markdown("#### Resultados del Espectro")
            info_p_text = (f"$T_0 = {data_esp['info_periodos']['T0']:.3f}$ s,  "
                           f"$T_C = {data_esp['info_periodos']['TC']:.3f}$ s,  "
                           f"$T_L = {data_esp['info_periodos']['TL_norma']:.3f}$ s")
            st.markdown(info_p_text)
            fig_espectro = graficar_espectro(T=data_esp['T'], Sa=data_esp['Sa'], info_periodos=data_esp['info_periodos'], titulo=f"Espectro NSR-10 ({data_esp['tipo'].capitalize()})", R_val=data_esp['R_usado'], I_val=data_esp['I_usado'])
            st.pyplot(fig_espectro)
            df_data_espectro = pd.DataFrame({'Periodo (s)': data_esp['T'], f'Sa_{data_esp["tipo"]} (g)': data_esp['Sa']})
            csv = df_data_espectro.to_csv(index=False, sep=";", decimal=",")
            st.download_button(label=f"Descargar datos del espectro ({data_esp['tipo']}) (CSV)", data=csv, file_name=f"espectro_nsr10_{data_esp['tipo']}.csv", mime="text/csv")


    # --- Pestaña Fuerza Horizontal Equivalente ---
    with tab_fhe:
        st.subheader("🏢 Fuerza Horizontal Equivalente (NSR-10 A.4)")
        if not st.session_state.espectro_calculado_data or st.session_state.espectro_calculado_data['tipo'] != "diseño":
            st.warning("Primero genere el Espectro de **Diseño** en la pestaña anterior.")
        else:
            data_esp_diseno = st.session_state.espectro_calculado_data
            try:
                Ta_calc = calcular_Ta_aproximado(PG['altura_total_edificio_m'], PG['sistema_estructural_R0_desc']) # Asumiendo 0 sótanos si no se pide
                st.metric(f"Periodo Fundamental Aproximado $T_a$ (NSR-10 A.4.2.2.1)", f"{Ta_calc:.3f} s")
                st.session_state['Ta_calculado'] = Ta_calc
                Sa_para_Ta = np.interp(Ta_calc, data_esp_diseno['T'], data_esp_diseno['Sa'])
                st.info(f"Para $T_a = {Ta_calc:.3f}$ s  ➔  $S_a(T_a) = {Sa_para_Ta:.4f}$ g")
            except Exception as e:
                st.error(f"Error calculando Ta: {e}")
                if 'Ta_calculado' in st.session_state: del st.session_state['Ta_calculado']

            if 'Ta_calculado' in st.session_state:
                st.markdown("---")
                peso_total_sismico_kN = st.number_input("Peso Total Sísmico Edificación W (kN)", min_value=1.0, value=5000.0, step=100.0, help="CM + %CV relevante (NSR-10 A.4.1). Obtener de análisis de cargas.")
                num_pisos_para_fhe = st.number_input("Número de pisos sobre la base (para Fx)", min_value=1, value=PG.get('num_pisos_aereos', 4), step=1)

                if st.button("🏢 Calcular Fuerza Horizontal Equivalente"):
                    try:
                        Vs_kN, df_Fx = calcular_Vs_fuerza_horizontal_equivalente(peso_total_sismico_kN, Sa_para_Ta, st.session_state['Ta_calculado'], num_pisos_para_fhe, PG['altura_tipica_entrepiso_m'])
                        st.session_state['resultados_fhe'] = {"Vs_kN": Vs_kN, "df_Fx": df_Fx, "k_dist": 1.0 + (st.session_state['Ta_calculado'] - 0.5) / 2.0 if 0.5 < st.session_state['Ta_calculado'] < 2.5 else (1.0 if st.session_state['Ta_calculado'] <= 0.5 else 2.0)}
                        st.success("Cálculo de FHE completado.")
                    except Exception as e:
                        st.error(f"Error al calcular FHE: {e}")
                        if 'resultados_fhe' in st.session_state: del st.session_state['resultados_fhe']

            if st.session_state.get('resultados_fhe'):
                res_fhe = st.session_state['resultados_fhe']
                st.metric("Cortante Sísmico Basal $V_s$", f"{res_fhe['Vs_kN']:.2f} kN")
                st.markdown("#### Distribución de Fuerzas Sísmicas $F_x$ por Nivel")
                st.dataframe(res_fhe['df_Fx'].style.format({'Altura_hi (m)': '{:.2f}', 'wi_hi^k (kN*m^k)': '{:.2f}', 'Cvx': '{:.4f}', 'Fx (kN)': '{:.2f}', 'Suma_Fx_acum (kN)': '{:.2f}'}))
                st.caption(f"Exponente k para distribución: {res_fhe['k_dist']:.3f}")
                st.caption("Fuerzas listadas desde cubierta hacia base.")

    # --- Pestaña Evaluación de Irregularidades ---
    with tab_irregularidades:
        st.subheader("📐 Evaluación de Irregularidades Estructurales (NSR-10 A.3.3)")
        st.info("Defina aquí los factores de ajuste para R (ΦA, ΦP) basados en su evaluación de las irregularidades del proyecto según NSR-10.")

        st.markdown("##### Irregularidades en Altura (NSR-10 Tabla A.3-3)")
        phi_A_eval = st.slider("Seleccione el Factor ΦA", 0.7, 1.0, st.session_state.phi_A_calculado, 0.05, key="phi_A_irr_input", help="1.0 si no hay irregularidades en altura.")

        st.markdown("##### Irregularidades en Planta (NSR-10 Tabla A.3-4)")
        phi_P_eval = st.slider("Seleccione el Factor ΦP", 0.7, 1.0, st.session_state.phi_P_calculado, 0.05, key="phi_P_irr_input", help="1.0 si no hay irregularidades en planta.")

        if st.button("💾 Guardar Factores de Irregularidad"):
            st.session_state.phi_A_calculado = phi_A_eval
            st.session_state.phi_P_calculado = phi_P_eval
            st.success("Factores ΦA y ΦP guardados. Se usarán en el cálculo del espectro de diseño.")

        st.markdown("---")
        st.write("Para una evaluación detallada, consulte las secciones A.3.3.4 y A.3.3.5 de la NSR-10.")
        # Placeholder para usar tu función 'evaluar_irregularidades' si se proporcionan los datos necesarios.