from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib import messages
from django.utils.decorators import method_decorator

from usuarios.utils import exige_permissao, advogado_dono
from .models import Cliente
from .forms import ClienteForm

# --- Listagem de clientes visíveis ao advogado ou colaborador ---
# clientes/views.py

@method_decorator(exige_permissao('listar_clientes'), name='dispatch')
class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = 'clientes/cliente_list.html'
    context_object_name = 'clientes'

    def get_queryset(self):
        #print(f"--- DIAGNÓSTICO EM ClienteListView.get_queryset ---")
        dono = advogado_dono(self.request)
        #print(f"A view está buscando clientes para o advogado: {dono.email}")
        
        queryset = Cliente.objects.filter(advogado_responsavel=dono).order_by('nome')
        #print(f"Consulta ao banco de dados encontrou: {queryset.count()} clientes.")
        
        query = self.request.GET.get('q')
        if query:
            #print(f"Aplicando filtro de busca para: '{query}'")
            queryset = queryset.filter(Q(nome__icontains=query) | Q(cpf_cnpj__icontains=query))
            #print(f"Após o filtro de busca, restaram: {queryset.count()} clientes.")
            
        #print(f"--- FIM DIAGNóstico ClienteListView ---\n")
        return queryset


    #def get_context_data(self, **kwargs):
     #   context = super().get_context_data(**kwargs)
      #  context['tem_permissao'] = True  # ✅ Isso corrige o problema
       #"" return context


# --- Cadastro de cliente por advogado ou colaborador com permissão ---
@method_decorator(exige_permissao('cadastrar_cliente'), name='dispatch')
class ClienteCreateView(LoginRequiredMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'clientes/cliente_form.html'
    success_url = reverse_lazy('clientes:lista')

    def form_valid(self, form):
        try:
            form.instance.advogado_responsavel = advogado_dono(self.request)
            messages.success(self.request, 'Cliente cadastrado com sucesso!')
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f'Erro ao salvar: {str(e)}')
            return self.form_invalid(form)


# --- Edição de cliente com validação de vínculo ---
@method_decorator(exige_permissao('editar_cliente'), name='dispatch')
class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    model: type[Cliente] = Cliente
    form_class: type[ClienteForm] = ClienteForm
    template_name = 'clientes/cliente_form.html'

    def get_queryset(self):
        # Adicione este método para garantir que o colaborador
        # só possa editar clientes do seu advogado.
        dono = advogado_dono(self.request)
        return Cliente.objects.filter(advogado_responsavel=dono)

    def get_success_url(self):
        return reverse_lazy('clientes:detalhe', kwargs={'pk': self.object.pk})


# --- Visualização dos dados do cliente ---
@method_decorator(exige_permissao('visualizar_cliente'), name='dispatch')
class ClienteDetailView(LoginRequiredMixin, DetailView):
    model: type[Cliente] = Cliente
    template_name = 'clientes/cliente_detail.html'
    context_object_name = 'cliente'

    def get_queryset(self):
        # Adicione este método para garantir que o colaborador
        # só possa ver clientes do seu advogado.
        dono = advogado_dono(self.request)
        return Cliente.objects.filter(advogado_responsavel=dono)
