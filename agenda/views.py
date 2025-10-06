# agenda/views.py (VERSÃO REVISADA E CORRIGIDA)

from django.views.generic import ListView, CreateView, DetailView, UpdateView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse, Http404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from django.contrib.auth.decorators import login_required
from django.db import models
import json
from django.contrib import messages
from django.core.exceptions import ValidationError

from .models import Audiencia, LogAudiencia
from processos.models import Processo
from notificacoes.models import Notificacao
from .forms import AudienciaForm
from usuarios.utils import exige_permissao, advogado_dono

# --- Views da Agenda e Calendário ---

@method_decorator(exige_permissao('ver_agenda'), name='dispatch')
class AgendaView(LoginRequiredMixin, TemplateView):
    template_name = 'agenda/agenda.html'

@method_decorator(exige_permissao('ver_agenda'), name='dispatch')
class EventosJsonView(LoginRequiredMixin, View):
    def get(self, request):
        dono = advogado_dono(request)
        compromissos = Audiencia.objects.filter(
            models.Q(processo__advogado_responsavel=dono) | 
            models.Q(cliente__advogado_responsavel=dono)
        ).select_related('processo', 'processo__cliente', 'cliente').distinct()

        eventos_formatados = []
        for compromisso in compromissos:
            if compromisso.processo:
                titulo = f"Proc: {compromisso.processo.numero} - {compromisso.processo.cliente.nome}"
                cliente_nome = compromisso.processo.cliente.nome
                processo_numero = compromisso.processo.numero
            else:
                titulo = f"Cliente: {compromisso.cliente.nome}"
                cliente_nome = compromisso.cliente.nome
                processo_numero = "N/A"

            eventos_formatados.append({
                'id': compromisso.id,
                'title': titulo,
                'start': compromisso.data_hora.isoformat(),
                'allDay': False,
                'extendedProps': {
                    'tipo_evento': compromisso.get_tipo_display(),
                    'local': compromisso.local,
                    'processo_numero': processo_numero,
                    'cliente_nome': cliente_nome
                }
            })
        return JsonResponse(eventos_formatados, safe=False)

# --- Views de CRUD de Audiências/Compromissos ---

@method_decorator(exige_permissao('ver_agenda'), name='dispatch')
class AudienciaListView(LoginRequiredMixin, ListView):
    model = Audiencia
    template_name = 'agenda/audiencia_list.html'
    context_object_name = 'audiencias'
    
    def get_queryset(self):
        dono = advogado_dono(self.request)
        return Audiencia.objects.filter(
            models.Q(processo__advogado_responsavel=dono) | 
            models.Q(cliente__advogado_responsavel=dono)
        ).distinct().order_by('-data_hora')

@method_decorator(exige_permissao('adicionar_evento'), name='dispatch')
class AudienciaCreateView(LoginRequiredMixin, CreateView):
    model = Audiencia
    form_class = AudienciaForm
    template_name = 'agenda/nova_audiencia.html'
    success_url = reverse_lazy('agenda:lista_audiencias')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        # Garante que pelo menos cliente ou processo está definido
        if not form.instance.processo and not form.instance.cliente:
            form.instance.request_user = self.request.user
            return self.form_invalid(form)
        return super().form_valid(form)

@method_decorator(exige_permissao('ver_agenda'), name='dispatch')
class AudienciaDetailView(LoginRequiredMixin, DetailView):
    model = Audiencia
    template_name = 'agenda/audiencia_detail.html'
    
    def get_queryset(self):
        dono = advogado_dono(self.request)
        return Audiencia.objects.filter(
            models.Q(processo__advogado_responsavel=dono) | 
            models.Q(cliente__advogado_responsavel=dono)
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['logs'] = LogAudiencia.objects.filter(
            audiencia=self.object
        ).order_by('-data_alteracao')
        return context

@method_decorator(exige_permissao('editar_evento'), name='dispatch')
class AudienciaUpdateView(LoginRequiredMixin, UpdateView):
    model = Audiencia
    form_class = AudienciaForm
    template_name = 'agenda/editar_audiencia.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_queryset(self):
        dono = advogado_dono(self.request)
        return Audiencia.objects.filter(
            models.Q(processo__advogado_responsavel=dono) | 
            models.Q(cliente__advogado_responsavel=dono)
        ).distinct()

    def form_valid(self, form):
        # Validação explícita para edição
        if not form.instance.processo and not form.instance.cliente:
            form.add_error(None, "O compromisso deve estar vinculado a um Processo ou a um Cliente")
            return self.form_invalid(form)
        
        response = super().form_valid(form)
        messages.success(self.request, "Compromisso atualizado com sucesso!")
        return response

    def get_success_url(self):
        return reverse_lazy('agenda:detalhe_audiencia', kwargs={'pk': self.object.pk})

@exige_permissao('editar_evento')
def cancelar_audiencia(request, pk):
    dono = advogado_dono(request)
    
    try:
        audiencia = Audiencia.objects.filter(
            models.Q(processo__advogado_responsavel=dono) | 
            models.Q(cliente__advogado_responsavel=dono),
            pk=pk
        ).first()
        
        if not audiencia:
            raise Http404("Audiência não encontrada ou você não tem permissão")
            
        audiencia.delete()
        messages.success(request, "Audiência cancelada com sucesso!")
        return redirect('agenda:lista_audiencias')
        
    except Exception as e:
        messages.error(request, f"Erro ao cancelar audiência: {str(e)}")
        return redirect('agenda:lista_audiencias')

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(exige_permissao('editar_evento'), name='dispatch')
class ReagendarAudienciaJsonView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            dono = advogado_dono(request)
            audiencia = get_object_or_404(
                Audiencia,
                models.Q(processo__advogado_responsavel=dono) | 
                models.Q(cliente__advogado_responsavel=dono),
                pk=pk
            )
            data = json.loads(request.body)
            nova_data = parse_datetime(data.get('data_hora'))
            if not nova_data:
                return JsonResponse({'status': 'error', 'mensagem': 'Data inválida'}, status=400)
            
            data_anterior = audiencia.data_hora
            audiencia.data_hora = nova_data
            audiencia.save()
            
            LogAudiencia.objects.create(
                audiencia=audiencia,
                alterado_por=request.user,
                data_anterior=data_anterior,
                nova_data=nova_data
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensagem': str(e)}, status=500)

@method_decorator(login_required, name='dispatch')
class PainelNotificacoesView(View):
    def get(self, request):
        notificacoes = request.user.notificacoes.all().order_by('-criada_em')
        return render(request, 'notificacoes/painel.html', {
            'notificacoes': notificacoes
        })

    def post(self, request):
        notificacao_id = request.POST.get('notificacao_id')
        if notificacao_id == 'todas':
            request.user.notificacoes.filter(lida=False).update(lida=True)
        else:
            Notificacao.objects.filter(
                id=notificacao_id,
                usuario=request.user
            ).update(lida=True)
        return redirect('notificacoes:painel')