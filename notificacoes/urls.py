from django.urls import include, path
from .views import PainelNotificacoesView

app_name = 'notificacoes'

urlpatterns = [
    path('', PainelNotificacoesView.as_view(), name='painel'),
    #path('notificacoes/', include('notificacoes.urls')),

]
