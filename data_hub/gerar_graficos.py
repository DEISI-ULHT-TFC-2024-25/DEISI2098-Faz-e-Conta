import json
import os
import base64
import io
import matplotlib.pyplot as plt
from django.conf import settings
from .models import *

palette = [
    (0.90, 0.10, 0.10), (0.10, 0.60, 0.10), (0.10, 0.10, 0.90),
    (0.95, 0.75, 0.10), (0.80, 0.10, 0.80), (0.10, 0.80, 0.80),
    (0.60, 0.60, 0.60), (1.00, 0.50, 0.00), (0.50, 0.10, 0.90),
    (0.40, 0.80, 0.40), (1.00, 0.50, 0.70), (0.40, 0.40, 1.00),
    (0.80, 0.40, 0.00), (0.60, 0.20, 0.00), (0.00, 0.60, 0.40),
    (0.70, 0.00, 0.70), (0.50, 0.50, 0.00), (0.10, 0.40, 0.80),
    (0.80, 0.80, 0.10), (0.20, 0.20, 0.20)
]

GRAPH_PATH = os.path.join(settings.BASE_DIR, 'static', 'graficos')
os.makedirs(GRAPH_PATH, exist_ok=True)

def gerar_grafico_barras(x, y, title, rotation=0, multi_color=False):
    plt.figure(figsize=(12, 6))
    colors = [palette[i % len(palette)] if multi_color else "blue" for i in range(len(y[1]))]
    plt.bar(x[1], y[1], color=colors)
    plt.xlabel(x[0])
    plt.ylabel(y[0])
    plt.title(title)
    plt.xticks(rotation=rotation, ha='right')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    grafico = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    plt.close()
    return grafico

def gerar_grafico_pizza(x, y, title):
    plt.figure(figsize=(12, 6))
    plt.pie(y[1], labels=x[1], autopct='%1.1f%%', startangle=140)
    plt.axis('equal')
    plt.title(title)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    grafico = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    plt.close()
    return grafico

def gerar_grafico_alunos_por_valencia():
    valencias = Sala.objects.values_list('sala_valencia', flat=True).distinct()
    alunos = Aluno.objects.select_related('sala').all()
    contagem = {val: 0 for val in valencias}
    for aluno in alunos:
        sala = Sala.objects.filter(alunos=aluno).first()
        if sala:
            contagem[sala.sala_valencia] += 1
    return gerar_grafico_barras(["Valência", list(contagem.keys())],
                                ["N.º de Alunos", list(contagem.values())],
                                "N.º de Alunos por Valência",
                                multi_color=True)

def gerar_grafico_mensalidades_por_valencia():
    valencias = Sala.objects.values_list('sala_valencia', flat=True).distinct()
    contagem = {val: 0 for val in valencias}
    for m in MensalidadeAluno.objects.select_related('aluno_id__sala_id'):
        sala = Sala.objects.filter(alunos=m.aluno_id).first()
        if sala:
            contagem[sala.sala_valencia] += 1
    return gerar_grafico_pizza(["Valência", list(contagem.keys())],
                               ["N.º de Mensalidades", list(contagem.values())],
                               "Mensalidades por Valência")

def gerar_grafico_vacinacao_por_tipo():
    vacinas = Vacina.objects.all()
    contagem = {v.vacina_name: 0 for v in vacinas}
    for v in Vacinacao.objects.select_related('dose_id__vacina_id'):
        nome = v.dose_id.vacina_id.vacina_name
        contagem[nome] = contagem.get(nome, 0) + 1
    return gerar_grafico_barras(["Vacina", list(contagem.keys())],
                                ["N.º de Doses", list(contagem.values())],
                                "Doses por Vacina",
                                rotation=45,
                                multi_color=True)

def gerar_grafico_plano_vacinacao():
    contagem = {"Incluídas": 0, "Excluídas": 0}
    for dose in Dose.objects.select_related('vacina_id'):
        if dose.vacina_id.plano_vacina:
            contagem["Incluídas"] += 1
        else:
            contagem["Excluídas"] += 1
    return gerar_grafico_pizza(["Plano Vacinação", list(contagem.keys())],
                               ["N.º de Vacinas", list(contagem.values())],
                               "Vacinas no Plano Nacional")

def gerar_grafico_despesas_fixas_por_tipo():
    despesas = DespesaFixa.objects.all()
    categorias = {}
    for d in despesas:
        categorias[d.produto] = categorias.get(d.produto, 0) + d.valor
    return gerar_grafico_barras(["Produto", list(categorias.keys())],
                                ["Total (€)", list(categorias.values())],
                                "Despesas Fixas por Produto",
                                rotation=45,
                                multi_color=True)
