from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/estado/', views.api_estado_sistema, name='api_estado'),
    path('api/solicitar/', views.api_solicitar_reunion, name='api_solicitar'),
    path('api/interprete/<int:interprete_id>/toggle/', views.api_toggle_interprete, name='api_toggle_interprete'),
    path('api/atender/<int:sesion_id>/', views.api_atender_solicitud, name='api_atender'),
    path('api/finalizar/<int:sesion_id>/', views.api_finalizar_reunion, name='api_finalizar'),
    path('api/cursos/crear/', views.api_crear_curso, name='api_crear_curso'),
    path('api/empresas/crear/', views.api_crear_empresa, name='api_crear_empresa'),
    path('api/chatbot/', views.api_chatbot_ia, name='api_chatbot_ia'), # <-- Nueva ruta Chatbot IA
]