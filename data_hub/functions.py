# Mensalidades
def calcular_rendimento_anual_bruto(responsaveis=None):
    from .models import ResponsavelEducativo
    from django.db.models import Sum
    try:
        if responsaveis is None:
            return 0
        if isinstance(responsaveis, ResponsavelEducativo):
            responsaveis = [responsaveis]
        total_rendimento = ResponsavelEducativo.objects.filter(pk__in=[r.pk for r in responsaveis]).aggregate(total=Sum('salario')*12)['total'] or 0
        return total_rendimento
    except Exception as e:
        print(f"Erro ao calcular rendimento anual bruto: {e}")
        return 0
    
def calcular_despesas_anuais_fixas(responsaveis=None):
    return 0

def calcular_despesas_mensais_fixas(responsaveis=None):
    return 0

def calcular_rendimento_medio_mensal_agregado(responsaveis=None):
    return (calcular_rendimento_anual_bruto(responsaveis)/12 - calcular_despesas_anuais_fixas(responsaveis)/12 - calcular_despesas_mensais_fixas(responsaveis))/responsaveis.count() if responsaveis else 0
    
def calcular_desconto_mensalidade(responsaveis=None):
    '''
        Escalões de desconto:
        - Até 600€: 50%
        - Entre 601€ e 760€: 30%
        - Entre 761€ e 1600€: 20%
        - Acima de 1600€: 10%
    '''
    rendimento_anual = calcular_rendimento_anual_bruto(responsaveis)/12
    if rendimento_anual <= 600:
        return 0.5
    elif rendimento_anual <= 760:
        return 0.3
    elif rendimento_anual <= 1600:
        return 0.2
    else:
        return 0.1

def calcular_mensalidade_aluno(id_aluno):
    from .models import Aluno, ResponsavelEducativo
    try:
        aluno = Aluno.objects.get(pk=id_aluno)
        responsaveis = ResponsavelEducativo.objects.filter(aluno_id=aluno.pk)
        mensalidade = calcular_rendimento_medio_mensal_agregado(responsaveis=responsaveis) * (1 - calcular_desconto_mensalidade(responsaveis=responsaveis))
        return mensalidade
    except Aluno.DoesNotExist:
        print(f"Aluno com ID {id_aluno} não encontrado.")
        return 0
    except ResponsavelEducativo.DoesNotExist:
        print(f"Responsável educativo para o aluno com ID {id_aluno} não encontrado.")
        return 0
    except Exception as e:
        print(f"Erro ao calcular mensalidade do aluno: {e}")
        return 0
    
    return 0
    




# Calculos
def calcular_despesas():
    from .models import DespesaFixa, DespesasVariavel
    from django.db.models import Sum
    try:
        despesas_fixas = DespesaFixa.objects.all()
        despesas_variaveis = DespesasVariavel.objects.all()
        
        total_fixas = despesas_fixas.aggregate(total=Sum('valor'))['total'] or 0
        total_variaveis = despesas_variaveis.aggregate(total=Sum('valor'))['total'] or 0

        return total_fixas + total_variaveis
    except Exception as e:
        print(f"Erro ao calcular despesas fixas e variáveis: {e}")
        return 0

def calcular_pagamento_mensal_alunos(mes=None):
    from .models import Aluno, pagamento
    from django.db.models import Sum

    try:
        if mes is None:
            pagamentos = pagamento.objects.filter(tipo_pagamento_id__tipo_pagamento="pagamento")
        else:
            pagamentos = pagamento.objects.filter(
            data_transacao__month=mes,
            tipo_pagamento_id__tipo_pagamento="pagamento"
            )
        alunos = Aluno.objects.all()
        
        total_pagamentos = pagamentos.aggregate(total=Sum('valor'))['total'] or 0
        total_alunos = alunos.count()
        
        if total_alunos == 0:
            return 0
        
        return total_pagamentos / total_alunos
    except Exception as e:
        print(f"Erro ao calcular pagamento mensal dos alunos: {e}")
        return 0

def calcular_pagamentos_falta_alunos(mes=None, ano=None):
    from .models import Aluno, Transacao
    from django.db.models import Sum
    from collections import defaultdict
    from django.db.models import Q
    
    alunos_saldo = set()
    
    if mes is None or ano is None:
        pagamentos = Transacao.objects.all()
    else:
        pagamentos = Transacao.objects.filter(
            (Q(data_transacao__year=ano) & Q(data_transacao__month__lte=mes)) |
            Q(data_transacao__year__lt=ano)
        )
    
    # Calcula o saldo de cada aluno a partir dos pagamentos
    alunos_saldo = defaultdict(float)
    for pagamento in pagamentos:
        alunos_saldo[pagamento.aluno_id_id] += pagamento.valor
    
    saldos = 0
    for aluno in alunos_saldo:
        if alunos_saldo[aluno] < 0:
            saldos -= abs(alunos_saldo[aluno])
    
    return saldos
            


# Transações
def get_tipo_transacao_default(valor):
    from .models import TipoTransacao
    if valor > 0:
        return TipoTransacao.objects.get(tipo_transacao="Carregamento")
    else:
        return TipoTransacao.objects.get(tipo_transacao="Pagamento")
    
def pagamento(id_aluno, valor, descricao=None, tipo_transacao=None, data_transacao=None):
    from .models import Aluno, Transacao, TipoTransacao
    from django.utils import timezone

    try:
        tipo_pagamento = None
        aluno = Aluno.objects.get(pk=id_aluno)
        aluno.saldo += valor
        
        if valor > 0:
            if descricao is None:
                descricao = "Carregamento"
            tipo_pagamento = TipoTransacao.objects.get(tipo_transacao="Carregamento")
        else:
            if descricao is None:
                descricao = "Pagamento"
            if tipo_transacao is None:
                tipo_pagamento = TipoTransacao.objects.get(tipo_transacao="Pagamento")
        if tipo_pagamento is None:
            tipo_pagamento = TipoTransacao.objects.get(pk = tipo_transacao)
        
        if data_transacao is not None:
            data_transacao = timezone.datetime.strptime(data_transacao, "%Y-%m-%d %H:%M:%S")
        else:
            data_transacao = timezone.now()
            
        Transacao.objects.create(
            aluno_id = aluno,
            valor = valor,
            data_transacao = data_transacao,
            descricao = descricao,
            tipo_transacao = tipo_pagamento,
        )
        aluno.save()
    except Exception as e:
        print(f"Erro ao registrar pagamento: {e}")

def verificar_pagamentos():
    from .models import Aluno, Transacao as pagamento
    try:
        pagamentos = pagamento.objects.filter(data_transacao__isnull=True)
        alunos = Aluno.objects.filter()
        valores_alunos = set()
        
        alunos_saldo_invalido = set()
        
        for pagamento in pagamentos:
            if pagamento.aluno_id and pagamento.valor:
                valores_alunos.add((pagamento.aluno_id.pk, pagamento.valor))
        
        for aluno in alunos:
            if valores_alunos[aluno.pk] == aluno.saldo:
                continue
            else:
                alunos_saldo_invalido[aluno.pk] = aluno.saldo-valores_alunos[aluno.pk]
                     
    except Exception as e:
        print(f"Erro ao verificar pagamentos: {e}")
    
    return alunos_saldo_invalido

# Other
def get_sala_id(aluno_id):
    from .models import Sala
    for sala in Sala.objects.all():
        if sala.alunos.filter(pk=aluno_id).exists():
            return sala.pk

# Backup
def create_backup():
    import os
    import shutil
    from datetime import datetime
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'db.sqlite3')
    backup_dir = os.path.join(base_dir, 'backup')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    now = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    backup_filename = f"db_{now}.sqlite3"
    backup_path = os.path.join(backup_dir, backup_filename)
    try:
        shutil.copy2(db_path, backup_path)
        print(f"Backup criado em: {backup_path}")
    except Exception as e:
        print(f"Erro ao criar backup: {e}")


def restore_backup(backup_filename=None):
    import os
    import shutil
    from datetime import datetime
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'db.sqlite3')
    backup_dir = os.path.join(base_dir, 'backup')
    if not os.path.exists(backup_dir):
        print("Diretório de backup não encontrado.")
        return
    if backup_filename is None:
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith('db_') and f.endswith('.sqlite3')]
        if not backup_files:
            print("Nenhum arquivo de backup encontrado.")
            return
        backup_filename = sorted(backup_files)[-1]  # Pega o mais recente
    backup_path = os.path.join(backup_dir, backup_filename)
    if not os.path.exists(backup_path):
        print(f"Arquivo de backup {backup_filename} não encontrado.")
        return
    try:
        shutil.copy2(backup_path, db_path)
        print(f"Backup restaurado de: {backup_path}")
    except Exception as e:
        print(f"Erro ao restaurar backup: {e}")

def listar_backups():
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backup_dir = os.path.join(base_dir, 'backup')
    if not os.path.exists(backup_dir):
        print("Diretório de backup não encontrado.")
        return []
    backup_files = [f for f in os.listdir(backup_dir) if f.startswith('db_') and f.endswith('.sqlite3')]
    if not backup_files:
        print("Nenhum arquivo de backup encontrado.")
        return []
    backup_files.sort(reverse=True)  # Ordena do mais recente para o mais antigo
    return [os.path.join(f) for f in backup_files]
