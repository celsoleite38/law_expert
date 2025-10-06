from django.db import models
from django.contrib.auth.models import User


# --- Ativação de conta por e-mail ---
class Ativacao(models.Model):
    token = models.CharField(max_length=64)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    ativo = models.BooleanField(default=False)
    email = models.EmailField(max_length=254, default='example@example.com')

    def __str__(self):
        return self.user.username


# --- Perfil profissional exclusivo para advogados ---
class PerfilProfissional(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    nome_completo = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14)
    oab = models.CharField(max_length=20)
    endereco_escritorio = models.CharField(max_length=255, blank=True, null=True)
    telefone_escritorio = models.CharField(max_length=20, blank=True, null=True)
    celular = models.CharField(max_length=20, blank=True, null=True)
    nome_escritorio = models.CharField(max_length=101, null=True, blank=True)
    logotipo = models.ImageField(upload_to='logos_profissionais/', blank=True, null=True)

    def __str__(self):
        return self.nome_completo


# --- Colaboradores vinculados ao advogado ---
class Colaborador(models.Model):
    advogado_responsavel = models.ForeignKey(User, on_delete=models.CASCADE, related_name='colaboradores')
    nome = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=20, blank=True)

    FUNCOES = [
        ('SEC', 'Secretária'),
        ('AUX', 'Advogado Auxiliar'),
    ]
    funcao = models.CharField(max_length=3, choices=FUNCOES)

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='colaborador_vinculado'
    )

    def __str__(self):
        return f'{self.get_funcao_display()} - {self.nome}'


# --- Extensão para definir tipo de usuário baseado no perfil ---
def tipo_usuario(self):
    try:
        if hasattr(self, 'perfilprofissional'):
            return 'ADV'
        elif hasattr(self, 'colaborador_vinculado'):
            return 'COLAB'
    except:
        return None
    return 'OUTRO'

User.add_to_class('tipo_usuario', property(tipo_usuario))


# --- Permissões específicas para cada colaborador ---
class PermissaoColaborador(models.Model):
    colaborador = models.OneToOneField(Colaborador, on_delete=models.CASCADE, related_name='permissoes')

    # 📁 Clientes
    cadastrar_cliente = models.BooleanField(default=True)
    editar_cliente = models.BooleanField(default=False)
    listar_clientes = models.BooleanField(default=True)
    visualizar_cliente = models.BooleanField(default=True)
    excluir_cliente = models.BooleanField(default=False)
    exportar_clientes = models.BooleanField(default=False)

    # ⚖️ Processos
    cadastrar_processo = models.BooleanField(default=False)
    editar_processo = models.BooleanField(default=False)
    listar_processos = models.BooleanField(default=False)
    visualizar_processo = models.BooleanField(default=False)
    excluir_processo = models.BooleanField(default=False)
    atualizar_status_processo = models.BooleanField(default=False)

    # 📅 Agenda / Audiências
    ver_agenda = models.BooleanField(default=False)
    adicionar_evento = models.BooleanField(default=False)
    editar_evento = models.BooleanField(default=False)
    excluir_evento = models.BooleanField(default=False)
    editar_audiencias = models.BooleanField(default=False)
    compartilhar_agenda = models.BooleanField(default=False)

    # 📦 Documentos
    acessar_documentos = models.BooleanField(default=False)
    upload_documento = models.BooleanField(default=False)
    download_documento = models.BooleanField(default=False)
    excluir_documento = models.BooleanField(default=False)
    visualizar_documentos = models.BooleanField(default=False)

    # 🔧 Sistema / Gerencial
    gerenciar_colaboradores = models.BooleanField(default=False)
    configurar_layout = models.BooleanField(default=False)
    visualizar_relatorios = models.BooleanField(default=False)

    def __str__(self):
        return f'Permissões de {self.colaborador.nome}'
