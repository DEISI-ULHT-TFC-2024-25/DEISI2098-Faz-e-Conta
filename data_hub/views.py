from django.shortcuts import render


from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group

from django.core.management import call_command
import io

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
    if request.method == 'POST':
        form = ImportFileForm(request.POST, request.FILES)
        if form.is_valid():
            json_file = request.FILES['file']
            try:
                data = json.load(json_file)
                # Suporta formato de dumpdata do Django (lista de dicts com 'model', 'pk', 'fields')
                if isinstance(data, list) and all('model' in item and 'fields' in item for item in data):
                    for item in data:
                        model_name = item['model'].split('.')[-1]
                        if model_name == 'aluno':
                            fields = item['fields']
                            pk = item['pk']
                            cuidados_especias = fields.pop('cuidados_especias', [])
                            aluno_obj, _ = Aluno.objects.update_or_create(pk=pk, defaults=fields)
                            if hasattr(aluno_obj, 'cuidados_especias'):
                                aluno_obj.cuidados_especias.set(cuidados_especias)
                        # Adicione outros modelos conforme necessário
                    messages.success(request, 'Dados importados com sucesso.')
                    return redirect('index')
                else:
                    messages.error(request, 'Formato de arquivo JSON não suportado.')
            except Exception as e:
                messages.error(request, f'Erro ao importar: {e}')
        else:
            messages.error(request, 'Formulário inválido.')
    else:
        form = ImportFileForm()
    return render(request, 'import/import_data.html', {'form': form})


@login_required(login_url=login_url)
def export_data_json(request):
    buffer = io.StringIO()
    call_command('dumpdata', 'data_hub', indent=4, stdout=buffer)
    json_data = buffer.getvalue()
    response = HttpResponse(json_data, content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="data_hub.json"'
    return response
    
