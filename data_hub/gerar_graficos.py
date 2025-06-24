import json
import os
import base64
import io

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from django.conf import settings
from .models import *
from .models import Imagem, TipoImagem
from django.core.files.base import ContentFile
import uuid

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

def save_grafico(grafico, title):
    tipo, _ = TipoImagem.objects.get_or_create(tipo_imagem="grafico")
    img_bytes = base64.b64decode(grafico)
    filename = f"{uuid.uuid4().hex}.png"
    imagem_existente = Imagem.objects.filter(alt=title, tipo_imagem_id=tipo).first()
    if imagem_existente:
        imagem_existente.imagem.save(filename, ContentFile(img_bytes), save=True)
        imagem_existente.save()
    else:
        imagem_obj = Imagem.objects.create(
            alt=title
        )
        imagem_obj.imagem.save(filename, ContentFile(img_bytes), save=True)
        imagem_obj.tipo_imagem_id.add(tipo)
        imagem_obj.save()

def gerar_grafico_barras(x, y, title, rotation=0, multi_color=False, return_path=False):
    plt.figure(figsize=(12, 6))
    colors = [palette[i % len(palette)] if multi_color else "blue" for i in range(len(y[1]))]
    plt.bar(x[1], y[1], color=colors)
    plt.xlabel(x[0])
    plt.ylabel(y[0])
    plt.title(title)
    plt.xticks(rotation=rotation, ha='right')
    
    if return_path:
        path = os.path.join(GRAPH_PATH, f"{title.replace(' ', '_')}.png")
        plt.savefig(path, format='png', bbox_inches='tight')
        plt.close()
        return path

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    buf.seek(0)
    grafico = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    
    save_grafico(grafico, title)
    
    return grafico

def gerar_grafico_pizza(x, y, title, return_path=False):
    labels = []
    values = []
    for label, value in zip(x[1], y[1]):
        if value > 0:
            labels.append(label)
            values.append(value)
    if not values:
        plt.figure(figsize=(8, 6))
        plt.text(0.5, 0.5, 'Sem dados para exibir', ha='center', va='center', fontsize=16)
        plt.axis('off')
    else:
        plt.figure(figsize=(12, 6))
        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
        plt.axis('equal')
        plt.title(title)
    buf = io.BytesIO()
    if return_path:
        path = os.path.join(GRAPH_PATH, f"{title.replace(' ', '_')}.png")
        plt.savefig(path)
        plt.close()
        return path

    plt.savefig(buf, format='png')
    buf.seek(0)
    grafico = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    plt.close()

    save_grafico(grafico, title)

    return grafico

def gerar_grafico_numero_alunos_por_valencia(return_path=False):
    valencias = Valencia.objects.all()
    contagem = {val.valencia_nome: 0 for val in valencias}
    for sala in Sala.objects.select_related('sala_valencia').prefetch_related('alunos'):
        valencia_nome = sala.sala_valencia.valencia_nome
        contagem[valencia_nome] += sala.alunos.count()
    return gerar_grafico_barras(
        ["Valência", list(contagem.keys())],
        ["Número de Alunos", list(contagem.values())],
        "Número de Alunos por Valência",
        multi_color=True,
        return_path=return_path
    )

def gerar_grafico_mensalidades_por_valencia(return_path=False):
    valencias = Valencia.objects.all()
    contagem = {val.valencia_nome: 0 for val in valencias}
    mensalidades = Transacao.objects.filter(tipo_transacao= TipoTransacao.objects.get(tipo_transacao= "Mensalidade"))
    
    for mensalidade in mensalidades:
        salas = Sala.objects.filter(alunos__in=[mensalidade.aluno_id])
        for sala in salas:
            valencia = sala.sala_valencia
            if valencia:
                contagem[valencia.valencia_nome] -= mensalidade.valor
                print(f"Valencia: {contagem[valencia.valencia_nome]}")

    
    return gerar_grafico_pizza(
        ["Valência", list(contagem.keys())],
        ["Valor de Mensalidades", list(contagem.values())],
        "Mensalidades por Valência",
        return_path=return_path
    )

def gerar_grafico_vacinacao_por_tipo(return_path=False):
    vacinas = Vacina.objects.all()
    contagem = {v.vacina_name: 0 for v in vacinas}
    for v in Vacinacao.objects.select_related('dose_id__vacina_id'):
        nome = v.dose_id.vacina_id.vacina_name
        contagem[nome] += 1
    return gerar_grafico_barras(
        ["Vacina", list(contagem.keys())],
        ["Número de Doses", list(contagem.values())],
        "Doses por Vacina",
        rotation=45,
        multi_color=True
    )

def gerar_grafico_plano_vacinacao(return_path=False):
    contagem = {"Incluídas": 0, "Excluídas": 0}
    for dose in Dose.objects.select_related('vacina_id'):
        if dose.vacina_id.plano_vacina:
            contagem["Incluídas"] += 1
        else:
            contagem["Excluídas"] += 1
    return gerar_grafico_pizza(
        ["Plano Vacinação", list(contagem.keys())],
        ["Número de Vacinas", list(contagem.values())],
        "Vacinas no Plano Nacional"
    )

def gerar_grafico_despesas_fixas_por_tipo(return_path=False):
    despesas = DespesaFixa.objects.all()
    categorias = {}
    for d in despesas:
        categorias[d.produto] = categorias.get(d.produto, 0) + d.valor
    return gerar_grafico_barras(
        ["Produto", list(categorias.keys())],
        ["Total (€)", list(categorias.values())],
        "Despesas Fixas por Produto",
        rotation=45,
        multi_color=True
    )

def gerar_grafico_mensalidades_SS_por_valencia(return_path=False):
    valencias = Valencia.objects.all()
    contagem = {val.valencia_nome: 0 for val in valencias}
    for m in ComparticipacaoMensalSs.objects.select_related('aluno_id'):
        salas = Sala.objects.filter(alunos=m.aluno_id).select_related('sala_valencia')
        for sala in salas:
            valencia_nome = sala.sala_valencia.valencia_nome
            contagem[valencia_nome] += 1
    return gerar_grafico_pizza(
        ["Valência", list(contagem.keys())],
        ["Mensalidades SS", list(contagem.values())],
        "Mensalidades SS por Valência",
        return_path=return_path
    )

def gerar_grafico_alunos_por_sala(return_path=False):
    salas = Sala.objects.all()
    contagem = {sala.sala_nome: sala.alunos.count() for sala in salas}
    return gerar_grafico_barras(
        ["Sala", list(contagem.keys())],
        ["Número de Alunos", list(contagem.values())],
        "Número de Alunos por Sala",
        rotation=45,
        multi_color=True
    )

def ResponsavelEducativo_HorariosEntradaQuantidade(return_path=False):
    horarios = {}
    for r in ResponsavelEducativo.objects.exclude(horario_trabalho__isnull=True):
        hora = r.horario_trabalho.hour
        key = f"{hora:02d}:00 - {((hora + 1) % 24):02d}:00"
        horarios[key] = horarios.get(key, 0) + 1
    horarios = dict(sorted(horarios.items()))
    return gerar_grafico_barras(
        ["Horário", list(horarios.keys())],
        ["Número de Responsáveis", list(horarios.values())],
        "Entradas por Hora"
    )

def graficos_modelo(model: str):
    graficos = []
    if model.lower() == "vacinacao":
        graficos.extend([
            gerar_grafico_vacinacao_por_tipo(),
            gerar_grafico_plano_vacinacao()
        ])
    elif model.lower() == "aluno":
        graficos.extend([
            gerar_grafico_numero_alunos_por_valencia(),
            gerar_grafico_alunos_por_sala()
        ])
    elif model.lower() == "mensalidade":
        graficos.extend([
            gerar_grafico_mensalidades_por_valencia(),
            gerar_grafico_mensalidades_SS_por_valencia()
        ])
    elif model.lower() == "despesa":
        graficos.append(gerar_grafico_despesas_fixas_por_tipo())
    elif model.lower() == "responsavel":
        graficos.append(ResponsavelEducativo_HorariosEntradaQuantidade())
    return graficos
