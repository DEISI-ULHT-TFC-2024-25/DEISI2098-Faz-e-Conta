from datetime import datetime as dt
from ..models import *
from ..functions import *
from django.db.models import Sum
from django.db.models import Q

def calcular_total_mensalidades():
    tipo_mensalidade = TipoTransacao.objects.filter(tipo_transacao__icontains="mensalidade").first()
    if not tipo_mensalidade:
        return 0
    total = Transacao.objects.filter(tipo_transacao=tipo_mensalidade).aggregate(total=Sum('valor'))['total']
    return total * -1 or 0\

def calcular_total_mensalidades_ss():
    return Transacao.objects.filter(tipo_transacao=3).aggregate(
        total=Sum('valor')
    )['total'] or 0

def calcular_mensalidades_ss_por_valencia():
    mensalidades_por_valencia_ss = set()
    valencias = Sala.objects.values_list('sala_valencia', flat=True).distinct()
    # valencias agora são IDs de Valencia, precisamos buscar o nome
    for valencia_id in valencias:
        valencia_obj = Valencia.objects.filter(pk=valencia_id).first()
        valencia_nome = valencia_obj.valencia_nome if valencia_obj else "Indefinido"
        mensalidades_por_valencia_ss.add(valencia_nome)
    mensalidades_por_valencia_ss = {valencia: 0 for valencia in mensalidades_por_valencia_ss}
    
    mensalidades = Transacao.objects.filter(tipo_transacao=3)
    
    for m in mensalidades:
        sala = Sala.objects.filter(alunos=m.aluno_id).first()
        if sala and sala.sala_valencia:
            valencia_nome = sala.sala_valencia.valencia_nome
        else:
            valencia_nome = "Indefinido"
        
        mensalidades_por_valencia_ss[valencia_nome] = mensalidades_por_valencia_ss.get(valencia_nome, 0) + m.valor

    print(mensalidades_por_valencia_ss)
    return mensalidades_por_valencia_ss

def calcular_comparticipacao_ss():
    total = Transacao.objects.filter(tipo_transacao=3).aggregate(total=Sum('valor'))['total']
    return total or 0

def listar_comparticipações_ss(mes=None, ano=None):
    pagamentos = Transacao.objects.filter(tipo_transacao=3)
    if mes is not None and ano is not None:
        pagamentos = pagamentos.filter(
            data_transacao__month=mes,
            data_transacao__year=ano
        )
    resultados = {}
    for pagamento in pagamentos.select_related('aluno_id'):
        aluno = pagamento.aluno_id
        if not aluno:
            continue
        nome_aluno = f"{aluno.nome_proprio} {aluno.apelido}"
        sala = Sala.objects.filter(alunos=aluno).first()
        valencia_nome = sala.sala_valencia.valencia_nome if sala and sala.sala_valencia else "Indefinido"
        if aluno.pk not in resultados:
            resultados[aluno.pk] = {
                "Nome de aluno": nome_aluno,
                "Valência": valencia_nome,
                "Valor pago pela SS": 0,
                "Data do último pagamento": None,
            }
        resultados[aluno.pk]["Valor pago pela SS"] += pagamento.valor
        # Guarda a data do pagamento mais recente
        if (resultados[aluno.pk]["Data do último pagamento"] is None or 
            (pagamento.data_transacao and pagamento.data_transacao > resultados[aluno.pk]["Data do último pagamento"])):
            resultados[aluno.pk]["Data do último pagamento"] = pagamento.data_transacao

    # Ajusta o formato da data para .date()
    for r in resultados.values():
        if r["Data do último pagamento"]:
            r["Data do último pagamento"] = r["Data do último pagamento"].date()
    return list(resultados.values())

def calcular_mensalidades_por_valencia():
    mensalidades_por_valencia = set()
    valencias = Sala.objects.values_list('sala_valencia', flat=True).distinct()
    # valencias agora são IDs de Valencia, precisamos buscar o nome
    for valencia_id in valencias:
        valencia_obj = Valencia.objects.filter(pk=valencia_id).first()
        valencia_nome = valencia_obj.valencia_nome if valencia_obj else "Indefinido"
        mensalidades_por_valencia.add(valencia_nome)
    mensalidades_por_valencia = {valencia: 0 for valencia in mensalidades_por_valencia}
    
    tipo_mensalidade = TipoTransacao.objects.filter(tipo_transacao__icontains="mensalidade").first()
    if not tipo_mensalidade:
        return mensalidades_por_valencia

    transacoes = Transacao.objects.filter(
        tipo_transacao=tipo_mensalidade
    ).select_related('aluno_id')

    for transacao in transacoes:
        sala = Sala.objects.filter(alunos=transacao.aluno_id).first()
        if sala and sala.sala_valencia:
            valencia_nome = sala.sala_valencia.valencia_nome
        else:
            valencia_nome = "Indefinido"
        mensalidades_por_valencia[valencia_nome] = mensalidades_por_valencia.get(valencia_nome, 0) - transacao.valor

    return mensalidades_por_valencia

def calcular_pagamentos_em_falta():
    dividas = Divida.objects.all()
    total_pagamentos_em_falta = 0

    for divida in dividas:
        try:
            valor_pagar = int(divida.valor_pagar)
        except (ValueError, TypeError):
            valor_pagar = 0

        try:
            valor_pago = int(divida.valor_pago) if divida.valor_pago is not None else 0
        except (ValueError, TypeError):
            valor_pago = 0

        total_pagamentos_em_falta += max(0, valor_pagar - valor_pago)

    return total_pagamentos_em_falta

def listar_pagamentos_em_falta(mes=None, ano=None):
    alunos = Aluno.objects.filter(saldo__lt=0).order_by('saldo')
    pagamentos_em_falta = []
    
    if mes is None or ano is None:
        print("Mes e ano não especificados, usando o mês atual.")
        mes = dt.now().month
        ano = dt.now().year
    
    pagamentos = Transacao.objects.all()
    
    for aluno in alunos:
        pagamentos_data = pagamentos.filter(aluno_id=aluno.pk).exclude(tipo_transacao__tipo_transacao_id=3).order_by('-data_transacao').first()
        sala = Sala.objects.filter(alunos=aluno).first()
        valencia_nome = sala.sala_valencia.valencia_nome if sala and sala.sala_valencia else "Indefinido"
        comparticipacoes_data = pagamentos.filter(aluno_id=aluno.pk, tipo_transacao=3).order_by('-data_transacao').first()
        valor_pago_ss = pagamentos.filter(aluno_id=aluno.pk, tipo_transacao=3).aggregate(total=Sum('valor'))['total'] or 0

        pagamento_em_falta = {
            "Nome de aluno": f"{aluno.nome_proprio} {aluno.apelido}",
            "Valência": valencia_nome,
            "Quantia em falta": aluno.saldo,
            "Data do último pagamento": pagamentos_data.data_transacao.date() if pagamentos_data and pagamentos_data.data_transacao else None,
            "Quantia do último pagamento": pagamentos_data.valor if pagamentos_data else 0,
            "Valor pago pela SS": valor_pago_ss,
            "Data último pagamento SS": comparticipacoes_data.data_transacao.date() if comparticipacoes_data and comparticipacoes_data.data_transacao else None,
        }

        pagamentos_em_falta.append(pagamento_em_falta)

    return pagamentos_em_falta

# Despesas
def calcular_despesas_fixas(mes=None, ano=None):
    despesas_fixas = DespesaFixa.objects.all()
    if mes is not None and ano is not None:
        despesas_fixas = despesas_fixas.filter(
            data__month=mes,
            data__year=ano
        )
    total_despesas = 0
    for despesa in despesas_fixas:
        try:
            total_despesas += int(despesa.valor)
        except (ValueError, TypeError):
            total_despesas += 0
    return total_despesas

def calcular_despesas_variaveis(mes=None, ano=None):
    despesas_variaveis = DespesasVariavel.objects.all()
    if mes is not None and ano is not None:
        despesas_variaveis = despesas_variaveis.filter(
            data__month=mes,
            data__year=ano
        )
    total_despesas = 0
    for despesa in despesas_variaveis:
        try:
            total_despesas += int(despesa.valor)
        except (ValueError, TypeError):
            total_despesas += 0
    return total_despesas

def calcular_despesas(mes=None, ano=None):
    total_despesas_fixas = calcular_despesas_fixas(mes=mes, ano=ano)
    total_despesas_variaveis = calcular_despesas_variaveis(mes=mes, ano=ano)
    return total_despesas_fixas + total_despesas_variaveis

def calcular_despesas_por_aluno(mes=None, ano=None):
    return (calcular_despesas(mes=mes, ano=ano) / Aluno.objects.count()) if Aluno.objects.count() > 0 else 0

def calcular_valor_medio_aluno(mes=None, ano=None):
    pagamentos = Transacao.objects.exclude(tipo_transacao=3)
    if mes is not None and ano is not None:
        pagamentos = pagamentos.filter(
            data_transacao__year__lte=ano
        ).filter(
            Q(data_transacao__year__lt=ano) | Q(data_transacao__year=ano, data_transacao__month__lte=mes)
        )
    total_pago = pagamentos.aggregate(total=Sum('valor'))['total'] or 0
    num_alunos = Aluno.objects.count()
    return (total_pago / num_alunos) if num_alunos > 0 else 0