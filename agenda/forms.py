from django import forms
from .models import Audiencia, BloqueioAgenda, HorarioAtendimento
from clientes.models import Cliente
from processos.models import Processo

class AudienciaForm(forms.ModelForm):

    class Meta:
        model = Audiencia
        fields = ['processo', 'cliente', 'data_hora', 'tipo', 'local', 'vara', 'resultado']
        
        widgets = {
            'processo': forms.Select(attrs={'class': 'form-select'}),
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'data_hora': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'tipo': forms.Select(attrs={'class': 'form-select tipo-select'}),
            'local': forms.TextInput(attrs={'class': 'form-control'}),
            'vara': forms.TextInput(attrs={'class': 'form-control'}),
            'resultado': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Lógica de campos não obrigatórios
        self.fields['processo'].required = False
        self.fields['cliente'].required = False

        # Lógica de filtragem dos dropdowns
        if request:
            from usuarios.utils import advogado_dono
            self.dono = advogado_dono(request)
            self.fields['processo'].queryset = Processo.objects.filter(advogado_responsavel=self.dono).order_by('-data_cadastro')
            self.fields['cliente'].queryset = Cliente.objects.filter(advogado_responsavel=self.dono).order_by('nome')

        # Remove o campo criado_por do formulário (será definido na view)
        if 'criado_por' in self.fields:
            del self.fields['criado_por']

        # Lógica de edição corrigida - APENAS PARA EDIÇÃO
        if self.instance and self.instance.pk:
            if self.instance.data_hora:
                self.initial['data_hora'] = self.instance.data_hora.strftime('%Y-%m-%dT%H:%M')
            
            # PARA EDIÇÃO: desabilita um campo se o outro estiver preenchido
            if self.instance.processo:
                self.fields['cliente'].disabled = True
                self.fields['cliente'].required = False
            elif self.instance.cliente:
                self.fields['processo'].disabled = True
                self.fields['processo'].required = False

    def clean(self):
        cleaned_data = super().clean()
        processo = cleaned_data.get("processo")
        cliente = cleaned_data.get("cliente")
        data_hora = cleaned_data.get("data_hora")

        if data_hora and hasattr(self, 'dono'):
        # Verifica se já existe QUALQUER compromisso neste horário
            conflito_geral = Audiencia.objects.filter(
            criado_por=self.dono,  # Apenas do mesmo profissional
            data_hora=data_hora
        )
        
        # Se estiver editando, exclui a instância atual
        if self.instance and self.instance.pk:
            conflito_geral = conflito_geral.exclude(pk=self.instance.pk)
        
        if conflito_geral.exists():
            compromisso_existente = conflito_geral.first()
            cliente_existente = compromisso_existente.cliente or compromisso_existente.processo.cliente
            raise forms.ValidationError({
                'data_hora': f'❌ Já existe um compromisso agendado para {cliente_existente.nome} neste horário. Por favor, escolha outro horário.'
            })
            
        if processo and cliente:
            raise forms.ValidationError(
                "Um compromisso deve ser ligado a um Processo OU a um Cliente, não a ambos.",
                code='invalid_choice'
            )
        
        # PARA EDIÇÃO: Se é uma edição e já tem um vinculado, preserva
        if self.instance and self.instance.pk:
            if not processo and not cliente:
                # Preserva o vínculo existente
                if self.instance.processo:
                    cleaned_data['processo'] = self.instance.processo
                elif self.instance.cliente:
                    cleaned_data['cliente'] = self.instance.cliente
        else:
            # PARA CRIAÇÃO: Exige um ou outro
            if not processo and not cliente:
                raise forms.ValidationError(
                    "Um compromisso precisa estar ligado a um Processo ou a um Cliente.",
                    code='required'
                )

        # NOVA VALIDAÇÃO: Verificar se há bloqueio na data/hora
        if data_hora and hasattr(self, 'dono'):
            if self.verificar_bloqueio_agenda(self.dono, data_hora):
                raise forms.ValidationError(
                    "❌ Não é possível agendar neste horário. A agenda está bloqueada para este período.",
                    code='agenda_bloqueada'
                )
        
            disponivel, mensagem = self.verificar_horario_atendimento(self.dono, data_hora)
            if not disponivel:
                raise ValidationError({
                        'data_hora': 'Já existe um compromisso agendado para este processo na data e hora selecionada. Por favor, escolha outro horário.'
                    })
            
        return cleaned_data

    def verificar_horario_atendimento(self, profissional, data_hora):
    
        from .models import HorarioAtendimento
        
        data = data_hora.date()
        hora = data_hora.time()
        
        # Mapeamento de dias da semana
        dias_map = {
            0: 'segunda',  # Monday
            1: 'terca',    # Tuesday
            2: 'quarta',   # Wednesday
            3: 'quinta',   # Thursday
            4: 'sexta',    # Friday
            5: 'sabado',   # Saturday
            6: 'domingo',  # Sunday
        }
        
        dia_semana = dias_map.get(data.weekday())
        if not dia_semana:
            return False, "❌ Data inválida"
        
        # Busca o horário de atendimento para esse dia
        try:
            horario = HorarioAtendimento.objects.get(
                profissional=profissional,
                dia_semana=dia_semana,
                ativo=True
            )
            
            # Verifica se o horário está dentro do período de atendimento
            if hora < horario.hora_inicio or hora >= horario.hora_fim:
                return False, f"❌ Fora do horário de atendimento. Horários disponíveis: {horario.hora_inicio.strftime('%H:%M')} às {horario.hora_fim.strftime('%H:%M')}"
            
            # Verifica se o horário está em um slot válido
            from datetime import datetime, timedelta
            hora_atual = horario.hora_inicio
            duracao_slot = timedelta(minutes=horario.duracao_slot)
            slot_valido = False
            
            while hora_atual < horario.hora_fim:
                hora_fim_slot = (datetime.combine(data, hora_atual) + duracao_slot).time()
                if hora_atual <= hora < hora_fim_slot:
                    slot_valido = True
                    break
                hora_atual = (datetime.combine(data, hora_atual) + duracao_slot).time()
            
            if not slot_valido:
                return False, f"❌ Horário não corresponde aos slots de {horario.duracao_slot} minutos"
                
            return True, "✅ Horário disponível"
            
        except HorarioAtendimento.DoesNotExist:
            return False, "❌ Não há horário de atendimento cadastrado para este dia da semana"

    def verificar_bloqueio_agenda(self, profissional, data_hora):
        """
        Verifica se há bloqueio de agenda para o profissional na data/hora especificada
        """
        from datetime import date, time
        
        data = data_hora.date()
        hora = data_hora.time()
        
        # Busca bloqueios ativos para o profissional na data especificada
        bloqueios = BloqueioAgenda.objects.filter(
            profissional=profissional,
            data_inicio__lte=data,
            data_fim__gte=data,
            ativo=True
        )
        
        for bloqueio in bloqueios:
            if bloqueio.dia_todo:
                # Bloqueio para o dia todo
                return True
            elif bloqueio.hora_inicio and bloqueio.hora_fim:
                # Bloqueio por horário específico
                if hora >= bloqueio.hora_inicio and hora <= bloqueio.hora_fim:
                    return True
        
        return False

class HorarioAtendimentoForm(forms.ModelForm):
    class Meta:
        model = HorarioAtendimento
        fields = ['dia_semana', 'hora_inicio', 'hora_fim', 'duracao_slot', 'max_compromissos', 'ativo']
        widgets = {
            'dia_semana': forms.Select(attrs={'class': 'form-select'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'hora_fim': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'duracao_slot': forms.NumberInput(attrs={'class': 'form-control', 'min': '15', 'step': '15'}),
            'max_compromissos': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_fim = cleaned_data.get('hora_fim')
        
        if hora_inicio and hora_fim and hora_fim <= hora_inicio:
            raise forms.ValidationError("Hora fim deve ser posterior à hora início")
        
        return cleaned_data

class BloqueioAgendaForm(forms.ModelForm):
    class Meta:
        model = BloqueioAgenda
        fields = ['titulo', 'descricao', 'data_inicio', 'data_fim', 'hora_inicio', 'hora_fim', 'dia_todo', 'tipo_bloqueio']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'data_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_fim': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'hora_fim': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'dia_todo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tipo_bloqueio': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        dia_todo = cleaned_data.get('dia_todo')
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_fim = cleaned_data.get('hora_fim')
        
        if data_fim and data_inicio and data_fim < data_inicio:
            raise forms.ValidationError("Data fim não pode ser anterior à data início")
        
        if not dia_todo:
            if not hora_inicio or not hora_fim:
                raise forms.ValidationError("Para bloqueio parcial, informe hora início e fim")
            if hora_fim <= hora_inicio:
                raise forms.ValidationError("Hora fim deve ser posterior à hora início")
        
        return cleaned_data
    
from django import forms
from django.core.exceptions import ValidationError
from .models import Compromisso

class CompromissoForm(forms.ModelForm):
    class Meta:
        model = Compromisso
        fields = '__all__'
