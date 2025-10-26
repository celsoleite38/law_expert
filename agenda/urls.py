# agenda/urls.py (VERSÃO COMPLETA)

from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required

app_name = 'agenda'

urlpatterns = [
    # Agenda Principal
    path('', login_required(views.AgendaView.as_view()), name='agenda'),
    path('painel/', login_required(views.PainelControleAgendaView.as_view()), name='painel_controle'),
    path('configuracoes/', login_required(views.ConfiguracoesAgendaView.as_view()), name='configuracoes'),
    
    # Audiências
    path('audiencias/', login_required(views.AudienciaListView.as_view()), name='lista_audiencias'),
    path('audiencias/novo/', login_required(views.AudienciaCreateView.as_view()), name='nova_audiencia'),
    path('audiencias/<int:pk>/', login_required(views.AudienciaDetailView.as_view()), name='detalhe_audiencia'),
    path('audiencias/<int:pk>/editar/', login_required(views.AudienciaUpdateView.as_view()), name='editar_audiencia'),
    path('audiencias/<int:pk>/cancelar/', login_required(views.cancelar_audiencia), name='cancelar_audiencia'),
    
    # Horários de Atendimento
    path('horarios/', login_required(views.HorarioAtendimentoListView.as_view()), name='lista_horarios'),
    path('horarios/novo/', login_required(views.HorarioAtendimentoCreateView.as_view()), name='novo_horario'),
    path('horarios/<int:pk>/editar/', login_required(views.HorarioAtendimentoUpdateView.as_view()), name='editar_horario'),
    path('horarios/<int:pk>/deletar/', login_required(views.deletar_horario), name='deletar_horario'),
    
    # Bloqueios de Agenda
    path('bloqueios/', login_required(views.BloqueioAgendaListView.as_view()), name='lista_bloqueios'),
    path('bloqueios/novo/', login_required(views.BloqueioAgendaCreateView.as_view()), name='novo_bloqueio'),
    path('bloqueios/<int:pk>/editar/', login_required(views.BloqueioAgendaUpdateView.as_view()), name='editar_bloqueio'),
    path('bloqueios/<int:pk>/deletar/', login_required(views.deletar_bloqueio), name='deletar_bloqueio'),
    
    # APIs
    path('api/eventos/', login_required(views.EventosJsonView.as_view()), name='api_eventos'),
    path('api/disponibilidade/', login_required(views.VerificarDisponibilidadeView.as_view()), name='api_disponibilidade'),
    path('api/verificar-agendamento/', login_required(views.VerificarDisponibilidadeAudienciaView.as_view()), name='api_verificar_agendamento'),
    path('audiencias/<int:pk>/reagendar/', views.ReagendarAudienciaJsonView.as_view(), name='reagendar_audiencia_json'),
]