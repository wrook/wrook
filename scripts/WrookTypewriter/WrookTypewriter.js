
function WrookEditor() {

	var editor = this;
	var isOpen = false;

	this.init = function() {
		this.createEditorTags();
		this.hookup("#wtw-text");
	}

	this.openMenu = function() {
		$("#mnu-saveAndExit")[0].focus();
		$("#wtw-menu").fadeIn(200);
		$("#wtw-help").fadeIn(200);
		editor.isOpen = true;
	}
	
	this.closeMenu = function() {
		$("#wtw-text")[0].focus();
		$("#wtw-menu").fadeOut(200);
		$("#wtw-help").fadeOut(200);
		editor.isOpen = false;
	}

	this.saveAndExit = function() {
		$("#wtw-form")[0].submit()
	}

	this.hookup = function(textFieldId) {
		editor.typewriterField = $("#wtw-text")[0];
		
		$(window).keyup(function (e) {
		  if (e.which == 27) {
			if (editor.isOpen) {
				editor.closeMenu();
			} else {
				editor.openMenu();
			}
		  }
		});

		$(window).keyup(function (e) {
		  if (e.which == 83) {
			if (editor.isOpen) {
				editor.saveAndExit();
			}
		  }
		});

	}

	this.createEditorTags = function() {
	}

	init();

}