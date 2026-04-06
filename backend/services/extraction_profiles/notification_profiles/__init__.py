from .base_notification_profile import BaseNotificationProfile
from .providencia_apremio_profile import ProvidenciaApremioProfile
from .resolucion_altas_bajas_profile import ResolucionAltasBajasProfile
from .reintegro_reta_profile import ReintegroRetaProfile
from .embargo_vehiculos_profile import EmbargoVehiculosProfile
from .levantamiento_embargo_cuenta_profile import LevantamientoEmbargoCuentaProfile
from .captura_precinto_vehiculos_profile import CapturaPrecintosVehiculosProfile
from .embargo_cuentas_profile import EmbargoCuentasProfile
from .requerimiento_bienes_profile import RequerimientoBienesProfile
from .regularizacion_reta_devolucion_profile import RegularizacionRetaDevolucionProfile
from .regularizacion_reta_ingreso_profile import RegularizacionRetaIngresoProfile

# Lista de perfiles disponibles
# El orden importa: los más específicos primero
PROFILES = [
    ProvidenciaApremioProfile(),
    ResolucionAltasBajasProfile(),
    ReintegroRetaProfile(),
    CapturaPrecintosVehiculosProfile(),   # TVA-336 antes que TVA-391
    EmbargoVehiculosProfile(),             # TVA-391
    EmbargoCuentasProfile(),               # TVA-313 antes que TVA-350
    LevantamientoEmbargoCuentaProfile(),   # TVA-350
    RequerimientoBienesProfile(),          # TVA-218
    RegularizacionRetaDevolucionProfile(), # Regularización RETA Devolución
    RegularizacionRetaIngresoProfile(),    # Regularización RETA Ingreso
]











def get_notification_profile(texto_completo: str) -> BaseNotificationProfile:
    """
    Devuelve el primer perfil que coincida con el texto.
    Si ninguno coincide, devuelve None (el extractor usará lógica genérica).
    """
    for profile in PROFILES:
        if profile.matches(texto_completo):
            return profile
    return None
