import streamlit as st
from calculosh.diseno_columna import *
from calculosh.diseno_columna_cortante import *
from unidades import *
from calculosh.diseno_columna import _generar_posicion_barras  
import pandas as pd

def mostrar_interfaz_columnas(PG, st_session):
    st.header("Diseño de Columnas - Diagrama de Interacción P-M-M")
    # Usar f'c y f'y de parámetros globales para columnas
    fc_col = PG['fc_columnas_MPa']
    fy_col = PG['fy_MPa']
    st.info(f"Usando Materiales Globales: f'c = {fc_col} MPa, f'y = {fy_col} MPa")

    col1, col2 = st.columns([1, 2]) # Dar más espacio a la columna de resultados/gráficos

    with col1: # Asumiendo que 'col1' es donde se ingresan los datos para el diagrama P-M-M
        st.subheader("Geometría y Refuerzo para Diagrama P-M-M")
        id_columna_reporte = st.text_input("ID Columna para Reporte (ej: C-1, C-EjeA-N1)", key="id_col_rep")
        b_cm_c = st.number_input("Ancho Columna b (cm)", min_value=20.0, value=40.0, step=5.0, key="b_col")
        h_cm_c = st.number_input("Peralte Columna h (cm)", min_value=20.0, value=50.0, step=5.0, key="h_col") # Ejemplo h>b

        st.markdown("---")
        st.markdown("##### Recubrimiento y Diámetros")
        rec_libre_cm_c = st.number_input("Recubrimiento libre (cm)", min_value=2.5, value=4.0, step=0.5, key="rec_libre_col", help="Distancia borde a estribo")

        # Selectores para diámetros
        diam_estribo_opts_mm_c = {"#3 (9.5mm)": 9.5, "#4 (12.7mm)": 12.7}
        sel_estribo_c = st.selectbox("Diámetro Estribo", list(diam_estribo_opts_mm_c.keys()), key="diam_e_col")
        diam_estribo_mm_c = diam_estribo_opts_mm_c[sel_estribo_c]

        diam_barra_opts_mm_c = {"#5 (15.9mm)": 15.9, "#6 (19.1mm)": 19.1, "#7 (22.2mm)": 22.2, "#8 (25.4mm)": 25.4, "#9 (28.7mm)": 28.7, "#10 (32.3mm)": 32.3}
        sel_barra_c = st.selectbox("Diámetro Barra Long.", list(diam_barra_opts_mm_c.keys()), index=1, key="diam_b_col") # #6 por defecto
        diam_barra_long_mm_c = diam_barra_opts_mm_c[sel_barra_c]

        st.markdown("---")
        st.markdown("##### Distribución del Refuerzo")
        nx_barras_c = st.number_input("Nº barras cara 'b' (Total en cara paralela a Y, incl. esquinas)", min_value=2, value=3, step=1, key="nx_b_col")
        ny_barras_c = st.number_input("Nº barras cara 'h' (Sólo intermedias en cara paralela a X)", min_value=0, value=1, step=1, key="ny_b_col", help="No incluir las barras de esquina (ya contadas en nx)")
        num_barras_tot_c = 2 * nx_barras_c + 2 * ny_barras_c
        st.info(f"Número total de barras: {num_barras_tot_c}")

        st.markdown("---")
        st.markdown("##### Parámetros de Cálculo (Diagrama)")
        n_c_steps = st.slider("Pasos eje neutro 'c'", 20, 60, 30, 5, key="nc_col_diag")
        n_theta_steps = st.slider("Pasos ángulo 'θ'", 24, 72, 36, 6, key="nt_col_diag")

    # Botón para generar diagrama
    if st.button("📊 Generar Diagrama de Interacción", key="btn_col_diag"):
        if not id_columna_reporte.strip():
                st.error("Por favor, ingrese un ID para la columna.")
        elif num_barras_tot_c < 4: # Asegúrate que num_barras_tot_c se calcule
                st.error("Se requieren al menos 4 barras en total.")
        else:
            try:
                with st.spinner("Calculando diagrama de interacción... Por favor espere."):
                    # Llamar a la función corregida
                    resultados_diag = calcular_diagrama_interaccion_columna(
                        b_cm=b_cm_c, h_cm=h_cm_c, rec_libre_cm=rec_libre_cm_c,
                        diam_estribo_mm=diam_estribo_mm_c, diam_barra_long_mm=diam_barra_long_mm_c,
                        nx_barras=nx_barras_c, ny_barras=ny_barras_c,
                        fc_MPa=fc_col, fy_MPa=fy_col,
                        num_puntos_c=n_c_steps, num_puntos_theta=n_theta_steps
                    )
                
                st.session_state["resultados_columna_diag"] = resultados_diag # Guardar resultados completos
                if resultados_diag.get("status") == "OK":
                    st.success(f"Diagrama para columna '{id_columna_reporte}' generado. {resultados_diag.get('mensaje', '')}")
                    # --- Guardar datos de flexo-compresión para el reporte ---
                    params_col_usados_diag = resultados_diag.get("params", {})
                    P_kN_max_phi = n_to_kn(np.max(resultados_diag["P_N"])) if "P_N" in resultados_diag else 0
                        
                    # Necesitas el área de acero total y la cuantía del refuerzo usado.
                    # La función _generar_posicion_barras es interna. As_total_mm2 y rho_g están en params_col_usados_diag
                    As_total_mm2_col = params_col_usados_diag.get('As_total_mm2', 0) # Si se guardó así
                    rho_g_col = params_col_usados_diag.get('rho_g', 0)

                    datos_col_flex_reporte = {
                        "ID Columna": id_columna_reporte,
                        "b (cm)": params_col_usados_diag.get('b_cm'),
                        "h (cm)": params_col_usados_diag.get('h_cm'),
                        "Rec. Libre (cm)": params_col_usados_diag.get('rec_libre_cm'),
                        "f'c (MPa)": params_col_usados_diag.get('fc_MPa'),
                        "fy (MPa)": params_col_usados_diag.get('fy_MPa'),
                        "Ø Barra Long. (mm)": params_col_usados_diag.get('diam_barra_long_mm'),
                        "Ø Estribo (mm)": params_col_usados_diag.get('diam_estribo_mm'),
                        "Nx Barras (cara b)": params_col_usados_diag.get('nx_barras'),
                        "Ny Barras (cara h, interm.)": params_col_usados_diag.get('ny_barras'),
                        "Nº Total Barras": params_col_usados_diag.get('num_barras_total'),
                        "As Total (cm²)": mm2_to_cm2(As_total_mm2_col) if As_total_mm2_col else "N/A",
                        "Cuantía (ρg)": f"{rho_g_col:.4f}" if rho_g_col else "N/A",
                        "φPn_max (kN)": round(P_kN_max_phi, 1),
                        # Podrías añadir φMnx_max y φMny_max si los calculas específicamente
                        "Estado Diagrama": "Generado OK"
                    }
                    st.session_state.lista_columnas_flex_reporte.append(datos_col_flex_reporte)
                    st.info(f"Datos de flexo-compresión de columna '{id_columna_reporte}' añadidos al reporte.")
                else:
                    st.error(f"Error al generar diagrama para '{id_columna_reporte}': {resultados_diag.get('mensaje', 'Error desconocido')}")

            except Exception as e:
                st.error(f"Error inesperado durante el cálculo: {e}")
                if 'resultados_columna_diag' in st.session_state: del st.session_state['resultados_columna_diag']

    # --- Mostrar Resultados y Gráficos si existen ---
    if st.session_state.get("resultados_columna_diag") and st.session_state["resultados_columna_diag"].get("status") == "OK":
        resultados_diag = st.session_state["resultados_columna_diag"]
        params_col_usados = resultados_diag.get("params", {})

        with col2:
            st.subheader("Resultados y Diseño Detallado") # Título general para la columna

            # Verificar si el diagrama P-M-M ha sido calculado y está disponible
            if st.session_state.get("resultados_columna_diag") and st.session_state["resultados_columna_diag"].get("status") == "OK":
                resultados_diag = st.session_state["resultados_columna_diag"]
                # 'params_col_usados' se obtiene de los resultados del diagrama P-M-M, generado en col1
                params_col_usados = resultados_diag.get("params", {})

                # Si params_col_usados está vacío, es porque el diagrama P-M-M no se generó correctamente o
                # la estructura de 'resultados_diag' no es la esperada.
                if not params_col_usados:
                    st.warning("No se encontraron los parámetros de la columna. Por favor, genere primero el Diagrama de Interacción en la columna izquierda.")
                else:
                    tab_diag, tab_cortante, tab_secc = st.tabs(["📈 Diagrama P-M-M", "✂️ Cortante y Confinamiento (DMO)", "🖼️ Sección Transversal"])

                    with tab_diag:
                        st.markdown("##### Vista del Diagrama de Interacción $(\phi P_n, \phi M_{nx}, \phi M_{ny})$")
                        
                        P_kN_diag = n_to_kn(resultados_diag["P_N"])
                        Mx_kNm_diag = nmm_to_knm(resultados_diag["Mx_Nmm"])
                        My_kNm_diag = nmm_to_knm(resultados_diag["My_Nmm"])
                        
                        vista_diag = st.radio("Tipo de Vista del Diagrama", ["3D", "2D (Mx-P, My-P)", "2D (Mx-My)"], horizontal=True, key="vista_diag_col_main")

                        fig_col_diag = plt.figure(figsize=(9, 7))

                        if vista_diag == "3D":
                            ax_3d = fig_col_diag.add_subplot(111, projection='3d')
                            sc = ax_3d.scatter(Mx_kNm_diag, My_kNm_diag, P_kN_diag, s=5, c=P_kN_diag, cmap='viridis', alpha=0.7)
                            fig_col_diag.colorbar(sc, ax=ax_3d, label='φ·P (kN)', shrink=0.6)
                            ax_3d.set_xlabel('φ·Mx (kN·m)')
                            ax_3d.set_ylabel('φ·My (kN·m)')
                            ax_3d.set_zlabel('φ·P (kN)')
                            ax_3d.set_title('Diagrama de Interacción P-M-M')
                        
                        elif vista_diag == "2D (Mx-P, My-P)":
                            gs = fig_col_diag.add_gridspec(1, 2)
                            ax1 = fig_col_diag.add_subplot(gs[0, 0])
                            ax2 = fig_col_diag.add_subplot(gs[0, 1])
                            
                            sc1 = ax1.scatter(Mx_kNm_diag, P_kN_diag, s=5, c=abs(My_kNm_diag), cmap='plasma', alpha=0.6)
                            fig_col_diag.colorbar(sc1, ax=ax1, label='|φ·My| (kN·m)')
                            ax1.set_xlabel('φ·Mx (kN·m)'); ax1.set_ylabel('φ·P (kN)'); ax1.set_title('Vista Mx-P'); ax1.grid(True)

                            sc2 = ax2.scatter(My_kNm_diag, P_kN_diag, s=5, c=abs(Mx_kNm_diag), cmap='plasma', alpha=0.6)
                            fig_col_diag.colorbar(sc2, ax=ax2, label='|φ·Mx| (kN·m)')
                            ax2.set_xlabel('φ·My (kN·m)'); ax2.set_ylabel('φ·P (kN)'); ax2.set_title('Vista My-P'); ax2.grid(True)
                            fig_col_diag.tight_layout()
                        
                        elif vista_diag == "2D (Mx-My)":
                            ax_2d = fig_col_diag.add_subplot(111)
                            sc_2d = ax_2d.scatter(Mx_kNm_diag, My_kNm_diag, s=5, c=P_kN_diag, cmap='viridis', alpha=0.6)
                            fig_col_diag.colorbar(sc_2d, ax=ax_2d, label='φ·P (kN)')
                            ax_2d.set_xlabel('φ·Mx (kN·m)'); ax_2d.set_ylabel('φ·My (kN·m)'); ax_2d.set_title('Vista Mx-My (Contorno)')
                            ax_2d.grid(True); ax_2d.axhline(0, color='grey', lw=0.5); ax_2d.axvline(0, color='grey', lw=0.5)
                            ax_2d.set_aspect('equal', adjustable='box')
                        
                        st.pyplot(fig_col_diag)
                        
                        df_diag = pd.DataFrame({'phi*Pn (kN)': P_kN_diag, 'phi*Mnx (kNm)': Mx_kNm_diag, 'phi*Mny (kNm)': My_kNm_diag})
                        csv_diag = df_diag.to_csv(index=False, sep=";", decimal=",")
                        st.download_button(label="Descargar Datos del Diagrama (CSV)", data=csv_diag, file_name="diagrama_interaccion_columna.csv", mime="text/csv", key="download_diag_col")

                    with tab_cortante:
                        st.subheader("Diseño por Cortante y Confinamiento (DMO)")
                        st.caption("Según NSR-10 C.21.4. El cortante de diseño ($V_e$) considera la plastificación de las vigas.")

                        # El formulario para el diseño por cortante
                        with st.form(key="cortante_col_form_v2"): # Nueva key para el form
                            st.markdown("##### Entradas para Cortante Probable y Cargas")
                            cort_col1_form, cort_col2_form = st.columns(2)
                            with cort_col1_form:
                                Mn_viga_izq_kNm_form = st.number_input("Momento Nominal Viga Izquierda ($M_{n,viga,izq}$ kNm)", min_value=0.0, value=250.0, step=10.0)
                                Mn_viga_der_kNm_form = st.number_input("Momento Nominal Viga Derecha ($M_{n,viga,der}$ kNm)", min_value=0.0, value=280.0, step=10.0)
                            with cort_col2_form:
                                L_libre_vigas_m_form = st.number_input("Luz Libre Promedio Vigas ($L_{n,vigas}$ m)", min_value=3.0, value=6.0, step=0.5)
                                
                                # Corrección para H_libre_col_m:
                                # Calcular un valor por defecto más seguro para H_libre_col_m
                                # Usamos la altura de la columna de params_col_usados (convertida a m)
                                # y le restamos un porcentaje por las vigas (ej. 10-15% de la altura típica de entrepiso por cada lado si es nudo intermedio)
                                # O simplemente la altura del entrepiso menos el peralte de la viga.
                                # Por ahora, un valor estimado más simple y robusto:
                                default_h_col_m = params_col_usados.get('h_cm', PG.get('altura_tipica_entrepiso_m', 3.0) * 100) / 100.0 # Altura total columna en m
                                # H_libre_col_m_value = default_h_col_m - 2 * (PG.get('altura_tipica_entrepiso_m', 3.0) * 0.15) # Estimación previa
                                # Una mejor estimación podría ser la altura típica de entrepiso menos un peralte típico de viga.
                                # Ejemplo: si altura_tipica_entrepiso_m = 3.0m, y viga de 0.5m, H_libre = 2.5m
                                # O permitir que el usuario lo ingrese o usar una lógica más detallada si tienes peraltes de vigas.
                                # Por ahora, lo haremos dependiente de altura_tipica_entrepiso_m menos un %
                                altura_entrepiso_global = PG.get('altura_tipica_entrepiso_m', 3.0)
                                # Estimación altura libre: altura entrepiso - 15% (aprox. peralte viga)
                                valor_estimado_H_libre = altura_entrepiso_global * 0.85 
                                H_libre_col_m_form_value = max(2.0, valor_estimado_H_libre) # Asegurar que sea >= min_value

                                H_libre_col_m_form = st.number_input("Altura Libre Columna ($H_{n,col}$ m)", 
                                                                    min_value=2.0, 
                                                                    value=H_libre_col_m_form_value, 
                                                                    step=0.1, 
                                                                    help="Altura libre de la columna entre caras de elementos de apoyo (losas/vigas).")

                            st.markdown("##### Cargas Axiales y Cortante de Análisis sobre la Columna")
                            puc_col1_form, puc_col2_form = st.columns(2)
                            with puc_col1_form:
                                Pu_kN_cort_form_val = st.number_input("Carga Axial Última ($P_u$ kN)", min_value=0.0, value=1500.0, step=50.0)
                            with puc_col2_form:
                                Vu_analisis_kN_form_val = st.number_input("Cortante del Análisis Estructural ($V_{u,análisis}$ kN)", min_value=0.0, value=80.0, step=10.0)
                            
                            # Botón de envío DENTRO del formulario
                            submitted_cortante_col_form = st.form_submit_button("✂️ Diseñar Refuerzo Transversal de Columna")

                        if submitted_cortante_col_form: # Evaluar después de que el formulario se envía
                            try:
                                res_cort_col = diseno_columna_cortante_dmo(
                                    b_col_cm=params_col_usados['b_cm'], h_col_cm=params_col_usados['h_cm'],
                                    fc_MPa=params_col_usados['fc_MPa'], fy_MPa=params_col_usados['fy_MPa'],
                                    Pu_kN=Pu_kN_cort_form_val, Vu_analisis_kN=Vu_analisis_kN_form_val,
                                    Mn_viga_izq_kNm=Mn_viga_izq_kNm_form, Mn_viga_der_kNm=Mn_viga_der_kNm_form,
                                    L_libre_vigas_m=L_libre_vigas_m_form,
                                    rec_libre_mm=cm_to_mm(params_col_usados['rec_libre_cm']),
                                    diam_estribo_mm=params_col_usados['diam_estribo_mm'],
                                    H_libre_col_m=H_libre_col_m_form
                                )
                                st.session_state['resultados_col_cortante'] = res_cort_col

                                st.markdown("##### Resultados del Diseño Transversal de Columna")
                                if res_cort_col['status'] == "OK":
                                    current_id_col_cort = st.session_state.get("id_col_para_cortante_actual", id_columna_reporte if 'id_columna_reporte' in locals() else "Col_Desconocida")
                                    st.metric("Cortante de Diseño Usado ($V_u$ o $V_e$)", f"{res_cort_col['Vu_diseno_kN']:.2f} kN")
                                    st.caption(f"Cortante por capacidad de vigas ($V_e$): {res_cort_col['Ve_capacidad_kN']:.2f} kN. {res_cort_col['mensaje_Vc']}")
                                    st.metric("Longitud de Confinamiento ($l_o$)", f"{res_cort_col['longitud_confinamiento_lo_cm']:.1f} cm")

                                    col_res_cort1, col_res_cort2 = st.columns(2)
                                    with col_res_cort1:
                                        st.success(f"**Zona Confinada (en extremos $l_o$):**\nUsar estribos Ø{res_cort_col['diam_estribo_usado_mm']} mm @ **{res_cort_col['s_final_confinado_mm']:.0f} mm**")
                                    with col_res_cort2:
                                        st.info(f"**Zona Central (fuera de $l_o$):**\nUsar estribos Ø{res_cort_col['diam_estribo_usado_mm']} mm @ **{res_cort_col['s_fuera_confinado_mm']:.0f} mm**")
                                    
                                    with st.expander("Ver detalles del cálculo de cortante"):
                                        st.json(res_cort_col)
                                    # Guardar resultados para reporte
                                    datos_col_cort_reporte = {
                                        "ID Columna": current_id_col_cort, # Usar el ID de la columna actual
                                        "Vu Diseño (kN)": res_cort_col.get('Vu_diseno_kN'),
                                        "Ve Capacidad (kN)": res_cort_col.get('Ve_capacidad_kN'),
                                        "Vc (kN)": res_cort_col.get('Vc_kN'),
                                        "Mensaje Vc": res_cort_col.get('mensaje_Vc'),
                                        "Vs Req (kN)": res_cort_col.get('Vs_req_kN'),
                                        "Lo (cm)": res_cort_col.get('longitud_confinamiento_lo_cm'),
                                        "Ash/s Req (mm²/m)": res_cort_col.get('Ash_s_req_mm2_por_m'),
                                        "s_max Confinado (mm)": res_cort_col.get('s_max_confinado_mm'),
                                        "Ø Estribo Usado (mm)": res_cort_col.get('diam_estribo_usado_mm'),
                                        "s Confinado Final (mm)": res_cort_col.get('s_final_confinado_mm'),
                                        "s Central Final (mm)": res_cort_col.get('s_fuera_confinado_mm'),
                                        "Estado Cortante": "OK"
                                    }
                                    st.session_state.lista_columnas_cort_reporte.append(datos_col_cort_reporte)
                                    st.info(f"Datos de cortante/confinamiento de columna '{current_id_col_cort}' añadidos al reporte.")
                                else:
                                    st.error(f"Error en diseño por cortante: {res_cort_col.get('mensaje', 'Desconocido')}")

                            except KeyError as ke:
                                st.error(f"Error: Falta un parámetro esperado para el diseño por cortante: {ke}. Asegúrese de generar primero el diagrama P-M-M.")
                            except Exception as e_cort:
                                st.error(f"Error en el diseño por cortante de columna: {e_cort}")
                                import traceback
                                st.text(traceback.format_exc())


                    with tab_secc:
                        st.subheader("Sección Transversal y Parámetros Usados")
                        
                        # Es importante que params_col_usados esté lleno aquí.
                        # Calcular As_total_calc_mm2 y rho_g aquí si no está en params_col_usados directamente.
                        try:
                            barras_para_seccion = _generar_posicion_barras(
                                cm_to_mm(params_col_usados['b_cm']), cm_to_mm(params_col_usados['h_cm']), 
                                cm_to_mm(params_col_usados['rec_libre_cm']), 
                                params_col_usados['diam_estribo_mm'], params_col_usados['diam_barra_long_mm'], 
                                params_col_usados['nx_barras'], params_col_usados['ny_barras']
                            )
                            As_total_calc_mm2_secc = sum(b['area'] for b in barras_para_seccion)
                            rho_g_secc = As_total_calc_mm2_secc / (cm_to_mm(params_col_usados['b_cm']) * cm_to_mm(params_col_usados['h_cm']))

                            param_df_data_col = {
                                "Parámetro": ["b (cm)", "h (cm)", "Rec. Libre (cm)", "f'c (MPa)", "f'y (MPa)", 
                                            "Ø Barra Long (mm)", "Ø Estribo (mm)", "Barras cara 'b' (nx, total)", "Barras cara 'h' (ny, intermedias)",
                                            "Nº Total Barras (Estimado)", "As total calculada (cm²)", "Cuantía (ρg)"],
                                "Valor": [
                                    f"{params_col_usados['b_cm']:.1f}", f"{params_col_usados['h_cm']:.1f}", f"{params_col_usados['rec_libre_cm']:.1f}",
                                    f"{params_col_usados['fc_MPa']:.1f}", f"{params_col_usados['fy_MPa']:.0f}",
                                    f"{params_col_usados['diam_barra_long_mm']:.1f}", f"{params_col_usados['diam_estribo_mm']:.1f}",
                                    params_col_usados['nx_barras'], params_col_usados['ny_barras'],
                                    params_col_usados.get('num_barras_total', len(barras_para_seccion)), # Usar el del cálculo de barras si existe
                                    f"{As_total_calc_mm2_secc / 100.0:.2f}",
                                    f"{rho_g_secc:.3%}" 
                                ]
                            }
                            st.dataframe(pd.DataFrame(param_df_data_col))

                            st.markdown("###### Disposición del Refuerzo (Esquemático)")
                            fig_sec_col, ax_sec_col = plt.subplots(figsize=(5, 5 * params_col_usados['h_cm'] / params_col_usados['b_cm'] if params_col_usados['b_cm'] > 0 else 5))
                            b_plot_col = params_col_usados['b_cm']
                            h_plot_col = params_col_usados['h_cm']
                            rec_plot_col = params_col_usados['rec_libre_cm']
                            d_bar_plot_col = params_col_usados['diam_barra_long_mm'] / 10.0 # a cm

                            ax_sec_col.add_patch(plt.Rectangle((0, 0), b_plot_col, h_plot_col, fill=True, color='lightgray', ec='black'))
                            # Dibujo del estribo (aproximado al recubrimiento libre)
                            ax_sec_col.add_patch(plt.Rectangle((rec_plot_col, rec_plot_col), 
                                                            b_plot_col - 2*rec_plot_col, 
                                                            h_plot_col - 2*rec_plot_col, 
                                                            fill=False, color='dimgray', linewidth=1.0, linestyle='-'))

                            for barra in barras_para_seccion:
                                x_plot_b = barra['x']/10.0 + b_plot_col/2.0
                                y_plot_b = barra['y']/10.0 + h_plot_col/2.0
                                ax_sec_col.add_patch(plt.Circle((x_plot_b, y_plot_b), radius=d_bar_plot_col/2.0, color='black'))

                            ax_sec_col.set_xlim(-b_plot_col*0.1, b_plot_col*1.1) # Ajustar límites para mejor visualización
                            ax_sec_col.set_ylim(-h_plot_col*0.1, h_plot_col*1.1)
                            ax_sec_col.set_aspect('equal', adjustable='box')
                            ax_sec_col.set_xlabel('b (cm)')
                            ax_sec_col.set_ylabel('h (cm)')
                            ax_sec_col.set_title(f"Sección {b_plot_col:.0f}x{h_plot_col:.0f} cm - {len(barras_para_seccion)}Ø{params_col_usados['diam_barra_long_mm']:.1f}mm")
                            ax_sec_col.grid(True, linestyle=':', alpha=0.5)
                            st.pyplot(fig_sec_col)
                        
                        except KeyError as ke:
                            st.error(f"Error al mostrar la sección transversal: Falta el parámetro '{ke}'. Asegúrese de generar primero el diagrama P-M-M.")
                        except Exception as e_plot:
                            st.error(f"Error al dibujar la sección transversal: {e_plot}")

            else: # Si el diagrama P-M-M no se ha calculado o falló
                if st.session_state.get("resultados_columna_diag") and st.session_state["resultados_columna_diag"].get("status") == "Error":
                    st.error(f"No se puede mostrar el diagrama de interacción ni los detalles de la sección: {st.session_state['resultados_columna_diag'].get('mensaje')}")
                else:
                    st.info("⬅️ Ingrese los datos de la columna y presione 'Generar Diagrama de Interacción' en la columna izquierda para ver los resultados y habilitar el diseño detallado.")
    #else: # Si hubo error en el cálculo del diagrama
        # if st.session_state.get("resultados_columna_diag") and st.session_state["resultados_columna_diag"].get("status") == "Error":
        #     with col2:
        #         st.error(f"No se puede mostrar el diagrama: {st.session_state['resultados_columna_diag'].get('mensaje')}")
        # pass # No mostrar nada si no hay diagrama