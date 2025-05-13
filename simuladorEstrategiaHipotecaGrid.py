import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Tuple, Optional
from tqdm.notebook import tqdm
import contextlib
import sys
import os

class HipotecaSimulator:
    """
    Simulador avanzado de hipotecas que permite comparar diferentes estrategias
    de amortización y analizar sus impactos financieros a largo plazo.
    """
    def __init__(
            self, 
            capital_inicial: float, 
            plazo_años: int, 
            tasa_interes_anual: float,
            amortizacion_inicial: float = 0,
            amortizacion_semestral_tipo: str = 'cuotas',  # 'cuotas' o 'constante'
            amortizacion_semestral_valor: float = 2000,  # Cuotas o importe en euros
            años_amortizacion_parcial: int = 10,  # Años con amortizaciones parciales
            fecha_inicio: Optional[str] = None,
            dia_pago: int = 1,  # Día del mes para el pago (1-28)
            titulo: str = 'Análisis de Estrategia de Amortización' # Título
        ):
        """
        Inicializa el simulador con los parámetros básicos de la hipoteca.
        
        Parameters
        ----------
        capital_inicial : float
            Capital inicial del préstamo en euros
        plazo_años : int
            Plazo del préstamo en años
        tasa_interes_anual : float
            Tasa de interés anual en porcentaje (ej: 1.9 para 1.9%)
        amortizacion_inicial : float, optional
            Amortización inicial justo después de la firma, by default 0
        amortizacion_semestral_tipo : str, optional
            Tipo de amortización semestral: 'cuotas' o 'constante', by default 'cuotas'
        amortizacion_semestral_valor : float, optional
            Si tipo='cuotas', número de cuotas mensuales
            Si tipo='constante', valor fijo en euros, by default 2
        años_amortizacion_parcial : int, optional
            Número de años durante los que se realizarán amortizaciones parciales, by default 10
        fecha_inicio : str, optional
            Fecha de inicio del préstamo en formato 'YYYY-MM-DD', by default None
        dia_pago : int, optional
            Día del mes para el pago (1-28), by default 1
        """
        # Validación de parámetros
        self._validar_parametros_iniciales(
            capital_inicial, 
            plazo_años, 
            tasa_interes_anual, 
            amortizacion_inicial,
            amortizacion_semestral_tipo,
            amortizacion_semestral_valor,
            años_amortizacion_parcial,
            dia_pago
        )
        
        # Parámetros básicos de la hipoteca
        self.capital_inicial = capital_inicial
        self.plazo_años = plazo_años
        self.plazo_meses = plazo_años * 12
        self.tasa_interes_anual = tasa_interes_anual
        self.tasa_interes_mensual = tasa_interes_anual / 12 / 100
        self.amortizacion_inicial = amortizacion_inicial
        self.amortizacion_semestral_tipo = amortizacion_semestral_tipo
        self.amortizacion_semestral_valor = amortizacion_semestral_valor
        self.años_amortizacion_parcial = años_amortizacion_parcial
        self.meses_amortizacion_parcial = años_amortizacion_parcial * 12
        self.dia_pago = min(dia_pago, 28)  # Limitamos a 28 para evitar problemas con febrero
        self.titulo = titulo
        
        # Configuración de fechas
        if fecha_inicio is None:
            self.fecha_inicio = datetime.now().replace(day=1)
        else:
            self.fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            
        # Ajustar el día de pago
        self.fecha_inicio = self.fecha_inicio.replace(day=self.dia_pago)
        
        # Gastos mensuales
        self.gastos_mensuales = {}
        self.tasas_incremento_anual = {}
        
        # Calcular cuota mensual base después de amortización inicial
        self.capital_tras_amortizacion_inicial = self.capital_inicial - self.amortizacion_inicial
        self.cuota_mensual = self._calcular_cuota_mensual(self.capital_tras_amortizacion_inicial, 
                                                         self.tasa_interes_mensual, 
                                                         self.plazo_meses)
        
        # Resultados de la simulación
        self.df_estandar = None
        self.df_estrategia = None
        self.df_gastos = None
        self.resultados_ahorro = None
        
        # Colores para gráficos
        self.colors = {'estandar': '#3498db', 'estrategia': '#e74c3c', 'ahorro': '#2ecc71'}
        
        # Mostrar resumen de configuración
        self._mostrar_resumen_configuracion()
    

    def _calcular_cuota_mensual(self, capital: float, tasa_mensual: float, plazo_meses: int) -> float:
        """
        Calcula la cuota mensual según la fórmula de amortización francesa.
        Versión corregida para asegurar precisión en el cálculo de intereses.
        
        Parameters
        ----------
        capital : float
            Capital pendiente
        tasa_mensual : float
            Tasa de interés mensual en tanto por uno
        plazo_meses : int
            Plazo restante en meses
        
        Returns
        -------
        float
            Cuota mensual
        """
        if tasa_mensual == 0:
            return capital / plazo_meses
        
        # Fórmula de amortización francesa (sistema francés)
        # Usamos cálculos de alta precisión para evitar errores de redondeo
        numerador = capital * tasa_mensual * ((1 + tasa_mensual) ** plazo_meses)
        denominador = ((1 + tasa_mensual) ** plazo_meses) - 1
        
        # Verificamos que el denominador no sea cero para evitar divisiones por cero
        if abs(denominador) < 1e-10:
            return capital / plazo_meses
        
        return numerador / denominador


    def _configurar_estilo_graficos(self):
        """Configura el estilo global para los gráficos."""
        plt.rcParams['figure.figsize'] = (16, 12)
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.rcParams['font.size'] = 12

    def _generar_fechas_pago(self, num_meses: int) -> List[datetime]:
        """
        Genera una lista de fechas de pago mensuales.
        
        Parameters
        ----------
        num_meses : int
            Número de meses a generar
        
        Returns
        -------
        List[datetime]
            Lista de fechas de pago
        """
        fechas = [self.fecha_inicio]
        
        for i in range(1, num_meses + 1):
            # Usamos relativedelta para calcular correctamente los meses
            fecha = self.fecha_inicio + relativedelta(months=i)
            fechas.append(fecha)
            
        return fechas

    
    def _graficar_capital_pendiente(self, df_estandar, df_estrategia, ax):
        """Genera el gráfico de evolución del capital pendiente."""
        ax.plot(df_estandar.index, df_estandar['Capital Pendiente'], 
               color=self.colors['estandar'], linewidth=2.5, label='Estándar')
        ax.plot(df_estrategia.index, df_estrategia['Capital Pendiente'], 
               color=self.colors['estrategia'], linewidth=2.5, label='Con estrategia')
        
        # Sombrear área de ahorro (versión optimizada)
        indices = np.arange(len(df_estandar.index))
        cap_estandar = df_estandar['Capital Pendiente'].values.astype(float)
        cap_estrategia = df_estrategia['Capital Pendiente'].values.astype(float)
        
        # Creamos una máscara booleana para donde hay ahorro
        mask = cap_estandar > cap_estrategia
        
        if np.any(mask):  # Solo si hay algún punto donde existe ahorro
            ax.fill_between(indices[mask], 
                          cap_estrategia[mask], 
                          cap_estandar[mask],
                          color=self.colors['ahorro'], alpha=0.3, label='Ahorro')
        
        # Marcar fin de período de amortización parcial
        if self.meses_amortizacion_parcial > 0:
            ax.axvline(x=self.meses_amortizacion_parcial, color='gray', linestyle='--', alpha=0.7,
                     label=f'Fin amortización parcial ({self.años_amortizacion_parcial} años)')
        
        ax.set_title('Evolución del capital pendiente', fontsize=14)
        ax.set_xlabel('Mes', fontsize=12)
        ax.set_ylabel('Capital pendiente (€)', fontsize=12)
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f"{x:,.0f}€"))
        
        # Límites para mejor visualización
        min_capital = min(df_estrategia['Capital Pendiente'].min(), df_estandar['Capital Pendiente'].min())
        ax.set_ylim(bottom=max(0, min_capital*0.9))
        
        # Leyenda con mejor formato
        ax.legend(loc='lower left', frameon=True, fontsize=10, facecolor='white', edgecolor='gray')
        ax.grid(True, alpha=0.3)
    def _graficar_comparativa_pagos(self, ahorro, ax):
            """Genera el gráfico de comparativa de pagos totales."""
            labels = ['Estándar', 'Con estrategia']
            
            # Preparar datos para el gráfico de barras apiladas
            capital = np.array([self.capital_inicial, self.capital_inicial])
            intereses = np.array([ahorro['intereses_estandar'], ahorro['intereses_estrategia']])
            
            # Corregido: Utilizamos solo los pagos (no incluimos amortización inicial que ya está en el índice 0)
            pagos_totales = capital + intereses
            
            # Crear barras apiladas
            bar_width = 0.35
            ax.bar(labels, capital, bar_width, label='Capital', color='#3498db')
            ax.bar(labels, intereses, bar_width, bottom=capital, label='Intereses', color='#e74c3c')
            
            # Añadir etiquetas de valor total
            for i, total in enumerate(pagos_totales):
                ax.text(i, total + 0.01 * pagos_totales.max(), f'{total:,.2f}€', 
                       ha='center', va='bottom', fontsize=11, fontweight='bold')
            
            # Obtener cuota inicial del esquema estándar (sin estrategia)
            cuota_inicial = self.df_estandar.loc[1, 'Cuota']
            
            # Obtener cuota al final de la estrategia de amortización parcial
            if self.años_amortizacion_parcial > 0:
                # Si hay estrategia, tomamos la cuota justo después del período de amortización
                indice_final_estrategia = min(self.meses_amortizacion_parcial + 1, len(self.df_estrategia) - 1)
                cuota_final_estrategia = self.df_estrategia.loc[indice_final_estrategia, 'Cuota']
            else:
                # Si no hay estrategia o es solo amortización inicial, tomamos la primera cuota con estrategia
                cuota_final_estrategia = self.df_estrategia.loc[1, 'Cuota']
            
            # Calcular el ahorro porcentual en la cuota
            ahorro_cuota_pct = (cuota_inicial - cuota_final_estrategia) / cuota_inicial * 100 if cuota_inicial > 0 else 0
            
            # Añadir información de ahorro
            ahorro_text = (f"Ahorro: {ahorro['ahorro_global']:,.2f}€ "
                         f"({ahorro['ahorro_porcentaje']:.2f}%)")
                         
            # Añadir información sobre las cuotas
            ahorro_text += f"\n\nCuota estándar: {cuota_inicial:,.2f}€"
            ahorro_text += f"\nCuota final: {cuota_final_estrategia:,.2f}€"
            ahorro_text += f"\nAhorro en cuota: {ahorro_cuota_pct:.2f}%"
            
            # Añadir información de meses de adelanto si existe
            if 'meses_ahorro' in ahorro and ahorro['meses_ahorro'] > 0:
                ahorro_text += f"\nAdelanto: {ahorro['meses_ahorro']} meses"
                
            # Ajustar la posición vertical del bocadillo para dar espacio al texto adicional
            ax.text(0.5, 0.5, ahorro_text, ha='center', fontsize=12, fontweight='bold',
                   transform=ax.transAxes, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
            
            # Mejorar formato
            ax.set_title('Comparativa de pagos totales', fontsize=14)
            ax.set_ylabel('Importe (€)', fontsize=12)
            ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f"{x:,.0f}€"))
            ax.legend(loc='lower left', frameon=True, fontsize=10, facecolor='white', edgecolor='gray')

    def _graficar_cuota_mensual(self, df_estandar, df_estrategia, ax):
        """Genera el gráfico de evolución de la cuota mensual."""
        # Aseguramos que los índices empiezan en 1
        indices_cuota = np.arange(1, len(df_estandar.index))
        
        ax.plot(indices_cuota, df_estandar.loc[1:, 'Cuota'].values, 
               color=self.colors['estandar'], linewidth=2.5, label='Estándar')
        ax.plot(indices_cuota, df_estrategia.loc[1:, 'Cuota'].values, 
               color=self.colors['estrategia'], linewidth=2.5, label='Con estrategia')
        
        # Sombrear área de ahorro en cuota
        cuota_estandar = df_estandar.loc[1:, 'Cuota'].values.astype(float)
        cuota_estrategia = df_estrategia.loc[1:, 'Cuota'].values.astype(float)
        
        # Creamos una máscara booleana para donde hay ahorro en cuota
        mask_cuota = cuota_estandar > cuota_estrategia
        
        if np.any(mask_cuota):  # Solo si hay algún punto donde existe ahorro en cuota
            ax.fill_between(indices_cuota[mask_cuota], 
                           cuota_estrategia[mask_cuota], 
                           cuota_estandar[mask_cuota],
                           color=self.colors['ahorro'], alpha=0.3, label='Ahorro mensual')
        
        # Marcar fin de período de amortización parcial
        if self.meses_amortizacion_parcial > 0:
            ax.axvline(x=self.meses_amortizacion_parcial, color='gray', linestyle='--', alpha=0.7)
            
        # Formato y etiquetas
        ax.set_title('Evolución de la cuota mensual', fontsize=14)
        ax.set_xlabel('Mes', fontsize=12)
        ax.set_ylabel('Cuota mensual (€)', fontsize=12)
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f"{x:,.0f}€"))
        ax.legend(loc='lower left', frameon=True, fontsize=10, facecolor='white', edgecolor='gray')
        ax.grid(True, alpha=0.3)
    


    def _graficar_desglose_gastos(self, df_gastos, ax):
            """
            Genera el gráfico de desglose de gastos, optimizado para manejar casos sin gastos adicionales.
            Muestra la evolución de la cuota mensual cuando no hay gastos adicionales.
            """
            columnas_gastos = list(self.gastos_mensuales.keys())
            
            try:
                if columnas_gastos:  # Hay gastos adicionales configurados
                    # Mostrar todos los meses de vida de la hipoteca
                    meses_mostrar = len(df_gastos) - 1  # Todos los meses excepto el inicial (índice 0)
                    titulo_gastos = 'Desglose de gastos mensuales durante la vida del préstamo'
                    
                    # Verificar que tenemos suficientes meses para mostrar
                    if meses_mostrar > 0:
                        # Crear datos para el gráfico de área apilada
                        df_plot = df_gastos.loc[1:meses_mostrar+1, ['Cuota'] + columnas_gastos].copy()
                        
                        # Usar un colormap para los gastos
                        import matplotlib.cm as cm
                        n_colors = len(columnas_gastos) + 1  # +1 para la cuota
                        colors_gastos = cm.viridis(np.linspace(0, 0.8, n_colors))
                        
                        # Gráfico de área apilada
                        df_plot.plot(kind='area', stacked=True, ax=ax, color=colors_gastos, alpha=0.7)
                                               
                        # Añadir línea para gasto total mensual continua a lo largo de toda la vida del préstamo
                        if self.años_amortizacion_parcial > 0:
                            # Crear una serie continua sin saltos para visualización
                            serie_provisiones = df_gastos['Gasto Total Mensual'].copy()
                            
                            # Durante el período de amortización, usar Provisión Total Mensual 
                            if 'Provisión Total Mensual' in df_gastos.columns:
                                periodo_amortizacion = df_gastos.index <= self.meses_amortizacion_parcial
                                serie_provisiones[periodo_amortizacion] = df_gastos.loc[periodo_amortizacion, 'Provisión Total Mensual']
    
                            # Ajustar límites del eje Y al máximo de la serie provisiones más un 10%
                            max_provision = serie_provisiones.max() * 1.1  # Valor máximo + 10%
                            ax.set_ylim(0, max_provision)
                            
                            # Trazar la línea continua
                            ax.plot(df_gastos.index, serie_provisiones, 
                                   'k--', linewidth=2, label='Provisión total mensual')
                        else:
                            
                            # Ajustar límites del eje Y al máximo de la serie provisiones más un 10%
                            max_provision = df_gastos['Gasto Total Mensual'].max() * 1.1  # Valor máximo + 10%
                            ax.set_ylim(0, max_provision)
                            
                            # Sin estrategia de amortización - trazar la línea normal
                            if 'Gasto Total Mensual' in df_gastos.columns:
                                ax.plot(df_gastos.index, df_gastos['Gasto Total Mensual'],
                                       'k--', linewidth=2, label='Gasto total mensual')
                                
                        # Ajustar formato
                        ax.set_title(titulo_gastos, fontsize=14)
                        ax.set_xlabel('Mes', fontsize=12)
                        ax.set_ylabel('Importe (€)', fontsize=12)
                        ax.legend(loc='lower left', frameon=True, fontsize=10, facecolor='white', edgecolor='gray')
                        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f"{x:,.0f}€"))
    
                        handles, labels = ax.get_legend_handles_labels()
                        ax.legend(handles=handles, labels=labels, loc='lower left', frameon=True, 
                                   fontsize=10, facecolor='white', edgecolor='gray')
                else:
                    # OPTIMIZACIÓN: Si no hay gastos adicionales, mostrar la evolución de la cuota mensual
                    ax.set_title('Evolución de la cuota y provisión total', fontsize=14)
                    
                    # Mostrar evolución de la cuota mensual
                    indices = df_gastos.index[1:]  # Excluimos el índice 0 (inicial)
                    ax.plot(indices, df_gastos.loc[indices, 'Cuota'], 
                           color=self.colors['estandar'], linewidth=2.5, label='Cuota mensual')
                    
                    # Si hay amortizaciones parciales, mostrar la provisión total
                    if self.años_amortizacion_parcial > 0 and 'Provisión Total Mensual' in df_gastos.columns:
                        ax.plot(indices, df_gastos.loc[indices, 'Provisión Total Mensual'],
                               'k--', linewidth=2, label='Provisión total mensual')
                    
                    ax.set_xlabel('Mes', fontsize=12)
                    ax.set_ylabel('Importe (€)', fontsize=12)
                    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f"{x:,.0f}€"))
                    ax.legend(loc='lower left', frameon=True, fontsize=10, facecolor='white', edgecolor='gray')
                    ax.grid(True, alpha=0.3)
                    
            except Exception as e:
                print(f"Error en gráfico de gastos: {str(e)}")
                ax.set_title('Error al visualizar gastos', fontsize=14)
                ax.text(0.5, 0.5, f"Ocurrió un error: {str(e)}", 
                       ha='center', va='center', transform=ax.transAxes, fontsize=12)

    def _mostrar_resumen_ahorro(self, ahorro, df_gastos):
            """Muestra un resumen textual del ahorro generado por la estrategia."""
            print("\n=== RESUMEN DE AHORRO ===")
            print(f"Intereses totales (Estándar): {ahorro['intereses_estandar']:,.2f}€")
            print(f"Intereses totales (Estrategia): {ahorro['intereses_estrategia']:,.2f}€")
            print(f"Ahorro en intereses: {ahorro['ahorro_intereses']:,.2f}€")
            print(f"Pagos totales (Estándar): {ahorro['pagos_estandar']:,.2f}€")
            print(f"Pagos totales (Estrategia): {ahorro['pagos_estrategia']:,.2f}€")
            print(f"Ahorro global: {ahorro['ahorro_global']:,.2f}€ ({ahorro['ahorro_porcentaje']:.2f}%)")
            
            if 'meses_ahorro' in ahorro and ahorro['meses_ahorro'] > 0:
                print(f"Cancelación anticipada: {ahorro['meses_ahorro']} meses antes")
                print(f"Fecha estimada de cancelación: {ahorro['fecha_cancelacion'].strftime('%d/%m/%Y')}")
            
            if self.años_amortizacion_parcial > 0:
                print(f"\nPorcentaje de intereses en los primeros {self.años_amortizacion_parcial} años: "
                     f"{ahorro['porcentaje_intereses_periodo']:.2f}%")
            
            try:
                # Mostrar provisión mensual total (promedio de los primeros 12 meses)
                if 'Provisión Total Mensual' in df_gastos.columns:
                    provision_promedio = df_gastos.loc[1:13, 'Provisión Total Mensual'].mean()
                    print(f"\nProvisión mensual promedio (primer año): {provision_promedio:,.2f}€")
                    
                    # Mostrar evolución de la provisión solo si hay amortizaciones parciales
                    hay_amortizaciones = self.años_amortizacion_parcial > 0 and self.amortizacion_semestral_valor > 0
                    
                    if hay_amortizaciones:
                        # Verificar si hay al menos una provisión de amortizaciones no nula
                        df_anual = df_gastos.loc[1:].groupby('Año').mean(numeric_only=True)
                        
                        if 'Provisión Amortizaciones' in df_anual.columns and df_anual['Provisión Amortizaciones'].sum() > 0:
                            print("\nEvolución de la provisión mensual por año:")
                            df_mostrar = df_anual[['Provisión Amortizaciones']].round(2)
                            print(df_mostrar.to_string(float_format="{:,.2f}€".format))
            except Exception as e:
                print(f"Error mostrando información de provisión: {str(e)}")

    def _mostrar_resumen_configuracion(self) -> None:
        """Muestra un resumen de la configuración actual del simulador."""
        print("\n=== CONFIGURACIÓN DE LA HIPOTECA ===")
        print(f"Capital inicial: {self.capital_inicial:,.2f}€")
        print(f"Capital tras amortización inicial: {self.capital_tras_amortizacion_inicial:,.2f}€")
        print(f"Cuota mensual inicial calculada: {self.cuota_mensual:,.2f}€")
        print(f"Plazo: {self.plazo_meses} meses ({self.plazo_años} años)")
        print(f"Tasa de interés anual: {self.tasa_interes_anual:.2f}%")
        print(f"Tasa de interés mensual efectiva: {self.tasa_interes_mensual*100:.6f}%")
        print(f"Fecha inicio: {self.fecha_inicio.strftime('%d/%m/%Y')}")
        
        tipo_amort = "Equivalente a cuotas mensuales" if self.amortizacion_semestral_tipo == 'cuotas' else "Importe fijo en euros"
        print("\nEstrategia de amortización parcial:")
        print(f"  - Tipo: {self.amortizacion_semestral_tipo} ({tipo_amort})")
        print(f"  - Valor: {self.amortizacion_semestral_valor}")
        print(f"  - Duración: {self.años_amortizacion_parcial} años ({self.meses_amortizacion_parcial} meses)")
        
        

    def _validar_parametros_iniciales(
            self, 
            capital_inicial: float, 
            plazo_años: int, 
            tasa_interes_anual: float,
            amortizacion_inicial: float,
            amortizacion_semestral_tipo: str,
            amortizacion_semestral_valor: float,
            años_amortizacion_parcial: int,
            dia_pago: int
        ) -> None:
        """
        Valida los parámetros iniciales del simulador.
        
        Raises
        ------
        ValueError
            Si alguno de los parámetros no cumple con las condiciones requeridas
        """
        if capital_inicial <= 0:
            raise ValueError("El capital inicial debe ser mayor que cero")
        
        if plazo_años <= 0:
            raise ValueError("El plazo debe ser mayor que cero")
        
        if tasa_interes_anual < 0:
            raise ValueError("La tasa de interés anual no puede ser negativa")
        
        if amortizacion_inicial < 0:
            raise ValueError("La amortización inicial no puede ser negativa")
        
        if amortizacion_inicial >= capital_inicial:
            raise ValueError("La amortización inicial no puede ser mayor o igual al capital inicial")
        
        if amortizacion_semestral_tipo not in ['cuotas', 'constante']:
            raise ValueError("El tipo de amortización semestral debe ser 'cuotas' o 'constante'")
        
        if amortizacion_semestral_valor < 0:
            raise ValueError("El valor de amortización semestral no puede ser negativo")
        
        if años_amortizacion_parcial < 0:
            raise ValueError("Los años de amortización parcial no pueden ser negativos")
        
        if años_amortizacion_parcial > plazo_años:
            raise ValueError("Los años de amortización parcial no pueden superar el plazo del préstamo")
        
        if not (1 <= dia_pago <= 28):
            raise ValueError("El día de pago debe estar entre 1 y 28")


    def agregar_gasto_mensual(self, nombre: str, valor: float, tasa_incremento_anual: float = 0, mensualizado: bool = True) -> None:
        """
        Agrega un gasto recurrente con su tasa de incremento anual.
        
        Parameters
        ----------
        nombre : str
            Nombre del gasto (ej: "Comunidad", "IBI", etc.)
        valor : float
            Valor del gasto. Si mensualizado=True, se considera un valor mensual.
            Si mensualizado=False, se considera un valor anual que será prorrateado automáticamente.
        tasa_incremento_anual : float, optional
            Tasa de incremento anual en porcentaje (ej: 3.0 para 3%), by default 0
        mensualizado : bool, optional
            Indica si el valor proporcionado está mensualizado (True) o es anual (False), by default True
        """
        if valor < 0:
            raise ValueError(f"El valor para '{nombre}' no puede ser negativo")
        
        if tasa_incremento_anual < 0:
            raise ValueError(f"La tasa de incremento anual para '{nombre}' no puede ser negativa")
        
        # Convertir valor anual a mensual si no está mensualizado
        valor_mensual = valor if mensualizado else valor / 12
            
        self.gastos_mensuales[nombre] = valor_mensual
        self.tasas_incremento_anual[nombre] = tasa_incremento_anual / 100
        
        # Formatear el mensaje de confirmación según el tipo de valor proporcionado
        if mensualizado:
            print(f"Añadido gasto mensual: {nombre} = {valor_mensual:,.2f}€/mes (Incremento anual: {tasa_incremento_anual}%)")
        else:
            print(f"Añadido gasto anual: {nombre} = {valor:,.2f}€/año ({valor_mensual:,.2f}€/mes) (Incremento anual: {tasa_incremento_anual}%)")    

    def analizar_distribucion_intereses(self) -> pd.DataFrame:
            """
            Analiza la distribución de intereses a lo largo del tiempo para validar
            la elección del periodo de amortización parcial.
            
            Returns
            -------
            pd.DataFrame
                DataFrame con la distribución porcentual de intereses por año
            """
            try:
                # Simular amortización estándar si aún no se ha hecho
                if self.df_estandar is None:
                    print("\n=== ANALIZANDO DISTRIBUCIÓN DE INTERESES ===")
                    self.df_estandar = self.simular_amortizacion_estandar()
                
                # Agrupar intereses por año
                intereses_por_año = self.df_estandar.groupby('Año')['Intereses'].sum().reset_index()
                intereses_totales = intereses_por_año['Intereses'].sum()
                
                # Calcular porcentajes y acumulados
                intereses_por_año['Porcentaje'] = intereses_por_año['Intereses'] / intereses_totales * 100
                intereses_por_año['Porcentaje_Acumulado'] = intereses_por_año['Porcentaje'].cumsum()
                
                # Crear visualización
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
                fig.suptitle('Análisis de Distribución de Intereses', fontsize=16)
                
                # Configuración estética
                colors = {'barras': '#3498db', 'linea': '#e74c3c', 'umbral': '#e67e22'}
                
                # Gráfico de intereses anuales
                # NOTA: Las siguientes dos llamadas a plot() deben ejecutarse sin 
                # asignar su resultado a variables para evitar errores de dimensión
                # excesiva en la generación de imágenes
                intereses_por_año.plot(x='Año', y='Intereses', kind='bar', ax=ax1, 
                                       color=colors['barras'], alpha=0.7)
                
                # Añadir porcentajes encima de las barras
                for i, (_, row) in enumerate(intereses_por_año.iterrows()):
                    ax1.text(i, row['Intereses'] * 1.02, f"{row['Porcentaje']:.1f}%", 
                           ha='center', va='bottom', fontsize=9)
                
                ax1.set_title('Intereses pagados por año', fontsize=14)
                ax1.set_xlabel('Año', fontsize=12)
                ax1.set_ylabel('Intereses (€)', fontsize=12)
                ax1.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f"{x:,.0f}€"))
                ax1.grid(True, axis='y', alpha=0.3)
                
                # Gráfico de porcentaje acumulado
                intereses_por_año.plot(x='Año', y='Porcentaje_Acumulado', kind='line', 
                                       marker='o', color=colors['linea'], linewidth=2.5,
                                       ax=ax2, markersize=5)
                
                # Añadir línea horizontal en el 50%
                ax2.axhline(y=50, color=colors['umbral'], linestyle='--', alpha=0.7)
                
                # Añadir línea horizontal en el 80%
                ax2.axhline(y=80, color=colors['umbral'], linestyle=':', alpha=0.7)
                
                # Destacar el año donde se supera el 50%
                año_50_pct = None
                año_80_pct = None
                
                if any(intereses_por_año['Porcentaje_Acumulado'] >= 50):
                    año_50_pct = intereses_por_año[intereses_por_año['Porcentaje_Acumulado'] >= 50].iloc[0]['Año']
                    pct_en_año_50 = intereses_por_año[intereses_por_año['Año'] == año_50_pct]['Porcentaje_Acumulado'].values[0]
                    
                    ax2.plot(año_50_pct, pct_en_año_50, 'o', color=colors['umbral'], markersize=8)
                    ax2.annotate(f'50%: Año {año_50_pct}', 
                                xy=(año_50_pct, pct_en_año_50), 
                                xytext=(año_50_pct-1, pct_en_año_50+10),
                                arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5),
                                fontsize=10)
                
                if any(intereses_por_año['Porcentaje_Acumulado'] >= 80):
                    año_80_pct = intereses_por_año[intereses_por_año['Porcentaje_Acumulado'] >= 80].iloc[0]['Año']
                    pct_en_año_80 = intereses_por_año[intereses_por_año['Año'] == año_80_pct]['Porcentaje_Acumulado'].values[0]
                    
                    ax2.plot(año_80_pct, pct_en_año_80, 'o', color=colors['umbral'], markersize=8)
                    ax2.annotate(f'80%: Año {año_80_pct}', 
                                xy=(año_80_pct, pct_en_año_80), 
                                xytext=(año_80_pct+0.5, pct_en_año_80-10),
                                arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5),
                                fontsize=10)
                
                # Añadir línea vertical para el periodo elegido si hay amortizaciones parciales
                if self.años_amortizacion_parcial > 0:
                    año_elegido = intereses_por_año['Año'].iloc[0] + self.años_amortizacion_parcial - 1
                    if año_elegido in intereses_por_año['Año'].values:
                        pct_en_año_elegido = intereses_por_año[intereses_por_año['Año'] == año_elegido]['Porcentaje_Acumulado'].values[0]
                        
                        ax2.axvline(x=año_elegido, color='green', linestyle='--', alpha=0.7)
                        ax2.plot(año_elegido, pct_en_año_elegido, 'o', color='green', markersize=8)
                        ax2.annotate(f'Período elegido: {self.años_amortizacion_parcial} años ({pct_en_año_elegido:.1f}%)', 
                                    xy=(año_elegido, pct_en_año_elegido), 
                                    xytext=(año_elegido-2, pct_en_año_elegido-15),
                                    arrowprops=dict(facecolor='green', shrink=0.05, width=1, headwidth=5),
                                    fontsize=10)
                
                # Formato del gráfico
                ax2.set_title('Porcentaje acumulado de intereses', fontsize=14)
                ax2.set_xlabel('Año', fontsize=12)
                ax2.set_ylabel('Porcentaje acumulado (%)', fontsize=12)
                ax2.yaxis.set_major_formatter(mtick.PercentFormatter())
                ax2.set_ylim(0, 105)  # Límite para visualización adecuada
                ax2.grid(True, alpha=0.3)
                
                plt.tight_layout(rect=[0, 0, 1, 0.95])  # Dejar espacio para el título
                plt.show()
                
                # Imprimir estadísticas
                print("\n=== ANÁLISIS DE DISTRIBUCIÓN DE INTERESES ===")
                años_elegidos = self.años_amortizacion_parcial
                
                try:
                    año_base = intereses_por_año['Año'].iloc[0]
                    año_final = año_base + años_elegidos - 1
                    
                    if año_final in intereses_por_año['Año'].values:
                        pct_acum_en_años_elegidos = intereses_por_año[intereses_por_año['Año'] == año_final]['Porcentaje_Acumulado'].values[0]
                    else:
                        pct_acum_en_años_elegidos = np.nan
                except:
                    pct_acum_en_años_elegidos = np.nan
                    
                print(f"Período de amortización parcial elegido: {años_elegidos} años")
                
                if not np.isnan(pct_acum_en_años_elegidos) and años_elegidos > 0:
                    print(f"En los primeros {años_elegidos} años se paga el {pct_acum_en_años_elegidos:.2f}% del total de intereses")
                
                if año_50_pct:
                    print(f"El 50% de los intereses se pagan aproximadamente en el año {año_50_pct}")
                    
                    años_para_50pct = año_50_pct - intereses_por_año['Año'].iloc[0] + 1
                    print(f"Esto equivale a {años_para_50pct} años desde el inicio del préstamo")
                    
                    # Solo mostrar recomendaciones si hay un período de amortización definido
                    if años_elegidos > 0:
                        if años_elegidos < años_para_50pct:
                            print(f"RECOMENDACIÓN: Considerar extender el periodo de amortizaciones parciales hasta el año {año_50_pct}, para cubrir al menos el 50% de los intereses")
                        elif años_elegidos > años_para_50pct + 2:
                            print(f"RECOMENDACIÓN: Podrías considerar reducir el periodo de amortizaciones parciales hasta el año {año_50_pct}, ya que cubrirías el 50% de los intereses")
                        else:
                            print(f"El periodo de amortización parcial elegido ({años_elegidos} años) es adecuado para tu estrategia")
                    elif años_para_50pct > 0:
                        print(f"RECOMENDACIÓN: Considera implementar amortizaciones parciales durante al menos {años_para_50pct} años para cubrir el 50% de los intereses")
                else:
                    print("No se alcanza el 50% de los intereses en el plazo analizado")
                
                if año_80_pct:
                    print(f"El 80% de los intereses se pagan aproximadamente en el año {año_80_pct}")
                
                # Devolver el DataFrame con los resultados
                return intereses_por_año
            except Exception as e:
                print(f"Error en el análisis de distribución de intereses: {str(e)}")
                import traceback
                traceback.print_exc()
                return pd.DataFrame()

    def calcular_ahorro(self, df_estandar: Optional[pd.DataFrame] = None, 
                        df_estrategia: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        Calcula el ahorro generado por la estrategia de amortización.
        Versión corregida para comparar valores consistentes.
        
        Parameters
        ----------
        df_estandar : pd.DataFrame, optional
            Cuadro de amortización estándar, by default None (usa self.df_estandar)
        df_estrategia : pd.DataFrame, optional
            Cuadro de amortización con estrategia, by default None (usa self.df_estrategia)
        
        Returns
        -------
        Dict[str, float]
            Diccionario con información sobre el ahorro
        """
        if df_estandar is None:
            if self.df_estandar is None:
                raise ValueError("Debe ejecutar simular_amortizacion_estandar() primero o proporcionar df_estandar")
            df_estandar = self.df_estandar
            
        if df_estrategia is None:
            if self.df_estrategia is None:
                raise ValueError("Debe ejecutar simular_amortizacion_estrategia() primero o proporcionar df_estrategia")
            df_estrategia = self.df_estrategia
        
        # Calcular intereses totales
        intereses_estandar = df_estandar['Intereses'].sum()
        intereses_estrategia = df_estrategia['Intereses'].sum()
        
        # Calcular ahorro en intereses
        ahorro_intereses = intereses_estandar - intereses_estrategia
        
        # Calcular pagos totales (sin incluir amortización inicial en ambos casos)
        pagos_estandar = df_estandar.loc[1:, 'Cuota'].sum()
        
        # Aquí sumamos la amortización inicial porque es parte de la estrategia
        pagos_estrategia = (self.amortizacion_inicial + 
                           df_estrategia.loc[1:, 'Cuota'].sum() + 
                           df_estrategia.loc[1:, 'Amortización Extra'].sum())        
        
        # Calcular ahorro global y como porcentaje
        ahorro_global = pagos_estandar - pagos_estrategia
        ahorro_porcentaje = (ahorro_global / pagos_estandar) * 100 if pagos_estandar > 0 else 0
        
        # Calcular la concentración de intereses en los primeros años
        años_analisis = min(self.años_amortizacion_parcial, self.plazo_meses // 12)
        intereses_periodo_estandar = df_estandar.loc[1:años_analisis*12, 'Intereses'].sum()
        porcentaje_intereses_periodo = (intereses_periodo_estandar / intereses_estandar) * 100 if intereses_estandar > 0 else 0
        
        # Corregido: Como usamos la estrategia de reducir cuota manteniendo plazo, 
        # no habrá cancelación anticipada significativa
        # Solo analizamos si el último pago es menor por redondeo o ajuste final
        meses_ahorro = 0
        fecha_cancelacion = df_estrategia.iloc[-1]['Fecha']
        
        # Verificamos si el último pago de la estrategia es significativamente menor 
        if len(df_estrategia) > 1 and len(df_estandar) > 1:
            ultimo_pago_estandar = df_estandar.iloc[-1]['Cuota']
            ultimo_pago_estrategia = df_estrategia.iloc[-1]['Cuota']
            
            # Si el último pago es menor que el 50% del pago estándar, podemos considerar
            # que hay un adelanto parcial del último mes
            if ultimo_pago_estrategia < 0.5 * ultimo_pago_estandar:
                meses_ahorro = 1  # Como máximo ahorramos un mes (el último)
        
        # Almacenar resultados
        resultados = {
            'intereses_estandar': intereses_estandar,
            'intereses_estrategia': intereses_estrategia,
            'intereses_periodo_estandar': intereses_periodo_estandar,
            'porcentaje_intereses_periodo': porcentaje_intereses_periodo,
            'ahorro_intereses': ahorro_intereses,
            'pagos_estandar': pagos_estandar,
            'pagos_estrategia': pagos_estrategia,
            'ahorro_global': ahorro_global,
            'ahorro_porcentaje': ahorro_porcentaje,
            'meses_ahorro': meses_ahorro,
            'fecha_cancelacion': fecha_cancelacion
        }
        
        # Guardar para uso posterior
        self.resultados_ahorro = resultados
        
        return resultados
    

    def calcular_gastos_totales(self, df_amortizacion: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Calcula los gastos totales mensuales incluyendo cuota hipotecaria y otros gastos.
        Versión optimizada para manejar correctamente casos sin gastos adicionales.
        
        Parameters
        ----------
        df_amortizacion : pd.DataFrame, optional
            Cuadro de amortización, by default None (usa df_estrategia si existe)
        
        Returns
        -------
        pd.DataFrame
            Dataframe con los gastos totales mensuales
        """
        if df_amortizacion is None:
            if self.df_estrategia is None:
                raise ValueError("Debe ejecutar simular_amortizacion_estrategia() primero o proporcionar un DataFrame")
            df_amortizacion = self.df_estrategia
        
        # Copiar el dataframe de amortización
        df = df_amortizacion.copy()
        
        # Verificar si hay gastos adicionales configurados
        tiene_gastos_adicionales = bool(self.gastos_mensuales)
        
        if tiene_gastos_adicionales:
            # Agregar columnas para cada gasto
            for nombre in self.gastos_mensuales:
                df[nombre] = 0.0
                
            # Calcular gastos para cada mes utilizando vectorización
            años_base = df['Año'].iloc[1]  # Tomamos el primer año como base
            
            for nombre, valor_inicial in self.gastos_mensuales.items():
                tasa_incremento = self.tasas_incremento_anual[nombre]
                
                # Crear una función vectorizada para calcular el valor con incremento
                df[nombre] = df.apply(
                    lambda row: valor_inicial * (1 + tasa_incremento) ** (row['Año'] - años_base) if row.name > 0 else 0, 
                    axis=1
                )
            
            # Calcular gasto total mensual
            columnas_gastos = list(self.gastos_mensuales.keys())
            df['Gastos Adicionales'] = df[columnas_gastos].sum(axis=1)
        else:
            # Si no hay gastos adicionales, agregar columna de gastos adicionales con valor 0
            df['Gastos Adicionales'] = 0.0
            
        # Calcular gasto total mensual
        df['Gasto Total Mensual'] = df['Cuota'] + df['Gastos Adicionales']
        
        # Calcular provisión mensual para amortizaciones extraordinarias
        df['Provisión Amortizaciones'] = 0.0
        
        # Solo calculamos provisiones si hay amortizaciones parciales configuradas
        hay_amortizaciones = self.años_amortizacion_parcial > 0 and self.amortizacion_semestral_valor > 0
        
        if hay_amortizaciones:
            # Buscar las próximas amortizaciones y distribuir el ahorro
            for i in range(1, len(df)):
                if i % 6 == 1 and i <= self.meses_amortizacion_parcial:  # Inicio de semestre
                    # Calcular la próxima amortización
                    if self.amortizacion_semestral_tipo == 'cuotas':
                        cuota_ref = df.loc[i, 'Cuota']
                        proxima_amortizacion = cuota_ref * self.amortizacion_semestral_valor
                    else:
                        proxima_amortizacion = self.amortizacion_semestral_valor
                    
                    # Distribuir en los próximos 6 meses (o menos si quedan menos)
                    meses_restantes = min(6, len(df) - i)
                    for j in range(meses_restantes):
                        if i + j < len(df):
                            df.loc[i+j, 'Provisión Amortizaciones'] = proxima_amortizacion / meses_restantes
        
        # Calcular provisión total mensual
        df['Provisión Total Mensual'] = df['Gasto Total Mensual'] + df['Provisión Amortizaciones']
        
        # Guardar el dataframe para uso posterior
        self.df_gastos = df
        
        return df
    
    
    def generar_informe(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float]]:
        """
        Genera un informe completo con tablas de amortización, gastos y resultados de ahorro.
        
        Returns
        -------
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float]]
            (df_estandar, df_estrategia, df_gastos, ahorro)
        """
        print("\n=== GENERANDO INFORME COMPLETO ===")
        
        # Simular amortización estándar (si no se ha hecho ya)
        if self.df_estandar is None:
            self.df_estandar = self.simular_amortizacion_estandar()
        else:
            print("Usando cuadro de amortización estándar previamente calculado.")
        
        # Simular amortización con estrategia (si no se ha hecho ya)
        if self.df_estrategia is None:
            self.df_estrategia = self.simular_amortizacion_estrategia()
        else:
            print("Usando cuadro de amortización con estrategia previamente calculado.")
        
        # Calcular gastos totales (si no se ha hecho ya)
        if self.df_gastos is None:
            self.df_gastos = self.calcular_gastos_totales(self.df_estrategia)
        else:
            print("Usando cuadro de gastos previamente calculado.")
        
        # Calcular ahorro (si no se ha hecho ya)
        if self.resultados_ahorro is None:
            self.resultados_ahorro = self.calcular_ahorro(self.df_estandar, self.df_estrategia)
        else:
            print("Usando resultados de ahorro previamente calculados.")
        
        return self.df_estandar, self.df_estrategia, self.df_gastos, self.resultados_ahorro
                
    def mostrar_primeras_amortizaciones(self, df_estrategia: Optional[pd.DataFrame] = None, 
                                           num_amortizaciones: int = 10) -> None:
            """
            Muestra las primeras amortizaciones parciales para verificar el funcionamiento.
            Si no hay amortizaciones parciales, se muestra un mensaje informativo conciso.
            
            Parameters
            ----------
            df_estrategia : pd.DataFrame, optional
                Cuadro de amortización con estrategia, by default None
            num_amortizaciones : int, optional
                Número de amortizaciones a mostrar, by default 10
            """
            if df_estrategia is None:
                if self.df_estrategia is None:
                    print("No hay datos de amortización con estrategia. Ejecute simular_amortizacion_estrategia() primero.")
                    return
                df_estrategia = self.df_estrategia
            
            # Filtrar filas con amortización extra
            filas_amortizacion = df_estrategia[df_estrategia['Amortización Extra'] > 0].sort_index()
            
            if len(filas_amortizacion) == 0:
                # Si no hay estrategia de amortización configurada, mostrar un mensaje más conciso
                if self.años_amortizacion_parcial == 0 or self.amortizacion_semestral_valor == 0:
                    print("\nNo se ha configurado ninguna estrategia de amortizaciones parciales.")
                else:
                    print("\n=== DETALLE DE LAS PRIMERAS AMORTIZACIONES PARCIALES ===")
                    print("No se encontraron amortizaciones parciales en los datos proporcionados.")
                return
            
            print("\n=== DETALLE DE LAS PRIMERAS AMORTIZACIONES PARCIALES ===")
            
            # Limitar al número solicitado
            filas_mostrar = filas_amortizacion.head(num_amortizaciones)
            
            # Mostrar las columnas relevantes
            columnas = ['Fecha', 'Cuota', 'Amortización Extra', 'Capital Pendiente', 'Cuota Recalculada']
            
            # Formatear la salida para mejor legibilidad
            pd.set_option('display.float_format', '{:,.2f}'.format)
            df_mostrar = filas_mostrar[columnas].copy()
            
            # Para la salida formateada, convertimos la fecha a string
            df_mostrar['Fecha'] = df_mostrar['Fecha'].dt.strftime('%d/%m/%Y')
            
            print(df_mostrar.to_string(index=True))
            
            # Verificar coherencia del valor de amortización configurado
            if self.amortizacion_semestral_tipo == 'constante':
                promedio = filas_mostrar['Amortización Extra'].mean()
                print(f"\nValor promedio de amortizaciones: {promedio:,.2f}€")
                print(f"Valor configurado: {self.amortizacion_semestral_valor:,.2f}€")
                
                if abs(promedio - self.amortizacion_semestral_valor) > 1:
                    print("\n⚠️ ATENCIÓN: El valor medio de las amortizaciones no coincide con el configurado.")
                    print("   Posible limitación por capital pendiente o problema en modo 'constante'.")
            elif self.amortizacion_semestral_tipo == 'cuotas':
                # Verificar coherencia con el número de cuotas
                primera_fila = filas_mostrar.iloc[0]
                cuota = primera_fila['Cuota']
                extra = primera_fila['Amortización Extra']
                ratio = extra / cuota
                
                print(f"\nValor primera amortización: {extra:,.2f}€")
                print(f"Cuota mensual en ese momento: {cuota:,.2f}€")
                print(f"Equivale a {ratio:.2f} cuotas mensuales")
                print(f"Valor configurado: {self.amortizacion_semestral_valor:.2f} cuotas mensuales")
                
                if abs(ratio - self.amortizacion_semestral_valor) > 0.1:
                    print("\n⚠️ ATENCIÓN: El valor en cuotas no coincide exactamente con el configurado.")
                    if ratio < self.amortizacion_semestral_valor:
                        print("   Posible limitación por capital pendiente disponible.")

    def resumen_ejecutivo(self) -> None:
            """
            Muestra un resumen ejecutivo de los resultados de la simulación.
            Versión optimizada que adapta su salida según la configuración real de la hipoteca.
            """
            if not all([self.df_estandar is not None, self.df_estrategia is not None, 
                       self.df_gastos is not None, self.resultados_ahorro is not None]):
                print("No hay datos completos para generar el resumen. Ejecute generar_informe() primero.")
                return
            
            print("\n" + "="*80)
            print(" "*30 + "RESUMEN EJECUTIVO")
            print("="*80)
            
            # Detalles del préstamo
            print("\n📋 DETALLES DEL PRÉSTAMO:")
            print(f"Capital inicial: {self.capital_inicial:,.2f}€")
            print(f"Plazo: {self.plazo_años} años ({self.plazo_meses} meses)")
            print(f"Tipo de interés: {self.tasa_interes_anual:.2f}%")
            
            # Solo mostrar amortización inicial si existe
            if self.amortizacion_inicial > 0:
                print(f"Amortización inicial: {self.amortizacion_inicial:,.2f}€")
            
            print(f"Cuota mensual inicial: {self.cuota_mensual:,.2f}€")
            
            # Estrategia de amortización - adaptar mensaje según configuración
            hay_estrategia = self.amortizacion_inicial > 0 or (self.años_amortizacion_parcial > 0 and self.amortizacion_semestral_valor > 0)
            
            if hay_estrategia:
                print("\n🔄 ESTRATEGIA DE AMORTIZACIÓN:")
                
                # Describir estrategia de amortización inicial (si existe)
                if self.amortizacion_inicial > 0:
                    print(f"Amortización inicial: {self.amortizacion_inicial:,.2f}€")
                
                # Describir estrategia de amortizaciones parciales (si existen)
                if self.años_amortizacion_parcial > 0 and self.amortizacion_semestral_valor > 0:
                    tipo_str = "cuotas mensuales" if self.amortizacion_semestral_tipo == 'cuotas' else "euros"
                    print(f"Amortizaciones parciales de {self.amortizacion_semestral_valor} {tipo_str} cada 6 meses")
                    print(f"Duración de amortizaciones parciales: {self.años_amortizacion_parcial} años")
                else:
                    # Solo mostrar este mensaje si hay amortización inicial pero no hay amortizaciones parciales
                    if self.amortizacion_inicial > 0:
                        print("No se han configurado amortizaciones parciales")
            
            # Resultados financieros
            ahorro = self.resultados_ahorro
            hay_ahorro = ahorro['ahorro_global'] > 0.01  # Consideramos que hay ahorro si es mayor a 1 céntimo
            
            if hay_ahorro:
                print("\n💰 RESULTADOS FINANCIEROS:")
                print(f"Intereses totales (sin estrategia): {ahorro['intereses_estandar']:,.2f}€")
                print(f"Intereses totales (con estrategia): {ahorro['intereses_estrategia']:,.2f}€")
                print(f"Ahorro en intereses: {ahorro['ahorro_intereses']:,.2f}€ ({ahorro['ahorro_intereses']/ahorro['intereses_estandar']*100:.2f}%)")
                
                # Total a pagar
                print("\n💵 TOTAL A PAGAR:")
                print(f"Total pagado (sin estrategia): {ahorro['pagos_estandar']:,.2f}€")
                print(f"Total pagado (con estrategia): {ahorro['pagos_estrategia']:,.2f}€")
                print(f"Ahorro total: {ahorro['ahorro_global']:,.2f}€ ({ahorro['ahorro_porcentaje']:.2f}%)")
            else:
                # Si no hay ahorro porque no hay estrategia, simplificamos la salida
                print("\n💰 RESULTADOS FINANCIEROS:")
                print(f"Intereses totales: {ahorro['intereses_estandar']:,.2f}€")
                
                # Total a pagar
                print("\n💵 TOTAL A PAGAR:")
                print(f"Total a pagar: {ahorro['intereses_estandar'] + self.capital_inicial:,.2f}€")
            
            # Reducción de plazo
            if 'meses_ahorro' in ahorro and ahorro['meses_ahorro'] > 0:
                print("\n⏱️ REDUCCIÓN DE PLAZO:")
                print(f"Cancelación anticipada: {ahorro['meses_ahorro']} meses ({ahorro['meses_ahorro']/12:.1f} años)")
                print(f"Fecha estimada de cancelación: {ahorro['fecha_cancelacion'].strftime('%d/%m/%Y')}")
            
            # Información sobre gastos mensuales
            tiene_gastos_adicionales = bool(self.gastos_mensuales)
            hay_amortizaciones_parciales = self.años_amortizacion_parcial > 0 and self.amortizacion_semestral_valor > 0
            
            # Mostrar información sobre provisión mensual según configuración
            if hay_amortizaciones_parciales and 'Provisión Total Mensual' in self.df_gastos.columns:
                provision_promedio = self.df_gastos.loc[1:13, 'Provisión Total Mensual'].mean()
                cuota_promedio = self.df_gastos.loc[1:13, 'Cuota'].mean()
                
                print("\n📊 PROVISIÓN MENSUAL (Primer año):")
                print(f"Cuota hipoteca: {cuota_promedio:,.2f}€")
                
                if tiene_gastos_adicionales:
                    gastos_adicionales = provision_promedio - cuota_promedio - self.df_gastos.loc[1:13, 'Provisión Amortizaciones'].mean()
                    print(f"Gastos adicionales: {gastos_adicionales:,.2f}€")
                    
                print(f"Provisión amortizaciones: {self.df_gastos.loc[1:13, 'Provisión Amortizaciones'].mean():,.2f}€")
                print(f"Provisión total: {provision_promedio:,.2f}€")
            elif tiene_gastos_adicionales and 'Gasto Total Mensual' in self.df_gastos.columns:
                # Si no hay amortizaciones parciales pero hay gastos adicionales
                gasto_promedio = self.df_gastos.loc[1:13, 'Gasto Total Mensual'].mean()
                cuota_promedio = self.df_gastos.loc[1:13, 'Cuota'].mean()
                
                print("\n📊 GASTOS MENSUALES (Primer año):")
                print(f"Cuota hipoteca: {cuota_promedio:,.2f}€")
                print(f"Gastos adicionales: {gasto_promedio - cuota_promedio:,.2f}€")
                print(f"Gasto total: {gasto_promedio:,.2f}€")
            else:
                # Si no hay ni amortizaciones parciales ni gastos adicionales
                cuota_promedio = self.df_gastos.loc[1:13, 'Cuota'].mean()
                print("\n📊 GASTOS MENSUALES (Primer año):")
                print(f"Cuota hipoteca: {cuota_promedio:,.2f}€")
            
            # Conclusión
            print("\n✅ CONCLUSIÓN:")
            if not hay_estrategia:
                print("No se ha configurado ninguna estrategia de amortización adicional")
            else:
                if ahorro['ahorro_porcentaje'] > 10:
                    nivel_ahorro = "significativo"
                elif ahorro['ahorro_porcentaje'] > 5:
                    nivel_ahorro = "moderado"
                elif ahorro['ahorro_porcentaje'] > 0.1:
                    nivel_ahorro = "ligero"
                else:
                    nivel_ahorro = "mínimo"
                        
                print(f"La estrategia planteada genera un ahorro {nivel_ahorro} del {ahorro['ahorro_porcentaje']:.2f}%")
                
                if 'meses_ahorro' in ahorro and ahorro['meses_ahorro'] > 0:
                    print(f"La estrategia permite cancelar la hipoteca {ahorro['meses_ahorro']} meses antes")
            
            print("\n" + "="*80)    
    
            
    def simular_amortizacion_estandar(self) -> pd.DataFrame:
        """
        Genera un cuadro de amortización estándar sin ninguna estrategia de amortización.
        """
        # Calcular desde el capital inicial completo, ignorando cualquier amortización inicial
        capital_pendiente = self.capital_inicial
        plazo_restante = self.plazo_meses
        cuota_mensual = self._calcular_cuota_mensual(capital_pendiente, self.tasa_interes_mensual, plazo_restante)
        
        # Crear dataframe para el cuadro de amortización
        fechas = self._generar_fechas_pago(plazo_restante)
        df = pd.DataFrame(index=range(plazo_restante + 1), 
                         columns=['Fecha', 'Cuota', 'Intereses', 'Amortización', 'Capital Pendiente'])
        
        # Valores iniciales
        df.loc[0, 'Fecha'] = fechas[0]
        df.loc[0, 'Cuota'] = 0
        df.loc[0, 'Intereses'] = 0
        df.loc[0, 'Amortización'] = 0  # Sin amortización inicial
        df.loc[0, 'Capital Pendiente'] = capital_pendiente
        
        # Calcular cuadro de amortización
        for i in range(1, plazo_restante + 1):
            fecha = fechas[i]
            intereses = capital_pendiente * self.tasa_interes_mensual
            amortizacion = cuota_mensual - intereses
            capital_pendiente -= amortizacion
            
            # Ajuste para el último pago para evitar saldos negativos
            if i == plazo_restante:
                amortizacion = max(0, capital_pendiente + amortizacion)  # Ajustamos la amortización final
                cuota_mensual = amortizacion + intereses
                capital_pendiente = 0
            
            df.loc[i, 'Fecha'] = fecha
            df.loc[i, 'Cuota'] = cuota_mensual
            df.loc[i, 'Intereses'] = intereses
            df.loc[i, 'Amortización'] = amortizacion
            df.loc[i, 'Capital Pendiente'] = max(0, capital_pendiente)
        
        # Convertir fechas a formato de fecha
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        df['Mes'] = df['Fecha'].dt.month
        df['Año'] = df['Fecha'].dt.year
        
        # Verificar totales para debug
        total_intereses = df['Intereses'].sum()
        total_amortizacion = df['Amortización'].sum()
        
        # Corregido: no incluimos la amortización inicial en el total_amortizacion
        # porque ya está incluida en el índice 0 del dataframe
        total_pagado = total_intereses + total_amortizacion
        
        print("\n=== RESUMEN AMORTIZACIÓN ESTÁNDAR ===")
        print(f"Total intereses: {total_intereses:,.2f}€")
        print(f"Total amortización: {total_amortizacion:,.2f}€")
        
        # Solo mostrar información sobre amortización inicial si existe
        if self.amortizacion_inicial > 0:
            print(f"Total amortización inicial: {self.amortizacion_inicial:,.2f}€")
        
        print(f"Total pagado: {total_pagado:,.2f}€")
        print(f"Capital inicial: {self.capital_inicial:,.2f}€")
        
        # Corregido: verificamos que el total amortizado sea igual al capital inicial
        diferencia = total_amortizacion - self.capital_inicial
        print(f"Diferencia total amortización vs capital inicial: {diferencia:,.2f}€")
        
        # Verificamos que el total pagado sea igual a la suma del capital inicial y los intereses
        cuadre = abs(total_amortizacion - self.capital_inicial) < 0.01
        if not cuadre:
            print("⚠️ ADVERTENCIA: El total amortizado no coincide exactamente con el capital inicial.")
            print(f"  La diferencia es: {diferencia:,.2f}€")
        
        # Guardar el dataframe para uso posterior
        self.df_estandar = df
        
        return df
    
    def simular_amortizacion_estrategia(self) -> pd.DataFrame:
        """
        Genera un cuadro de amortización con la estrategia de amortizaciones extraordinarias.
        Versión corregida para reducir la cuota manteniendo el plazo.
        
        Returns
        -------
        pd.DataFrame
            Cuadro de amortización con amortizaciones extraordinarias
        """
        # Inicializar variables
        capital_pendiente = self.capital_tras_amortizacion_inicial
        plazo_restante = self.plazo_meses
        cuota_mensual = self.cuota_mensual
        
        # Crear dataframe para el cuadro de amortización
        fechas = self._generar_fechas_pago(plazo_restante)
        df = pd.DataFrame(index=range(plazo_restante + 1), 
                          columns=['Fecha', 'Cuota', 'Intereses', 'Amortización', 
                                  'Amortización Extra', 'Capital Pendiente', 'Cuota Recalculada'])
        
        # Valores iniciales
        df.loc[0, 'Fecha'] = fechas[0]
        df.loc[0, 'Cuota'] = 0
        df.loc[0, 'Intereses'] = 0
        df.loc[0, 'Amortización'] = self.amortizacion_inicial
        df.loc[0, 'Amortización Extra'] = 0
        df.loc[0, 'Capital Pendiente'] = capital_pendiente
        df.loc[0, 'Cuota Recalculada'] = cuota_mensual
        
        # Calcular cuadro de amortización
        for i in range(1, plazo_restante + 1):
            fecha = fechas[i]
            intereses = capital_pendiente * self.tasa_interes_mensual
            amortizacion = cuota_mensual - intereses
            
            # Determinar si corresponde amortización extraordinaria (cada 6 meses)
            if i % 6 == 0 and i <= self.meses_amortizacion_parcial:
                if self.amortizacion_semestral_tipo == 'cuotas':
                    amortizacion_extra = cuota_mensual * self.amortizacion_semestral_valor
                else:  # tipo 'constante'
                    amortizacion_extra = self.amortizacion_semestral_valor
                
                # Limitar la amortización extra al capital pendiente
                amortizacion_extra = min(amortizacion_extra, capital_pendiente - amortizacion)
            else:
                amortizacion_extra = 0
            
            # Actualizar capital pendiente
            capital_pendiente = capital_pendiente - amortizacion - amortizacion_extra
            
            # Recalcular cuota si hay amortización extra (estrategia de reducir cuota, no plazo)
            if amortizacion_extra > 0:
                meses_restantes = plazo_restante - i
                if meses_restantes > 0:  # Evitar división por cero
                    cuota_mensual = self._calcular_cuota_mensual(capital_pendiente, 
                                                              self.tasa_interes_mensual, 
                                                              meses_restantes)
            
            # Ajuste para el último pago para evitar saldos negativos
            if i == plazo_restante:
                amortizacion = max(0, capital_pendiente + amortizacion)  # Ajustamos la amortización final
                cuota_mensual = amortizacion + intereses
                capital_pendiente = 0
            
            df.loc[i, 'Fecha'] = fecha
            df.loc[i, 'Cuota'] = cuota_mensual
            df.loc[i, 'Intereses'] = intereses
            df.loc[i, 'Amortización'] = amortizacion
            df.loc[i, 'Amortización Extra'] = amortizacion_extra
            df.loc[i, 'Capital Pendiente'] = max(0, capital_pendiente)
            df.loc[i, 'Cuota Recalculada'] = cuota_mensual
            
        # Convertir fechas a formato de fecha
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        df['Mes'] = df['Fecha'].dt.month
        df['Año'] = df['Fecha'].dt.year
        
        # Verificar totales para debug
        total_intereses = df['Intereses'].sum()
        total_amortizacion = df['Amortización'].sum()
        total_amortizacion_extra = df['Amortización Extra'].sum()
        
        # Corregido: no incluimos la amortización inicial en este cálculo
        # porque ya está incluida en el índice 0 del dataframe
        total_pagado = total_intereses + total_amortizacion + total_amortizacion_extra
        
        print("\n=== RESUMEN AMORTIZACIÓN CON ESTRATEGIA ===")
        print(f"Total intereses: {total_intereses:,.2f}€")
        print(f"Total amortización: {total_amortizacion:,.2f}€")
        print(f"Total amortización extra: {total_amortizacion_extra:,.2f}€")
        
        # Solo mostrar información sobre amortización inicial si existe
        if self.amortizacion_inicial > 0:
            print(f"Total amortización inicial: {self.amortizacion_inicial:,.2f}€")
        
        print(f"Total pagado: {total_pagado:,.2f}€")
        print(f"Capital inicial: {self.capital_inicial:,.2f}€")
        
        # Corregido: verificamos que el total amortizado sea igual al capital inicial
        total_amortizado = total_amortizacion + total_amortizacion_extra
        
        # Ajustamos el mensaje según exista o no amortización inicial
        if self.amortizacion_inicial > 0:
            diferencia = total_amortizado - self.capital_inicial + self.amortizacion_inicial
            print(f"Diferencia total amortizado vs capital después de amortización inicial: {diferencia:,.2f}€")
        else:
            diferencia = total_amortizado - self.capital_inicial
            print(f"Diferencia total amortizado vs capital inicial: {diferencia:,.2f}€")
        
        # Guardar el dataframe para uso posterior
        self.df_estrategia = df
        
        return df

    def visualizar_resultados(self, 
                             df_estandar: Optional[pd.DataFrame] = None, 
                             df_estrategia: Optional[pd.DataFrame] = None, 
                             df_gastos: Optional[pd.DataFrame] = None, 
                             ahorro: Optional[Dict[str, float]] = None) -> None:
        """
        Visualiza los resultados de la simulación con gráficos (versión optimizada).
        
        Parameters
        ----------
        df_estandar : pd.DataFrame, optional
            Cuadro de amortización estándar, by default None
        df_estrategia : pd.DataFrame, optional
            Cuadro de amortización con estrategia, by default None
        df_gastos : pd.DataFrame, optional
            Gastos totales mensuales, by default None
        ahorro : Dict[str, float], optional
            Información sobre el ahorro, by default None
        """
        # Usar datos previamente calculados si no se proporcionan
        if df_estandar is None:
            df_estandar = self.df_estandar
        if df_estrategia is None:
            df_estrategia = self.df_estrategia
        if df_gastos is None:
            df_gastos = self.df_gastos
        if ahorro is None:
            ahorro = self.resultados_ahorro
            
        # Comprobar que tenemos todos los datos necesarios
        if any(x is None for x in [df_estandar, df_estrategia, df_gastos, ahorro]):
            print("Falta información necesaria. Ejecute generar_informe() primero.")
            return
            
        try:
            # Configuración estética global
            self._configurar_estilo_graficos()
            
            # Crear figura y subplots
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'{self.titulo}', fontsize=18, y=0.98)
            
            # Generar los gráficos específicos
            self._graficar_capital_pendiente(df_estandar, df_estrategia, axes[0, 0])
            self._graficar_cuota_mensual(df_estandar, df_estrategia, axes[0, 1])
            self._graficar_desglose_gastos(df_gastos, axes[1, 0])
            self._graficar_comparativa_pagos(ahorro, axes[1, 1])
            
            # Ajustar layout y mostrar
            plt.tight_layout(rect=[0, 0, 1, 0.95])  # Dejar espacio para el título
            plt.show()
            
            # Mostrar información adicional textual
            self._mostrar_resumen_ahorro(ahorro, df_gastos)
            
        except Exception as e:
            print(f"Error en la visualización: {str(e)}")
            import traceback
            traceback.print_exc()


class HipotecaGridSearch:
    """
    Implementa una búsqueda exhaustiva en rejilla para optimizar estrategias de amortización
    hipotecaria, evaluando combinaciones de parámetros y sus impactos financieros.
    """
    def __init__(
            self, 
            capital_inicial: float, 
            plazo_años: int, 
            tasa_interes_anual: float,
            fecha_inicio: str = None,
            dia_pago: int = 1,
            gastos_mensuales: dict = None,
            tasas_incremento: dict = None
        ):
        """
        Inicializa el sistema de búsqueda en rejilla con los parámetros base de la hipoteca.
        
        Parameters
        ----------
        capital_inicial : float
            Capital inicial del préstamo en euros
        plazo_años : int
            Plazo del préstamo en años
        tasa_interes_anual : float
            Tasa de interés anual en porcentaje
        fecha_inicio : str, optional
            Fecha de inicio en formato 'YYYY-MM-DD'
        dia_pago : int, optional
            Día del mes para el pago (1-28)
        gastos_mensuales : dict, optional
            Diccionario de gastos mensuales {nombre: valor}
        tasas_incremento : dict, optional
            Diccionario de tasas de incremento anual para gastos {nombre: tasa_porcentual}
        """
        # Parámetros base que serán constantes en todas las simulaciones
        self.capital_inicial = capital_inicial
        self.plazo_años = plazo_años
        self.tasa_interes_anual = tasa_interes_anual
        self.fecha_inicio = fecha_inicio
        self.dia_pago = dia_pago
        
        # Gastos mensuales y tasas
        self.gastos_mensuales = gastos_mensuales or {}
        self.tasas_incremento = tasas_incremento or {}
        
        # Almacenamiento de resultados
        self.resultados = []
        self.parametros_grid = {}
        self.mejor_estrategia = {}
        
        # Configuraciones de visualización
        self.colores = plt.cm.tab20(np.linspace(0, 1, 20))  # Paleta de 20 colores
    
    def configurar_grid(self, 
                      amortizacion_inicial_valores: list = None,
                      amortizacion_tipos: list = None,
                      amortizacion_valores: dict = None,
                      años_amortizacion_valores: list = None):
        """
        Configura el espacio de búsqueda para la exploración de estrategias.
        
        Parameters
        ----------
        amortizacion_inicial_valores : list, optional
            Lista de valores de amortización inicial a probar
        amortizacion_tipos : list, optional
            Lista de tipos de amortización ('cuotas', 'constante')
        amortizacion_valores : dict, optional
            Diccionario {tipo: [valores]} con los valores a probar para cada tipo
        años_amortizacion_valores : list, optional
            Lista de duraciones (en años) para las amortizaciones parciales
        """
        # Valores por defecto si no se especifican
        self.parametros_grid = {
            'amortizacion_inicial': amortizacion_inicial_valores or [0],
            'amortizacion_tipo': amortizacion_tipos or ['cuotas', 'constante'],
            'amortizacion_valor': amortizacion_valores or {
                'cuotas': [2, 3, 4],
                'constante': [1000, 2000, 3000]
            },
            'años_amortizacion': años_amortizacion_valores or [5, 10, 15]
        }
        
        # Calcular el número total de combinaciones
        n_combinaciones = len(self.parametros_grid['amortizacion_inicial'])
        for tipo in self.parametros_grid['amortizacion_tipo']:
            n_combinaciones *= len(self.parametros_grid['amortizacion_valor'].get(tipo, []))
        n_combinaciones *= len(self.parametros_grid['años_amortizacion'])
        
        print(f"Grid configurado con {n_combinaciones} combinaciones de parámetros.")
        return self
    
    def ejecutar_grid(self, progreso: bool = True, limite_combinaciones: int = None):
        """
        Ejecuta simulaciones para todas las combinaciones de parámetros definidas.
        
        Parameters
        ----------
        progreso : bool, optional
            Mostrar barra de progreso, por defecto True
        limite_combinaciones : int, optional
            Limitar el número máximo de combinaciones a ejecutar
            
        Returns
        -------
        self
            Instancia actualizada con resultados
        """
        
        # Generar todas las combinaciones posibles
        combinaciones = []
        for amort_ini in self.parametros_grid['amortizacion_inicial']:
            for tipo in self.parametros_grid['amortizacion_tipo']:
                for valor in self.parametros_grid['amortizacion_valor'].get(tipo, []):
                    for años in self.parametros_grid['años_amortizacion']:
                        combinaciones.append({
                            'amortizacion_inicial': amort_ini,
                            'amortizacion_tipo': tipo,
                            'amortizacion_valor': valor,
                            'años_amortizacion': años
                        })
        
        # Limitar el número de combinaciones si se especifica
        if limite_combinaciones and limite_combinaciones < len(combinaciones):
            print(f"Limitando a {limite_combinaciones} de {len(combinaciones)} combinaciones posibles")
            combinaciones = combinaciones[:limite_combinaciones]
        
        # Ejecutar simulaciones
        self.resultados = []
        iterator = tqdm(combinaciones) if progreso else combinaciones
        
        for params in iterator:
            # Crear simulador con los parámetros actuales
            sim = HipotecaSimulator(
                capital_inicial=self.capital_inicial,
                plazo_años=self.plazo_años,
                tasa_interes_anual=self.tasa_interes_anual,
                amortizacion_inicial=params['amortizacion_inicial'],
                amortizacion_semestral_tipo=params['amortizacion_tipo'],
                amortizacion_semestral_valor=params['amortizacion_valor'],
                años_amortizacion_parcial=params['años_amortizacion'],
                fecha_inicio=self.fecha_inicio,
                dia_pago=self.dia_pago,
                titulo=f"Estrategia {len(self.resultados)+1}"
            )
            
            # Agregar gastos mensuales
            for nombre, valor in self.gastos_mensuales.items():
                tasa = self.tasas_incremento.get(nombre, 0)
                sim.agregar_gasto_mensual(nombre, valor, tasa)
            
            # Simular y guardar resultados sin visualización
            with self._suppress_output():  # Función auxiliar para suprimir salidas
                df_estandar, df_estrategia, df_gastos, ahorro = sim.generar_informe()
            
            # Guardar resultados con los parámetros utilizados
            resultado = {
                'parametros': params.copy(),
                'ahorro': ahorro,
                'df_estrategia': df_estrategia,
                'df_gastos': df_gastos,
                'simulador': sim
            }
            
            # Añadir métricas adicionales para comparación
            resultado['metricas'] = {
                'ahorro_total': ahorro['ahorro_global'],
                'ahorro_porcentaje': ahorro['ahorro_porcentaje'],
                'cuota_final': df_estrategia.loc[params['años_amortizacion']*12+1, 'Cuota'] if params['años_amortizacion'] > 0 else df_estrategia.loc[1, 'Cuota'],
                'provision_mensual': df_gastos.loc[1:13, 'Provisión Total Mensual'].mean() if 'Provisión Total Mensual' in df_gastos.columns else df_gastos.loc[1:13, 'Gasto Total Mensual'].mean()
            }
            
            self.resultados.append(resultado)
        
        # Identificar la mejor estrategia según diferentes criterios
        self._identificar_mejores_estrategias()
        
        print(f"Completadas {len(self.resultados)} simulaciones.")
        return self
    
    def _identificar_mejores_estrategias(self):
        """Identifica las mejores estrategias según diferentes criterios."""
        if not self.resultados:
            return
        
        # Organizar resultados por criterios
        criterios = {
            'ahorro_total': {'indice': None, 'valor': 0},
            'ahorro_porcentaje': {'indice': None, 'valor': 0},
            'cuota_final': {'indice': None, 'valor': float('inf')},
            'provision_mensual': {'indice': None, 'valor': float('inf')},
            'relacion_ahorro_provision': {'indice': None, 'valor': 0}
        }
        
        # Calcular relación ahorro/provisión para cada estrategia
        for i, resultado in enumerate(self.resultados):
            metricas = resultado['metricas']
            metricas['relacion_ahorro_provision'] = metricas['ahorro_total'] / metricas['provision_mensual'] if metricas['provision_mensual'] > 0 else 0
            
            # Actualizar mejores estrategias
            if metricas['ahorro_total'] > criterios['ahorro_total']['valor']:
                criterios['ahorro_total'] = {'indice': i, 'valor': metricas['ahorro_total']}
                
            if metricas['ahorro_porcentaje'] > criterios['ahorro_porcentaje']['valor']:
                criterios['ahorro_porcentaje'] = {'indice': i, 'valor': metricas['ahorro_porcentaje']}
                
            if metricas['cuota_final'] < criterios['cuota_final']['valor']:
                criterios['cuota_final'] = {'indice': i, 'valor': metricas['cuota_final']}
                
            if metricas['provision_mensual'] < criterios['provision_mensual']['valor']:
                criterios['provision_mensual'] = {'indice': i, 'valor': metricas['provision_mensual']}
                
            if metricas['relacion_ahorro_provision'] > criterios['relacion_ahorro_provision']['valor']:
                criterios['relacion_ahorro_provision'] = {'indice': i, 'valor': metricas['relacion_ahorro_provision']}
        
        # Guardar índices de las mejores estrategias
        self.mejor_estrategia = {criterio: info['indice'] for criterio, info in criterios.items()}
    
    def visualizar_comparativa(self, 
                              criterio: str = 'ahorro_total', 
                              top_n: int = 5, 
                              estrategias_indices: list = None):
        """
        Visualiza una comparativa entre las mejores estrategias según un criterio.
        
        Parameters
        ----------
        criterio : str, optional
            Criterio para seleccionar las mejores estrategias:
            'ahorro_total', 'ahorro_porcentaje', 'cuota_final', 'provision_mensual', 'relacion_ahorro_provision'
        top_n : int, optional
            Número de mejores estrategias a visualizar
        estrategias_indices : list, optional
            Índices específicos de estrategias a comparar, sobreescribe criterio y top_n
            
        Returns
        -------
        tuple
            Figura y ejes de matplotlib con la visualización
        """
        if not self.resultados:
            print("No hay resultados para visualizar. Ejecute primero ejecutar_grid().")
            return None, None
        
        # Seleccionar estrategias a comparar
        if estrategias_indices is not None:
            indices = [i for i in estrategias_indices if 0 <= i < len(self.resultados)]
        else:
            # Ordenar por criterio especificado
            if criterio == 'cuota_final' or criterio == 'provision_mensual':
                # Para estos criterios, menor es mejor
                ordenados = sorted(enumerate(self.resultados), 
                                  key=lambda x: x[1]['metricas'][criterio])
            else:
                # Para el resto, mayor es mejor
                ordenados = sorted(enumerate(self.resultados), 
                                  key=lambda x: x[1]['metricas'][criterio], 
                                  reverse=True)
            
            # Tomar los top_n índices
            indices = [idx for idx, _ in ordenados[:top_n]]
        
        if not indices:
            print("No se encontraron estrategias válidas para comparar.")
            return None, None
        
        # Crear visualización
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Comparativa de las {len(indices)} mejores estrategias por {criterio}', 
                    fontsize=18, y=0.98)
        
        # Gráficas comparativas
        self._graficar_comparativa_capital(indices, axes[0, 0])
        self._graficar_comparativa_cuotas(indices, axes[0, 1])
        self._graficar_comparativa_ahorro(indices, axes[1, 0])
        self._graficar_tabla_parametros(indices, axes[1, 1])
        
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.show()
        
        return fig, axes
    
    def _graficar_comparativa_capital(self, indices, ax):
        """Grafica comparativa de evolución del capital pendiente."""
        # Graficar la referencia estándar (sin estrategia)
        ref = self.resultados[indices[0]]
        df_estandar = ref['simulador'].df_estandar
        ax.plot(df_estandar.index, df_estandar['Capital Pendiente'],
               'k--', linewidth=1.5, label='Estándar (sin estrategia)')
        
        # Graficar cada estrategia seleccionada
        for i, idx in enumerate(indices):
            resultado = self.resultados[idx]
            df = resultado['df_estrategia']
            color = self.colores[i % len(self.colores)]
            
            # Etiquetar con info resumida 
            params = resultado['parametros']
            if params['amortizacion_tipo'] == 'cuotas':
                label = f"E{idx+1}: Ini={params['amortizacion_inicial']/1000}K, {params['amortizacion_valor']} cuot, {params['años_amortizacion']}a"
            else:
                label = f"E{idx+1}: Ini={params['amortizacion_inicial']/1000}K, {params['amortizacion_valor']/1000}K€, {params['años_amortizacion']}a"
            
            ax.plot(df.index, df['Capital Pendiente'], 
                   color=color, linewidth=2, label=label)
        
        # Formato
        ax.set_title('Evolución del capital pendiente', fontsize=14)
        ax.set_xlabel('Mes', fontsize=12)
        ax.set_ylabel('Capital pendiente (€)', fontsize=12)
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f"{x:,.0f}€"))
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', frameon=True, fontsize=9)
    
    def _graficar_comparativa_cuotas(self, indices, ax):
        """Grafica comparativa de evolución de cuotas mensuales."""
        # Graficar la referencia estándar (sin estrategia)
        ref = self.resultados[indices[0]]
        df_estandar = ref['simulador'].df_estandar
        ax.plot(df_estandar.index[1:], df_estandar.loc[1:, 'Cuota'],
               'k--', linewidth=1.5, label='Estándar (sin estrategia)')
        
        # Graficar cada estrategia seleccionada
        for i, idx in enumerate(indices):
            resultado = self.resultados[idx]
            df = resultado['df_estrategia']
            color = self.colores[i % len(self.colores)]
            
            # Etiquetar con info resumida y ahorro
            ahorro_pct = resultado['metricas']['ahorro_porcentaje']
            label = f"E{idx+1}: Ahorro {ahorro_pct:.1f}%"
            
            ax.plot(df.index[1:], df.loc[1:, 'Cuota'], 
                   color=color, linewidth=2, label=label)
        
        # Formato
        ax.set_title('Evolución de la cuota mensual', fontsize=14)
        ax.set_xlabel('Mes', fontsize=12)
        ax.set_ylabel('Cuota mensual (€)', fontsize=12)
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f"{x:,.0f}€"))
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', frameon=True, fontsize=9)
    
    def _graficar_comparativa_ahorro(self, indices, ax):
        """Grafica comparativa de ahorro total y mensual."""
        # Preparar datos
        indices_graf = np.arange(len(indices))
        ahorros = [self.resultados[idx]['metricas']['ahorro_total'] for idx in indices]
        ahorros_pct = [self.resultados[idx]['metricas']['ahorro_porcentaje'] for idx in indices]
        provision = [self.resultados[idx]['metricas']['provision_mensual'] for idx in indices]
        
        # Crear gráfico de barras para ahorro total
        bars = ax.bar(indices_graf, ahorros, width=0.6, color=[self.colores[i % len(self.colores)] for i in range(len(indices))])
        
        # Añadir etiquetas con porcentaje de ahorro
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + max(ahorros)*0.02,
                   f"{ahorros_pct[i]:.1f}%", ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # Añadir línea para provisión mensual (eje secundario)
        ax2 = ax.twinx()
        ax2.plot(indices_graf, provision, 'ko--', linewidth=1.5, markersize=6, label='Provisión mensual')
        
        # Formato de los ejes
        ax.set_title('Comparativa de ahorro total y provisión mensual', fontsize=14)
        ax.set_xticks(indices_graf)
        ax.set_xticklabels([f"E{idx+1}" for idx in indices], fontsize=10)
        ax.set_xlabel('Estrategia', fontsize=12)
        ax.set_ylabel('Ahorro total (€)', fontsize=12)
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f"{x:,.0f}€"))
        
        ax2.set_ylabel('Provisión mensual (€)', fontsize=12)
        ax2.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f"{x:,.0f}€"))
        
        # Añadir leyenda
        ax.legend(['Ahorro total'], loc='upper left', frameon=True, fontsize=9)
        ax2.legend(loc='upper right', frameon=True, fontsize=9)
        
        ax.grid(True, axis='y', alpha=0.3)
    
    def _graficar_tabla_parametros(self, indices, ax):
        """Crea una tabla visual de parámetros y métricas."""
        # Preparar datos para la tabla
        estrategias = [f"E{idx+1}" for idx in indices]
        
        # Crear datos de tabla
        datos = []
        encabezados = ["Estrategia", "Amort. Inicial", "Tipo", "Valor", "Años", 
                      "Ahorro Total", "Ahorro %", "Cuota Final", "Provisión"]
        
        for i, idx in enumerate(indices):
            resultado = self.resultados[idx]
            params = resultado['parametros']
            metricas = resultado['metricas']
            
            # Formatear valor según tipo
            if params['amortizacion_tipo'] == 'cuotas':
                valor_str = f"{params['amortizacion_valor']} cuotas"
            else:
                valor_str = f"{params['amortizacion_valor']:,}€"
            
            # Añadir fila con datos
            datos.append([
                f"E{idx+1}",
                f"{params['amortizacion_inicial']:,}€",
                params['amortizacion_tipo'].capitalize(),
                valor_str,
                f"{params['años_amortizacion']} años",
                f"{metricas['ahorro_total']:,.2f}€",
                f"{metricas['ahorro_porcentaje']:.2f}%",
                f"{metricas['cuota_final']:,.2f}€",
                f"{metricas['provision_mensual']:,.2f}€"
            ])
        
        # Crear tabla
        ax.axis('off')
        tabla = ax.table(
            cellText=datos,
            colLabels=encabezados,
            loc='center',
            cellLoc='center',
            colColours=['#f2f2f2']*len(encabezados)
        )
        
        # Formato de la tabla
        tabla.auto_set_font_size(False)
        tabla.set_fontsize(10)
        tabla.scale(1.2, 1.5)
        
        # Título
        ax.set_title('Parámetros y métricas de las estrategias', fontsize=14, pad=20)
    
    def resumen_top_estrategias(self, n=5):
        """
        Muestra un resumen de las mejores estrategias según diferentes criterios.
        
        Parameters
        ----------
        n : int, optional
            Número de estrategias a mostrar por criterio, por defecto 5
        """
        if not self.resultados:
            print("No hay resultados para mostrar. Ejecute primero ejecutar_grid().")
            return
        
        criterios = [
            ('ahorro_total', 'Ahorro total (€)', True),
            ('ahorro_porcentaje', 'Ahorro porcentual (%)', True),
            ('cuota_final', 'Cuota mensual final (€)', False),
            ('provision_mensual', 'Provisión mensual media (€)', False),
            ('relacion_ahorro_provision', 'Relación ahorro/provisión', True)
        ]
        
        print("\n" + "="*100)
        print(f"RESUMEN DE LAS MEJORES ESTRATEGIAS (TOP {n})".center(100))
        print("="*100)
        
        for criterio, titulo, mayor_mejor in criterios:
            print(f"\n{titulo}:")
            print("-" * 100)
            
            # Ordenar estrategias
            if mayor_mejor:
                ordenados = sorted(enumerate(self.resultados), 
                                  key=lambda x: x[1]['metricas'][criterio], 
                                  reverse=True)
            else:
                ordenados = sorted(enumerate(self.resultados), 
                                  key=lambda x: x[1]['metricas'][criterio])
            
            # Mostrar top-n
            formato = "{:<5} {:<15} {:<10} {:<15} {:<10} {:<20} {:<15} {:<15} {:<15}"
            print(formato.format(
                "Rank", "Amort. Inicial", "Tipo", "Valor", "Años", 
                "Ahorro Total", "Ahorro %", "Cuota Final", "Provisión"
            ))
            print("-" * 100)
            
            for rank, (idx, resultado) in enumerate(ordenados[:n], 1):
                params = resultado['parametros']
                metricas = resultado['metricas']
                
                # Formatear valor según tipo
                if params['amortizacion_tipo'] == 'cuotas':
                    valor_str = f"{params['amortizacion_valor']} cuotas"
                else:
                    valor_str = f"{params['amortizacion_valor']:,}€"
                
                print(formato.format(
                    f"E{idx+1}",
                    f"{params['amortizacion_inicial']:,}€",
                    params['amortizacion_tipo'].capitalize(),
                    valor_str,
                    f"{params['años_amortizacion']} años",
                    f"{metricas['ahorro_total']:,.2f}€",
                    f"{metricas['ahorro_porcentaje']:.2f}%",
                    f"{metricas['cuota_final']:,.2f}€",
                    f"{metricas['provision_mensual']:,.2f}€"
                ))
    
    def visualizar_estrategia(self, indice):
        """
        Visualiza una estrategia específica en detalle.
        
        Parameters
        ----------
        indice : int
            Índice de la estrategia a visualizar
        """
        if not 0 <= indice < len(self.resultados):
            print(f"Índice {indice} fuera de rango. Hay {len(self.resultados)} estrategias disponibles.")
            return
        
        resultado = self.resultados[indice]
        simulador = resultado['simulador']
        
        # Mostrar detalles de la estrategia
        print(f"\n=== ESTRATEGIA {indice+1} ===")
        params = resultado['parametros']
        print(f"Amortización inicial: {params['amortizacion_inicial']:,}€")
        if params['amortizacion_tipo'] == 'cuotas':
            print(f"Amortización semestral: {params['amortizacion_valor']} cuotas mensuales")
        else:
            print(f"Amortización semestral: {params['amortizacion_valor']:,}€")
        print(f"Duración amortizaciones: {params['años_amortizacion']} años")
        
        # Visualizar con el simulador original
        simulador.visualizar_resultados()
        simulador.resumen_ejecutivo()
    
    def obtener_mejor_estrategia(self, criterio='ahorro_total'):
        """
        Devuelve el simulador de la mejor estrategia según el criterio especificado.
        
        Parameters
        ----------
        criterio : str, optional
            Criterio para seleccionar la mejor estrategia, por defecto 'ahorro_total'
            
        Returns
        -------
        HipotecaSimulator
            Simulador de la mejor estrategia
        """
        if not self.resultados or criterio not in self.mejor_estrategia:
            return None
        
        idx = self.mejor_estrategia[criterio]
        return self.resultados[idx]['simulador'] if idx is not None else None
    
    @contextlib.contextmanager
    def _suppress_output(self):
        """Contexto para suprimir temporalmente la salida estándar."""
        # Redirige stdout y stderr a /dev/null
        devnull = open(os.devnull, 'w')
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = devnull, devnull
        
        try:
            yield
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            devnull.close()


# Ejemplo de uso
def ejemplo_gridsearch():
    """
    Ejemplo de uso del GridSearch para explorar estrategias hipotecarias.
    """
    # Definir parámetros constantes para todas las simulaciones
    capital_inicial = 232741
    plazo_años = 30
    tasa_interes_anual = 1.90
    fecha_inicio = '2025-06-01'

    # Definir gastos mensuales
    gastos = {
        "Comunidad": 50.0,
        "IBI": 25.0,
        "Seguro Hogar": 45.83,
        "Seguro Vida": 37.50,
        "Alquiler garaje": 100
    }

    tasas = {
        "Comunidad": 3.0,
        "IBI": 2.0,
        "Seguro Hogar": 5.0,
        "Seguro Vida": 4.0,
        "Alquiler garaje":3.0
    }

    # Crear y configurar el GridSearch
    grid = HipotecaGridSearch(
        capital_inicial=capital_inicial,
        plazo_años=plazo_años,
        tasa_interes_anual=tasa_interes_anual,
        fecha_inicio=fecha_inicio,
        gastos_mensuales=gastos,
        tasas_incremento=tasas
    )

    # Configurar espacio de búsqueda (reducido para ejemplo)
    grid.configurar_grid(
        amortizacion_inicial_valores=[0, 5000, 10000, 15000],
        amortizacion_tipos=['constante', 'cuotas'],
        amortizacion_valores={
            'constante': [0, 600, 1200, 1800, 2400],
            'cuotas':[1,2,3]
        },
        años_amortizacion_valores=[2*n for n in range(8)]
    )

    # Ejecutar búsqueda (limitar a 10 combinaciones por ejemplo)
    grid.ejecutar_grid(progreso=True, limite_combinaciones=1000)

    # Ver resumen de las mejores estrategias
    grid.resumen_top_estrategias(n=5)

    # Visualizar comparativa de las mejores estrategias por ahorro total
    grid.visualizar_comparativa(criterio='ahorro_total', top_n=5)

    # Obtener el simulador de la mejor estrategia para análisis adicionales
    mejor_simulador = grid.obtener_mejor_estrategia(criterio='ahorro_total')
    
    return mejor_simulador, grid

# Ejemplo de uso sin amortización comprando garaje
def ejemplo_sin_amortizacion_y_garaje():
    """
    Ejecuta un ejemplo sin amortización partcial pero comprando garaje.
    """
    try:
        # Parámetros base
        capital_inicial = 232741
        plazo_años = 30
        tasa_interes_anual = 1.90
        amortizacion_inicial = 0
        fecha_inicio = '2025-06-01'  # Formato: 'YYYY-MM-DD'
        
        # Crear simulador con amortización constante
        sim = HipotecaSimulator(
            capital_inicial=capital_inicial,
            plazo_años=plazo_años,
            tasa_interes_anual=tasa_interes_anual,
            amortizacion_inicial=amortizacion_inicial,
            amortizacion_semestral_tipo='constante',  # Tipo constante en euros
            amortizacion_semestral_valor=0,  # 2000€ cada 6 meses
            años_amortizacion_parcial=0,
            fecha_inicio=fecha_inicio,
            dia_pago=1,  # Pago el día 1 de cada mes
            titulo = "Estrategia noamort cte + noinit + garaje"
        )
        
        # Agregar los mismos gastos para comparar
        sim.agregar_gasto_mensual("Comunidad", 50.0, 3.0)  # 3% de incremento anual
        sim.agregar_gasto_mensual("IBI", 25.0, 2.0)  # 2% de incremento anual
        sim.agregar_gasto_mensual("Seguro Hogar", 45.83, 5.0)  # 5% de incremento anual
        sim.agregar_gasto_mensual("Seguro Vida", 37.50, 4.0)  # 4% de incremento anual
                
        # Generar informe completo
        df_estandar, df_estrategia, df_gastos, ahorro = sim.generar_informe()
        
        # Mostrar detalle de primeras amortizaciones
        sim.mostrar_primeras_amortizaciones(df_estrategia)
        
        # Visualizar resultados
        sim.visualizar_resultados(df_estandar, df_estrategia, df_gastos, ahorro)
        
        # Mostrar resumen ejecutivo
        sim.resumen_ejecutivo()
        
        return df_estandar, df_estrategia, df_gastos, ahorro, sim
    except Exception as e:
        print(f"Error ejecutando el ejemplo: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None
    
    
def ejemplo_amortizacion_constante10_1800():
    """
    Ejecuta un ejemplo usando amortización constante comprando una plaza de
    garaje en vez de hacer una amortización inicial.
    """
    try:
        # Parámetros base
        capital_inicial = 232741
        plazo_años = 30
        tasa_interes_anual = 1.90
        amortizacion_inicial = 0
        fecha_inicio = '2025-06-01'  # Formato: 'YYYY-MM-DD'
        
        # Crear simulador con amortización constante
        sim = HipotecaSimulator(
            capital_inicial=capital_inicial,
            plazo_años=plazo_años,
            tasa_interes_anual=tasa_interes_anual,
            amortizacion_inicial=amortizacion_inicial,
            amortizacion_semestral_tipo='constante',  # Tipo constante en euros
            amortizacion_semestral_valor=1800,  # 2000€ cada 6 meses
            años_amortizacion_parcial=10,
            fecha_inicio=fecha_inicio,
            dia_pago=1,  # Pago el día 1 de cada mes
            titulo = "Estrategia amort cte 1800€ 10y+ noinit + garaje comprado"
        )
        
        # Agregar los mismos gastos para comparar
        sim.agregar_gasto_mensual("Comunidad", 50.0, 3.0)  # 3% de incremento anual
        sim.agregar_gasto_mensual("IBI", 25.0, 2.0)  # 2% de incremento anual
        sim.agregar_gasto_mensual("Seguro Hogar", 45.83, 5.0)  # 5% de incremento anual
        sim.agregar_gasto_mensual("Seguro Vida", 37.50, 4.0)  # 4% de incremento anual
        
        # Analizar la distribución de intereses (validación del periodo de amortización)
        sim.analizar_distribucion_intereses()
        
        # Generar informe completo
        df_estandar, df_estrategia, df_gastos, ahorro = sim.generar_informe()
        
        # Mostrar detalle de primeras amortizaciones
        sim.mostrar_primeras_amortizaciones(df_estrategia)
        
        # Visualizar resultados
        sim.visualizar_resultados(df_estandar, df_estrategia, df_gastos, ahorro)
        
        # Mostrar resumen ejecutivo
        sim.resumen_ejecutivo()
        
        return df_estandar, df_estrategia, df_gastos, ahorro, sim
    except Exception as e:
        print(f"Error ejecutando el ejemplo: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None

def ejemplo_amortizacion_constante15_1800():
    """
    Ejecuta un ejemplo usando amortización constante comprando una plaza de
    garaje en vez de hacer una amortización inicial.
    """
    try:
        # Parámetros base
        capital_inicial = 232741
        plazo_años = 30
        tasa_interes_anual = 1.90
        amortizacion_inicial = 0
        fecha_inicio = '2025-06-01'  # Formato: 'YYYY-MM-DD'
        
        # Crear simulador con amortización constante
        sim = HipotecaSimulator(
            capital_inicial=capital_inicial,
            plazo_años=plazo_años,
            tasa_interes_anual=tasa_interes_anual,
            amortizacion_inicial=amortizacion_inicial,
            amortizacion_semestral_tipo='constante',  # Tipo constante en euros
            amortizacion_semestral_valor=1800,  # 2000€ cada 6 meses
            años_amortizacion_parcial=15,
            fecha_inicio=fecha_inicio,
            dia_pago=1,  # Pago el día 1 de cada mes
            titulo = "Estrategia amort cte 1800€ 15y+ noinit + garaje comprado"
        )
        
        # Agregar los mismos gastos para comparar
        sim.agregar_gasto_mensual("Comunidad", 50.0, 3.0)  # 3% de incremento anual
        sim.agregar_gasto_mensual("IBI", 25.0, 2.0)  # 2% de incremento anual
        sim.agregar_gasto_mensual("Seguro Hogar", 45.83, 5.0)  # 5% de incremento anual
        sim.agregar_gasto_mensual("Seguro Vida", 37.50, 4.0)  # 4% de incremento anual
        
        # Analizar la distribución de intereses (validación del periodo de amortización)
        sim.analizar_distribucion_intereses()
        
        # Generar informe completo
        df_estandar, df_estrategia, df_gastos, ahorro = sim.generar_informe()
        
        # Mostrar detalle de primeras amortizaciones
        sim.mostrar_primeras_amortizaciones(df_estrategia)
        
        # Visualizar resultados
        sim.visualizar_resultados(df_estandar, df_estrategia, df_gastos, ahorro)
        
        # Mostrar resumen ejecutivo
        sim.resumen_ejecutivo()
        
        return df_estandar, df_estrategia, df_gastos, ahorro, sim
    except Exception as e:
        print(f"Error ejecutando el ejemplo: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None

def ejemplo_amortizacion_constante10_2400():
    """
    Ejecuta un ejemplo usando amortización constante comprando una plaza de
    garaje en vez de hacer una amortización inicial.
    """
    try:
        # Parámetros base
        capital_inicial = 232741
        plazo_años = 30
        tasa_interes_anual = 1.90
        amortizacion_inicial = 0
        fecha_inicio = '2025-06-01'  # Formato: 'YYYY-MM-DD'
        
        # Crear simulador con amortización constante
        sim = HipotecaSimulator(
            capital_inicial=capital_inicial,
            plazo_años=plazo_años,
            tasa_interes_anual=tasa_interes_anual,
            amortizacion_inicial=amortizacion_inicial,
            amortizacion_semestral_tipo='constante',  # Tipo constante en euros
            amortizacion_semestral_valor=2400,  # 2000€ cada 6 meses
            años_amortizacion_parcial=10,
            fecha_inicio=fecha_inicio,
            dia_pago=1,  # Pago el día 1 de cada mes
            titulo = "Estrategia amort cte 2400€ 10y+ noinit + garaje comprado"
        )
        
        # Agregar los mismos gastos para comparar
        sim.agregar_gasto_mensual("Comunidad", 50.0, 3.0)  # 3% de incremento anual
        sim.agregar_gasto_mensual("IBI", 25.0, 2.0)  # 2% de incremento anual
        sim.agregar_gasto_mensual("Seguro Hogar", 45.83, 5.0)  # 5% de incremento anual
        sim.agregar_gasto_mensual("Seguro Vida", 37.50, 4.0)  # 4% de incremento anual
        
        # Analizar la distribución de intereses (validación del periodo de amortización)
        sim.analizar_distribucion_intereses()
        
        # Generar informe completo
        df_estandar, df_estrategia, df_gastos, ahorro = sim.generar_informe()
        
        # Mostrar detalle de primeras amortizaciones
        sim.mostrar_primeras_amortizaciones(df_estrategia)
        
        # Visualizar resultados
        sim.visualizar_resultados(df_estandar, df_estrategia, df_gastos, ahorro)
        
        # Mostrar resumen ejecutivo
        sim.resumen_ejecutivo()
        
        return df_estandar, df_estrategia, df_gastos, ahorro, sim
    except Exception as e:
        print(f"Error ejecutando el ejemplo: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None
    
def ejemplo_amortizacion_constante15_2400():
    """
    Ejecuta un ejemplo usando amortización constante comprando una plaza de
    garaje en vez de hacer una amortización inicial.
    """
    try:
        # Parámetros base
        capital_inicial = 232741
        plazo_años = 30
        tasa_interes_anual = 1.90
        amortizacion_inicial = 0
        fecha_inicio = '2025-06-01'  # Formato: 'YYYY-MM-DD'
        
        # Crear simulador con amortización constante
        sim = HipotecaSimulator(
            capital_inicial=capital_inicial,
            plazo_años=plazo_años,
            tasa_interes_anual=tasa_interes_anual,
            amortizacion_inicial=amortizacion_inicial,
            amortizacion_semestral_tipo='constante',  # Tipo constante en euros
            amortizacion_semestral_valor=2400,  # 2000€ cada 6 meses
            años_amortizacion_parcial=15,
            fecha_inicio=fecha_inicio,
            dia_pago=1,  # Pago el día 1 de cada mes
            titulo = "Estrategia amort cte 2400€ 15y+ noinit + garaje comprado"
        )
        
        # Agregar los mismos gastos para comparar
        sim.agregar_gasto_mensual("Comunidad", 50.0, 3.0)  # 3% de incremento anual
        sim.agregar_gasto_mensual("IBI", 25.0, 2.0)  # 2% de incremento anual
        sim.agregar_gasto_mensual("Seguro Hogar", 45.83, 5.0)  # 5% de incremento anual
        sim.agregar_gasto_mensual("Seguro Vida", 37.50, 4.0)  # 4% de incremento anual
        
        # Analizar la distribución de intereses (validación del periodo de amortización)
        sim.analizar_distribucion_intereses()
        
        # Generar informe completo
        df_estandar, df_estrategia, df_gastos, ahorro = sim.generar_informe()
        
        # Mostrar detalle de primeras amortizaciones
        sim.mostrar_primeras_amortizaciones(df_estrategia)
        
        # Visualizar resultados
        sim.visualizar_resultados(df_estandar, df_estrategia, df_gastos, ahorro)
        
        # Mostrar resumen ejecutivo
        sim.resumen_ejecutivo()
        
        return df_estandar, df_estrategia, df_gastos, ahorro, sim
    except Exception as e:
        print(f"Error ejecutando el ejemplo: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None

if __name__ == "__main__":
    # Ejecutar ejemplo de GridSearch
    mejor_simulador, grid = ejemplo_gridsearch()
    
    print("Simulación sin amortización:")
    df_estandar, df_estrategia, df_gastos, ahorro, sim = ejemplo_sin_amortizacion_y_garaje()
    
    print("Simulación sin amortización:")
    df_estandar2, df_estrategia2, df_gastos2, ahorro2, sim2  = ejemplo_amortizacion_constante10_1800()

    print("Simulación sin amortización con garaje:")
    df_estandar3, df_estrategia3, df_gastos3, ahorro3, sim3= ejemplo_amortizacion_constante15_1800()
    
    print("Simulación con amortización por cuotas:")
    df_estandar4, df_estrategia4, df_gastos4, ahorro4, sim4 = ejemplo_amortizacion_constante10_2400()
    
    print("Simulación con amortización constante:")
    df_estandar5, df_estrategia5, df_gastos5, ahorro5, sim5 = ejemplo_amortizacion_constante15_2400()
