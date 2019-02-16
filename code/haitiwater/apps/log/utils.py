from django.core.mail import send_mail
from django.http import HttpResponse

from .models import Log
from ..water_network.models import Element, Zone
from ..consumers.models import Consumer
from ..report.models import Report, Ticket
from django.contrib.auth.models import User, Group


def log_add(table, column, value, transaction):
    new_val = Log(action="ADD", table_name=table, column_name=column,
                  new_value=value, transaction=transaction)
    new_val.save()


def log_delete(table, column, value, transaction):
    new_val = Log(action="DELETE", table_name=table, column_name=column,
                  old_value=value, transaction=transaction)
    new_val.save()


def log_edit(table, column, old_val, new_val, transaction):
    new_val = Log(action="EDIT", table_name=table, column_name=column,
                  old_value=old_val, new_value=new_val, transaction=transaction)
    new_val.save()


def roll_back(transaction):
    logs = Log.objects.filter(transaction=transaction)
    if logs[0].action == "EDIT": #Edit case
        elements = get_elem_logged(logs)
        tables = get_concerned_tables(logs)
        for number, table in enumerate(tables):
            roll_back_item(
                elements[number],
                {log.column_name: log.old_value
                       for log in logs
                       if log.table_name == table and log.column_name != "ID"}
            )
        log_finished()
    elif logs[0].action == "ADD": #Add case
        elements = get_elem_logged(logs)
        for elem in elements:
            elem.delete()
        log_finished()
    elif logs[0].action == "DELETE": #Delete case
        re_add_item(logs)
        log_finished()


def get_concerned_tables(logs):
    tables = []
    for log in logs:
        if log.column_name == "ID":
            tables.append(log.table_name)
    return tables


def log_finished(logs, transaction):
    for log in logs:
        log.delete()
    transaction.delete()


def roll_back_item(item, values):
    all_attributes = item._meta.get_fields()
    for verbose_field, value in values.items():
        for field in all_attributes:
            if verbose_field == field.verbose_name and verbose_field != "ID":
                item.__setattr__(field.name, value)
    item.save()


def re_add_item(logs):
    tables = get_concerned_tables(logs)
    for table in tables:
        restore_item(
            {log.column_name: log.old_value
                for log in logs
                if log.table_name == table and log.column_name != "ID"},
                table)


def restore_item(dict, table):
    if table == "Consumer":
        outlet = Element.objects.filter(id=dict["Sortie d'eau"])
        if len(outlet) != 1:
            return HttpResponse("Impossible de restaurer cet élément", status=500)
        outlet = outlet[0]
        restored = Consumer(last_name=dict["Nom"], first_name=dict["Prénom"],
                          gender=dict["Genre"], location=dict["Adresse"], phone_number=dict["Numéro de téléphone"],
                          email="", household_size=dict["Taille du ménage"], water_outlet=outlet)
        restored.save()
    elif table == "Ticket":
        outlet = Element.objects.filter(id=dict["Sortie d'eau concernée"])
        if len(outlet) != 1:
            return HttpResponse("Impossible de restaurer cet élément", status=500)
        outlet = outlet[0]
        restored = Ticket(water_outlet=outlet, type=dict["Type de panne"],
                          comment=dict["Commentaire"], urgency=dict["Niveau d'urgence"],
                          status=dict["Etat de résolution"], image=None)
        restored.save()
    elif table == "WaterElement":
        zone = Zone.objects.filter(id=dict["Zone de l'élément"])
        if len(zone) != 1:
            return HttpResponse("Impossible de restaurer cet élément", status=500)
        zone = zone[0]
        restored = Element(name=dict["Nom"], type=dict["Type"],
                           status=dict["État"], location=dict["Localisation"],
                           zone=zone)
        restored.save()
    elif table == "Zone":
        id_zone = dict["Zone mère"].split()[0]
        super_zone = Zone.objects.filter(id=id_zone)
        if len(super_zone) != 1:
            return HttpResponse("Impossible de restaurer cet élément", status=500)
        super_zone = super_zone[0]
        restored = Zone(name=dict["Nom"], superzone=super_zone, subzones=[])
        up = True
        while up:
            super_zone.subzones.append(dict["Nom"])
            super_zone.save()
            super_zone = super_zone.superzone
            if super_zone == None:
                up = False
        restored.save()
    elif table == "Report":
        pass
    elif table == "User":
        password = User.objects.make_random_password()  # New random password
        user = User.objects.create_user(username=dict["Identifiant"],
                                        email=dict["Email"],
                                        password=password,
                                        first_name=dict["Prénom"],
                                        last_name=dict["Nom de famille"])

        if dict["Role"] == "Gestionnaire de fontaine":
            import ast
            water_out = ast.literal_eval(dict["outlets"])
            if len(water_out) < 1:
                user.delete()
                return HttpResponse("Vous n'avez pas choisi de fontaine a attribuer !", status=500)
            elif len(water_out) > 1:
                res = Element.objects.filter(id__in=water_out)
            else:
                res = Element.objects.filter(id=water_out[0])
            if len(res) > 0:
                for outlet in res:
                    user.profile.outlets.append(outlet.id)
            else:
                user.delete()
                return HttpResponse("Impossible d'attribuer cette fontaine au gestionnaire", status=404)
            my_group = Group.objects.get(name='Gestionnaire de fontaine')
            my_group.user_set.add(user)
        elif dict["Role"] == "Gestionnaire de zone":
            zone = dict["Zone gérée"]
            print("zone")
            res = Zone.objects.filter(id=zone)
            print(res)
            if len(res) == 1:
                user.profile.zone = res[0]
                user.save()
            else:
                user.delete()
                return HttpResponse("Impossible d'attribuer cette zone au gestionnaire", status=404)
            my_group = Group.objects.get(name='Gestionnaire de zone')
            my_group.user_set.add(user)
        else:
            user.delete()
            return HttpResponse("Impossible d'ajouter l'utilisateur", status=500)
        send_mail(
            'Changement de mot de passe.',
            'Votre compte haitiwater a été modifié, vous devez donc en changer le mot de passe.'+
            '\nVoici votre nouveau mot de passe autogénéré : ' + password +
            '\nVeuillez vous connecter pour le modifier.\nPour rappel, ' +
            'votre identifiant est : ' + dict["Identifiant"],
            '',
            [dict["Email"]],
            fail_silently=False,
        )


def get_elem_logged(logs):
    tables = get_concerned_tables()
    ids = []
    for elem in logs:
        if elem.column_name =="ID":
            ids.append(elem.new_value)
    elems = []
    for number, table in enumerate(tables):
        elem = None
        if table == "Consumer":
            elem = Consumer.objects.filter(id=ids[number])[0]
        elif table == "Ticket":
            elem = Ticket.objects.filter(id=ids[number])[0]
        elif table == "WaterElement":
            elem = Element.objects.filter(id=ids[number])[0]
        elif table == "Zone":
            elem = Zone.objects.filter(id=ids[number])[0]
        elif table == "Report":
            elem = Report.objects.filter(id=ids[number])[0]
        elif table == "User":
            elem = User.objects.filter(id=ids[number])[0]
        elems.append(elem)
    return elems
