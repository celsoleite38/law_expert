from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required

app_name = 'financeiro'

urlpatterns = [
    # Dashboard Financeiro (visão geral)
    path('', login_required(views.FinanceiroDashboardView.as_view()), name='dashboard_financeiro'),

    # Categorias Financeiras
    path('categorias/', login_required(views.CategoriaFinanceiraListView.as_view()), name='lista_categorias'),
    path('categorias/nova/', login_required(views.CategoriaFinanceiraCreateView.as_view()), name='nova_categoria'),
    path('categorias/<int:pk>/editar/', login_required(views.CategoriaFinanceiraUpdateView.as_view()), name='editar_categoria'),
    path('categorias/<int:pk>/excluir/', login_required(views.CategoriaFinanceiraDeleteView.as_view()), name='excluir_categoria'),

    # Transações Financeiras (Receitas e Despesas)
    path('transacoes/', login_required(views.TransacaoFinanceiraListView.as_view()), name='lista_transacoes'),
    path('transacoes/nova/', login_required(views.TransacaoFinanceiraCreateView.as_view()), name='nova_transacao'),
    path('transacoes/<int:pk>/', login_required(views.TransacaoFinanceiraDetailView.as_view()), name='detalhe_transacao'),
    path('transacoes/<int:pk>/editar/', login_required(views.TransacaoFinanceiraUpdateView.as_view()), name='editar_transacao'),
    path('transacoes/<int:pk>/excluir/', login_required(views.TransacaoFinanceiraDeleteView.as_view()), name='excluir_transacao'),

    # Contas a Pagar
    path('contas-a-pagar/', login_required(views.ContaAPagarListView.as_view()), name='lista_contas_a_pagar'),
    path('contas-a-pagar/nova/', login_required(views.ContaAPagarCreateView.as_view()), name='nova_conta_a_pagar'),
    path('contas-a-pagar/<int:pk>/editar/', login_required(views.ContaAPagarUpdateView.as_view()), name='editar_conta_a_pagar'),
    path('contas-a-pagar/<int:pk>/excluir/', login_required(views.ContaAPagarDeleteView.as_view()), name='excluir_conta_a_pagar'),

    # Contas a Receber
    path('contas-a-receber/', login_required(views.ContaAReceberListView.as_view()), name='lista_contas_a_receber'),
    path('contas-a-receber/nova/', login_required(views.ContaAReceberCreateView.as_view()), name='nova_conta_a_receber'),
    path('contas-a-receber/<int:pk>/editar/', login_required(views.ContaAReceberUpdateView.as_view()), name='editar_conta_a_receber'),
    path('contas-a-receber/<int:pk>/excluir/', login_required(views.ContaAReceberDeleteView.as_view()), name='excluir_conta_a_receber'),

    # Honorários (agora integrados com Contas a Receber)
    path('honorarios/novo/', login_required(views.HonorarioCreateView.as_view()), name='novo_honorario'),
    path('honorarios/<int:pk>/editar/', login_required(views.HonorarioUpdateView.as_view()), name='editar_honorario'),
    path('honorarios/<int:pk>/excluir/', login_required(views.HonorarioDeleteView.as_view()), name='excluir_honorario'),

    # Relatórios Financeiros (manter e expandir)
    path('fluxo-de-caixa/', login_required(views.FluxoDeCaixaView.as_view()), name='fluxo_de_caixa'),
    path('relatorios/', login_required(views.RelatorioFinanceiroView.as_view()), name='relatorios_financeiros'),
    path('relatorios/exportar/', login_required(views.exportar_relatorio), name='exportar_relatorio'),

    # Formas de Pagamento
    path('formas-pagamento/', views.FormaPagamentoListView.as_view(), name='lista_formas_pagamento'),
    path('formas-pagamento/nova/', views.FormaPagamentoCreateView.as_view(), name='nova_forma_pagamento'),
    
    # Condições de Pagamento
    path('condicoes-pagamento/', views.CondicaoPagamentoListView.as_view(), name='lista_condicoes_pagamento'),
    path('condicoes-pagamento/nova/', views.CondicaoPagamentoCreateView.as_view(), name='nova_condicao_pagamento'),
    path('condicoes-pagamento/editar/<int:pk>/', views.CondicaoPagamentoUpdateView.as_view(), name='editar_condicao_pagamento'),
    path('condicoes-pagamento/excluir/<int:pk>/', views.CondicaoPagamentoDeleteView.as_view(), name='excluir_condicao_pagamento'),
]