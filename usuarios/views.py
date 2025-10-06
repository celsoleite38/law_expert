from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

from usuarios.utils import exige_permissao, advogado_dono
from usuarios.models import Ativacao, PerfilProfissional, Colaborador, PermissaoColaborador
from usuarios.forms import (
    FormCadastroUsuario, PerfilProfissionalForm, CadastroColaboradorForm,
    PermissaoColaboradorForm, ColaboradorForm, AlterarSenhaForm
)

from clientes.models import Cliente
from clientes.forms import ClienteForm
from processos.models import Processo

import uuid

# --- Públicas / sem login ---

def cadastrar_usuario(request):
    if request.method == 'POST':
        form = FormCadastroUsuario(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.is_active = False
            usuario.save()

            token = str(uuid.uuid4())
            Ativacao.objects.create(
                user=usuario,
                token=token,
                email=usuario.email
            )

            link_ativacao = request.build_absolute_uri(f'/usuarios/ativar/{token}/')
            send_mail(
                subject='Ative sua conta',
                message=f'Olá, {usuario.username}!\nClique no link para ativar sua conta:\n{link_ativacao}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                fail_silently=False,
            )

            messages.success(request, 'Cadastro realizado! Verifique seu e-mail para ativar a conta.')
            return redirect('usuarios:login')
    else:
        form = FormCadastroUsuario()
    return render(request, 'usuarios/cadastro.html', {'form': form})


def ativar_conta(request, token):
    ativacao = get_object_or_404(Ativacao, token=token)
    if not ativacao.ativo:
        ativacao.ativo = True
        ativacao.user.is_active = True
        ativacao.user.save()
        ativacao.save()
        messages.success(request, 'Conta ativada com sucesso! Faça login abaixo.')
    else:
        messages.warning(request, 'Este link já foi utilizado.')
    return redirect('usuarios:login')


def logar_usuario(request):
    if request.method == 'POST':
        username = request.POST['username']
        senha = request.POST['password']
        user = authenticate(request, username=username, password=senha)
        if user:
            login(request, user)
            return redirect('usuarios:dashboard')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')
    return render(request, 'usuarios/login.html')


def logout_usuario(request):
    logout(request)
    return redirect('usuarios:login')


@login_required
def dashboard(request):
    return render(request, 'core/dashboard.html')


# --- Perfil profissional do advogado ---

@login_required
def editar_advogado(request):
    perfil, _ = PerfilProfissional.objects.get_or_create(usuario=request.user)
    if request.method == 'POST':
        form = PerfilProfissionalForm(request.POST, request.FILES, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('usuarios:dashboard')
        else:
            messages.error(request, 'Por favor, corrija os erros abaixo.')
    else:
        form = PerfilProfissionalForm(instance=perfil)
    return render(request, 'usuarios/editar_advogado.html', {'form': form})


# --- Gestão de colaboradores ---

@exige_permissao('gerenciar_colaboradores')
@login_required
def colaborador(request):
    if not hasattr(request.user, 'perfilprofissional') or request.user.tipo_usuario != 'ADV':
        messages.error(request, 'Você não tem permissão para cadastrar colaboradores.')
        return redirect('usuarios:dashboard')

    colaboradores = Colaborador.objects.filter(advogado_responsavel=request.user)

    if request.method == 'POST':
        form = CadastroColaboradorForm(request.POST)
        if form.is_valid():
            colaborador = form.save(commit=False)
            colaborador.advogado_responsavel = request.user
            senha = form.cleaned_data['senha']
            status_ativo = form.cleaned_data.get('is_active', True)

            novo_usuario = User.objects.create_user(
                username=colaborador.email,
                email=colaborador.email,
                password=senha
            )
            novo_usuario.is_active = status_ativo
            novo_usuario.save()

            colaborador.usuario = novo_usuario
            colaborador.save()
            PermissaoColaborador.objects.create(colaborador=colaborador)

            messages.success(request, 'Colaborador cadastrado com sucesso!')
            return redirect('usuarios:colaborador')
        else:
            messages.error(request, 'Por favor, corrija os erros abaixo.')
    else:
        form = CadastroColaboradorForm()

    return render(request, 'usuarios/colaborador.html', {
        'form': form,
        'colaboradores': colaboradores
    })


@exige_permissao('gerenciar_colaboradores')
@login_required
def gerenciar_permissoes_colaborador(request, colaborador_id):
    colaborador = get_object_or_404(Colaborador, id=colaborador_id, advogado_responsavel=request.user)
    permissoes, _ = PermissaoColaborador.objects.get_or_create(colaborador=colaborador)

    if request.method == 'POST':
        form = PermissaoColaboradorForm(request.POST, instance=permissoes)
        if form.is_valid():
            form.save()
            messages.success(request, 'Permissões atualizadas com sucesso!')
            return redirect('usuarios:colaborador')
    else:
        form = PermissaoColaboradorForm(instance=permissoes)

    return render(request, 'usuarios/painel_permissoes.html', {
        'colaborador': colaborador,
        'form': form
    })


@exige_permissao('gerenciar_colaboradores')
@login_required
def alterar_senha_colaborador(request, colaborador_id):
    colaborador = get_object_or_404(Colaborador, id=colaborador_id, advogado_responsavel=request.user)

    if not colaborador.usuario:
        messages.error(request, 'Esse colaborador ainda não possui um usuário vinculado.')
        return redirect('usuarios:colaborador')

    if request.method == 'POST':
        nova_senha = request.POST.get('nova_senha')
        if nova_senha:
            colaborador.usuario.password = make_password(nova_senha)
            colaborador.usuario.save()
            messages.success(request, f'Senha de {colaborador.nome} alterada com sucesso!')
            return redirect('usuarios:colaborador')
        else:
            messages.error(request, 'Informe uma nova senha válida.')

    return render(request, 'usuarios/alterar_senha_colaborador.html', {'colaborador': colaborador})


@login_required
def editar_colaborador(request, pk):
    colaborador = get_object_or_404(Colaborador, pk=pk)
    user = colaborador.usuario

    if request.method == 'POST':
        form = ColaboradorForm(request.POST, instance=colaborador, usuario_instance=user)
        form_senha = AlterarSenhaForm(request.POST)

        if form.is_valid() and form_senha.is_valid():
            form.save()
            nova_senha = form_senha.cleaned_data['nova_senha']

            if user:
                user.email = colaborador.email
                user.username = colaborador.email
                user.is_active = form.cleaned_data.get('is_active', True)
                if nova_senha:
                    user.set_password(nova_senha)
                user.save()

            messages.success(request, f'{colaborador.nome} atualizado com sucesso!')
            return redirect('usuarios:colaborador')
    else:
        form = ColaboradorForm(instance=colaborador, usuario_instance=user)
        form_senha = AlterarSenhaForm()

    return render(request, 'usuarios/editar_colaborador.html', {
        'form': form,
        'form_senha': form_senha,
        'colaborador': colaborador
    })


# --- Clientes ---
@exige_permissao('listar_clientes')
@login_required
def listar_clientes(request):
    dono = advogado_dono(request)
    clientes = Cliente.objects.filter(advogado_responsavel=dono)

    # 🔒 Verificação de permissão real
    tem_permissao = False

    if hasattr(request.user, 'colaborador_vinculado'):
        colaborador = request.user.colaborador_vinculado
        try:
            tem_permissao = colaborador.permissoes.listar_clientes
        except AttributeError:
            tem_permissao = False
    else:
        # ✅ Se for advogado, acesso liberado
        tem_permissao = True

    print('🧠 Permissão listar_clientes na view:', tem_permissao)

    return render(request, 'clientes/lista.html', {
        'clientes': clientes,
        'tem_permissao': tem_permissao
    })



@login_required
@exige_permissao('cadastrar_cliente')
def cadastrar_cliente(request):
    dono = advogado_dono(request)

    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.advogado_responsavel = dono
            cliente.save()
            messages.success(request, 'Cliente cadastrado com sucesso!')
            return redirect('usuarios:listar_clientes')
    else:
        form = ClienteForm()

    return render(request, 'clientes/cadastro.html', {'form': form})


# --- Processos ---
@exige_permissao('listar_processos')
@login_required
def listar_processos(request):
    dono = advogado_dono(request)
    
    processos = Processo.objects.filter(advogado_responsavel=dono)
    return render(request, 'processos/lista.html', {'processos': processos})





@login_required
def diagnostico_acesso_colaborador(request):
    dono = advogado_dono(request)

    clientes = Cliente.objects.filter(advogado_responsavel=dono)
    processos = Processo.objects.filter(advogado_responsavel=dono)

    contexto = {
        'usuario_logado': request.user,
        'advogado_identificado': dono,
        'clientes': clientes,
        'processos': processos,
    }

    return render(request, 'diagnostico/resultado.html', contexto)
