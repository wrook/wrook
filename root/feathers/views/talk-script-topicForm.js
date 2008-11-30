$(document).ready(function() { 
    var options = { 
        //target:        '',   // target element(s) to be updated with server response 
        beforeSubmit:  frmAddNewTopicOnBeforeSubmit,  // pre-submit callback 
        success: frmAddNewTopicOnSuccess  // post-submit callback 
 
        // other available options: 
        //url:       url         // override for form's 'action' attribute 
        //type:      type        // 'get' or 'post', override for form's 'method' attribute 
        //dataType:  null        // 'xml', 'script', or 'json' (expected server response type) 
        //clearForm: true        // clear all form fields after successful submit 
        //resetForm: true        // reset the form after successful submit 
         // $.ajax options can be used here too, for example: 
        //timeout:   3000 
    }; 
 
    // bind form using 'ajaxForm' 
    $('#frmAddNewTopic').ajaxForm(options); 
    $('#frmAddNewTopic-body').autogrow({
		maxHeight: 200,
		minHeight: 40
	});


	frm = $('#frmAddNewTopic');
/*
	$('input', frm).example(function() {
		return $(this).attr('title');
	}, { className: 'inputExample' });

	$('textarea', frm).example(function() {
		return $(this).attr('title');
	}, { className: 'inputExample' });
*/
	$("#frmAddNewTopic").validate({
		onsubmit: false,
		rules: {
			title: "required"
		},
		messages: {
			title: {required: "The title of the topic is mandatory"}
		}
	});

}); 
function frmAddNewTopicOnBeforeSubmit(formData, jqForm, options) {
	if (jqForm.valid()) {
		$(".submit", jqForm).hide();
		$(".loadingMessage", jqForm).show();
		return true;
	} else {
		return false;
	}
}
function frmAddNewTopicOnSuccess(responseText, statusText) {
	var elems = $("#newTopicsPlaceholder").prepend(responseText)
	frm = $("#frmAddNewTopic")
	frm.clearForm();
	$(".submit", frm).show();
	$(".loadingMessage", frm).hide();
	$(elems).effect("highlight", {}, 10000);
}
