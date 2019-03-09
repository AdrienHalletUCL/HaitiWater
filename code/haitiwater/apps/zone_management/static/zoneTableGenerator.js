function drawZoneTable(){
    let baseURL = location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '');
    let dataURL = baseURL + "/api/table/?name=zone";
    console.log("Request data from: " + dataURL);
    $('#datatable-zone').DataTable(getZoneTableConfiguration(dataURL));

    let table = $('#datatable-zone').DataTable();
    $('#datatable-zone tbody').on( 'click', 'tr td:not(:last-child)', function () {
        row = $(this).closest('tr');
        if ( row.hasClass('selected') ) {
            row.removeClass('selected');
            filterManagerFromZone(table);
            filterWaterElementFromZone(table);
        }
        else {
            table.$('.selected').removeClass('selected');
            row.addClass('selected');
            filterManagerFromZone(table);
            filterWaterElementFromZone(table);
        }
    });

    $('#datatable-zone tbody').on( 'click', '.remove-row', function () {
        let data = $(this).parents('tr')[0].getElementsByTagName('td');
        if (confirm("Voulez-vous supprimer: " + data[1].innerText + ' ' + data[2].innerText + ' ?')){
            removeElement("zone", data[0].innerText);
        } else {}
    } );
    $('#datatable-zone tbody').on( 'click', '.edit-row', function () {
        let data = table.row($(this).closest('tr')).data();
        setupModalZoneEdit(data);
    } );
    prettifyHeader('zone');

    return table;
}

/**
 * Automatically fill the field on the manager table from the selected zone
 * (Takes the data from the first tr.selected)
 *
 * @param zoneTable the table zone datatable object
 */
function filterManagerFromZone(zoneTable){
    let data = zoneTable.row('tr.selected').data();

    if  (data == null){ // If nothing selected
        $('#datatable-manager').DataTable().search("").draw();
        return;
    }
    let zoneName = data[1];
    $('#datatable-manager').DataTable().search(zoneName).draw();

}

function filterWaterElementFromZone(zoneTable){
    let data = zoneTable.row('tr.selected').data();

    if  (data == null){ // If nothing selected
        $('#datatable-water_element').DataTable().search("").draw();
        return;
    }
    let zoneName = data[1];
    $('#datatable-water_element').DataTable().search(zoneName).draw();
}

function getZoneTableConfiguration(dataURL){
    let config = {
        lengthMenu: [
            [ 10, 25, 50, -1 ],
            [ '10', '25', '50', 'Tout afficher' ]
        ],
        dom: 'Bfrtip',
        buttons: [
            {
                extend: 'print',
                exportOptions: {
                    columns: [0,1,2,3,4,5,6],
                },
            },
            'pageLength'
        ],
        "sortable": true,
        "processing": true,
        "serverSide": true,
        "responsive": false,
        "autoWidth": true,
        scrollX:        true,
        scrollCollapse: true,
        paging:         true,
        fixedColumns:   {
            leftColumns: 1,
            rightColumns: 1
        },
        "columnDefs": [{
                "targets": -1,
                "data": null,
                "orderable": false,
                "defaultContent": getActionButtonsHTML("modalZone"),
            },
            ],
        "language": getDataTableFrenchTranslation(),
        "ajax": {
            url: dataURL
        },

        //Callbacks on fetched data
        "createdRow": function (row, data, index) {
            $('td', row).eq(5).addClass('text-center');
            $('td', row).eq(6).addClass('text-center');
        },
        "initComplete": function(settings, json){
            // Removes the last column (both header and body) if we cannot edit the table
            if(!(json.hasOwnProperty('editable') && json['editable'])){
                $('#datatable-zone').find('tr:last-child th:last-child, td:last-child').remove();
            }
        }
    };
    return config;
}
