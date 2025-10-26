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
from django.utils import timezone
from datetime import datetime
from django.contrib.auth import get_user_model

from .models import Audiencia, BloqueioAgenda, HorarioAtendimento, LogAudiencia
from processos.models import Processo
from notificacoes.models import Notificacao
from .forms import AudienciaForm, BloqueioAgendaForm, HorarioAtendimentoForm
from usuarios.utils import exige_permissao, advogado_dono

User = get_user_model()

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
        # Define o usuário logado como criado_por
        form.instance.criado_por = self.request.user
        
        # Garante que pelo menos cliente ou processo está definido
        if not form.instance.processo and not form.instance.cliente:
            form.add_error(None, "O compromisso deve estar vinculado a um Processo ou a um Cliente")
            return self.form_invalid(form)
            
        messages.success(self.request, "✅ Compromisso agendado com sucesso!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "❌ Erro ao agendar compromisso. Verifique os dados informados.")
        return super().form_invalid(form)

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
        # PARA EDIÇÃO: Preserva os vínculos existentes se não foram alterados
        if not form.instance.processo and not form.instance.cliente:
            # Se ambos estão vazios, preserva os originais
            if self.object.processo:
                form.instance.processo = self.object.processo
            elif self.object.cliente:
                form.instance.cliente = self.object.cliente
        
        response = super().form_valid(form)
        messages.success(self.request, "✅ Compromisso atualizado com sucesso!")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "❌ Erro ao atualizar compromisso. Verifique os dados.")
        return super().form_invalid(form)

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

# --- Views para Horários de Atendimento ---

@method_decorator(exige_permissao('gerenciar_agenda'), name='dispatch')
class HorarioAtendimentoListView(LoginRequiredMixin, ListView):
    model = HorarioAtendimento
    template_name = 'agenda/horarios_atendimento.html'
    context_object_name = 'horarios'
    
    def get_queryset(self):
        dono = advogado_dono(self.request)
        return HorarioAtendimento.objects.filter(profissional=dono).order_by('dia_semana', 'hora_inicio')

@method_decorator(exige_permissao('gerenciar_agenda'), name='dispatch')
class HorarioAtendimentoCreateView(LoginRequiredMixin, CreateView):
    model = HorarioAtendimento
    form_class = HorarioAtendimentoForm
    template_name = 'agenda/horario_atendimento_form.html'
    success_url = reverse_lazy('agenda:lista_horarios')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.profissional = advogado_dono(self.request)
        return super().form_valid(form)

@method_decorator(exige_permissao('gerenciar_agenda'), name='dispatch')
class HorarioAtendimentoUpdateView(LoginRequiredMixin, UpdateView):
    model = HorarioAtendimento
    form_class = HorarioAtendimentoForm
    template_name = 'agenda/horario_atendimento_form.html'
    success_url = reverse_lazy('agenda:lista_horarios')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_queryset(self):
        dono = advogado_dono(self.request)
        return HorarioAtendimento.objects.filter(profissional=dono)

# --- Views para Bloqueios de Agenda ---

@method_decorator(exige_permissao('gerenciar_agenda'), name='dispatch')
class BloqueioAgendaListView(LoginRequiredMixin, ListView):
    model = BloqueioAgenda
    template_name = 'agenda/bloqueios_agenda.html'
    context_object_name = 'bloqueios'
    
    def get_queryset(self):
        dono = advogado_dono(self.request)
        return BloqueioAgenda.objects.filter(profissional=dono).order_by('-data_inicio', '-data_fim')

@method_decorator(exige_permissao('gerenciar_agenda'), name='dispatch')
class BloqueioAgendaCreateView(LoginRequiredMixin, CreateView):
    model = BloqueioAgenda
    form_class = BloqueioAgendaForm
    template_name = 'agenda/bloqueio_agenda_form.html'
    success_url = reverse_lazy('agenda:lista_bloqueios')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.profissional = advogado_dono(self.request)
        return super().form_valid(form)

@method_decorator(exige_permissao('gerenciar_agenda'), name='dispatch')
class BloqueioAgendaUpdateView(LoginRequiredMixin, UpdateView):
    model = BloqueioAgenda
    form_class = BloqueioAgendaForm
    template_name = 'agenda/bloqueio_agenda_form.html'
    success_url = reverse_lazy('agenda:lista_bloqueios')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_queryset(self):
        dono = advogado_dono(self.request)
        return BloqueioAgenda.objects.filter(profissional=dono)

# --- Views Adicionais ---

@method_decorator(exige_permissao('ver_agenda'), name='dispatch')
class VerificarDisponibilidadeView(LoginRequiredMixin, View):
    def get(self, request):
        """API para verificar disponibilidade de horários"""
        profissional_id = request.GET.get('profissional_id')
        data_str = request.GET.get('data')
        
        if not profissional_id or not data_str:
            return JsonResponse({'error': 'Parâmetros faltando'}, status=400)
        
        try:
            dono = advogado_dono(request)
            profissional = User.objects.get(id=profissional_id)
            
            # Verifica se o usuário tem permissão para ver este profissional
            if profissional != dono and not request.user.is_superuser:
                return JsonResponse({'error': 'Sem permissão'}, status=403)
            
            data_alvo = datetime.strptime(data_str, '%Y-%m-%d').date()
            from .utils import get_horarios_disponiveis
            horarios_disponiveis = get_horarios_disponiveis(profissional, data_alvo)
            
            return JsonResponse({
                'horarios': horarios_disponiveis,
                'data': data_str,
                'profissional': profissional.get_full_name()
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@method_decorator(exige_permissao('gerenciar_agenda'), name='dispatch')
class PainelControleAgendaView(LoginRequiredMixin, TemplateView):
    """Painel principal para controle da agenda"""
    template_name = 'agenda/painel_controle.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dono = advogado_dono(self.request)
        
        # Estatísticas
        context['total_horarios'] = HorarioAtendimento.objects.filter(profissional=dono, ativo=True).count()
        context['total_bloqueios_ativos'] = BloqueioAgenda.objects.filter(profissional=dono, ativo=True).count()
        context['proximos_compromissos'] = Audiencia.objects.filter(
            models.Q(processo__advogado_responsavel=dono) | 
            models.Q(cliente__advogado_responsavel=dono),
            data_hora__gte=timezone.now()
        ).order_by('data_hora')[:5]
        
        # Bloqueios futuros
        context['proximos_bloqueios'] = BloqueioAgenda.objects.filter(
            profissional=dono,
            data_fim__gte=timezone.now().date(),
            ativo=True
        ).order_by('data_inicio')[:5]
        
        return context

@method_decorator(exige_permissao('gerenciar_agenda'), name='dispatch')
class ConfiguracoesAgendaView(LoginRequiredMixin, TemplateView):
    """Página de configurações da agenda"""
    template_name = 'agenda/configuracoes.html'

# Views para deletar horários e bloqueios
@exige_permissao('gerenciar_agenda')
def deletar_horario(request, pk):
    dono = advogado_dono(request)
    
    try:
        horario = HorarioAtendimento.objects.filter(profissional=dono, pk=pk).first()
        if not horario:
            messages.error(request, "Horário não encontrado")
            return redirect('agenda:lista_horarios')
            
        horario.delete()
        messages.success(request, "Horário deletado com sucesso!")
        return redirect('agenda:lista_horarios')
        
    except Exception as e:
        messages.error(request, f"Erro ao deletar horário: {str(e)}")
        return redirect('agenda:lista_horarios')

@exige_permissao('gerenciar_agenda')
def deletar_bloqueio(request, pk):
    dono = advogado_dono(request)
    
    try:
        bloqueio = BloqueioAgenda.objects.filter(profissional=dono, pk=pk).first()
        if not bloqueio:
            messages.error(request, "Bloqueio não encontrado")
            return redirect('agenda:lista_bloqueios')
            
        bloqueio.delete()
        messages.success(request, "Bloqueio deletado com sucesso!")
        return redirect('agenda:lista_bloqueios')
        
    except Exception as e:
        messages.error(request, f"Erro ao deletar bloqueio: {str(e)}")
        return redirect('agenda:lista_bloqueios')

# View para verificar disponibilidade ao criar audiência
@method_decorator(exige_permissao('adicionar_evento'), name='dispatch')
class VerificarDisponibilidadeAudienciaView(LoginRequiredMixin, View):
    def post(self, request):
        """Verifica disponibilidade ao criar/editar audiência"""
        try:
            data = json.loads(request.body)
            data_hora_str = data.get('data_hora')
            profissional_id = data.get('profissional_id')
            audiencia_id = data.get('audiencia_id')  # Para edição
            
            if not data_hora_str or not profissional_id:
                return JsonResponse({'error': 'Dados insuficientes'}, status=400)
            
            data_hora = parse_datetime(data_hora_str)
            if not data_hora:
                return JsonResponse({'error': 'Data/hora inválida'}, status=400)
            
            profissional = User.objects.get(id=profissional_id)
            from .utils import verificar_disponibilidade
            disponivel, mensagem = verificar_disponibilidade(profissional, data_hora)
            
            return JsonResponse({
                'disponivel': disponivel,
                'mensagem': mensagem,
                'data_hora': data_hora_str
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

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