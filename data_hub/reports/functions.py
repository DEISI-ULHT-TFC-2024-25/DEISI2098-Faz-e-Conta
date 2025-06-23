from datetime import datetime as dt
from ..models import *
from ..functions import *
from django.db.models import Sum
from django.db.models import Q


def calcular_total_mensalidades():
    return MensalidadeAluno.objects.filter(mensalidade_paga__isnull=False).aggregate(
        total=Sum('mensalidade_paga')
    )['total'] or 0

def calcular_mensalidades_por_valencia():
    mensalidades_por_valencia = {}
    mensalidades = MensalidadeAluno.objects.filter(mensalidade_paga__isnull=False)

    for m in mensalidades:
        sala = m.aluno_id.sala_set.first()
        valencia = sala.sala_valencia if sala else "Indefinido"
        mensalidades_por_valencia[valencia] = mensalidades_por_valencia.get(valencia, 0) + m.mensalidade_paga

    return mensalidades_por_valencia

def calcular_total_mensalidades_ss():
    return ComparticipacaoMensalSs.objects.filter(mensalidade_paga__isnull=False).aggregate(
        total=Sum('mensalidade_paga')
    )['total'] or 0

def calcular_mensalidades_ss_por_valencia():
    mensalidades_por_valencia_ss = {}
    mensalidades = ComparticipacaoMensalSs.objects.filter(mensalidade_paga__isnull=False)

    for m in mensalidades:
        sala = m.aluno_id.sala_set.first()
        valencia = sala.sala_valencia if sala else "Indefinido"
        mensalidades_por_valencia_ss[valencia] = mensalidades_por_valencia_ss.get(valencia, 0) + m.mensalidade_paga

    return mensalidades_por_valencia_ss

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
        pagamentos_data = pagamentos.filter(aluno_id=aluno.pk).order_by('-data_pagamento').first()
            
        pagamento_em_falta = {
            "Nome de aluno": f"{aluno.nome_proprio} {aluno.apelido}",
            "Valência": Sala.objects.get(pk=get_sala_id(aluno.pk)).sala_valencia,
            "Quantia mensal devida": f"{aluno.saldo} __Temp__",
            "Quantia em falta": aluno.saldo,
            "Data do último pagamento": pagamentos_data.data_pagamento if pagamentos_data else None,
            "Quantia do último pagamento": pagamentos_data.valor if pagamentos_data else 0,
            "Valor pago pela SS": 0,
            "Data último pagamento SS": None,
            "Acordo": "Não" + "__Temp__",
        }

        pagamentos_em_falta.append(pagamento_em_falta)

    return pagamentos_em_falta

