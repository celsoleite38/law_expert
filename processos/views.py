from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.db.models import Q

from usuarios.utils import exige_permissao, advogado_dono
from usuarios.models import PermissaoColaborador
from .models import Processo, Andamento
from .forms import ProcessoForm, AndamentoForm

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.views.generic.edit import FormMixin # 1. IMPORTE O FORMMIXIN

from django.views.generic import DetailView



@method_decorator(exige_permissao('cadastrar_processo'), name='dispatch')
class ProcessoCreateView(LoginRequiredMixin, CreateView):
    model = Processo
    form_class = ProcessoForm
    template_name = 'processos/processo_form.html'
    success_url = reverse_lazy('processos:lista_processos')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request  # Passa o request para o form
        return kwargs

    def form_valid(self, form):
        form.instance.advogado_responsavel = advogado_dono(self.request)
        messages.success(self.request, "Processo cadastrado com sucesso!")
        return super().form_valid(form)


@method_decorator(exige_permissao('editar_processo', redirect_to='processos:lista'), name='dispatch')
class ProcessoUpdateView(UpdateView):
    model = Processo
    form_class = ProcessoForm
    template_name = 'processos/processo_form.html'
    
    def get_queryset(self):
        """Filtra apenas processos do advogado responsável"""
        return super().get_queryset().filter(advogado_responsavel=advogado_dono(self.request))
    
    def get_success_url(self):
        messages.success(self.request, "Processo atualizado com sucesso!")
        return reverse('processos:detalhe_processo', kwargs={'pk': self.object.pk})





@method_decorator(exige_permissao('visualizar_processo'), name='dispatch')
class ProcessoDetailView(LoginRequiredMixin, FormMixin, DetailView): # 3. ADICIONE FORMMIXIN
    model = Processo
    template_name = 'processos/processo_detail.html'
    context_object_name = 'processo'
    form_class = AndamentoForm # 4. ESPECIFIQUE A CLASSE DO FORMULÁRIO

    def get_success_url(self):
        # URL para onde o usuário será redirecionado após criar um andamento com sucesso
        return reverse('processos:detalhe_processo', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        # Adiciona a lista de andamentos e o formulário ao contexto
        context = super().get_context_data(**kwargs)
        processo = self.get_object()
        
        context['andamentos'] = processo.andamentos.all().order_by('-criado_em')
        #context['andamento_form'] = self.get_form() # Adiciona o formulário ao contexto
        return context

    def post(self, request, *args, **kwargs):
        """
        Este método é chamado quando o formulário de andamento é enviado (POST).
        """
        self.object = self.get_object() # Pega o objeto do processo
        form = self.get_form()
        
        if form.is_valid():
            # Se o formulário for válido, chama o form_valid abaixo
            return self.form_valid(form)
        else:
            # Se for inválido, re-renderiza a página com os erros
            return self.form_invalid(form)

    def form_valid(self, form):
        # Salva o novo andamento associado ao processo e ao usuário
        andamento = form.save(commit=False)
        andamento.processo = self.object
        andamento.usuario = self.request.user
        andamento.save()
        messages.success(self.request, "Andamento adicionado com sucesso!")
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        # Sua lógica de permissão continua a mesma, não precisa mudar
        processo = self.get_object()
        if processo.advogado_responsavel != advogado_dono(request):
            messages.error(request, "Você não tem permissão para visualizar este processo.")
            return redirect('processos:lista')
        return super().dispatch(request, *args, **kwargs)



@method_decorator(exige_permissao('listar_processos'), name='dispatch')
class ProcessoListView(LoginRequiredMixin, ListView):
    model = Processo
    template_name = 'processos/processo_list.html'
    context_object_name = 'processos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona as áreas de direito ao contexto
        context['AREAS_DIREITO'] = Processo.AREAS_DIREITO
        context['selected_area_direito'] = self.request.GET.get('area_direito', '')
        return context

    def get_queryset(self):
        dono = advogado_dono(self.request)
        queryset = Processo.objects.filter(advogado_responsavel=dono, status__in=['ANDAMENTO', 'CONCLUIDO'])
        
        # Filtro por área de direito
        area_direito = self.request.GET.get('area_direito')
        if area_direito:
            queryset = queryset.filter(area_direito=area_direito)
        
        # Filtro por busca textual
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(numero__icontains=query) |
                Q(cliente__nome__icontains=query) |
                Q(descricao__icontains=query)
            )
        
        return queryset.order_by('-data_cadastro')


class AndamentoCreateView(LoginRequiredMixin, CreateView):
    model = Andamento
    form_class = AndamentoForm
    template_name = 'processos/andamento_form.html'

    def dispatch(self, request, *args, **kwargs):
        # Esta verificação de permissão já está correta, não precisa mudar.
        processo = get_object_or_404(Processo, pk=self.kwargs['processo_id'])
        if processo.advogado_responsavel != advogado_dono(request):
            messages.error(request, "Você não tem permissão para adicionar andamento neste processo.")
            return redirect('processos:lista')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Esta função adiciona dados extras ao contexto do template.
        """
        # 1. Pega o contexto que a CreateView já montou (que inclui o 'form').
        context = super().get_context_data(**kwargs)
        
        # 2. Busca o objeto do processo usando a ID da URL.
        processo = get_object_or_404(Processo, pk=self.kwargs['processo_id'])
        
        # 3. Adiciona o objeto 'processo' ao contexto.
        context['processo'] = processo
        
        # 4. Retorna o contexto modificado para o template.
        return context

    def form_valid(self, form):
        # Busca o processo novamente para associar ao novo andamento.
        processo = get_object_or_404(Processo, pk=self.kwargs['processo_id'])
        form.instance.processo = processo
        form.instance.usuario = self.request.user
        messages.success(self.request, "Andamento cadastrado com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        # Esta parte agora funcionará, pois a pk sempre estará presente.
        return reverse_lazy('processos:detalhe_processo', kwargs={'pk': self.kwargs['processo_id']})

@login_required
def arquivar_processo(request, pk):
    processo = get_object_or_404(Processo, pk=pk)

    if processo.advogado_responsavel != advogado_dono(request):
        messages.error(request, "Você não tem permissão para arquivar este processo.")
        return redirect('processos:lista')

    processo.status = 'ARQUIVADO'
    processo.save()

    messages.success(request, f"O processo {processo.numero} foi arquivado com sucesso.")
    return redirect('processos:detalhe_processo', pk=pk)

# processos/views.py
@method_decorator(exige_permissao('listar_processos'), name='dispatch')
class ProcessosArquivadosListView(LoginRequiredMixin, ListView):
    model = Processo
    template_name = 'processos/processos_arquivados.html'
    context_object_name = 'processos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['AREAS_DIREITO'] = Processo.AREAS_DIREITO
        context['selected_area_direito'] = self.request.GET.get('area_direito', '')
        return context

    def get_queryset(self):
        dono = advogado_dono(self.request)
        # Filtra apenas processos arquivados
        queryset = Processo.objects.filter(
            advogado_responsavel=dono,
            status='ARQUIVADO'
        )
        
        # Filtro por área de direito
        area_direito = self.request.GET.get('area_direito')
        if area_direito:
            queryset = queryset.filter(area_direito=area_direito)
        
        # Filtro por busca textual
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(numero__icontains=query) |
                Q(cliente__nome__icontains=query) |
                Q(descricao__icontains=query)
            )
        
        return queryset.order_by('-data_cadastro')
    
    # processos/views.py
@login_required
def desarquivar_processo(request, pk):
    processo = get_object_or_404(Processo, pk=pk)

    if processo.advogado_responsavel != advogado_dono(request):
        messages.error(request, "Você não tem permissão para desarquivar este processo.")
        return redirect('processos:arquivados')

    processo.status = 'ANDAMENTO', 'CONCLUIDO'  # Ou outro status desejado
    processo.save()

    messages.success(request, f"O processo {processo.numero} foi desarquivado com sucesso.")
    return redirect('processos:arquivados')