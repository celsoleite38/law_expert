from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import Notificacao
from usuarios.utils import exige_permissao

@method_decorator(login_required, name='dispatch')
class PainelNotificacoesView(View):
    def get(self, request):
        notificacoes = request.user.notificacoes.all().order_by('-criada_em')
        return render(request, 'notificacoes/painel.html', {'notificacoes': notificacoes})

    def post(self, request):
        notificacao_id = request.POST.get('notificacao_id')

        if notificacao_id == 'todas':
            request.user.notificacoes.filter(lida=False).update(lida=True)
        else:
            Notificacao.objects.filter(id=notificacao_id, usuario=request.user).update(lida=True)

        return redirect('notificacoes:painel')
