from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required

app_name = 'financeiro'

urlpatterns = [
    # Honorários
    path('honorarios/', login_required(views.HonorarioListView.as_view()), name='lista_honorarios'),
    path('honorarios/novo/', login_required(views.HonorarioCreateView.as_view()), name='novo_honorario'),
    path('honorarios/<int:pk>/pagar/', login_required(views.marcar_como_pago), name='pagar_honorario'),
    
    # Relatórios Financeiros
    path('relatorios/', login_required(views.RelatorioFinanceiroView.as_view()), name='relatorios_financeiros'),
    path('relatorios/exportar/', login_required(views.exportar_relatorio), name='exportar_relatorio'),
]