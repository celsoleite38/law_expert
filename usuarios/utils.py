# usuarios/utils.py (VERSÃO FINAL CORRIGIDA)

from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

# ----------------------------------------------------------------
# Função 1: exige_permissao (Versão limpa, sem diagnóstico)
# ----------------------------------------------------------------
def exige_permissao(permissao_necessaria, redirect_to='core:dashboard'):
    """
    Decorator que verifica permissões de forma mais robusta
    Args:
        permissao_necessaria (str): Nome da permissão requerida
        redirect_to (str): Nome da URL para redirecionamento em caso de falha
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Verificação simplificada do usuário
            if not hasattr(request, 'user'):
                messages.error(request, 'Sessão inválida')
                return redirect(redirect_to)
            
            user = request.user
            
            # Advogados têm acesso completo
            if user.is_authenticated and user.tipo_usuario == 'ADV':
                return view_func(request, *args, **kwargs)
            
            # Verificação para colaboradores
            if user.is_authenticated and user.tipo_usuario == 'COLAB':
                colaborador = getattr(user, 'colaborador_vinculado', None)
                if colaborador and getattr(colaborador.permissoes, permissao_necessaria, False):
                    return view_func(request, *args, **kwargs)
            
            messages.error(request, f'Acesso negado. Permissão requerida: {permissao_necessaria}')
            return redirect(redirect_to)
        
        return _wrapped_view
    return decorator

# ----------------------------------------------------------------
# Função 2: advogado_dono (LÓGICA CORRIGIDA E SIMPLIFICADA)
# ----------------------------------------------------------------
def advogado_dono(request):
    """
    Retorna o usuário do advogado principal,
    seja o usuário logado um advogado ou um colaborador.
    """
    user = request.user

    # Se o usuário logado for um colaborador, retorne o advogado responsável por ele.
    # O related_name 'colaborador_vinculado' no modelo User nos dá acesso ao objeto Colaborador.
    if hasattr(user, 'colaborador_vinculado'):
        return user.colaborador_vinculado.advogado_responsavel
    
    # Se não for um colaborador (ou seja, é o próprio advogado), retorne o usuário logado.
    return user
