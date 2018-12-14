$(document).ready(function() {

    //Show only relevant form component to the desired user type
    $('#form-add-manager').find('#select-manager-type').on('click', function(){
        $('#form-group-select-zone').addClass('hidden');
        $('#form-group-multiselect-outlets').addClass('hidden');

        if(this.value === 'fountain-manager'){
            $('#form-group-multiselect-outlets').removeClass('hidden');
        }
        else if (this.value === 'zone-manager'){
            $('#form-group-select-zone').removeClass('hidden');
        }
    });
});


/**
 * Validate (check if valid) the form.
 * If not valid, display messages
 */
function validateManagerForm() {
    console.log("validating");
    let form = document.forms["form-add-manager"];

    let id = form["input-manager-id"].value;
    let lastName = form["input-manager-last-name"].value;
    let firstName = form["input-manager-first-name"].value;
    let email = form["input-manager-email"].value;
    let password = form["input-manager-password"].value;
    let type = form["select-manager-type"].value;
    let zone = form["select-manager-zone"].value;

    let outlets = $('#multiselect-manager-outlets').val();


    // Construct an object with selectors for the fields as keys, and
    // per-field validation functions as values like so
    const fieldsToValidate = {
      '#input-manager-last-name' : value => value.trim() !== '',
      '#input-manager-first-name' : value => value.trim() !== '',
      '#input-manager-id' : value => value.trim() !== '',
      '#input-manager-email' : value => value.trim() !== '', //Todo check if email
      '#input-manager-password' : value => value.trim() !== '', //Todo modify
      '#select-manager-type' : value => value.trim() !== 'none',
    };

    const invalidFields = Object.entries(fieldsToValidate)
    .filter(entry => {
        // Extract field selector and validator for this field
        const fieldSelector = entry[0];
        const fieldValueValidator = entry[1];
        const field = form.querySelector(fieldSelector);

        if(!fieldValueValidator(field.value)) {
            // For invalid field, apply the error class
            let fieldErrorSelector = '#' + field.id + '-error';
            form.querySelector(fieldErrorSelector).className = 'error';
            return true;
        }

        return false;
    });

    if (type === 'fountain-manager'){
        if (outlets == null){
            console.log('no fountain');
            $('#multiselect-manager-outlets-error').removeClass('hidden');
            return false;
        }
    }
    if (type === 'zone-manager'){
        if (zone === 'none'){
            console.log('no zone');
            $('#select-manager-zone-error').removeClass('hidden');
            return false;
        }
    }

    // If invalid field length is greater than zero, this signifies
    // a form state that failed validation
    if(invalidFields.length > 0){
        console.log('invalid');
        return false
    } else {
        return buildManagerRequest(id,
            lastName,
            firstName,
            email,
            password,
            type,
            zone,
            outlets);
    }

}

function buildManagerRequest(id, lastName, firstName, email, password, type, zone, outlets){
    let request = "table=manager";
    request += "&id=" + id;
    request += "&lastname=" + lastName;
    request += "&firstname=" + firstName;
    request += "&email=" + email;
    request += "&password=" + password;
    request += "&type=" + type;
    request += "&zone=" + zone;
    request += "&outlets=" + outlets;

    return request;
}

/**
 * Hide the error message in the form
 */
function hideFormErrorMsg(){
    document.getElementById("form-error").className = "alert alert-danger hidden";
}

function setupModalManagerAdd(){
    //Show add components
    $('#modal-manager-title-add').removeClass("hidden");
    $('#modal-manager-submit-add').removeClass("hidden");

    //Hide edit components
    $('#modal-manager-title-edit').addClass("hidden");
    $('#modal-manager-submit-edit').addClass("hidden");

    showManagerModal();
}

function setupModalManagerEdit(data){
    //Todo
}

function showManagerModal(){
    $('#plus-manager').magnificPopup({
        type: 'inline',
        preloader: false,
        focus: '#name',
        modal: true,

        // Do not zoom on mobile
        callbacks: {
            beforeOpen: function() {
                if($(window).width() < 700) {
                    this.st.focus = false;
                } else {
                    this.st.focus = '#name';
                }
            }
        }
    }).magnificPopup('open');
}

/**
 * Hide the modal
 */
function dismissModal() {
    $.magnificPopup.close();
}
