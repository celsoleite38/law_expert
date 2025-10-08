# core/views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from processos.models import Processo
from agenda.models import Audiencia
from usuarios.utils import advogado_dono  # 1. IMPORTE A FUNÇÃO 'advogado_dono'
from django.utils.timezone import now
from django.db import models
@login_required
def dashboard(request):
    # 2. IDENTIFIQUE O DONO DA CONTA (seja o advogado ou o chefe do colaborador)
    dono_da_conta = advogado_dono(request)
    hoje = now()

    # 3. USE 'dono_da_conta' EM TODAS AS BUSCAS NO BANCO DE DADOS
    processos_recentes = Processo.objects.filter(advogado_responsavel=dono_da_conta, status__in=['ANDAMENTO', 'CONCLUIDO']).order_by('-data_cadastro')[:10]
    
    compromissos = Audiencia.objects.filter(
        models.Q(processo__advogado_responsavel=dono_da_conta) |  # Compromissos com processo
        models.Q(cliente__advogado_responsavel=dono_da_conta)     # Compromissos diretos com clientes
    ).filter(
        data_hora__gte=hoje
    ).order_by('data_hora')[:10]

    context = {
        'processos': processos_recentes,
        'compromissos': compromissos
    }
    return render(request, 'core/dashboard.html', context)
