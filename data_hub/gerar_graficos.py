# gerar_graficos.py atualizado com base no novo models.py, incluindo todos os gráficos existentes

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
    try:
        img_data = base64.b64decode(grafico)
        file_name = f"{uuid.uuid4().hex}_{title.replace(' ', '_')}.png"
        image_file = ContentFile(img_data, name=file_name)

        # Cria ou atualiza o registro Imagem
        imagem_obj = Imagem.objects.create(
            imagem=image_file,
            alt=title,
            tipo_imagem_id=TipoImagem.objects.get_or_create(tipo_imagem="grafico")[0]
        )

        imagem_obj.save()
    except Exception as e:
        pass

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
    plt.figure(figsize=(12, 6))
    plt.pie(y[1], labels=x[1], autopct='%1.1f%%', startangle=140)
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
    valencias = Sala.objects.values_list('sala_valencia', flat=True).distinct()
    alunos = Aluno.objects.prefetch_related('sala_set').all()
    contagem = {val: 0 for val in valencias}
    for aluno in alunos:
        salas = aluno.sala_set.all()
        for sala in salas:
            contagem[sala.sala_valencia] += 1
            
    return gerar_grafico_barras(["Valencia", list(contagem.keys())],
                                ["Numero de Alunos", list(contagem.values())],
                                "Numero de Alunos por Valencia",
                                multi_color=True,
                                return_path=return_path)

def gerar_grafico_mensalidades_por_valencia(return_path=False):
    valencias = Sala.objects.values_list('sala_valencia', flat=True).distinct()
    contagem = {val: 0 for val in valencias}
    for m in MensalidadeAluno.objects.select_related('aluno_id'):
        salas = m.aluno_id.sala_set.all()
        for sala in salas:
            contagem[sala.sala_valencia] += 1
    return gerar_grafico_pizza(["Valencia", list(contagem.keys())],
                               ["Numero de Mensalidades", list(contagem.values())],
                               "Mensalidades por Valencia",
                               return_path=return_path)

def gerar_grafico_vacinacao_por_tipo(return_path=False):
    vacinas = Vacina.objects.all()
    contagem = {v.vacina_name: 0 for v in vacinas}
    for v in Vacinacao.objects.select_related('dose_id__vacina_id'):
        nome = v.dose_id.vacina_id.vacina_name
        contagem[nome] += 1
    return gerar_grafico_barras(["Vacina", list(contagem.keys())],
                                ["Numero de Doses", list(contagem.values())],
                                "Doses por Vacina",
                                rotation=45,
                                multi_color=True)

def gerar_grafico_plano_vacinacao(return_path=False):
    contagem = {"Incluídas": 0, "Excluídas": 0}
    for dose in Dose.objects.select_related('vacina_id'):
        if dose.vacina_id.plano_vacina:
            contagem["Incluídas"] += 1
        else:
            contagem["Excluídas"] += 1
    return gerar_grafico_pizza(["Plano Vacinação", list(contagem.keys())],
                               ["Numero de Vacinas", list(contagem.values())],
                               "Vacinas no Plano Nacional")

def gerar_grafico_despesas_fixas_por_tipo(return_path=False):
    despesas = DespesaFixa.objects.all()
    categorias = {}
    for d in despesas:
        categorias[d.produto] = categorias.get(d.produto, 0) + d.valor
    return gerar_grafico_barras(["Produto", list(categorias.keys())],
                                ["Total (€)", list(categorias.values())],
                                "Despesas Fixas por Produto",
                                rotation=45,
                                multi_color=True)

def gerar_grafico_mensalidades_SS_por_valencia(return_path=False):
    valencias = Sala.objects.values_list('sala_valencia', flat=True).distinct()
    contagem = {val: 0 for val in valencias}
    for m in ComparticipacaoMensalSs.objects.select_related('aluno_id'):
        salas = m.aluno_id.sala_set.all()
        for sala in salas:
            contagem[sala.sala_valencia] += 1
    return gerar_grafico_pizza(["Valencia", list(contagem.keys())],
                               ["Mensalidades SS", list(contagem.values())],
                               "Mensalidades SS por Valência",
                               return_path=return_path)

def gerar_grafico_alunos_por_sala(return_path=False):
    salas = Sala.objects.all()
    contagem = {sala.sala_nome: sala.alunos.count() for sala in salas}
    return gerar_grafico_barras(["Sala", list(contagem.keys())],
                                ["Numero de Alunos", list(contagem.values())],
                                "Numero de Alunos por Sala",
                                rotation=45,
                                multi_color=True)

def ResponsavelEducativo_HorariosEntradaQuantidade(return_path=False):
    horarios = {}
    for r in ResponsavelEducativo.objects.exclude(horario_trabalho__isnull=True):
        hora = r.horario_trabalho.hour
        key = f"{hora:02d}:00 - {((hora + 1) % 24):02d}:00"
        horarios[key] = horarios.get(key, 0) + 1
    horarios = dict(sorted(horarios.items()))
    return gerar_grafico_barras(["Horario", list(horarios.keys())],
                                ["Numero de Responsaveis", list(horarios.values())],
                                "Entradas por Hora")

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
