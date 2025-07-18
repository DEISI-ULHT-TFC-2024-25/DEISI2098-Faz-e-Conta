import textwrap
import io
import base64
from datetime import datetime as dt

from ..gerar_graficos import *
from .functions import *
from ..models import *
from ..functions import *

from django.apps import apps
from django.http import FileResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader

from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, KeepTogether
)

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from PyPDF2 import PdfMerger

login_url = 'login'


@login_required(login_url=login_url)
def gerar_pdf(request, model):
    model_class = None
    for app in apps.get_app_configs():
        try:
            model_class = apps.get_model(app.label, model)
            break
        except LookupError:
            continue

    if not model_class:
        return HttpResponse("Modelo não encontrado", status=404)

    objetos = model_class.objects.all()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"Relatório: {model}", styles['Title']))
    elements.append(Paragraph(f"Total de registros: {objetos.count()}", styles['Normal']))
    elements.append(Spacer(1, 6))

    data = []
    for obj in objetos:
        wrapped_text = textwrap.wrap(str(obj), width=70)
        data.append(["\n".join(wrapped_text)])

    table = Table(data)
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    graficos = graficos_modelo(model)
    for grafico_base64 in graficos:
        if grafico_base64:
            grafico_bytes = base64.b64decode(grafico_base64)
            elements.append(Image(io.BytesIO(grafico_bytes), width=400, height=200))
            elements.append(Spacer(1, 220))

    if elements:
        doc.build(elements)

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"{model}_relatorio.pdf")


@login_required(login_url=login_url)
def gerar_pdf_aluno(request, aluno_id):
    try:
        aluno = Aluno.objects.get(aluno_id=aluno_id)
    except Aluno.DoesNotExist:
        return HttpResponse("Aluno não encontrado", status=404)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('WrapStyle', parent=styles['Normal'], wordWrap='CJK')

    elements.append(Paragraph(f"Relatório do {aluno}", styles['Title']))
    elements.append(Spacer(1, 6))

    head = [field.name for field in Aluno._meta.fields]
    data = []
    for field in head:
        value = getattr(aluno, field)
        data.append([
            Paragraph(str(field), wrap_style),
            Paragraph(str(value), wrap_style)
        ])

    table_width = doc.width * 0.95
    col_widths = [table_width * 0.3, table_width * 0.7]
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    elements.append(table)

    elements.append(PageBreak())

    elements.append(Paragraph("Transações do aluno:", styles['Heading2']))
    elements.append(Spacer(1, 6))

    pagamentos = Transacao.objects.filter(aluno_id=aluno.pk).order_by('-data_transacao')
    if pagamentos.exists():
        table_data = [
            [
                Paragraph("Data", wrap_style),
                Paragraph("Tipo Transação", wrap_style),
                Paragraph("Valor", wrap_style),
                Paragraph("Descrição", wrap_style)
            ]
        ]
        for pagamento in pagamentos:
            table_data.append([
                Paragraph(pagamento.data_transacao.strftime('%d/%m/%Y') if pagamento.data_transacao else "", wrap_style),
                Paragraph(f"{pagamento.tipo_transacao or ''}", wrap_style),
                Paragraph(f"{abs(pagamento.valor):.2f}€", wrap_style),
                Paragraph(f"{pagamento.descricao or ''}", wrap_style),
            ])
        trans_table_width = doc.width * 0.95
        trans_col_widths = [
            trans_table_width * 0.18,
            trans_table_width * 0.22,
            trans_table_width * 0.20,
            trans_table_width * 0.40,
        ]
        table = Table(table_data, colWidths=trans_col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("Nenhuma Transação encontrada.", styles['Normal']))
    elements.append(Spacer(1, 12))

    if elements:
        doc.build(elements)

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"{str(aluno)}_relatorio.pdf")


@login_required(login_url=login_url)
def reportAlunoSala(request):
    Aluno = Sala = None
    for app in apps.get_app_configs():
        try:
            Aluno = apps.get_model(app.label, 'Aluno')
            Sala = apps.get_model(app.label, 'Sala')
            if Aluno and Sala:
                break
        except LookupError:
            continue

    if not (Aluno and Sala):
        return HttpResponse("Modelos não encontrados", status=404)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Relatório de Alunos por Sala", styles['Title']))
    elements.append(Spacer(1, 12))

    salas = Sala.objects.all()
    for sala in salas:
        elements.append(Paragraph(f"Sala: {sala.sala_nome}", styles['Heading2']))
        elements.append(Spacer(1, 12))

        alunos = sala.alunos.all()
        data = [["ID", "Nome", "Apelido", "Processo", "Numero\nDocumento", "Data\nAdmissao"]]
        for aluno in alunos:
            data.append([
                aluno.aluno_id,
                Paragraph(aluno.nome_proprio, styles['Normal']),
                Paragraph(aluno.apelido, styles['Normal']),
                Paragraph(aluno.processo or '', styles['Normal']),
                Paragraph(aluno.numero_documento, styles['Normal']),
                Paragraph(str(aluno.data_admissao.date()), styles['Normal'])
            ])

        table = Table(data, colWidths=[doc.width / 6.0] * 6)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))

        elements.append(table)
        elements.append(PageBreak())

    doc.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="relatorio_alunos_sala.pdf")


@login_required(login_url=login_url)
def reportMensal(request, month=None, year=None):
    bullet_icons = ['➼', '➾', '➔']
    now = dt.now()
    date_time = now.strftime('%d-%m-%Y %H:%M:%S')
    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle('WrapStyle', parent=styles['Normal'], wordWrap='CJK')

    # Parte 1 - Vertical
    buffer1 = io.BytesIO()
    doc1 = SimpleDocTemplate(buffer1, pagesize=A4)
    elements1 = []

    if month is None or year is None:
        elements1.append(Paragraph(f"Relatório gerado a {date_time}", styles['Title']))
    else:
        elements1.append(Paragraph(f"Relatório do mês {month}/{year}", styles['Title']))
        elements1.append(Paragraph(f"Gerado a {date_time}", styles['Title']))
    elements1.append(Spacer(1, 12))

    # Gráfico 1
    try:
        grafico_base64 = gerar_grafico_numero_alunos_por_valencia()
        if grafico_base64:
            grafico_bytes = base64.b64decode(grafico_base64)
            elements1.append(Image(io.BytesIO(grafico_bytes), width=400, height=200))
        elements1.append(Spacer(1, 12))
    except Exception as e:
        elements1.append(Paragraph(f"Erro ao gerar gráfico de número de alunos por valência: {str(e)}", styles['Normal']))

    # Gráfico 2
    total_fees_paid_by_students = float(calcular_total_mensalidades() or 0)
    elements1.append(PageBreak())
    elements1.append(Paragraph(f"Valor total de mensalidades pagas pelos alunos: {total_fees_paid_by_students:.2f}€", styles['Title']))
    elements1.append(Spacer(1, 12))

    try:
        grafico_base64 = gerar_grafico_mensalidades_por_valencia()
        if grafico_base64:
            grafico_bytes = base64.b64decode(grafico_base64)
            elements1.append(Image(io.BytesIO(grafico_bytes), width=400, height=200))
        elements1.append(Spacer(1, 12))
    except Exception as e:
        elements1.append(Paragraph(f"Erro ao gerar gráfico de mensalidades por valência: {str(e)}", styles['Normal']))

    for valence, amount in calcular_mensalidades_por_valencia().items():
        elements1.append(Paragraph(f"{bullet_icons[0]} Valor por valência ({valence}): {amount:.2f}€", styles['Normal']))
        elements1.append(Spacer(1, 12))

    # Gráfico 3
    total_fees_paid_by_ss = float(calcular_total_mensalidades_ss() or 0)
    elements1.append(PageBreak())
    elements1.append(Paragraph(f"Valor total de mensalidades pagas pela SS: {total_fees_paid_by_ss:.2f}€", styles['Title']))
    elements1.append(Spacer(1, 12))

    try:
        grafico_base64 = gerar_grafico_mensalidades_SS_por_valencia()
        if grafico_base64:
            grafico_bytes = base64.b64decode(grafico_base64)
            elements1.append(Image(io.BytesIO(grafico_bytes), width=400, height=200))
        elements1.append(Spacer(1, 12))
    except Exception as e:
        elements1.append(Paragraph(f"Erro ao gerar gráfico de mensalidades SS por valência: {str(e)}", styles['Normal']))

    for valence, amount in calcular_mensalidades_ss_por_valencia().items():
        elements1.append(Paragraph(f"{bullet_icons[0]} Valor pela SS por valência ({valence}): {amount:.2f}€", styles['Normal']))
        elements1.append(Spacer(1, 12))

    doc1.build(elements1)

    # Parte 2 - Tabela horizontal
    buffer2 = io.BytesIO()
    doc2 = SimpleDocTemplate(buffer2, pagesize=landscape(A4), leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    elements2 = []

    payments_in_default = float(calcular_pagamentos_falta_alunos(mes=month, ano=year)*-1 or 0)
    elements2.append(Paragraph(f"Valor de pagamentos de alunos em falta: {payments_in_default}€", styles['Title']))
    elements2.append(Spacer(1, 12))

    pagamentos = listar_pagamentos_em_falta(mes=month, ano=year)
    table_data = [[
        Paragraph("Nome de aluno", wrap_style),
        Paragraph("Valência", wrap_style),
        Paragraph("Quantia em falta", wrap_style),
        Paragraph("Data do último pagamento", wrap_style),
        Paragraph("Quantia do último pagamento", wrap_style),
        # Paragraph("Quantia mensal devida", wrap_style),
        # Paragraph("Acordo", wrap_style),
    ]]

    for p in pagamentos:
        table_data.append([
            Paragraph(str(p["Nome de aluno"]), wrap_style),
            Paragraph(str(p["Valência"]), wrap_style),
            Paragraph(str(p["Quantia em falta"]), wrap_style),
            Paragraph(str(p["Data do último pagamento"]), wrap_style),
            Paragraph(str(p["Quantia do último pagamento"]), wrap_style),
            #Paragraph(str(p["Quantia mensal devida"]), wrap_style),
            #Paragraph(str(p["Acordo"]), wrap_style),
        ])

    col_widths = [100, 80, 70, 70, 85, 75, 75, 85, 70]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements2.append(KeepTogether(table))
    
    elements2.append(PageBreak())
    comparticipacoes = calcular_comparticipacao_ss()
    elements2.append(Paragraph(f"Comparticipações SS: {comparticipacoes}€", styles['Title']))
    elements2.append(Spacer(1, 12))

    pagamentos = listar_comparticipações_ss(mes=month, ano=year)
    table_data = [
        [
            Paragraph("Nome de aluno", wrap_style),
            Paragraph("Valência", wrap_style),
            Paragraph("Valor pago pela SS", wrap_style),
            Paragraph("Data do Ultimo Pagamento", wrap_style),
        ]
    ]

    for p in pagamentos:
        table_data.append([
            Paragraph(str(p["Nome de aluno"]), wrap_style),
            Paragraph(str(p["Valência"]), wrap_style),
            Paragraph(f'{float(p["Valor pago pela SS"]):.2f}€', wrap_style),
            Paragraph(p["Data do último pagamento"].strftime('%d/%m/%Y') if p["Data do último pagamento"] else "", wrap_style),
        ])

    col_widths = [100, 80, 70, 70, 85, 75, 75, 85, 70]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements2.append(KeepTogether(table))
    
    
    doc2.build(elements2)

    # Parte 3 - Final
    buffer3 = io.BytesIO()
    doc3 = SimpleDocTemplate(buffer3, pagesize=A4)
    elements3 = []

   
    fixed_expenses = float(calcular_despesas_fixas(mes=month, ano=year) or 0)
    variable_expenses = float(calcular_despesas_variaveis(mes=month, ano=year) or 0)
    total_students = Aluno.objects.count() or 1

    # cost_per_student = calcular_despesas_por_aluno(mes=month, ano=year) * -1
    cost_per_student = calcular_valor_medio_aluno(mes=month, ano=year)
    
    final_balance = (
        total_fees_paid_by_students + total_fees_paid_by_ss
        - fixed_expenses - variable_expenses - payments_in_default
    )

    if month is None or year is None:
        elements3.append(Paragraph("Despesas Gerais:", styles['Title']))
        elements3.append(Paragraph(f"Despesas fixas Gerais: {fixed_expenses:.2f}€", styles['Normal']))
        elements3.append(Paragraph(f"Despesas variáveis Gerais: {variable_expenses:.2f}€", styles['Normal']))
    else:
        elements3.append(Paragraph("Despesas do mês:", styles['Title']))
        elements3.append(Paragraph(f"Despesas fixas do mês: {fixed_expenses:.2f}€", styles['Normal']))
        elements3.append(Paragraph(f"Despesas variáveis do mês: {variable_expenses:.2f}€", styles['Normal']))

    elements3.append(Spacer(1, 12))
    if cost_per_student > 0:
        elements3.append(Paragraph(f"Valor médio por aluno: {cost_per_student:.2f}€", styles['Normal']))
    else:
        elements3.append(Paragraph(f"Valor médio por aluno: <font color='red'>{cost_per_student:.2f}€</font>", styles['Normal']))

    elements3.append(Spacer(1, 12))
    if final_balance > 0:
        elements3.append(Paragraph(f"Balanço final: {final_balance:.2f}€", styles['Normal']))
    else:
        elements3.append(Paragraph(f"Balanço final: <font color='red'>{final_balance:.2f}€</font>", styles['Normal']))

    doc3.build(elements3)

    # Merge dos PDFs
    final_buffer = io.BytesIO()
    merger = PdfMerger()
    buffer1.seek(0)
    buffer2.seek(0)
    buffer3.seek(0)
    merger.append(buffer1)
    merger.append(buffer2)
    merger.append(buffer3)
    merger.write(final_buffer)
    merger.close()
    final_buffer.seek(0)

    return FileResponse(final_buffer, as_attachment=True,
                        filename=f"relatorio_mensal_{date_time.replace(':', '-')}.pdf")
