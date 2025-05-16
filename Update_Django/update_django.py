import pandas as pd
import socket
import os
from django.utils import timezone
from django.shortcuts import render

hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)

# App creation
def get_apps(folder_path):
    try:
        return [f.replace('.xlsx', '') for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and f.endswith('.xlsx')]
    except Exception as e:
        print(f"Erro ao acessar a pasta: {e}")
        return []

def add_app(app_name, project_name="project"):
    try:
        settings_path = os.path.join(project_name, "settings.py")
        with open(settings_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        start_index = None
        for i, line in enumerate(lines):
            if "INSTALLED_APPS" in line:
                start_index = i
                break

        if start_index is None:
            print("INSTALLED_APPS não encontrado em settings.py.")
            return

        if app_name in "".join(lines[start_index:]):
            print(f"'{app_name}' já está em INSTALLED_APPS.")
            return

        for i in range(start_index, len(lines)):
            if "]" in lines[i]:
                lines.insert(i, f"    '{app_name}',\n")
                break

        with open(settings_path, "w", encoding="utf-8") as file:
            file.writelines(lines)
    except Exception as e:
        print(f"Erro ao atualizar settings.py: {e}")

def add_url(app_name, project_name="project"):
    # Create urls.py in the application
    try:
        app_urls_path = os.path.join(app_name, "urls.py")
        with open(app_urls_path, "w", encoding="utf-8") as file:
            file.write(f"""from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
]
""")
            print(f"Arquivo 'urls.py' criado com sucesso para o app '{app_name}'.")
    except Exception as e:
        print(f"Erro ao criar o arquivo 'urls.py' para o app '{app_name}': {e}")
        
    try:
        urls_path = os.path.join(project_name, "urls.py")
        with open(urls_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
        
        import_index = 0
        # Replace 'from django.urls import path' with 'from django.urls import include, path'
        for i, line in enumerate(lines):
            if line.strip() == "from django.urls import path":
                import_index = i
                print("Import index: " + str(import_index))
                break
        if import_index > 0:
            lines[import_index] = 'from django.urls import include, path\n'   
            with open(urls_path, "w", encoding="utf-8") as file:
                file.writelines(lines)
        
        
        start_index = None
        for i, line in enumerate(lines):
            if "urlpatterns" in line:
                start_index = i
                break

        if start_index is None:
            print("urlpatterns não encontrado em urls.py.")
            return

        # Check if the app is already in urlpatterns
        if f"path('{app_name}/', include('{app_name}.urls'))" in "".join(lines[start_index:]):
            print(f"'{app_name}' já está em urlpatterns.")
            return
    
        for i in range(start_index, len(lines)):
            if "]" in lines[i]:
                lines.insert(i, f"    path('{app_name}/', include('{app_name}.urls')),\n")
                break
        
        print("--------------------------------------------------")
        for line in lines:
            print(line.strip())
        print("--------------------------------------------------")
        
        with open(urls_path, "w", encoding="utf-8") as file:
            file.writelines(lines)
    except Exception as e:
        print(f"Erro ao atualizar urls.py: {e}")

def add_view(app_name):
    try:
        views_path = os.path.join(app_name, "views.py")
        with open(views_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        # Check if the view function already exists
        if "def index(request):" in "".join(lines):
            print(f"A view 'index' já existe em '{views_path}'.")
            return

        # Add the view function to views.py
        with open(views_path, "a", encoding="utf-8") as file:
            file.write("""
def index(request):
    return render(request, 'index.html', {'application_name': '""" + app_name + """'})
""")
    except Exception as e:
        print(f"Erro ao adicionar a view 'index' em '{views_path}': {e}")
                       

# App model creation
def create_model(df, table_name):
    # Function to create models
    info = f"""class {table_name.title().replace("_", "")}(models.Model):
    class Meta:
        db_table = '{table_name}'\n"""
    attributes = []

    for _, row in df.iterrows():
        attributes.append(row["column_name"])
        field_declaration = f"    {row['column_name']} = models.{row['django_field_type']}("
        params = []

        if row["auto_id"] == "Yes":
            params.append("primary_key=True")

        if row["django_field_type"] == "CharField":
            max_length = int(row["datatype_parameters"]) if pd.notna(row["datatype_parameters"]) else 255
            params.append(f"max_length={max_length}")

        if row["django_field_type"] == "ForeignKey":
            params.append(f"to='{row['datatype_parameters'].title().replace('_', '')}', on_delete=models.CASCADE")

        if row["django_field_type"] == "BooleanField":
            if row["null_constraint"] == "NOT NULL":
                default_value = False if pd.isna(row["datatype_parameters"]) else row["datatype_parameters"]
                params.append(f"default={default_value}")
            else:
                params.append("default=False")

        if row["django_field_type"] == "DateField":
            params.append("default=timezone.now")

        if row["null_constraint"] != "NOT NULL":
            params.append("null=True, blank=True")
        else:
            if row["django_field_type"] == "CharField":
                params.append("default=''")

        field_declaration += ", ".join(params) + ")"
        info += field_declaration + "\n"

    info += """
    def __str__(self):
        return f"{""" + f"self.{attributes[1]}" + "} {self." + f"{attributes[2]}" + "}, " + f"{attributes[0].replace('_', ' ').title()}: " + "{" + f"self.{attributes[0]}" + '}"\n'

    return info

def create_models(table_summary_df, file_path, models_path,table_name):
    with open(models_path, "w", encoding="utf-8") as file:
            file.write("from django.db import models\nfrom django.utils import timezone\n\n")
            class_list = []
            table_names = table_summary_df["table_name"].dropna().tolist()
            for table_name in table_names:
                try:
                    sheet_df = pd.read_excel(file_path, sheet_name=table_name)
                    if not sheet_df.empty:
                        model_code = create_model(sheet_df, table_name)
                        file.write(f"{model_code}\n")
                        class_list.append(table_name.capitalize())
                except Exception as e:
                    print(f"Erro ao ler a planilha '{table_name}': {e}")
    return class_list

def add_admin_class(class_list, admin_path):
    with open(admin_path, "w", encoding="utf-8") as file:
        file.write("from django.contrib import admin\n")
        file.write("from .models import *\n\n")
        for table_name in class_list:
            file.write(f"admin.site.register({table_name.title().replace('_', '')})\n")


# HTML creation
def create_directories(application_name):
    # Create 'templates' and 'templatetags' directories
    templates_path = os.path.join(application_name, "templates")
    templatetags_path = os.path.join(application_name, "templatetags")

    try:
        os.makedirs(templates_path, exist_ok=True)
        print(f"Pasta 'templates' criada com sucesso em '{templates_path}'.")
    except Exception as e:
        print(f"Erro ao criar a pasta 'templates': {e}")

    try:
        os.makedirs(templatetags_path, exist_ok=True)
        init_file_path = os.path.join(templatetags_path, "__init__.py")
        with open(init_file_path, "w", encoding="utf-8") as init_file:
            init_file.write("# This file makes this directory a Python package\n")
        print(f"Pasta 'templatetags' criada com sucesso em '{templatetags_path}'.")
    except Exception as e:
        print(f"Erro ao criar a pasta 'templatetags': {e}")

def create_base_templates(application_name):
    base_template_path = os.path.join(application_name, "templates", "layout.html")
    index_template_path = os.path.join(application_name, "templates", "index.html")

    try:
# Create layout.html
        with open(base_template_path, "w", encoding="utf-8") as layout_file:
            layout_file.write("""{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %} {{application_name}} {% endblock %}</title>
    <link rel="stylesheet" href="{% static 'css/style.css' %}">
</head>
<body>
    <header>
        <h1>Welcome to {{ application_name }}</h1>
    </header>
    <nav>
        {% block nav %}
        <ul>
            <li><a href="/">Home</a></li>
        </ul>
        {% endblock %}
    </nav>
    <main>
        {% block content %}
        {% endblock %}
    </main>
    <footer>
        <p>&copy; 2023 My Application</p>
    </footer>
</body>
</html>
""")
# Create index.html
        with open(index_template_path, "w", encoding="utf-8") as index_file:
            index_file.write("""{% extends 'layout.html' %}

{% block title %}Home{% endblock %}

{% block content %}
<h2>Welcome to the Home Page</h2>
<p>This is the index page for {{ application_name }}.</p>
{% endblock %}
""")
    except Exception as e:
        print(f"Erro ao criar os templates base: {e}")

def create_static_files(application_name, project_name="project"):
    static_path = os.path.join(application_name, "static", "css")
    
    static_root = os.path.join(project_name, "static")
    
    try:
        os.makedirs(static_path, exist_ok=True)
        css_file_path = os.path.join(static_path, "style.css")
        with open(css_file_path, "w", encoding="utf-8") as css_file:
            css_file.write("/* CSS styles for the application */\n")
    except Exception as e:
        print(f"Erro ao criar o arquivo CSS: {e}")
    
    try:
        settings_path = os.path.join(project_name, "settings.py")
        with open(settings_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
        
        # Check if 'os' is imported, and if not, add it
        if not any(line.strip().startswith("import os") for line in lines):
            lines.insert(0, "import os\n")
        
        with open(settings_path, "w", encoding="utf-8") as file:
            file.writelines(lines)

        static_root_line = ""
        if not any(line.strip().startswith("STATIC_ROOT = os.path.join(BASE_DIR, '{static_root}')") for line in lines):
            static_root_line = f"STATIC_ROOT = os.path.join(BASE_DIR, '{static_root}')\n"

        # Check if STATIC_ROOT is already defined
        if any("STATIC_ROOT" in line for line in lines):
            print("STATIC_ROOT já está definido no settings.py.")
        else:
            # Add STATIC_ROOT at the end of the file
            with open(settings_path, "a", encoding="utf-8") as file:
                file.write("\n" + static_root_line)
            print("STATIC_ROOT adicionado com sucesso no settings.py.")
    except Exception as e:
        print(f"Erro ao adicionar STATIC_ROOT no settings.py: {e}")

def create_base_pages(application_name, project_name="faz_e_conta"):
    try:
        create_directories(application_name)
        create_base_templates(application_name)
        create_static_files(application_name, project_name)
        print(f"Páginas base criadas com sucesso para '{application_name}'!")
    except Exception as e:
        print(f"Erro ao criar páginas base para '{application_name}': {e}")

# App framework creation
def read_cdm(sheet_name="Table Summary", application_name="", path=""):
    file_path = os.path.join(path, f"{application_name}.xlsx")
    models_path = os.path.join(application_name, "models.py")
    admin_path = os.path.join(application_name, "admin.py")

    try:
        table_summary_df = pd.read_excel(file_path, sheet_name)
        class_list = []
    except FileNotFoundError:
        print(f"Erro: O arquivo '{file_path}' não foi encontrado.")
        return
    except Exception as e:
        print(f"Erro ao ler a planilha '{sheet_name}': {e}")
        return
    
    if "table_name" not in table_summary_df.columns:
            print("Erro: A coluna 'table_name' não está presente na planilha 'Table Summary'.")
            return

# Models
    try:
        class_list = create_models(table_summary_df, file_path, models_path, sheet_name)
        add_admin_class(class_list, admin_path)
        add_url(application_name, "faz_e_conta")
        add_view(application_name)
        print(f"Modelos criados e adicionados com sucesso para '{application_name}'!")
    except Exception as e:
        print(f"Erro: {e}")
        
# HTML
    # create_base_pages(application_name, "faz_e_conta")


def run():
    os.system("cls")
    folder_path = "./Update_Django/projects/"
    file_names = get_apps(folder_path)

    print("--------------------------------------------------")
    for file_name in file_names:
        print(f"Iniciando o app '{file_name}'...")
        print("--------------------------------------------------")
        app_path = os.path.join("faz_e_conta", file_name)
        if not os.path.exists(app_path):
            try:
                os.system(f"django-admin startapp {file_name}")
            except Exception as e:
                print(f"Erro ao criar o app '{file_name}': {e}")
                continue
        
        try:
            add_app(file_name, "faz_e_conta")
        except Exception as e:
            continue
        
        read_cdm(path=folder_path, application_name=file_name)

        print(f"Processo concluído com sucesso para '{file_name}'!")
        print("Iniciando o próximo app...")
        print("--------------------------------------------------")
        
    print("Todos os apps foram processados com sucesso!")


    print("--------------------------------------------------")
    print("Fazendo a migração do banco de dados...")
    os.system("python manage.py makemigrations")
    os.system("python manage.py migrate")
    print("Migração do banco de dados concluída com sucesso!")
    
    os.system("python manage.py createsuperuser")


    print("--------------------------------------------------")
    if input("Deseja iniciar o servidor Django? (s/n): ").lower() == "s":
        print("Iniciando o servidor Django...")
        os.system("python manage.py runserver 0.0.0.0:8000")
        print("Servidor Django iniciado com sucesso!")
        print("--------------------------------------------------")

# Run
run()