from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required
from .views import PainelNotificacoesView

app_name = 'agenda'

urlpatterns = [
    # Agenda
    path('', login_required(views.AgendaView.as_view()), name='agenda'),
    
    # Audiências
    path('audiencias/', login_required(views.AudienciaListView.as_view()), name='lista_audiencias'),
    path('audiencias/novo/', login_required(views.AudienciaCreateView.as_view()), name='nova_audiencia'),
    path('audiencias/<int:pk>/', login_required(views.AudienciaDetailView.as_view()), name='detalhe_audiencia'),
    path('audiencias/<int:pk>/editar/', login_required(views.AudienciaUpdateView.as_view()), name='editar_audiencia'),
    path('audiencias/<int:pk>/cancelar/', login_required(views.cancelar_audiencia), name='cancelar_audiencia'),
    
    # API para calendário
    path('api/eventos/', login_required(views.EventosJsonView.as_view()), name='api_eventos'),
    path('audiencias/<int:pk>/reagendar/', views.ReagendarAudienciaJsonView.as_view(), name='reagendar_audiencia_json'),


]