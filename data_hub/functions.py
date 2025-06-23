def calcular_mensalidade(id_aluno):
    pass

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
            data_pagamento__month=mes,
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
            (Q(data_pagamento__year=ano) & Q(data_pagamento__month__lte=mes)) |
            Q(data_pagamento__year__lt=ano)
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
def pagamento(id_aluno, valor, descricao=None):
    from .models import Aluno, Transacao, TipoTransacao
    from django.utils import timezone

    try:
        tipo_pagamento = None
        aluno = Aluno.objects.get(pk=id_aluno)
        aluno.saldo += valor
        
        if valor > 0:
            if descricao is None:
                descricao = "Carregamento"
            else:
                tipo_pagamento = TipoTransacao.objects.get(tipo_transacao="Carregamento")
        else:
            if descricao is None:
                descricao = "Pagamento"
            else:
                tipo_pagamento = TipoTransacao.objects.get(tipo_transacao="Pagamento")
            
        Transacao.objects.create(
            aluno_id = aluno,
            valor = valor,
            data_transacao = timezone.now(),
            descricao = descricao,
            tipo_transacao = tipo_pagamento,
        )
        aluno.save()
    except Exception as e:
        print(f"Erro ao registrar pagamento: {e}")

def verificar_pagamentos():
    from .models import Aluno, Transacao as pagamento
    try:
        pagamentos = pagamento.objects.filter(data_pagamento__isnull=True)
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