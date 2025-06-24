from django.shortcuts import render


from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group

from data_hub import functions

from .reports.reports import *
from .models import *
from .urls import *
from django.urls import get_resolver
import csv, json
from .forms import ImportFileForm
from .forms import *
import datetime
import io
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


login_url='login'
# Create your views here.

@login_required(login_url=login_url)
def index(request, counter: int = 2):
    imagens = Imagem.objects.all()
    graficos = [imagem.imagem.url for imagem in imagens if imagem.imagem.name.lower().endswith(('.png', '.jpg', '.jpeg'))]

    # Check if the request is from a mobile
    if request.META.get('HTTP_USER_AGENT'):
        user_agent = request.META['HTTP_USER_AGENT'].lower()
        if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
            counter = 1

    return render(request, "index.html", {
        "counter": counter,
        "graficos": graficos
    })

@login_required(login_url=login_url)
def reports(request):
    content = {
        'title': 'Reports',
        'description': 'This is the reports page.',
        'data': []
    }
    return render(request, 'financas/reports.html', content)

# Finanças
@login_required(login_url=login_url)
def alunos_dividas(request):
    content = {
        'title': 'Alunos com Dividas',
        'description': 'Lista de alunos com dividas.',
        'alunos_dividas': Aluno.objects.filter(saldo__lt=-1) if hasattr(Aluno, 'saldo') else [],
    }
    return render(request, 'financas/alunos_dividas.html', content)

@login_required(login_url=login_url)
def add_saldo(request, id_aluno):
    aluno = Aluno.objects.get(pk=id_aluno)
    if request.method == 'POST':
        try:
            valor = float(request.POST.get('valor', 0))
            aluno.saldo += valor
            aluno.save()
            messages.success(request, f'Saldo atualizado com sucesso: {valor}')
        except ValueError:
            messages.error(request, 'Valor inválido.')
        return redirect('alunos_dividas')
    return render(request, 'financas/add_saldo.html', {'aluno': aluno})

@login_required(login_url=login_url)
def registar_pagamento(request, id_aluno=None, tipo_transacao=None, valor=None):
    if request.method == 'POST':
        form = TransacaoForm(request.POST)
        if form.is_valid():
            aluno_id = form.cleaned_data['aluno_id'].pk
            valor = form.cleaned_data['valor']
            descricao = form.cleaned_data['descricao']
            tipo_transacao = form.cleaned_data['tipo_transacao'] or functions.get_tipo_transacao_default(valor)
            try:
                
                functions.pagamento(id_aluno=aluno_id, valor=valor, descricao=descricao, tipo_transacao=tipo_transacao.tipo_transacao_id)
                messages.success(request, f'Pagamento registado com sucesso: {valor}')
            except ValueError:
                messages.error(request, 'Valor inválido.')
            return redirect('/admin/data_hub/aluno/')
    else:
        if id_aluno is None:
            form = TransacaoForm()
        else:
            try:
                aluno = Aluno.objects.get(pk=id_aluno)
                initial = {'aluno_id': aluno}
                if tipo_transacao is not None:
                    initial['tipo_transacao'] = tipo_transacao
                if valor is not None and valor != '':
                    try:
                        valor_float = float(valor)
                        # Se tipo_transacao não for 2, inverter o sinal
                        if str(tipo_transacao) != '2':
                            valor_float = -abs(valor_float)
                        else:
                            valor_float = abs(valor_float)
                        initial['valor'] = valor_float
                    except ValueError:
                        messages.error(request, 'Valor inválido no URL.')
                form = TransacaoForm(initial=initial)
            except Aluno.DoesNotExist:
                form = TransacaoForm()
    return render(request, 'financas/registar_pagamento.html', {'form': form})

# User
def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.groups.filter(name='Pendente').exists() and not user.is_staff and not user.is_superuser:
                messages.error(request, 'O utilizador está pendente de aprovação.')
            else:
                login(request, user)
                return redirect('index')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'user/login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('login')

@login_required(login_url=login_url)
def user_management(request):
    return render(request, 'user/management.html')

# Alunos
@login_required(login_url=login_url)
def galeria(request):
    imagens_por_tipo = {}
    imagens = Imagem.objects.prefetch_related('tipo_imagem_id').all()

    for imagem in imagens:
        for tipo in imagem.tipo_imagem_id.all():
            tipo_nome = tipo.tipo_imagem
            if tipo_nome not in imagens_por_tipo:
                imagens_por_tipo[tipo_nome] = []
            imagens_por_tipo[tipo_nome].append(imagem)
    counter = 3
    # Check if the request is from a mobile
    if request.META.get('HTTP_USER_AGENT'):
        user_agent = request.META['HTTP_USER_AGENT'].lower()
        if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
            counter = 1
    content = {
        'imagens_por_tipo': imagens_por_tipo,
        'counter': counter,
    }
    return render(request, 'testes/galeria.html', content)

@login_required(login_url=login_url)
def import_data(request):
    error = None
    preview = None
    if request.method == 'POST':
        form = ImportFileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            ext = f.name.split('.')[-1].lower()
            if ext not in ['csv', 'json']:
                error = 'Invalid file extension. Only CSV or JSON allowed.'
            else:
                # Read data
                if ext == 'csv':
                    decoded = f.read().decode('utf-8').splitlines()
                    reader = csv.DictReader(decoded)
                    data = list(reader)
                else:
                    data = json.load(f)
                # Preview for row selection
                if 'confirm' not in request.POST:
                    preview = data
                else:
                    replace = form.cleaned_data.get('replace', False)
                    selected_rows = request.POST.getlist('rows')
                    from .models import Aluno  # Change to your target model
                    for i, row in enumerate(data):
                        if replace and str(i) in selected_rows:
                            Aluno.objects.update_or_create(id=row.get('id'), defaults=row)
                        else:
                            Aluno.objects.get_or_create(id=row.get('id'), defaults=row)
                    return redirect('index')
    else:
        form = ImportFileForm()
    if preview is not None:
        return render(request, 'import/import_preview.html', {'form': form, 'data': preview})
    return render(request, 'import/import.html', {'form': form, 'error': error})

@login_required(login_url=login_url)
def export_data_csv(request):
    # Export Aluno data as CSV
    alunos = Aluno.objects.all()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="alunos_export.csv"'

    writer = csv.writer(response)
    # Write header
    fields = [field.name for field in Aluno._meta.fields]
    writer.writerow(fields)
    # Write data rows
    for aluno in alunos:
        writer.writerow([getattr(aluno, field) for field in fields])

    return response

@login_required(login_url=login_url)
def export_data_json(request):
    os.system('python manage.py dumpdata data_hub --indent 4 > data_hub.json')
    with open('data_hub.json', 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="data_hub.json"'
        return response


@csrf_exempt
@login_required(login_url=login_url)
def import_json(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            messages.error(request, 'Nenhum ficheiro enviado.')
            return redirect('import_json')
        try:
            data = json.load(file)
            for obj in data:
                model_name = obj.get('model')
                fields = obj.get('fields', {})
                pk = obj.get('pk')
                if model_name == 'data_hub.aluno':
                    cuidados = fields.pop('cuidados_especias', [])
                    aluno, _ = Aluno.objects.update_or_create(pk=pk, defaults=fields)
                    if hasattr(aluno, 'cuidados_especias'):
                        aluno.cuidados_especias.set(cuidados)
                elif model_name == 'data_hub.responsaveleducativo':
                    aluno_id = fields.pop('aluno_id', None)
                    if aluno_id:
                        fields['aluno_id'] = Aluno.objects.get(pk=aluno_id)
                    ResponsavelEducativo.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.alunosaida':
                    aluno_id = fields.pop('aluno_id', None)
                    if aluno_id:
                        fields['aluno_id'] = Aluno.objects.get(pk=aluno_id)
                    AlunoSaida.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.vacinacao':
                    aluno_id = fields.pop('aluno_id', None)
                    dose_id = fields.pop('dose_id', None)
                    if aluno_id:
                        fields['aluno_id'] = Aluno.objects.get(pk=aluno_id)
                    if dose_id:
                        fields['dose_id'] = Dose.objects.get(pk=dose_id)
                    Vacinacao.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.despesafixa':
                    DespesaFixa.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.despesasvariavel':
                    DespesasVariavel.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.salario':
                    Salario.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.linkfiliacao':
                    aluno_id = fields.pop('aluno_id', None)
                    resp_id = fields.pop('responsavel_educativo_id', None)
                    if aluno_id:
                        fields['aluno_id'] = Aluno.objects.get(pk=aluno_id)
                    if resp_id:
                        fields['responsavel_educativo_id'] = ResponsavelEducativo.objects.get(pk=resp_id)
                    LinkFiliacao.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.tipotransacao':
                    TipoTransacao.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.transacao':
                    aluno_id = fields.pop('aluno_id', None)
                    tipo_transacao = fields.pop('tipo_transacao', None)
                    if aluno_id:
                        fields['aluno_id'] = Aluno.objects.get(pk=aluno_id)
                    if tipo_transacao:
                        fields['tipo_transacao'] = TipoTransacao.objects.get(pk=tipo_transacao)
                    Transacao.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.sala':
                    alunos = fields.pop('alunos', [])
                    funcionario_id = fields.pop('funcionario_id', None)
                    if funcionario_id:
                        fields['funcionario_id'] = Funcionario.objects.get(pk=funcionario_id)
                    sala, _ = Sala.objects.update_or_create(pk=pk, defaults=fields)
                    if alunos:
                        sala.alunos.set(Aluno.objects.filter(pk__in=alunos))
                elif model_name == 'data_hub.mensalidadealuno':
                    aluno_id = fields.pop('aluno_id', None)
                    aluno_financas_id = fields.pop('aluno_financas_id', None)
                    if aluno_id:
                        fields['aluno_id'] = Aluno.objects.get(pk=aluno_id)
                    if aluno_financas_id:
                        fields['aluno_financas_id'] = AlunoFinancas.objects.get(pk=aluno_financas_id)
                    MensalidadeAluno.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.alunofinancas':
                    aluno_id = fields.pop('aluno_id', None)
                    if aluno_id:
                        fields['aluno_id'] = Aluno.objects.get(pk=aluno_id)
                    AlunoFinancas.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.alunofinacascalc':
                    funcionario_id = fields.pop('funcionario_id', None)
                    if funcionario_id:
                        fields['funcionario_id'] = Funcionario.objects.get(pk=funcionario_id)
                    AlunoFinacasCalc.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.funcionario':
                    salario = fields.pop('salario', None)
                    if salario:
                        fields['salario'] = Salario.objects.get(pk=salario)
                    Funcionario.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.comparticipacaomensalss':
                    aluno_id = fields.pop('aluno_id', None)
                    aluno_financas_id = fields.pop('aluno_financas_id', None)
                    if aluno_id:
                        fields['aluno_id'] = Aluno.objects.get(pk=aluno_id)
                    if aluno_financas_id:
                        fields['aluno_financas_id'] = AlunoFinancas.objects.get(pk=aluno_financas_id)
                    ComparticipacaoMensalSs.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.vacina':
                    Vacina.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.dose':
                    vacina_id = fields.pop('vacina_id', None)
                    if vacina_id:
                        fields['vacina_id'] = Vacina.objects.get(pk=vacina_id)
                    Dose.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.divida':
                    aluno_id = fields.pop('aluno_id', None)
                    if aluno_id:
                        fields['aluno_id'] = Aluno.objects.get(pk=aluno_id)
                    Divida.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.acordo':
                    resp_id = fields.pop('responsavel_educativo_id', None)
                    divida_id = fields.pop('divida_id', None)
                    if resp_id:
                        fields['responsavel_educativo_id'] = ResponsavelEducativo.objects.get(pk=resp_id)
                    if divida_id:
                        fields['divida_id'] = Divida.objects.get(pk=divida_id)
                    Acordo.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.tipoimagem':
                    TipoImagem.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.imagem':
                    tipos = fields.pop('tipo_imagem_id', [])
                    imagem, _ = Imagem.objects.update_or_create(pk=pk, defaults=fields)
                    if tipos:
                        imagem.tipo_imagem_id.set(TipoImagem.objects.filter(pk__in=tipos))
                elif model_name == 'data_hub.tipoproblema':
                    TipoProblema.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.valencia':
                    Valencia.objects.update_or_create(pk=pk, defaults=fields)
                elif model_name == 'data_hub.cuidadoespecial':
                    tipo_problema = fields.pop('tipo_problema', None)
                    if tipo_problema:
                        fields['tipo_problema'] = TipoProblema.objects.get(pk=tipo_problema)
                    CuidadoEspecial.objects.update_or_create(pk=pk, defaults=fields)
            messages.success(request, 'Importação concluída com sucesso.')
            return redirect('index')
        except Exception as e:
            messages.error(request, f'Erro ao importar: {e}')
            return redirect('import_json')
    return render(request, 'index.html', {'error': 'Método inválido.'})
