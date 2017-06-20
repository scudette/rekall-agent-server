// Functions to run after the page is setup.
rekall.utils.update_badge();

rekall.globals.intervalID = setInterval(
    function() {
      rekall.utils.update_badge();
    }, 60000);


$("#inbox").on("click", rekall.users.show_notifications);

function shouldUseDefault(e) {
  return false;
  return ((e = (e || window.event)) && (e.type == 'click' || e.type == 'mousedown' || e.type == 'mouseup') && (e.which > 1 || e.button > 1 || e.ctrlKey || e.shiftKey || browser.mac && e.metaKey)) || false;
}

$("body").on("click", "li.web2py-menu-active a", function(clickEvent) {
  if (shouldUseDefault(clickEvent) === false) {
    rekall.utils.load(clickEvent.currentTarget.href);
    clickEvent.preventDefault();
  }
});


$("body").on("click", "a.link", function(clickEvent) {
  if (shouldUseDefault(clickEvent) === false) {
    rekall.utils.load(clickEvent.currentTarget.href);
    clickEvent.preventDefault();
  }
});
