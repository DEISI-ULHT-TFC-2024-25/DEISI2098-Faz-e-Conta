from django.test import TestCase

# Create your tests here.
from unittest import TestCase
from unittest.mock import patch, MagicMock

# python

from .reports.functions import (
    calcular_total_mensalidades,
    calcular_mensalidades_por_valencia,
    calcular_total_mensalidades_ss,
    calcular_mensalidades_ss_por_valencia,
    calcular_pagamentos_em_falta,
    listar_pagamentos_em_falta,
)

class FunctionsTests(TestCase):
    @patch('data_hub.reports.functions.MensalidadeAluno')
    def test_calcular_total_mensalidades(self, MockMensalidadeAluno):
        MockMensalidadeAluno.objects.filter.return_value.aggregate.return_value = {'total': None}
        self.assertEqual(calcular_total_mensalidades(), 0)
        MockMensalidadeAluno.objects.filter.return_value.aggregate.return_value = {'total': 150}
        self.assertEqual(calcular_total_mensalidades(), 150)

    @patch('data_hub.reports.functions.MensalidadeAluno')
    def test_calcular_mensalidades_por_valencia(self, MockMensalidadeAluno):
        mock1 = MagicMock()
        mock1.aluno_id.sala_id.sala_valencia = 'A'
        mock1.mensalidade_paga = 100
        mock2 = MagicMock()
        mock2.aluno_id.sala_id.sala_valencia = 'B'
        mock2.mensalidade_paga = 200
        mock3 = MagicMock()
        mock3.aluno_id.sala_id.sala_valencia = 'A'
        mock3.mensalidade_paga = 50
        MockMensalidadeAluno.objects.select_related().filter.return_value = [mock1, mock2, mock3]
        result = calcular_mensalidades_por_valencia()
        self.assertEqual(result, {'A': 150, 'B': 200})

    @patch('data_hub.reports.functions.ComparticipacaoMensalSs')
    def test_calcular_total_mensalidades_ss(self, MockComparticipacaoMensalSs):
        MockComparticipacaoMensalSs.objects.filter.return_value.aggregate.return_value = {'total': None}
        self.assertEqual(calcular_total_mensalidades_ss(), 0)
        MockComparticipacaoMensalSs.objects.filter.return_value.aggregate.return_value = {'total': 300}
        self.assertEqual(calcular_total_mensalidades_ss(), 300)

    @patch('data_hub.reports.functions.ComparticipacaoMensalSs')
    def test_calcular_mensalidades_ss_por_valencia(self, MockComparticipacaoMensalSs):
        mock1 = MagicMock()
        mock1.aluno_id.sala_id.sala_valencia = 'X'
        mock1.mensalidade_paga = 80
        mock2 = MagicMock()
        mock2.aluno_id.sala_id.sala_valencia = 'Y'
        mock2.mensalidade_paga = 120
        MockComparticipacaoMensalSs.objects.select_related().filter.return_value = [mock1, mock2]
        result = calcular_mensalidades_ss_por_valencia()
        self.assertEqual(result, {'X': 80, 'Y': 120})

    @patch('data_hub.reports.functions.Divida')
    def test_calcular_pagamentos_em_falta(self, MockDivida):
        mock1 = MagicMock(valor_pagar='100', valor_pago='30')
        mock2 = MagicMock(valor_pagar='200', valor_pago=None)
        mock3 = MagicMock(valor_pagar='abc', valor_pago='xyz')
        MockDivida.objects.all.return_value = [mock1, mock2, mock3]
        result = calcular_pagamentos_em_falta()
        self.assertEqual(result, 270)

    @patch('data_hub.reports.functions.MensalidadeAluno')
    @patch('data_hub.reports.functions.Divida')
    def test_listar_pagamentos_em_falta(self, MockDivida, MockMensalidadeAluno):
        aluno = MagicMock()
        aluno.nome_proprio = 'Ana'
        aluno.apelido = 'Silva'
        sala = MagicMock()
        sala.sala_valencia = 'Pré'
        aluno.sala_id = sala

        divida = MagicMock()
        divida.aluno_id = aluno
        divida.valor_pagar = '100'
        divida.valor_pago = '60'
        divida.acordo_set.exists.return_value = True

        MockDivida.objects.select_related.return_value = [divida]
        ultimo_pagamento = MagicMock()
        ultimo_pagamento.data_pagamento = '2024-06-01'
        ultimo_pagamento.mensalidade_paga = 60
        MockMensalidadeAluno.objects.filter.return_value.order_by.return_value.first.return_value = ultimo_pagamento

        result = listar_pagamentos_em_falta()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['Nome de aluno'], 'Ana Silva')
        self.assertEqual(result[0]['Valência'], 'Pré')
        self.assertEqual(result[0]['Quantia mensal devida'], 100)
        self.assertEqual(result[0]['Quantia em falta'], 40)
        self.assertEqual(result[0]['Data do último pagamento'], '2024-06-01')
        self.assertEqual(result[0]['Quantia do último pagamento'], 60)
        self.assertEqual(result[0]['Acordo'], 'Sim')