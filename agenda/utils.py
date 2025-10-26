# agenda/utils.py
from datetime import datetime, date, time, timedelta
from django.utils import timezone
from django.db import models
from .models import HorarioAtendimento, BloqueioAgenda, Audiencia
from django.contrib.auth import get_user_model

User = get_user_model()

def get_horarios_disponiveis(profissional, data_alvo):
    """Retorna os horários disponíveis para um profissional em uma data específica"""
    
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
    
    dia_semana = dias_map.get(data_alvo.weekday())
    if not dia_semana:
        return []
    
    # Busca o horário de atendimento para esse dia
    try:
        horario = HorarioAtendimento.objects.get(
            profissional=profissional,
            dia_semana=dia_semana,
            ativo=True
        )
    except HorarioAtendimento.DoesNotExist:
        return []
    
    # Verifica bloqueios para essa data
    bloqueios = BloqueioAgenda.objects.filter(
        profissional=profissional,
        data_inicio__lte=data_alvo,
        data_fim__gte=data_alvo,
        ativo=True
    )
    
    # Se há bloqueio para o dia todo, retorna vazio
    if bloqueios.filter(dia_todo=True).exists():
        return []
    
    # Gera os slots disponíveis
    slots = []
    hora_atual = horario.hora_inicio
    duracao_slot = timedelta(minutes=horario.duracao_slot)
    
    while hora_atual < horario.hora_fim:
        hora_fim_slot = (datetime.combine(date.today(), hora_atual) + duracao_slot).time()
        
        # Verifica se o slot está dentro do horário de trabalho
        if hora_fim_slot > horario.hora_fim:
            break
        
        # Verifica se o slot não está bloqueado
        slot_bloqueado = False
        for bloqueio in bloqueios:
            if bloqueio.hora_inicio and bloqueio.hora_fim:
                if hora_atual >= bloqueio.hora_inicio and hora_fim_slot <= bloqueio.hora_fim:
                    slot_bloqueado = True
                    break
        
        # Verifica se não há audiência agendada nesse horário
        if not slot_bloqueado:
            audiencias_existentes = Audiencia.objects.filter(
                models.Q(processo__advogado_responsavel=profissional) | 
                models.Q(cliente__advogado_responsavel=profissional),
                data_hora__date=data_alvo,
                data_hora__time=hora_atual
            ).count()
            
            if audiencias_existentes < horario.max_compromissos:
                slots.append({
                    'hora': hora_atual.strftime('%H:%M'),
                    'hora_formatada': hora_atual.strftime('%H:%M'),
                    'disponivel': True
                })
        
        # Avança para o próximo slot
        hora_atual = (datetime.combine(date.today(), hora_atual) + duracao_slot).time()
    
    return slots


def verificar_disponibilidade(profissional, data_hora, audiencia_existente=None):
    from .models import HorarioAtendimento, BloqueioAgenda, Audiencia
    from datetime import datetime, timedelta
    
    data = data_hora.date()
    hora = data_hora.time()
    
    # 1. Verificar horário de atendimento
    dia_semana = data.weekday()
    dias_map = {
        0: 'segunda', 1: 'terca', 2: 'quarta', 3: 'quinta', 
        4: 'sexta', 5: 'sabado', 6: 'domingo'
    }
    
    try:
        horario = HorarioAtendimento.objects.get(
            profissional=profissional,
            dia_semana=dias_map.get(dia_semana),
            ativo=True
        )
        
        # Verifica se está dentro do horário
        if hora < horario.hora_inicio or hora >= horario.hora_fim:
            return False, f"❌ Fora do horário de atendimento ({horario.hora_inicio.strftime('%H:%M')} às {horario.hora_fim.strftime('%H:%M')})"
        
        # Verifica se é um slot válido
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
            
    except HorarioAtendimento.DoesNotExist:
        return False, "❌ Não há horário de atendimento cadastrado para este dia"
    
    # 2. Verifica bloqueios
    bloqueios = BloqueioAgenda.objects.filter(
        profissional=profissional,
        data_inicio__lte=data,
        data_fim__gte=data,
        ativo=True
    )
    
    for bloqueio in bloqueios:
        if bloqueio.dia_todo:
            return False, "❌ Agenda bloqueada para este dia"
        
        if bloqueio.hora_inicio and bloqueio.hora_fim:
            if hora >= bloqueio.hora_inicio and hora < bloqueio.hora_fim:
                return False, f"❌ Agenda bloqueada neste horário ({bloqueio.hora_inicio.strftime('%H:%M')} às {bloqueio.hora_fim.strftime('%H:%M')})"
    
    # 3. Verifica conflitos com outras audiências
    audiencias_existentes = Audiencia.objects.filter(
        models.Q(processo__advogado_responsavel=profissional) | 
        models.Q(cliente__advogado_responsavel=profissional),
        data_hora__date=data,
        data_hora__time=hora
    )
    
    # Se é uma edição, exclui a própria audiência da contagem
    if audiencia_existente:
        audiencias_existentes = audiencias_existentes.exclude(pk=audiencia_existente.pk)
    
    if audiencias_existentes.count() >= horario.max_compromissos:
        return False, "❌ Horário já ocupado"
    
    return True, "✅ Horário disponível"

def validar_agendamento(profissional, data_hora, audiencia_existente=None):
    """
    Valida se um agendamento é possível
    audiencia_existente: para evitar conflito com a própria audiência sendo editada
    """
    disponivel, mensagem = verificar_disponibilidade(profissional, data_hora)
    
    if not disponivel:
        return False, mensagem
    
    # Se é uma edição, verifica se não está conflitando com ela mesma
    if audiencia_existente:
        mesmo_horario = Audiencia.objects.filter(
            models.Q(processo__advogado_responsavel=profissional) | 
            models.Q(cliente__advogado_responsavel=profissional),
            data_hora__date=data_hora.date(),
            data_hora__time=data_hora.time()
        ).exclude(pk=audiencia_existente.pk).count()
        
        if mesmo_horario > 0:
            return False, "Horário já ocupado por outro compromisso"
    
    return True, "Agendamento válido"

def verificar_disponibilidade_agendamento(profissional, data_hora):
    """
    Verifica se é possível agendar para um profissional em uma data/hora específica
    Retorna (disponivel, mensagem)
    """
    from .models import BloqueioAgenda, HorarioAtendimento
    from datetime import datetime, time
    
    data = data_hora.date()
    hora = data_hora.time()
    
    # 1. Verificar bloqueios de agenda
    bloqueios = BloqueioAgenda.objects.filter(
        profissional=profissional,
        data_inicio__lte=data,
        data_fim__gte=data,
        ativo=True
    )
    
    for bloqueio in bloqueios:
        if bloqueio.dia_todo:
            return False, "❌ Agenda bloqueada para este dia"
        elif bloqueio.hora_inicio and bloqueio.hora_fim:
            if hora >= bloqueio.hora_inicio and hora <= bloqueio.hora_fim:
                return False, f"❌ Agenda bloqueada neste horário ({bloqueio.hora_inicio.strftime('%H:%M')} às {bloqueio.hora_fim.strftime('%H:%M')})"
    
    # 2. Verificar horário de atendimento (opcional - se você quiser)
    # try:
    #     dia_semana = data.strftime('%A').lower()
    #     dias_map = {
    #         'monday': 'segunda', 'tuesday': 'terca', 'wednesday': 'quarta',
    #         'thursday': 'quinta', 'friday': 'sexta', 'saturday': 'sabado',
    #         'sunday': 'domingo'
    #     }
    #     horario = HorarioAtendimento.objects.get(
    #         profissional=profissional,
    #         dia_semana=dias_map.get(dia_semana),
    #         ativo=True
    #     )
    #     if hora < horario.hora_inicio or hora > horario.hora_fim:
    #         return False, f"❌ Fora do horário de atendimento ({horario.hora_inicio.strftime('%H:%M')} às {horario.hora_fim.strftime('%H:%M')})"
    # except HorarioAtendimento.DoesNotExist:
    #     pass  # Se não há horário definido, permite o agendamento
    
    return True, "✅ Horário disponível"