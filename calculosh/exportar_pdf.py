# ==============================================================================
# RESUMEN Y EXPORTACIÓN DE RESULTADOS
# ==============================================================================
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

def exportar_resultados(resultados, nombre_archivo='resultados_diseno_estructural.pdf'):
    """
    Exporta los resultados del diseño a un archivo PDF
    
    Parámetros:
    resultados: Diccionario con resultados de diseño
    nombre_archivo: Nombre del archivo PDF a generar
    """
    with PdfPages(nombre_archivo) as pdf:
        # Página de título
        plt.figure(figsize=(11, 8.5))
        plt.axis('off')
        plt.text(0.5, 0.8, 'RESULTADOS DE DISEÑO ESTRUCTURAL', 
                 fontsize=20, ha='center')
        plt.text(0.5, 0.7, 'Diseño de Estructuras en Hormigón II', 
                 fontsize=16, ha='center')
        plt.text(0.5, 0.6, 'NSR-10', fontsize=14, ha='center')
        plt.text(0.5, 0.4, f'Fecha: {resultados["fecha"]}', fontsize=12, ha='center')
        plt.text(0.5, 0.3, f'Proyecto: {resultados["proyecto"]}', fontsize=12, ha='center')
        pdf.savefig()
        plt.close()
        
        # Espectro de diseño
        if 'espectro' in resultados:
            plt.figure(figsize=(10, 6))
            plt.plot(resultados['espectro']['T'], resultados['espectro']['Sa'])
            plt.grid(True)
            plt.xlabel('Periodo T (s)')
            plt.ylabel('Aceleración espectral Sa (g)')
            plt.title('Espectro de Diseño NSR-10')
            pdf.savefig()
            plt.close()
        
        # Diagrama de interacción de columnas
        if 'columnas' in resultados:
            for i, col in enumerate(resultados['columnas']):
                plt.figure(figsize=(8, 8))
                plt.scatter(col['Mx']/1000, col['P']/1000, s=1)
                plt.grid(True)
                plt.xlabel('Momento M (kN·m)')
                plt.ylabel('Carga axial P (kN)')
                plt.title(f'Diagrama de Interacción - Columna {i+1}')
                pdf.savefig()
                plt.close()
        
        # Tabla de resultados de vigas
        if 'vigas' in resultados:
            fig, ax = plt.subplots(figsize=(11, 8.5))
            ax.axis('off')
            ax.text(0.5, 0.95, 'RESULTADOS DE DISEÑO DE VIGAS', 
                    fontsize=16, ha='center')
            
            data = []
            for i, viga in enumerate(resultados['vigas']):
                data.append([
                    f"Viga {i+1}",
                    f"{viga['b']}x{viga['h']}",
                    f"{viga['As_pos']:.2f}",
                    f"{viga['As_neg']:.2f}",
                    f"{viga['Av_s']:.2f}",
                    "Cumple" if viga['cumple_deflexion'] else "No cumple"
                ])
            
            columns = ['Viga', 'Dimensiones (cm)', 'As+ (cm²)', 
                      'As- (cm²)', 'Av/s (cm²/m)', 'Deflexión']
            
            tabla = ax.table(cellText=data, colLabels=columns, 
                            loc='center', cellLoc='center')
            tabla.auto_set_font_size(False)
            tabla.set_fontsize(10)
            tabla.scale(1, 1.5)
            pdf.savefig()
            plt.close()
        
        # Tabla de resultados de zapatas
        if 'zapatas' in resultados:
            fig, ax = plt.subplots(figsize=(11, 8.5))
            ax.axis('off')
            ax.text(0.5, 0.95, 'RESULTADOS DE DISEÑO DE ZAPATAS', 
                    fontsize=16, ha='center')
            
            data = []
            for i, zapata in enumerate(resultados['zapatas']):
                data.append([
                    f"Zapata {i+1}",
                    f"{zapata['B']:.2f}x{zapata['L']:.2f}",
                    f"{zapata['h']:.2f}",
                    f"{zapata['As_x']:.2f}",
                    f"{zapata['As_y']:.2f}",
                    f"{zapata['q_max']:.2f}"
                ])
            
            columns = ['Zapata', 'Dimensiones (m)', 'Altura (m)', 
                      'As-x (cm²/m)', 'As-y (cm²/m)', 'q max (kPa)']
            
            tabla = ax.table(cellText=data, colLabels=columns, 
                            loc='center', cellLoc='center')
            tabla.auto_set_font_size(False)
            tabla.set_fontsize(10)
            tabla.scale(1, 1.5)
            pdf.savefig()
            plt.close()
