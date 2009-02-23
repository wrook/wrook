function MiniMenu() {
	var miniMenu = this;
	this.isOpen = false;
	this.menu = null;
	this.menuElem = null;
	this.menuListElem = null;
	this.defaultTimeout = 2000;
	this.timeout = null;
	this.currentAnchorId = "";
	this.contextId = null;
	this.itemId = null;
	var handlers = {};

	this.registerHandler = function(context, handler) {
		handlers[context] = {
			"context": context,
			"handler": handler
		};
	};

	this.load = function() {
		$j("body").prepend("<div id='miniMenu'><ul></ul></div>");
		miniMenu.menu = $j("#miniMenu");
		miniMenu.menuElem = miniMenu.menu[0];
		miniMenu.menuList = $j("#miniMenu ul");
		miniMenu.menuListElem = miniMenu.menuList[0];
		miniMenu.menu.hover(miniMenu.mouseOver, miniMenu.mouseOut);
		$j(".miniMenuAnchor").each(miniMenu.anchorAttach);
	};

	this.close = function() {
		$j("#" + miniMenu.currentAnchorId).removeClass("stayOn");
		miniMenu.currentAnchorId = "";
		clearTimeout(miniMenu.timeout);
		miniMenu.menu.hide();
		miniMenu.menuList.empty();
		miniMenu.isOpen = false;
	};

	this.startClosing = function() {
		clearTimeout(miniMenu.timeout);
		miniMenu.timeout = setTimeout("miniMenu.onTimeout()", miniMenu.defaultTimeout);
	};

	this.stopClosing = function() {
		clearTimeout(miniMenu.timeout);
	};

	this.onTimeout = function(e) {
		miniMenu.close();
	};

	this.open = function(anchorElem) {
		if (miniMenu.isOpen) { miniMenu.close(); };
		miniMenu.currentAnchorId = anchorElem.id;
		miniMenu.contextId = miniMenu.currentAnchorId.substring(0, miniMenu.currentAnchorId.indexOf("-"));
		miniMenu.itemId = miniMenu.currentAnchorId.substring(miniMenu.currentAnchorId.indexOf("-")+1, 999);
		var handler = handlers[miniMenu.contextId].handler;
		$j("#" + miniMenu.currentAnchorId).addClass("stayOn");
		var offset = $j(anchorElem).offset();
		miniMenu.menuElem.style.top = offset.top + "px";
		miniMenu.menuElem.style.left = (offset.left-110) + "px";
		miniMenu.menuList.empty();
		var menuItems = handler.getMenuItems();
		var getMenuItemCallback = function(menuItem) {
			return function(e){
				menuItem.callback(miniMenu.contextId, menuItem.id, miniMenu.itemId);
				miniMenu.close();
			};
		}
		for (item in menuItems) {
			var menuItem = menuItems[item];
			var listItem = $j("<li><a href='javascript:return false;'>" + menuItem.label + "</a></li>");
			miniMenu.menuList.append(listItem);
			var anchor = $j("a", listItem).click(getMenuItemCallback(menuItem));
		};
		miniMenu.menu.show();
		miniMenu.isOpen = true;
	};

	this.mouseOut = function(e) {
		miniMenu.startClosing();
	};

	this.mouseOver = function(e) {
		miniMenu.stopClosing();
	};

	this.anchorMouseOver = function(e) {
		$j(this).addClass("on");
	};

	this.anchorMouseOut = function(e) {
		if (miniMenu.currentAnchorId == this.id) miniMenu.startClosing();
		$j(this).removeClass("on");
	};

	this.anchorClick = function(e, anchorElem) {
		miniMenu.open(anchorElem) /* TODO: INJECT CONTEXT FROM TAG HERE */
	};

	this.contextMouseOver = function(e, anchorElem) {
		$j(anchorElem).addClass("hover");
	};

	this.contextMouseOut = function(e, anchorElem) {
		$j(anchorElem).removeClass("hover");
	};

	this.anchorAttach = function(i, anchorElem) {
		$j(this).hover(miniMenu.anchorMouseOver, miniMenu.anchorMouseOut);
		$j(this).click(function(e){miniMenu.anchorClick(e, anchorElem)});
		$j(this).parents(".miniMenuContext").hover(function(e){miniMenu.contextMouseOver(e, anchorElem)}, function(e){miniMenu.contextMouseOut(e, anchorElem)});
	};
};

function miniMenuHandler(context) {
	var menuItems = {};
	this.context = context
	this.getMenuItems = function() {
		var tmpItems = []
		for (item in menuItems) tmpItems.push(menuItems[item])
		return tmpItems;
	};
	this.addMenuItem = function(id, label, callback) {
		menuItems[id] = {
			"id": id,
			"label": label,
			"callback": callback
		};
	};
};

var storyPostHandler = new miniMenuHandler();

storyPostHandler.addMenuItem("comment", "Comment", function(context, menuItemId, id){
	$.getJSON("/Talk/Post/" + id + "/Reply/MiniForm/JSON", function(data){
		if (data.errorCode == 0) {
			$j("#" + id).prepend(data.html);
		} else if(data.errorCode > 0) {
			alert("Oups! A problem occured: " + data.errorMessage + " (Error code:" + data.errorCode + ")");
		}
	});
});

storyPostHandler.addMenuItem("delete", "Delete", function(context, menuItemId, id){
	$.getJSON("/Stories/Post/" + id + "/Delete/JSON", function(data){
		if (data.errorCode == 0) {
			console.debug("deleting:", id);
			$j("#" + id).slideUp(1000);
		} else if(data.errorCode > 0) {
			alert("Oups! A problem occured: " + data.errorMessage + " (Error code:" + data.errorCode + ")");
		}
	});
});

var storyPostReplyHandler = new miniMenuHandler();
storyPostReplyHandler.addMenuItem("delete", "Delete", function(context, id){
	console.debug("delete", context, menuItemId, id)
});

var topicHandler = new miniMenuHandler();
topicHandler.addMenuItem("delete", "Delete", function(context, menuITemId, id){
	$.getJSON("/Talk/Topic/" + id + "/Delete/JSON", function(data){
		if (data.errorCode == 0) {
			console.debug("deleting:", id, data);
			$j("#" + id + "-topicMenu").hide();
			$j("#" + id).hide();
			$j("#" + id).after($j("<strong>" + data.html + "</strong>"));
		} else if(data.errorCode > 0) {
			alert("Oups! A problem occured: " + data.errorMessage + " (Error code:" + data.errorCode + ")");
		}
	});
});

var miniMenu = new MiniMenu();
miniMenu.registerHandler("topic", topicHandler);
miniMenu.registerHandler("storyPost", storyPostHandler);
miniMenu.registerHandler("storyPostReply", storyPostReplyHandler);
//REFACTOR: SHIT!!! TEST WITH INSTANCE NAME DIFFERENT FROM miniMenu !!!

$j(document).ready(function(){
	miniMenu.load();

	var offsetLeft = $j("#pageInner").offset().left;
	$j("body")[0].style.backgroundPosition = offsetLeft + "px 0px";

	/* Adjusts the height of the content column to match the height of the sidebar	*/
	sidebarHeight = $j(".sidebar")[0].offsetHeight;
	//contentHeight = $j(".blockBody .middle")[0].offsetHeight
	contentHeight = $j(".blockContent")[0].offsetHeight;
	if (contentHeight < sidebarHeight) {
		$j(".blockContent")[0].style.height = sidebarHeight + "px";
	}
});
