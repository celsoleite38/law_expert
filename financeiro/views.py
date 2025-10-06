from django.views.generic import ListView, CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from usuarios.utils import exige_permissao
from .models import Honorario
from processos.models import Processo
import csv

# 🔐 Permissão para visualizar o painel financeiro
@method_decorator(exige_permissao('acessar_financeiro'), name='dispatch')
class HonorarioListView(LoginRequiredMixin, ListView):
    model = Honorario
    template_name = 'financeiro/honorario_list.html'
    
    def get_queryset(self):
        return Honorario.objects.filter(processo__advogado_responsavel=self.request.user)

@method_decorator(exige_permissao('acessar_financeiro'), name='dispatch')
class HonorarioCreateView(LoginRequiredMixin, CreateView):
    model = Honorario
    template_name = 'financeiro/honorario_form.html'
    fields = ['processo', 'valor', 'data_vencimento', 'descricao']
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['processo'].queryset = Processo.objects.filter(
            advogado_responsavel=self.request.user
        )
        return form

@exige_permissao('acessar_financeiro')
def marcar_como_pago(request, pk):
    honorario = get_object_or_404(Honorario, pk=pk)
    honorario.pago = True
    honorario.save()
    return redirect('financeiro:lista_honorarios')

@method_decorator(exige_permissao('acessar_financeiro'), name='dispatch')
class RelatorioFinanceiroView(LoginRequiredMixin, TemplateView):
    template_name = 'financeiro/relatorios.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['honorarios'] = Honorario.objects.filter(
            processo__advogado_responsavel=self.request.user
        )
        return context

@exige_permissao('acessar_financeiro')
def exportar_relatorio(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_financeiro.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Processo', 'Valor', 'Vencimento', 'Status'])
    
    honorarios = Honorario.objects.filter(processo__advogado_responsavel=request.user)
    for h in honorarios:
        writer.writerow([
            h.processo.numero,
            h.valor,
            h.data_vencimento,
            'Pago' if h.pago else 'Pendente'
        ])
    
    return response
