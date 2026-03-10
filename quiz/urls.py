from django.urls import path, include
from . import views

urlpatterns = [
    path("<slug>/quizzes/", views.quiz_list, name="quiz_index"),
    path("progress/", view=views.QuizUserProgressView.as_view(), name="quiz_progress"),
    # path('marking/<int:pk>/', view=QuizMarkingList.as_view(), name='quiz_marking'),
    path("marking_list/", view=views.QuizMarkingList.as_view(), name="quiz_marking"),
    path(
        "marking/<int:pk>/",
        view=views.QuizMarkingDetail.as_view(),
        name="quiz_marking_detail",
    ),
    path("<slug>/take/", view=views.QuizTake.as_view(), name="quiz_take"),
    path("retake/<int:sitting_id>/", views.quiz_retake, name="quiz_retake"),
    path("<slug>/quiz_add/", views.QuizCreateView.as_view(), name="quiz_create"),
    path("<slug>/<int:pk>/add/", views.QuizUpdateView.as_view(), name="quiz_update"),
    path("<slug>/<int:pk>/delete/", views.quiz_delete, name="quiz_delete"),
    path(
        "mc-question/add/<slug>/<int:quiz_id>/",
        views.MCQuestionCreate.as_view(),
        name="mc_create",
    ),
    path('certificado/<int:sitting_id>/', views.generar_certificado, name='generar_certificado'),
    path('descargar-certificados/', views.descargar_tabla_pdf, name='descargar_certificados'),
    path('descargar-multiples/', views.descargar_certificados_multiples, name='descargar_certificados_multiples'),
    path('generar_anexo4/<int:sitting_id>/', views.generar_anexo4, name='generar_anexo4'),
    path('anexo_form/<int:sitting_id>/', views.anexo_form, name='anexo_form'),
    path('buscar-usuarios/', views.buscar_usuarios_ajax, name='buscar_usuarios_ajax'),
    path('buscar-cuestionarios/', views.buscar_cuestionarios_ajax, name='buscar_cuestionarios_ajax'),
    path('approve-renewal/', views.approve_renewal, name='approve_renewal'),

    # Dashboards de certificados
    path('dashboards/', include('quiz.dashboard_urls', namespace='dashboards')),
   
    # path('mc-question/add/<int:pk>/<quiz_pk>/', MCQuestionCreate.as_view(), name='mc_create'),
]
