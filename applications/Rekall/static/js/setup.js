// Functions to run after the page is setup.
rekall.utils.update_badge();

rekall.globals.intervalID = setInterval(
    function() {
      rekall.utils.update_badge();
    }, 60000);


$("#inbox").on("click", rekall.users.show_notifications);
