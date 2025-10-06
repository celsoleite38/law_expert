from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Colaborador, PerfilProfissional, PermissaoColaborador


# --- Cadastro de usuário padrão ---
class FormCadastroUsuario(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


# --- Perfil profissional do advogado ---
class PerfilProfissionalForm(forms.ModelForm):
    class Meta:
        model = PerfilProfissional
        fields = [
            'nome_completo', 'cpf', 'oab', 'nome_escritorio', 'logotipo',
            'endereco_escritorio', 'telefone_escritorio', 'celular'
        ]
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control'}),
            'oab': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_escritorio': forms.TextInput(attrs={'class': 'form-control'}),
            'logotipo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'endereco_escritorio': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone_escritorio': forms.TextInput(attrs={'class': 'form-control'}),
            'celular': forms.TextInput(attrs={'class': 'form-control'}),
        }


# --- Cadastro de colaborador ---
class CadastroColaboradorForm(forms.ModelForm):
    senha = forms.CharField(widget=forms.PasswordInput, label="Senha de acesso")

    is_active = forms.BooleanField(
        required=False,
        label='Usuário ativo',
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Colaborador
        fields = ['nome', 'email', 'telefone', 'funcao']


# --- Edição de colaborador (inclui controle de ativação) ---
class ColaboradorForm(forms.ModelForm):
    is_active = forms.BooleanField(
        required=False,
        label='Usuário ativo',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Colaborador
        fields = ['nome', 'email', 'funcao']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'funcao': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.usuario_instance = kwargs.pop('usuario_instance', None)
        super().__init__(*args, **kwargs)
        if self.usuario_instance:
            self.fields['is_active'].initial = self.usuario_instance.is_active

    def save(self, commit=True):
        colaborador = super().save(commit)
        if self.usuario_instance:
            self.usuario_instance.is_active = self.cleaned_data.get('is_active', True)
            if commit:
                self.usuario_instance.save()
        return colaborador


# --- Permissões do colaborador ---
class PermissaoColaboradorForm(forms.ModelForm):
    class Meta:
        model = PermissaoColaborador

        fields = [
            # 👥 Clientes
            'listar_clientes', 'visualizar_cliente', 'cadastrar_cliente',
            'editar_cliente', 'excluir_cliente', 'exportar_clientes',

            # ⚖️ Processos
            'listar_processos', 'visualizar_processo', 'cadastrar_processo',
            'editar_processo', 'excluir_processo', 'atualizar_status_processo',

            # 📅 Agenda e Audiências
            'ver_agenda', 'adicionar_evento', 'editar_evento',
            'excluir_evento', 'compartilhar_agenda', 'editar_audiencias',

            # 📦 Documentos
            'acessar_documentos', 'upload_documento', 'download_documento',
            'excluir_documento', 'visualizar_documentos',

            # ⚙️ Sistema
            'gerenciar_colaboradores', 'configurar_layout', 'visualizar_relatorios',
        ]

        # ✅ Usa widget de checkbox uniforme
        widgets = {
            field: forms.CheckboxInput(attrs={'class': 'form-check-input'})
            for field in fields
        }

        # ✅ Labels customizados para facilitar leitura (opcional)
        labels = {
            'listar_clientes': 'Ver lista de clientes',
            'visualizar_cliente': 'Ver detalhes do cliente',
            'cadastrar_cliente': 'Cadastrar cliente',
            'editar_cliente': 'Editar cliente',
            'excluir_cliente': 'Excluir cliente',
            'exportar_clientes': 'Exportar lista de clientes',

            'listar_processos': 'Ver lista de processos',
            'visualizar_processo': 'Ver detalhes do processo',
            'cadastrar_processo': 'Cadastrar processo',
            'editar_processo': 'Editar processo',
            'excluir_processo': 'Excluir processo',
            'atualizar_status_processo': 'Atualizar status do processo',

            'ver_agenda': 'Ver agenda',
            'adicionar_evento': 'Adicionar evento à agenda',
            'editar_evento': 'Editar evento',
            'excluir_evento': 'Excluir evento',
            'compartilhar_agenda': 'Compartilhar agenda',
            'editar_audiencias': 'Editar audiências',

            'acessar_documentos': 'Acessar documentos',
            'upload_documento': 'Enviar documentos',
            'download_documento': 'Baixar documentos',
            'excluir_documento': 'Excluir documentos',
            'visualizar_documentos': 'Visualizar documentos',

            'gerenciar_colaboradores': 'Gerenciar colaboradores',
            'configurar_layout': 'Configurar layout do painel',
            'visualizar_relatorios': 'Visualizar relatórios',
        }


# --- Alteração de senha ---
class AlterarSenhaForm(forms.Form):
    nova_senha = forms.CharField(
        label='Nova senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        max_length=128,
        required=False  # Deixar em branco mantém senha atual
    )
