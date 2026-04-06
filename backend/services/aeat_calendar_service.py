# backend/services/aeat_calendar_service.py
"""
Servicio para obtener y procesar el calendario del contribuyente de la AEAT
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
import re
import logging

logger = logging.getLogger(__name__)


class AEATCalendarService:
    """
    Servicio para obtener y procesar el calendario del contribuyente de la AEAT
    """
    
    BASE_URL = "https://sede.agenciatributaria.gob.es/Sede/ayuda/calendario-contribuyente"
    
    def fetch_calendar(self, year=None):
        """
        Obtiene el calendario tributario de un año específico
        
        Args:
            year (int): Año del calendario (por defecto el año actual)
        
        Returns:
            list: Lista de diccionarios con las fechas tributarias
        """
        if not year:
            year = datetime.now().year
        
        url = f"{self.BASE_URL}/calendario-contribuyente-{year}.html"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Referer': f'{self.BASE_URL}/calendario-contribuyente-{year}/calendario-anual.html'
        }
        
        try:
            logger.info(f"Obteniendo calendario AEAT para el año {year} desde {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parsear el HTML y extraer fechas
            fechas = self._parse_calendar_html(soup, year)
            
            logger.info(f"Se obtuvieron {len(fechas)} fechas del calendario AEAT {year}")
            return fechas
            
        except requests.RequestException as e:
            logger.error(f"Error obteniendo calendario AEAT: {e}")
            raise
    
    def _parse_calendar_html(self, soup, year):
        """
        Parsea el HTML del calendario y extrae las fechas importantes
        
        Args:
            soup: BeautifulSoup object con el HTML
            year: Año del calendario
        
        Returns:
            list: Lista de diccionarios con fechas tributarias
        """
        fechas = []
        
        # Buscar todas las tablas con clase 'tabla-calendario' o similar
        # (Esto dependerá de la estructura exacta del HTML de la AEAT)
        tablas = soup.find_all('table')
        
        for tabla in tablas:
            # Buscar filas de la tabla
            filas = tabla.find_all('tr')
            
            for fila in filas[1:]:  # Saltar encabezado
                celdas = fila.find_all('td')
                
                if len(celdas) >= 2:
                    try:
                        # Extraer fecha y descripción
                        fecha_str = celdas[0].get_text(strip=True)
                        titulo = celdas[1].get_text(strip=True)
                        descripcion = celdas[2].get_text(strip=True) if len(celdas) > 2 else ''
                        
                        # Parsear fecha
                        fecha_obj = self._parse_date(fecha_str, year)
                        
                        if fecha_obj and titulo:
                            fecha_data = {
                                'fecha': fecha_obj,
                                'titulo': titulo,
                                'descripcion': descripcion,
                                'tipo_impuesto': self._extract_tax_type(titulo),
                                'modelo': self._extract_model_number(titulo),
                                'periodicidad': self._extract_periodicity(titulo),
                                'año': year,
                                'mes': fecha_obj.month,
                                'trimestre': self._get_trimestre(fecha_obj.month)
                            }
                            fechas.append(fecha_data)
                            logger.debug(f"Fecha extraída: {fecha_obj} - {titulo[:50]}")
                            
                    except Exception as e:
                        logger.warning(f"Error parseando fila: {e}")
                        continue
        
        # Si no se encontraron fechas en tablas, intentar con listas
        if not fechas:
            logger.warning("No se encontraron fechas en tablas, intentando con listas...")
            fechas = self._parse_calendar_lists(soup, year)
        
        return fechas
    
    def _parse_calendar_lists(self, soup, year):
        """
        Parsea listas (ul/li) en caso de que no haya tablas
        """
        fechas = []
        
        # Buscar listas con fechas
        listas = soup.find_all(['ul', 'ol'])
        
        for lista in listas:
            items = lista.find_all('li')
            
            for item in items:
                texto = item.get_text(strip=True)
                
                # Buscar patrones de fecha en el texto
                # Ejemplo: "20 de enero - Modelo 303"
                match = re.search(r'(\d{1,2})\s+de\s+(\w+)', texto, re.IGNORECASE)
                
                if match:
                    try:
                        dia = int(match.group(1))
                        mes_str = match.group(2)
                        
                        fecha_obj = self._parse_date(f"{dia} de {mes_str}", year)
                        
                        if fecha_obj:
                            fecha_data = {
                                'fecha': fecha_obj,
                                'titulo': texto,
                                'descripcion': '',
                                'tipo_impuesto': self._extract_tax_type(texto),
                                'modelo': self._extract_model_number(texto),
                                'periodicidad': self._extract_periodicity(texto),
                                'año': year,
                                'mes': fecha_obj.month,
                                'trimestre': self._get_trimestre(fecha_obj.month)
                            }
                            fechas.append(fecha_data)
                            
                    except Exception as e:
                        logger.warning(f"Error parseando item de lista: {e}")
                        continue
        
        return fechas
    
    def _parse_date(self, date_str, year):
        """
        Convierte string de fecha a objeto datetime.date
        
        Args:
            date_str: String con la fecha (ej: "20 de enero", "20/01")
            year: Año
        
        Returns:
            date: Objeto date o None si no se puede parsear
        """
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        try:
            # Formato: "20 de enero"
            match = re.search(r'(\d{1,2})\s+de\s+(\w+)', date_str, re.IGNORECASE)
            if match:
                dia = int(match.group(1))
                mes_str = match.group(2).lower()
                mes = meses.get(mes_str)
                
                if mes:
                    return date(year, mes, dia)
            
            # Formato: "20/01" o "20-01"
            match = re.search(r'(\d{1,2})[/-](\d{1,2})', date_str)
            if match:
                dia = int(match.group(1))
                mes = int(match.group(2))
                return date(year, mes, dia)
            
            # Formato: "2026-01-20"
            match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
            if match:
                return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            
        except (ValueError, AttributeError) as e:
            logger.warning(f"No se pudo parsear fecha '{date_str}': {e}")
        
        return None
    
    def _extract_tax_type(self, titulo):
        """
        Extrae el tipo de impuesto del título
        
        Args:
            titulo: Título de la fecha tributaria
        
        Returns:
            str: Tipo de impuesto identificado
        """
        titulo_upper = titulo.upper()
        
        if 'IVA' in titulo_upper:
            return 'IVA'
        elif 'IRPF' in titulo_upper or 'RENTA' in titulo_upper:
            return 'IRPF'
        elif 'SOCIEDADES' in titulo_upper or 'IS' in titulo_upper:
            return 'Sociedades'
        elif 'RETENCIONES' in titulo_upper or 'RETENCIÓN' in titulo_upper:
            return 'Retenciones'
        elif 'INTRASTAT' in titulo_upper:
            return 'Intrastat'
        elif 'SII' in titulo_upper:
            return 'SII'
        elif 'SEGURIDAD SOCIAL' in titulo_upper or 'SS' in titulo_upper:
            return 'Seguridad Social'
        elif 'MODELO 347' in titulo_upper:
            return 'Operaciones con Terceros'
        elif 'MODELO 190' in titulo_upper or 'MODELO 180' in titulo_upper:
            return 'Resumen Anual'
        
        return 'Otro'
    
    def _extract_model_number(self, titulo):
        """
        Extrae el número de modelo (303, 111, etc.) del título
        
        Args:
            titulo: Título de la fecha tributaria
        
        Returns:
            str: Número de modelo o None
        """
        # Buscar "Modelo XXX" o "Mod. XXX"
        match = re.search(r'Modelo?\s*(\d{3})', titulo, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Buscar solo el número si está entre espacios
        match = re.search(r'\b(\d{3})\b', titulo)
        if match:
            modelo = match.group(1)
            # Validar que sea un modelo conocido
            modelos_conocidos = ['111', '115', '117', '123', '124', '130', '131', '180', '190', 
                                '200', '202', '216', '296', '303', '347', '349', '390']
            if modelo in modelos_conocidos:
                return modelo
        
        return None
    
    def _extract_periodicity(self, titulo):
        """
        Extrae la periodicidad (mensual, trimestral, anual) del título
        
        Args:
            titulo: Título de la fecha tributaria
        
        Returns:
            str: Periodicidad identificada
        """
        titulo_upper = titulo.upper()
        
        if 'MENSUAL' in titulo_upper or 'MES' in titulo_upper:
            return 'Mensual'
        elif 'TRIMESTRAL' in titulo_upper or 'TRIMESTRE' in titulo_upper or 'T1' in titulo_upper or 'T2' in titulo_upper or 'T3' in titulo_upper or 'T4' in titulo_upper:
            return 'Trimestral'
        elif 'ANUAL' in titulo_upper or 'AÑO' in titulo_upper or 'RESUMEN' in titulo_upper:
            return 'Anual'
        
        # Inferir por modelo
        modelo = self._extract_model_number(titulo)
        if modelo:
            if modelo in ['111', '115', '117', '123', '124', '303']:
                return 'Mensual'
            elif modelo in ['130', '131', '303']:
                return 'Trimestral'
            elif modelo in ['180', '190', '347', '349']:
                return 'Anual'
        
        return None
    
    def _get_trimestre(self, mes):
        """
        Obtiene el trimestre según el mes
        
        Args:
            mes: Número del mes (1-12)
        
        Returns:
            int: Número de trimestre (1-4)
        """
        if mes in [1, 2, 3]:
            return 1
        elif mes in [4, 5, 6]:
            return 2
        elif mes in [7, 8, 9]:
            return 3
        else:
            return 4
