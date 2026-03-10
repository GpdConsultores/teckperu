"""
Capa de servicios para la lógica de negocio de certificaciones.
Separa la lógica de negocio de las vistas para mejor mantenibilidad y testabilidad.
"""

from .certification_renewal import (
    can_retake_after_expiration,
    get_certificate_status,
    get_expired_certs_for_student,
    approve_renewal,
    validate_renewal_eligible,
    RenewalNotEligibleError,
)

__all__ = [
    "can_retake_after_expiration",
    "get_certificate_status",
    "get_expired_certs_for_student",
    "approve_renewal",
    "validate_renewal_eligible",
    "RenewalNotEligibleError",
]
