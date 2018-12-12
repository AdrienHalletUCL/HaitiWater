from django.http import HttpResponse
from django.template import loader
from haitiwater.settings import PROJECT_VERSION, PROJECT_NAME


def index(request):
    template = loader.get_template('zone_management.html')
    context = {
        'project_version': PROJECT_VERSION,
        'project_name': PROJECT_NAME,
        'zone_name': "Nom de la zone",  # Todo Backend
        'water_outlets': [(1, 'Ma fontaine avec un nom super long pour tester la taille de la fenêtre'), (2, 'Mon kiosque')]  # Todo backend
    }
    return HttpResponse(template.render(context, request))