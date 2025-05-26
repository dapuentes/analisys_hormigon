import streamlit as st
from calculosh.reportes import *
import matplotlib.pyplot as plt
from calculosh.espectro import graficar_espectro

def mostrar_interfaz_reportes(PG, st_session):
    st.header("📋 Generar Memoria de Cálculo en Excel")
    st.warning("Funcionalidad en desarrollo (Work In Progress).")
    st.info("Esta sección recopilará los resultados de los módulos de diseño (Vigas, Columnas, Zapatas, etc.) almacenados durante la sesión y los exportará a un archivo Excel.")
    
    if st.button("📄 Generar Reporte Excel", key="btn_gen_excel_report"):
        if not PG: # PG = st.session_state.parametros_globales
             st.error("Configure primero los parámetros globales del proyecto.")
        else:
            # --- 1. Recopilar TODOS los datos necesarios de st.session_state ---
            datos_memoria_final = {
                "info_proyecto": {
                    "nombre_proyecto": PG.get('nombre_proyecto', 'Proyecto Sin Nombre'),
                    "localizacion": PG.get('localizacion', 'Pereira'),
                    "fecha": st.session_state.current_date,
                    "normativa_principal": "NSR-10 Colombia", # Clave más específica
                    "ingenieros_responsables": "Nombres del Grupo" # Clave más específica
                },
                "parametros_globales": PG, # f'c, fy, Aa, Av, Fa, Fv, R0, I_coef, q_adm, etc.
                
                "info_cargas_criterios": st.session_state.get('info_cargas_criterios_reporte', {}),
                "info_irregularidades": st.session_state.get('info_irregularidades_reporte', { # Pasar los phi_A, phi_P actuales
                    "phi_A_usado": st.session_state.get('phi_A_calculado', 1.0),
                    "phi_P_usado": st.session_state.get('phi_P_calculado', 1.0),
                }),

                "espectro_calculado_data": st.session_state.get('espectro_calculado_data'),
                # Asegúrate que estos se guardan en session_state desde el módulo de Análisis Sísmico
                "resultados_fhe": st.session_state.get('resultados_fhe'),
                "peso_sismico_total_usado_para_fhe": st.session_state.get('peso_total_sismico_usado_fhe'),
                "Ta_calculado_para_fhe": st.session_state.get('Ta_calculado'),
                "Sa_Ta_usado_para_fhe": st.session_state.get('Sa_Ta_usado_fhe'),
                "R_final_usado_espectro": PG.get('R0', 5.0) * st.session_state.get('phi_A_calculado', 1.0) * st.session_state.get('phi_P_calculado', 1.0),

                # Listas de resultados de diseño
                "vigas_disenadas": st.session_state.get('lista_vigas_reporte', []),
                "columnas_flexion_disenadas": st.session_state.get('lista_columnas_flex_reporte', []),
                "columnas_cortante_disenadas": st.session_state.get('lista_columnas_cort_reporte', []),
                "zapatas_disenadas": st.session_state.get('lista_zapatas_reporte', []),
                "losas_macizas_disenadas": st.session_state.get('lista_losas_macizas_reporte', []),
                "nervios_disenados": st.session_state.get('lista_nervios_reporte', []),
                "escaleras_disenadas": st.session_state.get('lista_escaleras_reporte', []),
                "deflexiones_verificadas": st.session_state.get('lista_deflexiones_reporte', []),
                
                "combinaciones_usadas": st.session_state.get('combinaciones_calculadas')
            }

            # Generar y guardar la imagen del espectro si existe
            if datos_memoria_final["espectro_calculado_data"]:
                try:
                    data_esp_rep = datos_memoria_final["espectro_calculado_data"]
                    fig_esp_rep = graficar_espectro(
                        T=data_esp_rep['T'], Sa=data_esp_rep['Sa'], 
                        info_periodos=data_esp_rep['info_periodos'],
                        titulo=f"Espectro NSR-10 ({data_esp_rep['tipo'].capitalize()})",
                        R_val=data_esp_rep['R_usado'], I_val=data_esp_rep['I_usado']
                    )
                    fig_esp_rep.savefig("espectro_plot_temp.png", dpi=200) # Guardar con buena resolución
                    plt.close(fig_esp_rep) # Cerrar la figura para liberar memoria
                    datos_memoria_final["path_imagen_espectro"] = "espectro_plot_temp.png"
                except Exception as e_img:
                    st.warning(f"No se pudo generar la imagen del espectro para el reporte: {e_img}")
                    datos_memoria_final["path_imagen_espectro"] = None
            else:
                datos_memoria_final["path_imagen_espectro"] = None
            
            # Limpiar datos None para evitar problemas con Pandas o Openpyxl
            # (Esto es opcional, _escribir_dataframe_a_hoja ya maneja pd.notna)
            # for key, value in datos_memoria_final.items():
            #     if isinstance(value, list):
            #         for item_dict in value:
            #             if isinstance(item_dict, dict):
            #                 for k_dict, v_dict in item_dict.items():
            #                     if v_dict is None: item_dict[k_dict] = "N/A"
            #     elif isinstance(value, dict):
            #          for k_dict, v_dict in value.items():
            #              if v_dict is None: value[k_dict] = "N/A"


            # --- 2. Llamar a la función de generación del reporte ---
            try:
                # from calculosh.reportes import generar_memoria_excel # Ya debería estar importada al inicio de app2.py
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                nombre_archivo_excel = f"MemoriaCalculo_{datos_memoria_final['info_proyecto']['nombre_proyecto'].replace(' ','_')}_{timestamp}.xlsx"
                
                st.info(f"Generando memoria en '{nombre_archivo_excel}'...")
                mensaje_gen = generar_memoria_excel(datos_memoria_final, nombre_archivo_excel)
                
                if "exitosamente" in mensaje_gen.lower():
                    st.success(mensaje_gen)
                    # --- 3. Ofrecer Descarga ---
                    if os.path.exists(nombre_archivo_excel):
                        with open(nombre_archivo_excel, "rb") as fp:
                            st.download_button(
                                label="📥 Descargar Memoria Excel",
                                data=fp,
                                file_name=nombre_archivo_excel,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.error("El archivo de memoria no se encontró después de intentar generarlo.")
                else:
                    st.error(f"Error durante la generación: {mensaje_gen}")

            except ImportError:
                st.error("El módulo 'calculosh/reportes.py' o la función 'generar_memoria_excel' no se pudieron importar correctamente.")
            except Exception as e:
                st.error(f"Error inesperado al intentar generar el reporte Excel: {e}")
                # import traceback
                # st.text(traceback.format_exc()) # Para depuración avanzada