$(document).ready(function() { 
    var options = { 
        //target:        '',   // target element(s) to be updated with server response 
        beforeSubmit:  frmAddNewReplyOnBeforeSubmit,  // pre-submit callback 
        success: frmAddNewReplyOnSuccess  // post-submit callback 
 
        // other available options: 
        //url:       url         // override for form's 'action' attribute 
        //type:      type        // 'get' or 'post', override for form's 'method' attribute 
        //dataType:  null        // 'xml', 'script', or 'json' (expected server response type) 
        //clearForm: true        // clear all form fields after successful submit 
        //resetForm: true        // reset the form after successful submit 
         // $.ajax options can be used here too, for example: 
        //timeout:   3000 
    }; 
 
	frm = $('#frmAddNewReply');
    // bind form using 'ajaxForm' 
    frm.ajaxForm(options); 
    $('#frmAddNewReply-body').autogrow({
		maxHeight: 200,
		minHeight: 40
	});

/*
	$('input', frm).example(function() {
		return $(this).attr('title');
	}, { className: 'inputExample' });

	$('textarea', frm).example(function() {
		return $(this).attr('title');
	}, { className: 'inputExample' });
*/
	frm.validate({
		onsubmit: false,
		rules: {
			body: "required"
		},
		messages: {
			body: {required: "The text of the reply is mandatory"}
		}
	});

}); 
function frmAddNewReplyOnBeforeSubmit(formData, jqForm, options) {
	if (jqForm.valid()) {
		$(".submit", jqForm).hide();
		$(".loadingMessage", jqForm).show();
		return true;
	} else {
		return false;
	}
}
function frmAddNewReplyOnSuccess(responseText, statusText) {
	var elems = $("#newRepliesPlaceholder").prepend(responseText)
	frm = $("#frmAddNewReply")
	frm.clearForm();
	$(".submit", frm).show();
	$(".loadingMessage", frm).hide();
	$(elems).effect("highlight", {}, 10000);
}
