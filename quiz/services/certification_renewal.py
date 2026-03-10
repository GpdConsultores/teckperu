"""
Servicio de renovación de certificaciones.

Lógica de negocio para:
- Determinar si un usuario puede retomar examen por certificado vencido (renovación anual)
- Obtener el estado del certificado para la UI
- Listar certificados vencidos por estudiante (para el admin)
- Aprobar renovación (acción del admin, una por ciclo de vencimiento)
"""

from typing import Optional, Tuple

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from quiz.models import Sitting, CertificationRenewal
from accounts.models import Student


class RenewalNotEligibleError(Exception):
    """Excepción cuando el estudiante/curso no es elegible para renovación."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _get_latest_approved_sitting_for_course(user, course) -> Optional[Sitting]:
    """Obtiene el Sitting aprobado más reciente para user+course (cualquier quiz)."""
    queryset = (
        Sitting.objects.filter(
            user=user,
            course=course,
            complete=True,
            fecha_aprobacion__isnull=False,
        )
        .select_related("quiz", "course")
        .order_by("-fecha_aprobacion")
    )
    for s in queryset:
        if s.check_if_passed:
            return s
    return None


def _get_latest_approved_sitting(user, quiz, course) -> Optional[Sitting]:
    """Obtiene el Sitting aprobado más reciente para user+quiz+course."""
    queryset = (
        Sitting.objects.filter(
            user=user,
            quiz=quiz,
            course=course,
            complete=True,
            fecha_aprobacion__isnull=False,
        )
        .select_related("quiz", "course")
        .order_by("-fecha_aprobacion")
    )
    for s in queryset:
        if s.check_if_passed:
            return s
    return None


def _has_vigent_renewal(
    student: Student, course, last_sitting: Optional[Sitting] = None
) -> bool:
    """
    Renovación vigente = aprobada después del último certificado emitido.
    Si se provee last_sitting, evita consulta redundante (optimización ORM).
    """
    if last_sitting is None:
        last_sitting = _get_latest_approved_sitting_for_course(student.student, course)

    if not last_sitting or not last_sitting.fecha_aprobacion:
        return False

    return CertificationRenewal.objects.filter(
        student=student,
        course=course,
        approved_at__gt=last_sitting.fecha_aprobacion,
    ).exists()


def _renewals_vigent_for_sittings(
    student: Student, sittings_by_course: dict
) -> set:
    """
    Retorna set de course_ids que tienen renovación vigente.
    Una única consulta para todas las renovaciones del estudiante (evita N+1).
    """
    if not sittings_by_course:
        return set()

    course_ids = list(sittings_by_course.keys())
    renewals = (
        CertificationRenewal.objects.filter(
            student=student,
            course_id__in=course_ids,
        )
        .values_list("course_id", "approved_at")
    )

    vigent_course_ids = set()
    for course_id, approved_at in renewals:
        sitting = sittings_by_course.get(course_id)
        if sitting and sitting.fecha_aprobacion and approved_at > sitting.fecha_aprobacion:
            vigent_course_ids.add(course_id)

    return vigent_course_ids


def validate_renewal_eligible(student: Student, course) -> Tuple[bool, str]:
    """
    Valida que el estudiante sea elegible para renovación en el curso.

    Returns:
        Tuple[bool, str]: (es_elegible, mensaje_error)
    """
    last_sitting = _get_latest_approved_sitting_for_course(student.student, course)
    if not last_sitting:
        return False, _("El trabajador no tiene certificado aprobado para este curso.")

    if not last_sitting.check_if_passed:
        return False, _("El trabajador no ha aprobado este curso.")

    validez = last_sitting.fecha_validez_certificado
    if not validez or validez.date() >= timezone.localdate():
        return False, _("El certificado aún no ha vencido.")

    if _has_vigent_renewal(student, course, last_sitting=last_sitting):
        return False, _("Ya existe una renovación pendiente para este curso.")

    return True, ""


def can_retake_after_expiration(user, quiz, course) -> bool:
    """
    Determina si un usuario puede dar el examen por renovación (certificado vencido
    + renovación vigente aprobada por admin).

    Semántica anual: cada vencimiento requiere nueva aprobación del admin.
    """
    if not getattr(user, "student", None):
        return False

    approved_sitting = _get_latest_approved_sitting(user, quiz, course)
    if not approved_sitting or not approved_sitting.fecha_aprobacion:
        return False

    validez = approved_sitting.fecha_validez_certificado
    if not validez or validez.date() >= timezone.localdate():
        return False

    return _has_vigent_renewal(user.student, course, last_sitting=approved_sitting)


def get_certificate_status(user, sitting) -> dict:
    """
    Estado del certificado para un Sitting aprobado.
    Usado en templates para mostrar indicadores y acciones disponibles.

    Returns:
        dict con: status, expired, can_retake, valid_until
    """
    if not sitting.check_if_passed:
        return {
            "status": "failed",
            "expired": False,
            "can_retake": True,
            "valid_until": None,
        }

    validez = sitting.fecha_validez_certificado
    expired = validez is not None and validez.date() < timezone.localdate()

    if not expired:
        return {
            "status": "valid",
            "expired": False,
            "can_retake": False,
            "valid_until": validez,
        }

    has_renewal = False
    if getattr(user, "student", None):
        has_renewal = _has_vigent_renewal(user.student, sitting.course, last_sitting=sitting)

    return {
        "status": "expired",
        "expired": True,
        "can_retake": has_renewal,
        "valid_until": validez,
    }


def get_expired_certs_for_student(student: Student) -> list:
    """
    Obtiene los cursos del estudiante con certificado vencido que aún no tienen
    renovación vigente. Una aprobación por ciclo de vencimiento (anual).

    Optimizado: una única consulta de renovaciones para evitar N+1.
    """
    from result.models import TakenCourse

    taken_courses = TakenCourse.objects.filter(student=student).values_list(
        "course_id", flat=True
    )
    course_ids = list(taken_courses)

    approved_sittings = (
        Sitting.objects.filter(
            user=student.student,
            course_id__in=course_ids,
            complete=True,
            fecha_aprobacion__isnull=False,
        )
        .select_related("quiz", "course")
        .order_by("course_id", "-fecha_aprobacion")
    )

    by_course = {}
    for s in approved_sittings:
        if s.course_id not in by_course:
            by_course[s.course_id] = s
        elif s.check_if_passed and (
            not by_course[s.course_id].check_if_passed
            or s.fecha_aprobacion > by_course[s.course_id].fecha_aprobacion
        ):
            by_course[s.course_id] = s

    vigent_course_ids = _renewals_vigent_for_sittings(student, by_course)

    expired = []
    for course_id, sitting in by_course.items():
        if not sitting.check_if_passed or course_id in vigent_course_ids:
            continue
        validez = sitting.fecha_validez_certificado
        if validez and validez.date() < timezone.localdate():
            expired.append({
                "course": sitting.course,
                "sitting": sitting,
                "fecha_vencimiento": validez,
            })

    return expired


@transaction.atomic
def approve_renewal(
    student: Student, course, approved_by, notes: str = ""
) -> CertificationRenewal:
    """
    Crea un registro de renovación aprobada (una por ciclo anual de vencimiento).
    Valida elegibilidad antes de crear.

    Raises:
        RenewalNotEligibleError: Si no es elegible para renovación.
    """
    eligible, error_msg = validate_renewal_eligible(student, course)
    if not eligible:
        raise RenewalNotEligibleError(str(error_msg))

    return CertificationRenewal.objects.create(
        student=student,
        course=course,
        approved_by=approved_by,
        notes=notes,
    )
