from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from usuarios.utils import exige_permissao
from .models import CondicaoPagamento, FormaPagamento, Honorario, CategoriaFinanceira, TransacaoFinanceira, ContaAPagar, ContaAReceber, CategoriaFinanceira, TransacaoFinanceira, ContaAPagar, ContaAReceber, Honorario
from processos.models import Processo
import csv
from .forms import CategoriaFinanceiraForm, CondicaoPagamentoForm, FormaPagamentoForm, TransacaoFinanceiraForm, ContaAPagarForm, ContaAReceberForm, HonorarioForm
from django.db import models
from django.contrib.auth.decorators import login_required
from django.db.models.functions import TruncMonth
from django.db.models import Sum, Value
from django.db.models.fields import CharField
from datetime import date
from dateutil.relativedelta import relativedelta


from django.contrib import messages


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
    form_class = HonorarioForm
    template_name = 'financeiro/honorarios/honorario_form.html'
    success_url = reverse_lazy('financeiro:lista_contas_a_receber')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['processo'].queryset = Processo.objects.filter(advogado_responsavel=self.request.user)
        form.fields['forma_pagamento'].queryset = FormaPagamento.objects.filter(usuario_criador=self.request.user)
        form.fields['condicao_pagamento'].queryset = CondicaoPagamento.objects.filter(usuario_criador=self.request.user)
        return form

    def form_valid(self, form):
        try:
            print("=== INICIANDO CRIAÇÃO DE HONORÁRIO ===")
            
            honorario = form.save(commit=False)
            parcelar = form.cleaned_data.get('parcelar', False)
            condicao_pagamento = form.cleaned_data.get('condicao_pagamento')
            
            # Criar a TransacaoFinanceira principal
            transacao_data = self.request.POST.copy()
            transacao_data['tipo'] = 'RECEITA'
            
            if not transacao_data.get('descricao'):
                transacao_data['descricao'] = f"Honorário - Processo {honorario.processo.numero}"
            
            transacao_form = TransacaoFinanceiraForm(transacao_data, user=self.request.user)
            
            if transacao_form.is_valid():
                transacao = transacao_form.save(commit=False)
                transacao.usuario = self.request.user
                transacao.categoria = CategoriaFinanceira.objects.get_or_create(
                    nome='Honorários', 
                    tipo='RECEITA', 
                    usuario_criador=self.request.user
                )[0]
                transacao.save()
                print(f"Transação principal criada: {transacao.id}")

                # Salvar o honorário
                honorario.transacao = transacao
                honorario.parcelado = parcelar
                honorario.save()
                print(f"Honorário criado: {honorario.id}")

                if parcelar and condicao_pagamento:
                    # Criar parcelas
                    self._criar_parcelas(honorario, transacao, condicao_pagamento)
                    messages.success(self.request, f'Honorário parcelado em {condicao_pagamento.numero_parcelas}x criado com sucesso!')
                else:
                    # Criar conta única (comportamento original)
                    self._criar_conta_unica(honorario, transacao)
                    messages.success(self.request, 'Honorário à vista criado com sucesso!')

                return redirect('financeiro:lista_contas_a_receber')
                    
            else:
                print("Erros no form TransacaoFinanceira:", transacao_form.errors)
                return self.form_invalid(form)
                
        except Exception as e:
            print("Erro completo na criação:", str(e))
            import traceback
            traceback.print_exc()
            messages.error(self.request, f'Erro ao criar honorário: {str(e)}')
            return self.form_invalid(form)

    def _criar_conta_unica(self, honorario, transacao):
        """Cria uma única conta a receber (comportamento original)"""
        conta_a_receber_form = ContaAReceberForm(self.request.POST)
        if conta_a_receber_form.is_valid():
            conta_a_receber = conta_a_receber_form.save(commit=False)
            conta_a_receber.transacao = transacao
            conta_a_receber.honorario_vinculado = honorario
            
            if conta_a_receber.data_recebimento:
                conta_a_receber.recebido = True
                
            conta_a_receber.save()
            print(f"Conta única criada: {conta_a_receber.id}")

    def _criar_parcelas(self, honorario, transacao_principal, condicao_pagamento):
        """Cria parcelas do honorário"""
        valor_total = transacao_principal.valor
        numero_parcelas = condicao_pagamento.numero_parcelas
        valor_parcela = valor_total / numero_parcelas
        
        data_base = timezone.now().date()
        
        for i in range(1, numero_parcelas + 1):
            # Calcular data de vencimento
            data_vencimento = data_base + timedelta(days=(i-1) * condicao_pagamento.intervalo_dias)
            
            # Criar transação para a parcela
            transacao_parcela = TransacaoFinanceira(
                usuario=self.request.user,
                descricao=f"Parcela {i}/{numero_parcelas} - Honorário Processo {honorario.processo.numero}",
                valor=valor_parcela,
                data_transacao=data_base,
                tipo='RECEITA',
                categoria=CategoriaFinanceira.objects.get_or_create(
                    nome='Honorários Parcelados', 
                    tipo='RECEITA', 
                    usuario_criador=self.request.user
                )[0],
                processo=honorario.processo
            )
            transacao_parcela.save()
            
            # Criar conta a receber para a parcela
            conta_parcela = ContaAReceber(
                transacao=transacao_parcela,
                data_vencimento=data_vencimento,
                recebido=False
            )
            conta_parcela.save()
            
            # Criar parcela do honorário
            parcela = ParcelaHonorario(
                honorario=honorario,
                numero_parcela=i,
                valor_parcela=valor_parcela,
                data_vencimento=data_vencimento,
                transacao=transacao_parcela,
                conta_a_receber=conta_parcela
            )
            parcela.save()
            
            print(f"Parcela {i} criada: {parcela.id}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'transacao_form' not in context:
            context['transacao_form'] = TransacaoFinanceiraForm(
                user=self.request.user, 
                initial={
                    'tipo': 'RECEITA',
                    'descricao': 'Honorário'
                }
            )
        if 'conta_a_receber_form' not in context:
            context['conta_a_receber_form'] = ContaAReceberForm()
        return context
        
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


class CategoriaFinanceiraListView(LoginRequiredMixin, ListView):
    model = CategoriaFinanceira
    template_name = 'financeiro/categorias/categoria_list.html'
    context_object_name = 'categorias'

    def get_queryset(self):
        return CategoriaFinanceira.objects.filter(usuario_criador=self.request.user)

class CategoriaFinanceiraCreateView(LoginRequiredMixin, CreateView):
    model = CategoriaFinanceira
    form_class = CategoriaFinanceiraForm
    template_name = 'financeiro/categorias/categoria_form.html'
    success_url = reverse_lazy('financeiro:lista_categorias')

    def form_valid(self, form):
        form.instance.usuario_criador = self.request.user
        messages.success(self.request, 'Categoria criada com sucesso!')
        return super().form_valid(form)

class CategoriaFinanceiraUpdateView(LoginRequiredMixin, UpdateView):
    model = CategoriaFinanceira
    form_class = CategoriaFinanceiraForm
    template_name = 'financeiro/categorias/categoria_form.html'
    success_url = reverse_lazy('financeiro:lista_categorias')

    def get_queryset(self):
        return CategoriaFinanceira.objects.filter(usuario_criador=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Categoria atualizada com sucesso!')
        return super().form_valid(form)

class CategoriaFinanceiraDeleteView(LoginRequiredMixin, DeleteView):
    model = CategoriaFinanceira
    template_name = 'financeiro/categorias/categoria_confirm_delete.html'
    success_url = reverse_lazy('financeiro:lista_categorias')

    def get_queryset(self):
        return CategoriaFinanceira.objects.filter(usuario_criador=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Categoria excluída com sucesso!')
        return super().form_valid(form)


# --- Views de Transação Financeira (Receitas e Despesas) ---

class TransacaoFinanceiraListView(LoginRequiredMixin, ListView):
    model = TransacaoFinanceira
    template_name = 'financeiro/transacoes/transacao_list.html'
    context_object_name = 'transacoes'
    paginate_by = 10

    def get_queryset(self):
        queryset = TransacaoFinanceira.objects.filter(usuario=self.request.user)
        tipo = self.request.GET.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipo_filtro'] = self.request.GET.get('tipo', '')
        return context

class TransacaoFinanceiraCreateView(LoginRequiredMixin, CreateView):
    model = TransacaoFinanceira
    form_class = TransacaoFinanceiraForm
    template_name = 'financeiro/transacoes/transacao_form.html'
    success_url = reverse_lazy('financeiro:lista_transacoes')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, 'Transação criada com sucesso!')
        return super().form_valid(form)

class TransacaoFinanceiraUpdateView(LoginRequiredMixin, UpdateView):
    model = TransacaoFinanceira
    form_class = TransacaoFinanceiraForm
    template_name = 'financeiro/transacoes/transacao_form.html'
    success_url = reverse_lazy('financeiro:lista_transacoes')

    def get_queryset(self):
        return TransacaoFinanceira.objects.filter(usuario=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Transação atualizada com sucesso!')
        return super().form_valid(form)

class TransacaoFinanceiraDeleteView(LoginRequiredMixin, DeleteView):
    model = TransacaoFinanceira
    template_name = 'financeiro/transacoes/transacao_confirm_delete.html'
    success_url = reverse_lazy('financeiro:lista_transacoes')

    def get_queryset(self):
        return TransacaoFinanceira.objects.filter(usuario=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Transação excluída com sucesso!')
        return super().form_valid(form)

class TransacaoFinanceiraDetailView(LoginRequiredMixin, DetailView):
    model = TransacaoFinanceira
    template_name = 'financeiro/transacoes/transacao_detail.html'
    context_object_name = 'transacao'

    def get_queryset(self):
        return TransacaoFinanceira.objects.filter(usuario=self.request.user)


# --- Views de Contas a Pagar ---

class ContaAPagarListView(LoginRequiredMixin, ListView):
    model = ContaAPagar
    template_name = 'financeiro/contas/contas_a_pagar_list.html'
    context_object_name = 'contas_a_pagar'
    paginate_by = 10

    def get_queryset(self):
        return ContaAPagar.objects.filter(transacao__usuario=self.request.user, pago=False).order_by('data_vencimento')

class ContaAPagarCreateView(LoginRequiredMixin, CreateView):
    model = ContaAPagar
    form_class = ContaAPagarForm
    template_name = 'financeiro/contas/conta_a_pagar_form.html'
    success_url = reverse_lazy('financeiro:lista_contas_a_pagar')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        transacao_form = TransacaoFinanceiraForm(self.request.POST, user=self.request.user)
        if transacao_form.is_valid():
            transacao = transacao_form.save(commit=False)
            transacao.usuario = self.request.user
            transacao.tipo = 'DESPESA'
            transacao.save()
            form.instance.transacao = transacao
            messages.success(self.request, 'Conta a Pagar criada com sucesso!')
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'transacao_form' not in context:
            context['transacao_form'] = TransacaoFinanceiraForm(user=self.request.user)
        return context

class ContaAPagarUpdateView(LoginRequiredMixin, UpdateView):
    model = ContaAPagar
    form_class = ContaAPagarForm
    template_name = 'financeiro/contas/conta_a_pagar_form.html'
    success_url = reverse_lazy('financeiro:lista_contas_a_pagar')

    def get_queryset(self):
        return ContaAPagar.objects.filter(transacao__usuario=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        transacao_form = TransacaoFinanceiraForm(self.request.POST, instance=form.instance.transacao, user=self.request.user)
        if transacao_form.is_valid():
            transacao_form.save()
            messages.success(self.request, 'Conta a Pagar atualizada com sucesso!')
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'transacao_form' not in context:
            context['transacao_form'] = TransacaoFinanceiraForm(instance=self.object.transacao, user=self.request.user)
        return context

class ContaAPagarDeleteView(LoginRequiredMixin, DeleteView):
    model = ContaAPagar
    template_name = 'financeiro/contas/conta_a_pagar_confirm_delete.html'
    success_url = reverse_lazy('financeiro:lista_contas_a_pagar')

    def get_queryset(self):
        return ContaAPagar.objects.filter(transacao__usuario=self.request.user)

    def form_valid(self, form):
        transacao = form.instance.transacao
        messages.success(self.request, 'Conta a Pagar excluída com sucesso!')
        response = super().form_valid(form)
        transacao.delete() # Deleta a transação associada
        return response


# --- Views de Contas a Receber ---

class ContaAReceberListView(LoginRequiredMixin, ListView):
    model = ContaAReceber
    template_name = 'financeiro/contas/contas_a_receber_list.html'
    context_object_name = 'contas_a_receber'
    paginate_by = 10

    def get_queryset(self):
        return ContaAReceber.objects.filter(transacao__usuario=self.request.user, recebido=False).order_by('data_vencimento')

class ContaAReceberCreateView(LoginRequiredMixin, CreateView):
    model = ContaAReceber
    form_class = ContaAReceberForm
    template_name = 'financeiro/contas/conta_a_receber_form.html'
    success_url = reverse_lazy('financeiro:lista_contas_a_receber')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        transacao_form = TransacaoFinanceiraForm(self.request.POST, user=self.request.user)
        if transacao_form.is_valid():
            transacao = transacao_form.save(commit=False)
            transacao.usuario = self.request.user
            transacao.tipo = 'RECEITA'
            transacao.save()
            form.instance.transacao = transacao
            messages.success(self.request, 'Conta a Receber criada com sucesso!')
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'transacao_form' not in context:
            context['transacao_form'] = TransacaoFinanceiraForm(user=self.request.user)
        return context

class ContaAReceberUpdateView(LoginRequiredMixin, UpdateView):
    model = ContaAReceber
    form_class = ContaAReceberForm
    template_name = 'financeiro/contas/conta_a_receber_form.html'
    success_url = reverse_lazy('financeiro:lista_contas_a_receber')

    def get_queryset(self):
        return ContaAReceber.objects.filter(transacao__usuario=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        transacao_form = TransacaoFinanceiraForm(self.request.POST, instance=form.instance.transacao, user=self.request.user)
        if transacao_form.is_valid():
            transacao_form.save()
            messages.success(self.request, 'Conta a Receber atualizada com sucesso!')
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'transacao_form' not in context:
            context['transacao_form'] = TransacaoFinanceiraForm(instance=self.object.transacao, user=self.request.user)
        return context

class ContaAReceberDeleteView(LoginRequiredMixin, DeleteView):
    model = ContaAReceber
    template_name = 'financeiro/contas/conta_a_receber_confirm_delete.html'
    success_url = reverse_lazy('financeiro:lista_contas_a_receber')

    def get_queryset(self):
        return ContaAReceber.objects.filter(transacao__usuario=self.request.user)

    def form_valid(self, form):
        transacao = form.instance.transacao
        messages.success(self.request, 'Conta a Receber excluída com sucesso!')
        response = super().form_valid(form)
        transacao.delete() # Deleta a transação associada
        return response


class HonorarioUpdateView(LoginRequiredMixin, UpdateView):
    model = Honorario
    form_class = HonorarioForm
    template_name = 'financeiro/honorarios/honorario_form.html'
    success_url = reverse_lazy('financeiro:lista_contas_a_receber')

    def get_queryset(self):
        return Honorario.objects.filter(transacao__usuario=self.request.user)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['processo'].queryset = Processo.objects.filter(advogado_responsavel=self.request.user)
        return form

    def form_valid(self, form):
        honorario = form.instance
        transacao_form = TransacaoFinanceiraForm(self.request.POST, instance=honorario.transacao, user=self.request.user)
        conta_a_receber_form = ContaAReceberForm(self.request.POST, instance=honorario.transacao.conta_a_receber)

        if transacao_form.is_valid() and conta_a_receber_form.is_valid():
            # Salva as forms
            transacao_form.save()
            conta_a_receber = conta_a_receber_form.save(commit=False)
            
            # CORREÇÃO: Atualiza o status de recebido baseado na data_recebimento
            if conta_a_receber.data_recebimento:
                conta_a_receber.recebido = True
            else:
                conta_a_receber.recebido = False
                
            conta_a_receber.save()
            form.save()
            
            messages.success(self.request, 'Honorário atualizado com sucesso!')
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        honorario = self.object
        if 'transacao_form' not in context:
            context['transacao_form'] = TransacaoFinanceiraForm(instance=honorario.transacao, user=self.request.user)
        if 'conta_a_receber_form' not in context:
            context['conta_a_receber_form'] = ContaAReceberForm(instance=honorario.transacao.conta_a_receber)
        return context
    
class HonorarioDeleteView(LoginRequiredMixin, DeleteView):
    model = Honorario
    template_name = 'financeiro/honorarios/honorario_confirm_delete.html'
    success_url = reverse_lazy('financeiro:lista_contas_a_receber')

    def get_queryset(self):
        return Honorario.objects.filter(transacao__usuario=self.request.user)

    def form_valid(self, form):
        honorario = form.instance
        transacao = honorario.transacao
        messages.success(self.request, 'Honorário excluído com sucesso!')
        response = super().form_valid(form)
        transacao.delete() # Deleta a transação e a conta a receber associada
        return response

        print("Dados POST:", self.request.POST)
        print("Transação salva:", transacao.id, transacao.descricao, transacao.valor)
        print("Conta a Receber salva:", conta_a_receber.id, conta_a_receber.recebido, conta_a_receber.data_recebimento)
    



class FinanceiroDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'financeiro/dashboard_financeiro.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Transações do mês atual
        hoje = timezone.now()
        primeiro_dia_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ultimo_dia_mes = primeiro_dia_mes + relativedelta(months=1) - relativedelta(days=1)

        transacoes_mes = TransacaoFinanceira.objects.filter(
            usuario=user,
            data_transacao__range=(primeiro_dia_mes, ultimo_dia_mes)
        )

        receitas_mes = transacoes_mes.filter(tipo='RECEITA').aggregate(Sum('valor'))['valor__sum'] or 0
        despesas_mes = transacoes_mes.filter(tipo='DESPESA').aggregate(Sum('valor'))['valor__sum'] or 0
        saldo_mes = receitas_mes - despesas_mes

        context['receitas_mes'] = receitas_mes
        context['despesas_mes'] = despesas_mes
        context['saldo_mes'] = saldo_mes

        # Contas a Pagar e Receber próximas
        contas_a_pagar_proximas = ContaAPagar.objects.filter(
            transacao__usuario=user,
            pago=False,
            data_vencimento__gte=hoje
        ).order_by('data_vencimento')[:5]

        contas_a_receber_proximas = ContaAReceber.objects.filter(
            transacao__usuario=user,
            recebido=False,
            data_vencimento__gte=hoje
        ).order_by('data_vencimento')[:5]

        context['contas_a_pagar_proximas'] = contas_a_pagar_proximas
        context['contas_a_receber_proximas'] = contas_a_receber_proximas

        # Total de Honorários Pendentes
        honorarios_pendentes = Honorario.objects.filter(
            transacao__usuario=user,
            transacao__conta_a_receber__recebido=False
        ).aggregate(Sum('transacao__valor'))['transacao__valor__sum'] or 0
        context['honorarios_pendentes'] = honorarios_pendentes

        return context

class FluxoDeCaixaView(LoginRequiredMixin, TemplateView):
    template_name = 'financeiro/fluxo_de_caixa.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Filtros de data (últimos 6 meses por padrão)
        hoje = date.today()
        data_inicial = hoje - relativedelta(months=5)
        data_inicial = data_inicial.replace(day=1)
        data_final = hoje.replace(day=hoje.day) # até o dia atual

        # Dados de Receitas e Despesas por mês
        receitas_mensais = TransacaoFinanceira.objects.filter(
            usuario=user,
            tipo='RECEITA',
            data_transacao__range=(data_inicial, data_final)
        ).annotate(
            mes=TruncMonth('data_transacao')
        ).values('mes').annotate(
            total_receita=Sum('valor')
        ).order_by('mes')

        despesas_mensais = TransacaoFinanceira.objects.filter(
            usuario=user,
            tipo='DESPESA',
            data_transacao__range=(data_inicial, data_final)
        ).annotate(
            mes=TruncMonth('data_transacao')
        ).values('mes').annotate(
            total_despesa=Sum('valor')
        ).order_by('mes')

        # Combinar os dados
        fluxo_caixa = {}
        for r in receitas_mensais:
            mes_str = r['mes'].strftime('%Y-%m')
            fluxo_caixa[mes_str] = {'mes': r['mes'].strftime('%b/%Y'), 'receita': r['total_receita'], 'despesa': 0, 'saldo': r['total_receita']}

        for d in despesas_mensais:
            mes_str = d['mes'].strftime('%Y-%m')
            if mes_str in fluxo_caixa:
                fluxo_caixa[mes_str]['despesa'] = d['total_despesa']
                fluxo_caixa[mes_str]['saldo'] = fluxo_caixa[mes_str]['receita'] - d['total_despesa']
            else:
                fluxo_caixa[mes_str] = {'mes': d['mes'].strftime('%b/%Y'), 'receita': 0, 'despesa': d['total_despesa'], 'saldo': -d['total_despesa']}

        # Ordenar e calcular o acumulado (se necessário)
        fluxo_caixa_list = sorted(fluxo_caixa.values(), key=lambda x: date(int(x['mes'].split('/')[1]), list(date.today().strftime('%b').split()).index(x['mes'].split('/')[0]) + 1, 1))

        # Preparar dados para o gráfico (labels, receitas, despesas, saldos)
        labels = [item['mes'] for item in fluxo_caixa_list]
        dados_receita = [float(item['receita']) for item in fluxo_caixa_list]
        dados_despesa = [float(item['despesa']) for item in fluxo_caixa_list]
        dados_saldo = [float(item['saldo']) for item in fluxo_caixa_list]

        context['fluxo_caixa_list'] = fluxo_caixa_list
        context['chart_labels'] = labels
        context['chart_receita'] = dados_receita
        context['chart_despesa'] = dados_despesa
        context['chart_saldo'] = dados_saldo

        return context




class RelatorioFinanceiroView(LoginRequiredMixin, TemplateView):
    template_name = 'financeiro/relatorios.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Filtros (pode ser expandido com formulário)
        data_inicial = self.request.GET.get('data_inicial')
        data_final = self.request.GET.get('data_final')

        transacoes = TransacaoFinanceira.objects.filter(usuario=user)

        if data_inicial:
            transacoes = transacoes.filter(data_transacao__gte=data_inicial)
        if data_final:
            transacoes = transacoes.filter(data_transacao__lte=data_final)

        # Resumo Financeiro
        resumo = transacoes.aggregate(
            total_receitas=Sum('valor', filter=models.Q(tipo='RECEITA')),
            total_despesas=Sum('valor', filter=models.Q(tipo='DESPESA'))
        )
        total_receitas = resumo['total_receitas'] or 0
        total_despesas = resumo['total_despesas'] or 0
        saldo_final = total_receitas - total_despesas

        # Análise por Categoria
        categorias = CategoriaFinanceira.objects.filter(usuario_criador=user)
        analise_categorias = []
        for cat in categorias:
            valor = transacoes.filter(categoria=cat).aggregate(Sum('valor'))['valor__sum'] or 0
            analise_categorias.append({
                'nome': cat.nome,
                'tipo': cat.tipo,
                'valor': valor
            })

        context['total_receitas'] = total_receitas
        context['total_despesas'] = total_despesas
        context['saldo_final'] = saldo_final
        context['analise_categorias'] = analise_categorias
        context['data_inicial'] = data_inicial
        context['data_final'] = data_final
        
        # Preparar dados para gráficos (Ex: Receitas vs Despesas por Categoria)
        receitas_por_categoria = [c for c in analise_categorias if c['tipo'] == 'RECEITA' and c['valor'] > 0]
        despesas_por_categoria = [c for c in analise_categorias if c['tipo'] == 'DESPESA' and c['valor'] > 0]

        context['chart_receita_labels'] = [c['nome'] for c in receitas_por_categoria]
        context['chart_receita_data'] = [float(c['valor']) for c in receitas_por_categoria]
        context['chart_despesa_labels'] = [c['nome'] for c in despesas_por_categoria]
        context['chart_despesa_data'] = [float(c['valor']) for c in despesas_por_categoria]

        return context

@login_required
def exportar_relatorio(request):
    user = request.user
    data_inicial = request.GET.get('data_inicial')
    data_final = request.GET.get('data_final')

    transacoes = TransacaoFinanceira.objects.filter(usuario=user)

    if data_inicial:
        transacoes = transacoes.filter(data_transacao__gte=data_inicial)
    if data_final:
        transacoes = transacoes.filter(data_transacao__lte=data_final)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_financeiro_transacoes.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Data', 'Tipo', 'Descricao', 'Valor', 'Categoria', 'Processo'])
    
    for t in transacoes:
        writer.writerow([
            t.data_transacao.strftime('%d/%m/%Y'),
            t.get_tipo_display(),
            t.descricao,
            str(t.valor).replace('.', ','),
            t.categoria.nome if t.categoria else 'N/A',
            t.processo.numero_processo if t.processo else 'N/A'
        ])
    
    return response


# Views para FormaPagamento
class FormaPagamentoListView(LoginRequiredMixin, ListView):
    model = FormaPagamento
    template_name = 'financeiro/formas_pagamento/forma_list.html'
    
    def get_queryset(self):
        return FormaPagamento.objects.filter(usuario_criador=self.request.user)

class FormaPagamentoCreateView(LoginRequiredMixin, CreateView):
    model = FormaPagamento
    form_class = FormaPagamentoForm
    template_name = 'financeiro/formas_pagamento/forma_form.html'
    success_url = reverse_lazy('financeiro:lista_formas_pagamento')
    
    def form_valid(self, form):
        form.instance.usuario_criador = self.request.user
        messages.success(self.request, 'Forma de pagamento criada com sucesso!')
        return super().form_valid(form)

# Views para CondicaoPagamento
class CondicaoPagamentoListView(LoginRequiredMixin, ListView):
    model = CondicaoPagamento
    template_name = 'financeiro/condicoes_pagamento/condicao_list.html'
    
    def get_queryset(self):
        return CondicaoPagamento.objects.filter(usuario_criador=self.request.user)

class CondicaoPagamentoCreateView(LoginRequiredMixin, CreateView):
    model = CondicaoPagamento
    form_class = CondicaoPagamentoForm
    template_name = 'financeiro/condicoes_pagamento/condicao_form.html'
    success_url = reverse_lazy('financeiro:lista_condicoes_pagamento')
    
    def form_valid(self, form):
        form.instance.usuario_criador = self.request.user
        messages.success(self.request, 'Condição de pagamento criada com sucesso!')
        return super().form_valid(form)
class CondicaoPagamentoUpdateView(LoginRequiredMixin, UpdateView):
    model = CondicaoPagamento
    form_class = CondicaoPagamentoForm
    template_name = 'financeiro/condicoes_pagamento/condicao_form.html'
    success_url = reverse_lazy('financeiro:lista_condicoes_pagamento')
    
    def get_queryset(self):
        return CondicaoPagamento.objects.filter(usuario_criador=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Condição de pagamento atualizada com sucesso!')
        return super().form_valid(form)

class CondicaoPagamentoDeleteView(LoginRequiredMixin, DeleteView):
    model = CondicaoPagamento
    template_name = 'financeiro/condicoes_pagamento/condicao_confirm_delete.html'
    success_url = reverse_lazy('financeiro:lista_condicoes_pagamento')
    
    def get_queryset(self):
        return CondicaoPagamento.objects.filter(usuario_criador=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Condição de pagamento excluída com sucesso!')
        return super().form_valid(form)