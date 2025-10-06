from django.urls import path
from .views import (ProcessoListView, ProcessoCreateView, ProcessoDetailView, ProcessoUpdateView, AndamentoCreateView, arquivar_processo)

app_name = 'processos'

urlpatterns = [
    path('', ProcessoListView.as_view(), name='lista_processos'),
    path('novo/', ProcessoCreateView.as_view(), name='novo_processo'),
    path('<int:pk>/', ProcessoDetailView.as_view(), name='detalhe_processo'),
    path('<int:pk>/editar/', ProcessoUpdateView.as_view(), name='editar_processo'),
    path('<int:pk>/arquivar/', arquivar_processo, name='arquivar_processo'),
    path('<int:processo_id>/andamento/novo/', AndamentoCreateView.as_view(), name='novo_andamento'),
]
