from django.urls import path
from . import views  

app_name = 'processos'

urlpatterns = [
    path('', views.ProcessoListView.as_view(), name='lista_processos'),
    path('arquivados/', views.ProcessosArquivadosListView.as_view(), name='arquivados'),
    path('novo/', views.ProcessoCreateView.as_view(), name='novo_processo'),
    path('<int:pk>/', views.ProcessoDetailView.as_view(), name='detalhe_processo'),
    path('<int:pk>/editar/', views.ProcessoUpdateView.as_view(), name='editar_processo'),
    path('<int:pk>/arquivar/', views.arquivar_processo, name='arquivar'),
    path('<int:pk>/desarquivar/', views.desarquivar_processo, name='desarquivar'),
    
    path('<int:processo_id>/andamento/novo/', views.AndamentoCreateView.as_view(), name='novo_andamento'),
]