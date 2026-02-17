"""
Copyright (c) 2025 Alvaro Franco Cerna Ramos
Propiedad Intelectual - Plataforma Educativa Seguridad TECK Perú
Desarrollado exclusivamente para TECK Perú a través de G.P.D. CONSULTORES S.A.C.
Todos los derechos reservados.

Este módulo contiene funcionalidades únicas de generación de certificados PDF
y sistema de anexos personalizados. Prohibida su reproducción o modificación
sin autorización expresa del desarrollador.
"""

import os 
import io
import locale
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape,A4
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.db.models import Max, F, Q
from django.utils.translation import gettext as _ 
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from babel.dates import format_datetime
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from babel.dates import format_datetime
from .models import Sitting 
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .forms import AnexoForm
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.decorators import lecturer_required
from .forms import (
    EssayForm,
    MCQuestionForm,
    MCQuestionFormSet,
    QuestionForm,
    QuizAddForm,
)
from .models import (
    Course,
    EssayQuestion,
    MCQuestion,
    Progress,
    Question,
    Quiz,
    Sitting,
)
from course.models import CourseAllocation
from django.contrib.auth.models import User


# ########################################################
# Quiz Views 
# ########################################################
# def generar_certificado(request, sitting_id):
#     # Ruta de la plantilla de certificado en la carpeta `static/pdfs`
#     plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_template.pdf')

#     # Obtener el examen y validar que el usuario tiene permiso
#     sitting = get_object_or_404(Sitting, id=sitting_id, user=request.user)
    
#     # Verifica la puntuación antes de continuar
#     if sitting.get_percent_correct <= 80:
#         raise Http404("No se puede generar el certificado, la puntuación es menor al 80%.")

#     # Crear un buffer de memoria para el contenido que vamos a superponer
#     buffer = io.BytesIO()
#     p = canvas.Canvas(buffer, pagesize=landscape(A4))
#     ancho_pagina, alto_pagina = landscape(A4)
#     # Añadir el contenido de texto sobre la plantilla
#     # Ajusta la fuente, tamaño y color del texto
#     p.setFont("Helvetica-Bold", 30)  # Aumenta el tamaño de la fuente
#     p.setFillColorRGB(0.85, 0.64, 0.13)  # Color dorado en RGB


#     # Ajusta la posición del texto más abajo y centra el texto
#     p.drawCentredString(ancho_pagina / 2, 315, f"{request.user.first_name} {request.user.last_name}")
#     #p.drawCentredString(300, 370, f"Título del Examen: {sitting.quiz.title}")
#     p.setFillColorRGB(0.051, 0.231, 0.4)
#     p.setFont("Helvetica-Bold", 14)
#     p.drawCentredString(479, 198, f"{int(sitting.get_percent_correct / 5)}")
    
#     #locale.setlocale(locale.LC_TIME, 'es_ES.utf8')
#     #fecha_actual = datetime.now().strftime("%d de %B del %Y")
#     fecha_actual = format_datetime(
#         datetime.now(),
#         "d 'de' MMMM 'del' y",
#         locale='es'
#     )
#      # Formato dd/mm/yyyy
#     p.drawString(585, 220, f"{fecha_actual}")  # Ajusta la posición según sea necesario

#     p.setFont("Helvetica", 16)
#     p.setFillColorRGB(0.051, 0.231, 0.4)  # Color negro
#     p.drawString(485, 273, f"{request.user.username}")  

#     # Finalizar el contenido del buffer
#     p.showPage()
#     p.save()
#     buffer.seek(0)

#     # Cargar la plantilla de certificado
#     plantilla_pdf = PdfReader(plantilla_path)
#     pagina_plantilla = plantilla_pdf.pages[0]

#     # Crear un nuevo PDF con la plantilla y el contenido superpuesto
#     contenido_pdf = PdfReader(buffer)
#     writer = PdfWriter()
    
#     # Superponer la plantilla y el contenido nuevo
#     pagina_plantilla.merge_page(contenido_pdf.pages[0])
#     writer.add_page(pagina_plantilla)

#     # Guardar el PDF combinado en un nuevo buffer
#     resultado = io.BytesIO()
#     writer.write(resultado)
#     resultado.seek(0)

#     # Devolver el PDF combinado como respuesta
#     return FileResponse(resultado, as_attachment=True, filename='certificado.pdf')

# views.py

# views.py

# views.py

@login_required
def generar_certificado(request, sitting_id):
    # Ruta de la plantilla de certificado en la carpeta `static/pdfs`
    plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_template.pdf')

    # Obtener el examen
    sitting = get_object_or_404(Sitting, id=sitting_id)
    
    # Validar permisos: el usuario puede ser el estudiante o un instructor del curso
    if request.user != sitting.user:
        # Si no es el estudiante, verificar que sea instructor del curso
        if not request.user.is_superuser:
            # Verificar que el instructor tenga asignado este curso
            has_permission = CourseAllocation.objects.filter(
                lecturer=request.user,
                courses=sitting.quiz.course
            ).exists()
            
            if not has_permission:
                raise Http404("No tienes permisos para acceder a este certificado.")

    # Verifica la puntuación antes de continuar (opcional, comentado)
    # if sitting.get_percent_correct <= 80:
    #     raise Http404("No se puede generar el certificado, la puntuación es menor al 80%.")

    # Datos comunes - usar los datos del estudiante, no del usuario actual
    nombre_estudiante = f"{sitting.user.first_name} {sitting.user.last_name}"
    puntaje = int(sitting.get_percent_correct / 5)
    fecha_aprobacion_formateada = obtener_fecha_aprobacion(sitting)
    nombre_usuario = sitting.user.username
    certificate_code = sitting.certificate_code

    # Determinar la plantilla de certificado según el código del curso
    if sitting.quiz.course.code == "0001":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0001.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 305
        pos_puntaje = (728, 188)
        pos_fecha = (140, 188)
        pos_nombre_usuario = (525, 263)
        pos_codigo_certificado = (679, 466)
    elif sitting.quiz.course.code == "0002":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0002.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 305
        pos_puntaje = (138, 167)
        pos_fecha = (230, 188) 
        pos_nombre_usuario = (525, 263)
        pos_codigo_certificado = (679, 466)
    elif sitting.quiz.course.code == "0003":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0003.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 305
        pos_puntaje = (738, 188)
        pos_fecha = (110, 188)
        pos_nombre_usuario = (525, 263)
        pos_codigo_certificado = (679, 466)
    elif sitting.quiz.course.code == "0004":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0004.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 305
        pos_puntaje = (329, 188)
        pos_fecha = (397, 210)
        pos_nombre_usuario = (525, 263)
        pos_codigo_certificado = (679, 466)
    elif sitting.quiz.course.code == "0005":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0005.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 305
        pos_puntaje = (702, 190)
        pos_fecha = (111, 190)
        pos_nombre_usuario = (525, 263)
        pos_codigo_certificado = (679, 466)
    elif sitting.quiz.course.code == "0006":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0006.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 305
        pos_puntaje = (463, 184)
        pos_fecha = (561, 206)
        pos_nombre_usuario = (525, 263)
        pos_codigo_certificado = (679, 466)
    elif sitting.quiz.course.code == "0007":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0007.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 305
        pos_puntaje = (331, 183)
        pos_fecha = (380, 205)
        pos_nombre_usuario = (525, 263)
        pos_codigo_certificado = (679, 466)
    elif sitting.quiz.course.code == "0008":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0008.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 305
        pos_puntaje = (329, 183)
        pos_fecha = (461, 205)
        pos_nombre_usuario = (525, 263)
        pos_codigo_certificado = (679, 466)
    elif sitting.quiz.course.code == "0009":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0009.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 305
        pos_puntaje = (465, 184.5)
        pos_fecha = (565, 206)
        pos_nombre_usuario = (525, 263)
        pos_codigo_certificado = (679, 466)
    elif sitting.quiz.course.code == "0010":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0010.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 285
        pos_puntaje = (472, 164)
        pos_fecha = (450, 195.5)
        pos_nombre_usuario = (525, 252)
        pos_codigo_certificado = (680, 454.5)
    elif sitting.quiz.course.code == "0011":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0011.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 285
        pos_puntaje = (106.5, 152.5)
        pos_fecha = (100, 172.5)
        pos_nombre_usuario = (525, 252)
        pos_codigo_certificado = (680, 454.5)
    elif sitting.quiz.course.code == "0012":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0012.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 285
        pos_puntaje = (471.5, 164)
        pos_fecha = (505, 194)
        pos_nombre_usuario = (525, 252)
        pos_codigo_certificado = (680, 454.5)
    elif sitting.quiz.course.code == "0013":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0013.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 285
        pos_puntaje = (471.5, 172.5)
        pos_fecha = (606, 193.5)
        pos_nombre_usuario = (525, 252)
        pos_codigo_certificado = (680, 454.5)
    elif sitting.quiz.course.code == "0014":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0014.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 285
        pos_puntaje = (700.5, 164)
        pos_fecha = (95, 164)
        pos_nombre_usuario = (525, 252)
        pos_codigo_certificado = (680, 454.5)
    elif sitting.quiz.course.code == "0015":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0015.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 285
        pos_puntaje = (108.5, 164)
        pos_fecha = (185, 186)
        pos_nombre_usuario = (525, 252)
        pos_codigo_certificado = (680, 454.5)
    elif sitting.quiz.course.code == "0016":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0016.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 285
        pos_puntaje = (473, 185.5)
        pos_fecha = (577, 207)
        pos_nombre_usuario = (525, 252)
        pos_codigo_certificado = (680, 454.5)
    elif sitting.quiz.course.code == "0017":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0017.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 285
        pos_puntaje = (338.5, 186)
        pos_fecha = (385, 206.5)
        pos_nombre_usuario = (525, 252)
        pos_codigo_certificado = (680, 454.5)
    elif sitting.quiz.course.code == "0018":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0018.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 285
        pos_puntaje = (412, 185.5)
        pos_fecha = (495, 207)
        pos_nombre_usuario = (525, 252)
        pos_codigo_certificado = (680, 454.5)
    elif sitting.quiz.course.code == "0019":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0019.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 285
        pos_puntaje = (472, 164)
        pos_fecha = (450, 195.5)
        pos_nombre_usuario = (525, 252)
        pos_codigo_certificado = (680, 454.5)
    elif sitting.quiz.course.code == "0020":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0020.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 285
        pos_puntaje = (472, 164)
        pos_fecha = (450, 195.5)
        pos_nombre_usuario = (525, 252)
        pos_codigo_certificado = (680, 454.5)
    elif sitting.quiz.course.code == "0021":
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_0021.pdf')
        # Personalización de posiciones para este curso
        pos_nombre_estudiante = 285
        pos_puntaje = (412, 185.5)
        pos_fecha = (495, 207)
        pos_nombre_usuario = (525, 252)
        pos_codigo_certificado = (680, 454.5)
    else:
        plantilla_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'certificado_default.pdf')
        pos_nombre_estudiante = 430
        pos_puntaje = (479, 198)
        pos_fecha = (585, 220)
        pos_nombre_usuario = (485, 273)
    

    # Crear un buffer de memoria para el contenido que vamos a superponer
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    ancho_pagina, alto_pagina = landscape(A4)

    # Mantenemos los mismos colores y valores que usas en tu plantilla original
    p.setFont("Helvetica-Bold", 30)
    p.setFillColorRGB(0.85, 0.64, 0.13)  # Color dorado (como en tu plantilla original)
    
    # Centrar el nombre del estudiante en el eje X
    p.drawCentredString(ancho_pagina / 2, pos_nombre_estudiante, nombre_estudiante)

    # Puntaje, fecha y nombre de usuario con posiciones fijas en ambos ejes
    p.setFillColorRGB(0.051, 0.231, 0.4)  # Color azul (como en tu plantilla original)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(pos_puntaje[0], pos_puntaje[1], f"{puntaje}")

    # Fecha
    p.setFont("Helvetica", 16)
    p.setFillColorRGB(0.051, 0.231, 0.4)  # Color azul (como en tu plantilla original)
    p.drawString(pos_fecha[0], pos_fecha[1], f"{fecha_aprobacion_formateada}")

    # Nombre de usuario
    p.setFont("Helvetica", 16)
    p.setFillColorRGB(0.051, 0.231, 0.4)  # Color azul (como en tu plantilla original)
    p.drawString(pos_nombre_usuario[0], pos_nombre_usuario[1], f"{nombre_usuario}")

    # Código del certificado
    p.setFont("Helvetica-Bold", 16)
    p.setFillColorRGB(0.051, 0.231, 0.4)  # Color azul (como en tu plantilla original)
    p.drawString(pos_codigo_certificado[0], pos_codigo_certificado[1], f"{certificate_code}")

    # Finalizar el contenido del buffer
    p.showPage()
    p.save()
    buffer.seek(0)

    # Cargar la plantilla del certificado
    plantilla_pdf = PdfReader(plantilla_path)
    pagina_plantilla = plantilla_pdf.pages[0]

    # Crear un nuevo PDF con la plantilla y el contenido superpuesto
    contenido_pdf = PdfReader(buffer)
    writer = PdfWriter()
    pagina_plantilla.merge_page(contenido_pdf.pages[0])
    writer.add_page(pagina_plantilla)

    # Guardar el PDF combinado en un nuevo buffer
    resultado = io.BytesIO()
    writer.write(resultado)
    resultado.seek(0)

    # Devolver el PDF combinado como respuesta
    return FileResponse(resultado, as_attachment=True, filename='certificado.pdf')
    
def anexo_form(request, sitting_id):
    if request.method == 'POST':
        form = AnexoForm(request.POST)
        if form.is_valid():
            # Obtener los datos del formulario
            fecha_ingreso = form.cleaned_data['fecha_ingreso']
            ocupacion = form.cleaned_data['ocupacion']
            area_trabajo = form.cleaned_data['area_trabajo']
            empresa = form.cleaned_data['empresa']  # Nuevo campo
            distrito = form.cleaned_data['distrito']  # Nuevo campo
            provincia = form.cleaned_data['provincia']  # Nuevo campo

            # Generar el anexo con los datos del formulario
            return generar_anexo4(request, sitting_id, fecha_ingreso, ocupacion, area_trabajo, empresa, distrito, provincia)
    else:
        # Si no es POST, redirigir a la página de progreso
        return redirect('quiz_progress')

    # Esta línea nunca se ejecutará, pero la mantenemos por seguridad
    return redirect('quiz_progress')

def generar_anexo4(request, sitting_id, fecha_ingreso, ocupacion, area_trabajo, empresa, distrito, provincia):
    # Obtener el examen y validar que el usuario tiene permiso
    sitting = get_object_or_404(Sitting, id=sitting_id, user=request.user)

    # Obtener la fecha de aprobación
    fecha_aprobacion = obtener_fecha_aprobacion(sitting)

 
    # Ruta del anexo
    anexo_path = os.path.join(settings.BASE_DIR, 'static', 'pdfs', 'anexo4.pdf')

    # Crear un buffer para el anexo
    buffer_anexo = io.BytesIO()
    p_anexo = canvas.Canvas(buffer_anexo, pagesize=A4)  # Cambiar a A4 para orientación vertical
    ancho_pagina_anexo, alto_pagina_anexo = A4  # Obtener dimensiones de A4 en vertical

    # Personaliza el contenido del anexo
    p_anexo.setFont("Helvetica", 11)  # Cambiar a un tamaño de fuente más pequeño
    p_anexo.setFillColorRGB(0, 0, 0)  # Color negro

    #mifuente nueva para firmas
    pdfmetrics.registerFont(TTFont('MiFuenteCursiva', os.path.join(settings.BASE_DIR, 'static', 'fonts', 'MiFuenteCursiva.ttf')))

    # Dibujar el nombre del usuario
    p_anexo.drawString(370, alto_pagina_anexo - 150, f"{sitting.user.first_name} {sitting.user.last_name}")
    
    # Dibujar el DNI (nombre de usuario)
    p_anexo.drawString(475, alto_pagina_anexo - 193, f"{sitting.user.username}")

    # Agregar los datos del formulario
    p_anexo.drawString(403, alto_pagina_anexo - 171.5, f"{fecha_ingreso}")
    p_anexo.drawString(379, alto_pagina_anexo - 213, f"{ocupacion}")
    p_anexo.drawString(400, alto_pagina_anexo - 233.5, f"{area_trabajo}")

    # Agregar los nuevos datos
    p_anexo.drawString(126.5, alto_pagina_anexo -171.5, f"{empresa}")
    p_anexo.drawString(68.2, alto_pagina_anexo - 214, f"{distrito}")
    p_anexo.drawString(79, alto_pagina_anexo - 235, f"{provincia}")
    
    # Agregar la fecha de aprobación sin formatear
    p_anexo.drawString(391, alto_pagina_anexo - 641, f"{fecha_aprobacion}")

    # Usar la fuente personalizada para la firma
    p_anexo.setFont("MiFuenteCursiva", 8)  # Reducir el tamaño de la fuente de 10 a 8
    p_anexo.drawString(55, 115, f"{sitting.user.first_name} {sitting.user.last_name}")  # Mover más a la izquierda (de 69 a 55)

    # Finalizar el contenido del buffer del anexo
    p_anexo.showPage()
    p_anexo.save()
    buffer_anexo.seek(0)

    # Cargar el anexo
    anexo_pdf = PdfReader(anexo_path)
    pagina_anexo = anexo_pdf.pages[0]

    # Crear un nuevo PDF con el contenido del anexo
    contenido_anexo_pdf = PdfReader(buffer_anexo)
    writer_anexo = PdfWriter()
    pagina_anexo.merge_page(contenido_anexo_pdf.pages[0])
    writer_anexo.add_page(pagina_anexo)

    # Guardar el PDF combinado en un nuevo buffer
    resultado_anexo = io.BytesIO()
    writer_anexo.write(resultado_anexo)
    resultado_anexo.seek(0)

    # Devolver el PDF del anexo como respuesta
    return FileResponse(resultado_anexo, as_attachment=True, filename='anexo4.pdf')



def obtener_fecha_aprobacion(exam):
    # Obtener la fecha de aprobación
    fecha_aprobacion = exam.fecha_aprobacion

    # Crear un diccionario para los nombres de los meses
    meses = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre"
    }

    # Formatear el día con un cero delante si es necesario
    dia = f"{fecha_aprobacion.day:02d}"  # Formato con cero delante
    mes = meses[fecha_aprobacion.month]  # Obtener el nombre del mes
    año = fecha_aprobacion.year

    # Crear el string formateado
    return f"{dia} de {mes} del {año}"

def descargar_tabla_pdf(request):
    # Obtener todos los exámenes aprobados por el usuario
    exams = Sitting.objects.filter(user=request.user, fecha_aprobacion__isnull=False)

    if not exams.exists():
        return HttpResponse(_("No hay certificados para descargar."), status=404)

    # Crear un buffer de memoria
    buffer = io.BytesIO()

    # Configurar el documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []

    # Estilos para el PDF
    styles = getSampleStyleSheet()
    title = Paragraph(_("Consolidado de cursos aprobados"), styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Encabezados de la tabla
    data = [
        [
            _("Nombre del curso"),
            _("Puntuación Obtenida"),
            _("Puntuación Máxima"),
            _("Porcentaje"),
            _("Estado de Registro"),
            _("Fecha de Aprobación"),
        ]
    ]

    # Rellenar los datos de la tabla
    latest_exams = exams.values('quiz').annotate(max_score=Max('current_score'))

    for exam_data in latest_exams:
        # Obtener el último examen aprobado para ese curso
        exam = exams.filter(quiz_id=exam_data['quiz'], current_score=exam_data['max_score']) \
                    .order_by('-fecha_aprobacion').first()  # Si hay varios con la misma puntuación, tomamos el más reciente

        if exam:
            # Usar la función auxiliar para obtener la fecha de aprobación formateada
            fecha_aprobacion = obtener_fecha_aprobacion(exam)

            estado_registro = _("Curso completado") if exam.get_percent_correct >= 80 else _("En progreso")

            data.append([
                exam.quiz.title,
                2 * exam.current_score,
                2 * exam.get_max_score,
                f"{exam.get_percent_correct}%",
                estado_registro,
                fecha_aprobacion
            ])

    # Crear la tabla
    table = Table(data, repeatRows=1)

    # Definir los colores personalizados
    primary_color = colors.HexColor("#BA6022")  # Color principal
    white = colors.white
    black = colors.black
    light_grey = colors.HexColor("#f2f2f2")    # Para filas alternas o resaltes

    # Estilo de la tabla
    style = TableStyle([
        # Estilo del encabezado
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
 ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

        # Estilo de las filas de datos
        ('BACKGROUND', (0, 1), (-1, -1), white),
        ('TEXTCOLOR', (0, 1), (-1, -1), black),
        ('GRID', (0, 0), (-1, -1), 0.5, black),

        # Agregar alternancia de colores para mejorar la legibilidad
        ('BACKGROUND', (0, 1), (-1, -1), white),
    ])

    # Aplicar estilos condicionales
    for i, exam in enumerate(exams, start=1):
        porcentaje = exam.get_percent_correct

        # Resaltar filas con porcentaje >= 80% en color principal con texto blanco
        if porcentaje >= 80:
            style.add('BACKGROUND', (0, i), (-1, i), primary_color)
            style.add('TEXTCOLOR', (0, i), (-1, i), white)
        # Puedes añadir más condiciones si lo deseas
    table.setStyle(style)

    # Añadir la tabla al contenido
    elements.append(table)

    # Construir el PDF
    doc.build(elements)

    # Preparar la respuesta
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='consolidado.pdf')


@method_decorator([login_required, lecturer_required], name="dispatch")
class QuizCreateView(CreateView):
    model = Quiz
    form_class = QuizAddForm
    template_name = "quiz/quiz_form.html"

    def get_initial(self):
        initial = super().get_initial()
        course = get_object_or_404(Course, slug=self.kwargs["slug"])
        initial["course"] = course
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = get_object_or_404(Course, slug=self.kwargs["slug"])
        return context

    def form_valid(self, form):
        form.instance.course = get_object_or_404(Course, slug=self.kwargs["slug"])
        with transaction.atomic():
            self.object = form.save()
            return redirect(
                "mc_create", slug=self.kwargs["slug"], quiz_id=self.object.id
            )


@method_decorator([login_required, lecturer_required], name="dispatch")
class QuizUpdateView(UpdateView):
    model = Quiz
    form_class = QuizAddForm
    template_name = "quiz/quiz_form.html"

    def get_object(self, queryset=None):
        return get_object_or_404(Quiz, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = get_object_or_404(Course, slug=self.kwargs["slug"])
        return context

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            return redirect("quiz_index", self.kwargs["slug"])


@login_required
@lecturer_required
def quiz_delete(request, slug, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    quiz.delete()
    messages.success(request, "Quiz successfully deleted.")
    return redirect("quiz_index", slug=slug)


@login_required
def quiz_list(request, slug):
    course = get_object_or_404(Course, slug=slug)
    quizzes = Quiz.objects.filter(course=course).order_by("-timestamp")
    
    # Para estudiantes, añadir información sobre el estado de aprobación
    if request.user.is_student:
        for quiz in quizzes:
            # Buscar todos los intentos completados para este examen
            completed_sittings = Sitting.objects.filter(
                user=request.user,
                quiz=quiz,
                course=course,
                complete=True
            ).order_by('-end')
            
            if completed_sittings.exists():
                # Buscar primero un intento aprobado
                approved_sitting = None
                latest_sitting = None
                
                for sitting in completed_sittings:
                    if latest_sitting is None:
                        latest_sitting = sitting
                    
                    if sitting.check_if_passed:
                        approved_sitting = sitting
                        break
                
                # Usar el aprobado si existe, sino el más reciente
                if approved_sitting:
                    quiz.user_status = "approved"
                    quiz.user_sitting = approved_sitting
                else:
                    quiz.user_status = "failed"
                    quiz.user_sitting = latest_sitting
            else:
                quiz.user_status = "not_attempted"
                quiz.user_sitting = None
    
    return render(
        request, "quiz/quiz_list.html", {"quizzes": quizzes, "course": course}
    )


# ########################################################
# Multiple Choice Question Views
# ########################################################


@method_decorator([login_required, lecturer_required], name="dispatch")
class MCQuestionCreate(CreateView):
    model = MCQuestion
    form_class = MCQuestionForm
    template_name = "quiz/mcquestion_form.html"

    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()
    #     kwargs["quiz"] = get_object_or_404(Quiz, id=self.kwargs["quiz_id"])
    #     return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = get_object_or_404(Course, slug=self.kwargs["slug"])
        context["quiz_obj"] = get_object_or_404(Quiz, id=self.kwargs["quiz_id"])
        context["quiz_questions_count"] = Question.objects.filter(
            quiz=self.kwargs["quiz_id"]
        ).count()
        if self.request.method == "POST":
            context["formset"] = MCQuestionFormSet(self.request.POST)
        else:
            context["formset"] = MCQuestionFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            with transaction.atomic():
                # Save the MCQuestion instance without committing to the database yet
                self.object = form.save(commit=False)
                self.object.save()

                # Retrieve the Quiz instance
                quiz = get_object_or_404(Quiz, id=self.kwargs["quiz_id"])

                # set the many-to-many relationship
                self.object.quiz.add(quiz)

                # Save the formset (choices for the question)
                formset.instance = self.object
                formset.save()

                if "another" in self.request.POST:
                    return redirect(
                        "mc_create",
                        slug=self.kwargs["slug"],
                        quiz_id=self.kwargs["quiz_id"],
                    )
                return redirect("quiz_index", slug=self.kwargs["slug"])
        else:
            return self.form_invalid(form)


# ########################################################
# Quiz Progress and Marking Views
# ########################################################


@method_decorator([login_required], name="dispatch")
class QuizUserProgressView(TemplateView):
    template_name = "quiz/progress.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        progress, _ = Progress.objects.get_or_create(user=self.request.user)
        context["cat_scores"] = progress.list_all_cat_scores
        context["exams"] = progress.show_all_exams()
        context["exams_counter"] = len(context["exams"])
        return context


@method_decorator([login_required, lecturer_required], name="dispatch")
class QuizMarkingList(ListView):
    model = Sitting
    template_name = "quiz/sitting_list.html"
    paginate_by = 10  # Mostrar 10 exámenes por página
    context_object_name = 'sitting_list'

    def get_queryset(self):
        queryset = Sitting.objects.filter(complete=True).select_related(
            'user', 'quiz', 'course'
        ).order_by('-end')
        
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                quiz__course__allocated_course__lecturer__pk=self.request.user.id
            )
        
        # Filtros de búsqueda
        quiz_filter = self.request.GET.get("quiz_filter")
        if quiz_filter:
            # Buscar por título y descripción del cuestionario
            queryset = queryset.filter(
                Q(quiz__title__icontains=quiz_filter) |
                Q(quiz__description__icontains=quiz_filter) |
                Q(quiz__course__title__icontains=quiz_filter)
            )
        
        user_filter = self.request.GET.get("user_filter")
        if user_filter:
            # Buscar por nombre completo, apellido y username
            queryset = queryset.filter(
                Q(user__first_name__icontains=user_filter) |
                Q(user__last_name__icontains=user_filter) |
                Q(user__username__icontains=user_filter) |
                Q(user__email__icontains=user_filter)
            )
        
        # Filtro por fecha
        date_filter = self.request.GET.get("date_filter")
        if date_filter:
            queryset = queryset.filter(end__date=date_filter)
        
        # Filtro por porcentaje mínimo
        min_score = self.request.GET.get("min_score")
        if min_score and min_score.isdigit():
            min_score = int(min_score)
            # Convertir a lista para filtrar por porcentaje
            queryset = [s for s in queryset if s.get_percent_correct >= min_score]
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Agregar estadísticas
        queryset = self.get_queryset()
        
        # Manejar tanto QuerySet como lista
        if isinstance(queryset, list):
            # Es una lista
            context['total_exams'] = len(queryset)
        else:
            # Es un QuerySet
            context['total_exams'] = queryset.count()
        
        # Contar exámenes aprobados usando el método check_if_passed
        passed_count = 0
        failed_count = 0
        total_score = 0
        total_possible = 0
        certificates_generated = 0
        certificates_available = 0
        
        for sitting in queryset:
            if sitting.check_if_passed:
                passed_count += 1
            else:
                failed_count += 1
            
            # Contar certificados
            if sitting.certificate_code:
                certificates_generated += 1
                if sitting.check_if_passed:
                    certificates_available += 1
            
            total_score += sitting.current_score
            total_possible += sitting.get_max_score
        
        context['passed_exams'] = passed_count
        context['failed_exams'] = failed_count
        context['certificates_generated'] = certificates_generated
        context['certificates_available'] = certificates_available
        
        # Calcular promedio de puntuación
        if context['total_exams'] > 0 and total_possible > 0:
            context['average_score'] = round((total_score / total_possible) * 100, 2)
        else:
            context['average_score'] = 0
        
        # Mantener los filtros en la paginación
        context['current_filters'] = {
            'quiz_filter': self.request.GET.get("quiz_filter", ""),
            'user_filter': self.request.GET.get("user_filter", ""),
            'date_filter': self.request.GET.get("date_filter", ""),
            'min_score': self.request.GET.get("min_score", ""),
        }
        
        # Agregar lista de cursos disponibles para el filtro
        if self.request.user.is_superuser:
            # Administrador ve todos los cursos
            available_courses = Course.objects.filter(is_active=True).order_by('title')
            # print(f"SUPERUSER - Cursos totales: {available_courses.count()}")
        else:
            # Instructor ve solo sus cursos asignados - usar la misma lógica que la tabla
            available_courses = Course.objects.filter(
                allocated_course__lecturer__pk=self.request.user.id,
                is_active=True
            ).distinct().order_by('title')
            # print(f"INSTRUCTOR - Usuario: {self.request.user.username}")
            # print(f"INSTRUCTOR - ID: {self.request.user.id}")
            # print(f"INSTRUCTOR - Cursos encontrados: {available_courses.count()}")
            
            # Debug adicional: verificar si hay asignaciones
            allocations = CourseAllocation.objects.filter(lecturer=self.request.user)
            # print(f"INSTRUCTOR - Asignaciones totales: {allocations.count()}")
            for alloc in allocations:
                # Manejar tanto QuerySet como lista para alloc.courses
                if isinstance(alloc.courses, list):
                    courses_count = len(alloc.courses)
                else:
                    courses_count = alloc.courses.count()
                # print(f"  - Asignación {alloc.id}: {courses_count} cursos")
                for course in alloc.courses.all():
                    # print(f"    * {course.title} ({course.code}) - Activo: {course.is_active}")
                    pass
        
        # Debug final
        # print(f"CURSOS FINALES: {available_courses.count()}")
        for course in available_courses:
            # print(f"  - {course.title} ({course.code})")
            pass
        
        context['available_courses'] = available_courses
        
        return context


@method_decorator([login_required, lecturer_required], name="dispatch")
class QuizMarkingDetail(DetailView):
    model = Sitting
    template_name = "quiz/quiz_marking_detail.html"

    def post(self, request, *args, **kwargs):
        sitting = self.get_object()
        question_id = request.POST.get("qid")
        if question_id:
            question = Question.objects.get_subclass(id=int(question_id))
            if int(question_id) in sitting.get_incorrect_questions:
                sitting.remove_incorrect_question(question)
            else:
                sitting.add_incorrect_question(question)
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["questions"] = self.object.get_questions(with_answers=True)
        return context


# ########################################################
# Quiz Taking View
# ########################################################


@method_decorator([login_required], name="dispatch")
class QuizTake(FormView):
    form_class = QuestionForm
    template_name = "quiz/question.html"
    result_template_name = "quiz/result.html"

    def dispatch(self, request, *args, **kwargs):
        self.quiz = get_object_or_404(Quiz, slug=self.kwargs["slug"])
        self.course = self.quiz.course  # Obtener el curso directamente del examen
        if not Question.objects.filter(quiz=self.quiz).exists():
            messages.warning(request, "Este examen no tiene preguntas disponibles")
            return redirect("quiz_index", slug=self.course.slug)

        # Verificar si el usuario ya aprobó este examen
        if request.user.is_student:
            approved_sitting = Sitting.objects.filter(
                user=request.user,
                quiz=self.quiz,
                course=self.course,
                complete=True
            ).first()
            
            if approved_sitting and approved_sitting.check_if_passed:
                messages.info(
                    request,
                    "Ya has aprobado este examen. No puedes volver a tomarlo.",
                )
                return redirect("quiz_index", slug=self.course.slug)

        self.sitting = Sitting.objects.user_sitting(
            request.user, self.quiz, self.course
        )
        if not self.sitting:
            messages.info(
                request,
                "Ya has completado este cuestionario. Solo se permite un intento.",
            )
            return redirect("quiz_index", slug=self.course.slug)

        # Set self.question and self.progress here
        self.question = self.sitting.get_first_question()
        self.progress = self.sitting.progress()

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["question"] = self.question
        return kwargs

    def get_form_class(self):
        if isinstance(self.question, EssayQuestion):
            return EssayForm
        return self.form_class

    def form_valid(self, form):
        self.form_valid_user(form)
        if not self.sitting.get_first_question():
            return self.final_result_user()
        return super().get(self.request)

    def form_valid_user(self, form):
        progress, _ = Progress.objects.get_or_create(user=self.request.user)
        guess = form.cleaned_data["answers"]
        is_correct = self.question.check_if_correct(guess)

        if is_correct:
            self.sitting.add_to_score(1)
            progress.update_score(self.question, 1, 1)
        else:
            self.sitting.add_incorrect_question(self.question)
            progress.update_score(self.question, 0, 1)

        if not self.quiz.answers_at_end:
            self.previous = {
                "previous_answer": guess,
                "previous_outcome": is_correct,
                "previous_question": self.question,
                "answers": self.question.get_choices(),
                "question_type": {self.question.__class__.__name__: True},
            }
        else:
            self.previous = {}

        self.sitting.add_user_answer(self.question, guess)
        self.sitting.remove_first_question()

        # Update self.question and self.progress for the next question
        self.question = self.sitting.get_first_question()
        self.progress = self.sitting.progress()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["question"] = self.question
        context["quiz"] = self.quiz
        context["course"] = self.course
        if hasattr(self, "previous"):
            context["previous"] = self.previous
        if hasattr(self, "progress"):
            context["progress"] = self.progress
        return context

    def final_result_user(self):
        self.sitting.mark_quiz_complete()
        results = {
            "course": self.course,
            "quiz": self.quiz,
            "score": self.sitting.get_current_score,
            "max_score": self.sitting.get_max_score,
            "percent": self.sitting.get_percent_correct,  # Llama al método con paréntesis
            "sitting": self.sitting,
            "previous": getattr(self, "previous", {}),
        }

        if self.quiz.answers_at_end:
            results["questions"] = self.sitting.get_questions(with_answers=True)
            results["incorrect_questions"] = self.sitting.get_incorrect_questions

        if (
            not self.quiz.exam_paper
            or self.request.user.is_superuser
            or self.request.user.is_lecturer
        ):
            self.sitting.delete()

        return render(self.request, self.result_template_name, results)

@login_required
@lecturer_required
def descargar_certificados_multiples(request):
    """Descargar múltiples certificados como archivo ZIP"""
    from zipfile import ZipFile
    from io import BytesIO
    
    # Obtener los IDs de los certificados a descargar
    sitting_ids = request.GET.getlist('sitting_ids')
    if not sitting_ids:
        messages.error(request, "No se seleccionaron certificados para descargar.")
        return redirect('quiz_marking')
    
    # Crear un archivo ZIP en memoria
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zip_file:
        for sitting_id in sitting_ids:
            try:
                sitting = Sitting.objects.get(id=sitting_id)
                
                # Verificar permisos del instructor
                if not request.user.is_superuser:
                    if not CourseAllocation.objects.filter(
                        lecturer=request.user,
                        courses=sitting.quiz.course
                    ).exists():
                        continue
                
                # Generar el certificado individual
                if sitting.certificate_code and sitting.check_if_passed:
                    # Aquí reutilizaríamos la lógica de generar_certificado
                    # Por simplicidad, creamos un archivo de texto con la información
                    cert_info = f"""
Certificado: {sitting.certificate_code}
Estudiante: {sitting.user.get_full_name()}
Curso: {sitting.quiz.course.title}
Puntuación: {sitting.get_percent_correct}%
Fecha: {sitting.end.strftime('%d/%m/%Y') if sitting.end else 'N/A'}
                    """.strip()
                    
                    filename = f"certificado_{sitting.certificate_code}_{sitting.user.username}.txt"
                    zip_file.writestr(filename, cert_info)
                    
            except Sitting.DoesNotExist:
                continue
    
    zip_buffer.seek(0)
    
    # Devolver el archivo ZIP
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="certificados.zip"'
    return response

@login_required
@lecturer_required
def buscar_usuarios_ajax(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        query = request.GET.get('q', '')
        if len(query) >= 2:
            users = User.objects.filter(
                Q(first_name__icontains=query) | 
                Q(last_name__icontains=query) | 
                Q(username__icontains=query)
            )[:10]
            data = [{'id': user.id, 'text': f"{user.first_name} {user.last_name} ({user.username})"} for user in users]
            return JsonResponse({'results': data})
    return JsonResponse({'results': []})

@login_required
def quiz_retake(request, sitting_id):
    """
    Vista para permitir a un usuario reintentar un examen que no ha aprobado.
    Crea un nuevo intento (Sitting) y redirige al usuario al examen.
    """
    # Obtener el intento fallido
    previous_sitting = get_object_or_404(Sitting, id=sitting_id, user=request.user)
    
    # Verificar si ya existe un intento aprobado para este examen
    approved_sitting = Sitting.objects.filter(
        user=request.user,
        quiz=previous_sitting.quiz,
        course=previous_sitting.course,
        complete=True
    ).first()
    
    # Verificar si el intento encontrado está aprobado
    if approved_sitting and approved_sitting.check_if_passed:
        messages.error(request, "No puedes reintentar un examen que ya has aprobado.")
        return redirect('quiz_progress')
    
    # Verificar que el examen no sea de un solo intento
    if previous_sitting.quiz.single_attempt:
        messages.error(request, "Este examen solo permite un intento.")
        return redirect('quiz_progress')
    
    # Verificar si ya existe un Sitting incompleto para este usuario y examen
    existing_sitting = Sitting.objects.filter(
        user=request.user,
        quiz=previous_sitting.quiz,
        course=previous_sitting.course,
        complete=False
    ).first()
    
    if existing_sitting:
        # Si ya existe un intento incompleto, usar ese
        sitting_to_use = existing_sitting
    else:
        # Crear un nuevo intento usando el método del manager
        sitting_to_use = Sitting.objects.new_sitting(
            user=request.user,
            quiz=previous_sitting.quiz,
            course=previous_sitting.course
        )
    
    # Redirigir al usuario al inicio del intento
    return redirect('quiz_take', slug=previous_sitting.quiz.slug)

@login_required
@lecturer_required
def buscar_cuestionarios_ajax(request):
    """Vista AJAX para búsqueda de cuestionarios en tiempo real"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:  # Mínimo 2 caracteres para buscar
        return JsonResponse({'cuestionarios': []})
    
    # Obtener cuestionarios que tienen exámenes completados
    if request.user.is_superuser:
        # Administrador ve todos los cuestionarios
        cuestionarios = Quiz.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(course__title__icontains=query),
            sitting__complete=True
        ).distinct().values('id', 'title', 'description', 'course__title', 'course__code')[:10]
    else:
        # Instructor ve solo cuestionarios de sus cursos asignados
        cuestionarios = Quiz.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(course__title__icontains=query),
            sitting__complete=True,
            course__allocated_course__lecturer=request.user
        ).distinct().values('id', 'title', 'description', 'course__title', 'course__code')[:10]
    
    # Formatear resultados
    resultados = []
    for cuestionario in cuestionarios:
        descripcion = cuestionario['description'] or ''
        if len(descripcion) > 50:
            descripcion = descripcion[:50] + '...'
        
        resultados.append({
            'id': cuestionario['id'],
            'titulo': cuestionario['title'],
            'descripcion': descripcion,
            'curso': cuestionario['course__title'],
            'codigo_curso': cuestionario['course__code'],
            'texto_busqueda': f"{cuestionario['title']} - {cuestionario['course__title']}"
        })
    
    return JsonResponse({'cuestionarios': resultados})
