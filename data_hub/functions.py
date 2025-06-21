def calcular_mensalidade(id_aluno):
    pass

def pagamento(id_aluno, valor, descricao=None):
    from .models import Aluno, Pagamento, TipoPagamento
    from django.utils import timezone

    try:
        tipo_pagamento = None
        aluno = Aluno.objects.get(pk=id_aluno)
        aluno.saldo += valor
        
        if valor > 0:
            if descricao is None:
                descricao = "Carregamento"
            tipo_pagamento = TipoPagamento.objects.get(tipo_pagamento="Carregamento")
        else:
            if descricao is None:
                descricao = "Pagamento"
            tipo_pagamento = TipoPagamento.objects.get(tipo_pagamento="Pagamento")
            
        Pagamento.objects.create(
            aluno_id=aluno,
            valor=valor,
            data_pagamento=timezone.now(),
            descricao= descricao,
            tipo_pagamento= tipo_pagamento,
        )
        
        aluno.save()
    except Exception as e:
        print(f"Erro ao registrar pagamento: {e}")


def verificar_pagamentos():
    from .models import Aluno, Pagamento
    try:
        pagamentos = Pagamento.objects.filter(data_pagamento__isnull=True)
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