import re
import json
from django.http import HttpResponse

from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache

from django.contrib.auth.models import User, Group
from django.contrib.gis.geos import GEOSGeometry

from ..water_network.models import Element, ElementType, Zone, Location
from ..consumers.models import Consumer
from ..report.models import Report, Ticket
from ..api.get_table import *
from ..api.add_table import *
from ..api.edit_table import *
from ..utils.get_data import is_user_fountain
from ..log.models import Transaction, Log
from ..log.utils import *


error_500 = HttpResponse(False, status=500)
error_404 = HttpResponse(False, status=404)
success_200 = HttpResponse(status=200)


def graph(request):
    export_format = request.GET.get('type', None)
    if export_format == "consumer_gender_pie":
        export = """{
               "jsonarray": [{
                  "label": "Femmes",
                  "data": 0
               }, {
                  "label": "Hommes",
                  "data": 0
               }, {
                  "label": "Autre",
                  "data": 0
               }]}"""
        json_val = json.loads(export)
        all_consumers = Consumer.objects.all()
        for elem in all_consumers:
            if elem.gender == "F" or elem.gender == "Femme":
                json_val['jsonarray'][0]['data'] += 1 #One more women
            elif elem.gender == "M" or elem.gender == "Homme":
                json_val['jsonarray'][1]['data'] += 1 #One more man
            else:
                json_val['jsonarray'][2]['data'] += 1 #One more other
    if export_format == "average_monthly_volume_per_zone":
        # Todo backend : fill "label" with list of zones and "data" with their average output volume in cubic meters.
        # Note that they obviously have to be in the same order
        # Note that the conversion and use of galleons is done in front-end
        # For the formula, I think it would be better to differentiate zones with no data and zones with volume = 0. So
        # that "new" zones aren't left behind for lack of data.
        export = """{
                       "jsonarray": [{
                          "label": ["Nom zone 1", "Nome zone 2"],
                          "data": [10, 20]
                       }]}"""
        json_val = json.loads(export)
    return HttpResponse(json.dumps(json_val))


@csrf_exempt #TODO : this is a hot fix for something I don't understand, remove to debug
def gis_infos(request):
    print(request)
    if request.method == "GET":
        print("Getting infos")
        markers = request.GET.get("marker", None) #The fuck
        if markers == "all": #TODO : be mindfull of the connected user
            all_loc = Location.objects.all()
            result = {}
            for loc in all_loc:
                result[loc.elem.id] = [loc.elem.name, loc.json_representation]
        return HttpResponse(json.dumps(result))

    elif request.method == "POST":
        print("Posting infos")
        print(request.GET)
        elem_id = request.GET.get("id", -1) #The fuck
        if elem_id == -1:
            return HttpResponse("Impossible de trouver l'élément demandé", status=404)
        elem = Element.objects.filter(id=elem_id)
        if len(elem) != 1:
            return HttpResponse("Impossible de trouver l'élément demandé", status=404)
        elem = elem[0]
        if request.GET.get("action", "none") == "add":
            return add_location_element(request, elem)
        elif request.GET.get("action", None) == "remove":
            loc = Location.objects.get(elem_id=elem_id)
            log_element(loc, request)
            loc.delete()
            return HttpResponse(status=200)
        else:
            return HttpResponse("Impossible de traiter cette requête", status=500)



def table(request):
    # Todo backend https://datatables.net/manual/server-side
    # Note that "editable" is a custom field. Setting it to true displays the edit/delete buttons.
    export = """{
                      "editable": true,
                      "data": []
                    }"""
    json_test = json.loads(export)
    json_test["draw"] = str(int(request.GET.get('draw', "1")) + 1)
    d = parse(request)
    all = []
    #Get data
    cache_key = d["table_name"]+request.user.username
    if cache.get(cache_key):
        print("CACHE HIT !")
        all = json.loads(cache.get(cache_key))
        cache.touch(cache_key, 30)
        json_test["recordsTotal"] = len(all)
    else:
        print("CACHE MISS !")
        if d["table_name"] == "water_element":
            if is_user_fountain(request):
                json_test["editable"] = False
            all = get_water_elements(request, json_test, d)
        elif d["table_name"] == "consumer":
            all = get_consumer_elements(request, json_test, d)
        elif d["table_name"] == "zone":
            if is_user_fountain(request):
                return HttpResponse("Vous ne pouvez pas accéder à ces informations", 500)
            all = get_zone_elements(request, json_test, d)
        elif d["table_name"] == "manager":
            if is_user_fountain(request):
                return HttpResponse("Vous ne pouvez pas accéder à ces informations", 500)
            all = get_manager_elements(request, json_test, d)
        elif d["table_name"] == "report":
            all = get_last_reports(request, json_test, d)
        elif d["table_name"] == "ticket":
            all = get_ticket_elements(request, json_test, d)
        elif d["table_name"] == "logs":
            all = get_logs_elements(request, json_test, d)
        elif d["table_name"] == "logs_history":
            all = get_old_logs_elements(request, json_test, d)
        elif d["table_name"] == "payment":
            id = request.GET.get("user", "none")
            if id == "none":
                return success_200
            if is_user_fountain(request):
                json_test["editable"] = False
            all = get_payment_elements(request, json_test, d, id)
        else:
            return HttpResponse("Impossible de charger la table demande ("+d["table_name"]+").", status=404)
        if all:
            cache.set(cache_key, json.dumps(all), 30)

    if all is False: #There was a problem when retrieving the data
        return HttpResponse("Problème à la récupération des données de la table "+d["table_name"], status=500)

    #Filter data
    all = filter_search(d, all)

    if d["table_name"] == "logs" or d["table_name"] == "logs_history"\
            or d["table_name"] == "report":
        if len(all) > 1:
            keys = list(all[0].keys())
            final = sorted(all, key=lambda x: x[keys[d["column_ordered"]]],
                       reverse=d["type_order"] != "asc")
        else:
            final = all
    else:
        final = sorted(all, key=lambda x: x[d["column_ordered"]],
                       reverse=d["type_order"] != "asc")
    if d["length_max"] == -1:
        json_test["data"] = final
    else:
        json_test["data"] = final[d["start"]:d["start"]+d["length_max"]]
    json_test["recordsFiltered"] = len(final)
    print(json.dumps(json_test))
    return HttpResponse(json.dumps(json_test))


def add_element(request):
    element = request.POST.get("table", "")
    cache_key = element+request.user.username
    cache.delete(cache_key)
    if element == "water_element":
        return add_network_element(request)
    elif element == "consumer":
        return add_consumer_element(request)
    elif element == "zone":
        return add_zone_element(request)
    elif element == "manager":
        return add_collaborator_element(request)
    elif element == "ticket":
        return add_ticket_element(request)
    elif element == "payment":
        return add_payment_element(request)
    else:
        return HttpResponse("Impossible d'ajouter l'élément "+element, status=500)


def remove_element(request):
    element = request.POST.get("table", "")
    cache_key = element+request.user.username
    cache.delete(cache_key)
    if element == "water_element":
        id = request.POST.get("id", None)
        consumers = Consumer.objects.filter(water_outlet=id)
        if len(consumers) > 0: #Can't suppress outlets with consummers
            return HttpResponse("Vous ne pouvez pas supprimer cet élément, il est encore attribué à " +
                                "des consommateurs", status=500)
        elem_delete = Element.objects.filter(id=id)
        if len(elem_delete) != 1:
            return HttpResponse("Impossible de supprimer cet élément", status=500)
        elem_delete = elem_delete[0]
        transaction = Transaction(user=request.user)
        if not is_same(elem_delete, request.user):
            transaction.save()
            elem_delete.log_delete(transaction)
        elem_delete.delete()
        tickets = Ticket.objects.filter(water_outlet=id)
        for t in tickets:
            if not is_same(t, request.user):
                t.log_delete(transaction)
            t.delete()
        users = User.objects.filter()
        for u in users:
            if len(u.profile.outlets) > 0: #Gestionnaire de fontaine
                if str(id) in u.profile.outlets:
                    old = u.profile.infos()
                    u.profile.outlets.remove(str(id))
                    u.save()
                    u.profile.log_edit(old, transaction)
        return success_200
    elif element == "consumer":
        id = request.POST.get("id", None)
        to_delete = Consumer.objects.filter(id=id)
        if len(to_delete) != 1:
            return HttpResponse("Impossible de supprimer cet élément", status=500)
        to_delete = to_delete[0]
        log_element(to_delete, request)
        to_delete.delete()
        return HttpResponse({"draw": request.POST.get("draw", 0)+1}, status=200)
    elif element == "manager":
        id = request.POST.get("id", None)
        to_delete = User.objects.filter(username=id)
        if len(to_delete) != 1:
            return HttpResponse("Impossible de supprimer cet élément", status=500)
        to_delete = to_delete[0]
        log_element(to_delete.profile, request)
        to_delete.delete()
        return HttpResponse({"draw": request.POST.get("draw", 0) + 1}, status=200)
    elif element == "ticket":
        id = request.POST.get("id", None)
        to_delete = Ticket.objects.filter(id=id)
        if len(to_delete) != 1:
            return HttpResponse("Impossible de supprimer cet élément", status=500)
        to_delete = to_delete[0]
        log_element(to_delete, request)
        to_delete.delete()
        return HttpResponse({"draw": request.POST.get("draw", 0) + 1}, status=200)
    elif element == "payment":
        id = request.POST.get("id", None)
        payement = Payment.objects.get(id=id)
        log_element(payement, request)
        payement.delete()
        return HttpResponse({"draw": request.POST.get("draw", 0) + 1}, status=200)
    elif element == "zone":
        id = request.POST.get("id", None)
        to_delete = Zone.objects.filter(id=id)
        if len(to_delete) == 1:
            to_delete = to_delete[0]
        else:
            return HttpResponse("Impossible de trouver la zone que vous essayez de supprimer."+
                                " Essayez de recharger la page.", status=404)
        if len(to_delete.subzones) > 1:
            return HttpResponse("Vous ne pouvez pas supprimer cette zone, elle contient encore" +
                                "d'autres zones", status=500)
        if len(Element.objects.filter(zone=id)) > 0:
            return HttpResponse("Vous ne pouvez pas supprimer cette zone, elle contient encore" +
                                "des élements du réseau", status=500)
        for u in User.objects.all():
            if u.profile.zone == to_delete:
                return HttpResponse("Vous ne pouvez pas supprimer cette zone, elle est encore attribuée à" +
                                "un gestionnaire de zone", status=500)
        transaction = Transaction(user=request.user)
        for z in Zone.objects.all():
            if str(to_delete.name) in z.subzones:
                old = z.infos()
                z.subzones.remove(str(to_delete.name))
                z.save()
                z.log_edit(old, transaction)
        if not is_same(to_delete, request.user):
            to_delete.log_delete(transaction)
        transaction.save()
        to_delete.delete()
        return HttpResponse({"draw": request.POST.get("draw", 0) + 1}, status=200)
    return error_500


def edit_element(request):
    element = request.POST.get("table", "")
    cache_key = element+request.user.username
    cache.delete(cache_key)
    if not element:
        element = request.GET.get("table", None)
    if element == "water_element":
        return edit_water_element(request)
    elif element == "consumer":
        return edit_consumer(request)
    elif element == "zone":
        return edit_zone(request)
    elif element == "ticket":
        return edit_ticket(request)
    elif element == "manager":
        return edit_manager(request)
    elif element == "payment":
        return edit_payment(request)
    elif element == "report":
        return edit_report(request)
    else:
        return HttpResponse("Impossible d'éditer la table "+element+
                            ", elle n'est pas reconnue", status=500)


def details(request):
    table = request.GET.get("table", None)
    if table == "payment":
        balance, validity = get_payment_details(request)
        result = {}
        result["balance"] = balance
        result["validity"] = validity
        return HttpResponse(json.dumps(result))
    elif table == "water_element":
        return get_details_network(request)
    else:
        return HttpResponse("Impossible d'obtenir des détails pour la table " + table +
                            ", elle n'est pas reconnue", status=500)



def compute_logs(request):
    id_val = request.GET.get("id", -1)
    action = request.GET.get("action", None)
    cache_key = "logs"+request.user.username
    if id_val == -1 or action == None:
        return HttpResponse("Impossible de valider/annuler ce changement", status=500)
    transaction = Transaction.objects.filter(id=id_val)
    if len(transaction) != 1:
        return HttpResponse("Impossible d'identifier le changement", status=404)
    transaction = transaction[0]
    if action == "accept":
        log_finished(transaction, "ACCEPT")
        cache.delete(cache_key)
        return HttpResponse(status=200)
    elif action == "revert":
        roll_back(transaction)
        cache.delete(cache_key)
        return HttpResponse(status=200)
    else:
        return HttpResponse("Action non reconnue", status=500)


def log_element(element, request):
    if not is_same(element, request.user):
        transaction = Transaction(user=request.user)
        transaction.save()
        element.log_delete(transaction)


def is_same(element, user):
    print(element)
    log = Log.objects.filter(action="ADD", column_name="ID", table_name=element._meta.model_name,
                             new_value=element.id)
    if len(log) != 0:  # If we found a log for adding the element removed
        transaction = log[0].transaction
        if transaction.user == user:
            all_logs = Log.objects.filter(transaction=transaction)
            log_finished(all_logs, transaction)
            return True
    return False


def parse(request):
    test1 = re.compile('order\[\d*\]\[column\]')
    test2 = re.compile('order\[\d*\]\[dir\]')
    res1 = list(filter(test1.match, dict(request.GET).keys()))
    res2 = list(filter(test2.match, dict(request.GET).keys()))
    searchable_cols = []
    for i in range(25):
        if request.GET.get('columns['+str(i)+'][searchable]', False):
            searchable_cols.append(i)
    d = {"table_name": request.GET.get('name', None),
         "length_max": int(request.GET.get('length', 10)),
         "start": int(request.GET.get('start', 0)),
         "column_ordered": int(request.GET.get(res1[0], 0)),
         "type_order": request.GET.get(res2[0], 'asc'),
         "search": request.GET.get('search[value]', ""),
         "searchable": searchable_cols,
         "month_wanted": request.GET.get("month", "none")
         }

    return d
