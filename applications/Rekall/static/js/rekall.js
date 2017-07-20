// Various utilities for the UI
rekall.utils = {};

rekall.utils.load = function(url, data) {
  if (data) {
    url += "?" + $.param(data);
  };

  $(".loading").toggleClass("disabled", false);
  $.ajax({
    url: url,
    headers: {
      "x-rekall-bare-layout": 1,
    },
    success: function(data) {
      $("#main").html(data);
      if (window.location.href != url) {
        window.history.pushState({url: url}, "", url);
      }
      $("#modal").modal("hide");
      $(".loading").toggleClass("disabled", true);
    }
  });
}

rekall.utils.submit_form = function(obj) {
  var selector = obj.selector || "form";
  var url = obj.url || $(selector).attr("action");
  var method = $(selector).attr("method") || "GET";
  var data;

  if (method == "GET") {
    url += "?" + $(selector).serialize();
  } else {
    data = $(selector).serializeArray();
  }
  $(".loading").toggleClass("disabled", false);
  $.ajax({
    url: url,
    method: method,
    headers: {
      "x-rekall-bare-layout": 1,
    },
    data: data,
    success: function(html) {
      $("#main").html(html);
      if (window.location.href != url) {
        window.history.pushState({url: url, data: data, method: method}, "", url);
      }

      if (obj.next) {
        rekall.utils.load(obj.next, obj.data);
      } else {
        $(".loading").toggleClass("disabled", true);
      }
    }
  });
}

rekall.utils.api = function(endpoint) {
  return rekall.globals.api_route + endpoint;
}

// A wrapper around an $.ajax object which modifies the url, adds a common csrf
// header etc. The returned object should be sent to $.ajax for actual
// processing.
rekall.utils.call = function(obj) {
  if (!obj.headers) obj.headers = {};
  obj.headers["x-rekall-csrf-token"] = rekall.csrf_token;

  if (!obj.dataType) obj.dataType = "json";
  obj.url = rekall.utils.api(obj.api);
  return obj;
}

rekall.utils.escape_text = function(text) {
  return $("<div>").text(text).html();
}

rekall.utils.get = function(obj, item, def) {
  var result = obj[item];
  if (result === undefined) {
    return def;
  }
  return result;
}

rekall.utils.make_link = function(url, image) {
  var link = $("<a class='link rekall-glyphicon'>").attr("href", url).append(
      $("<span class='glyphicon' aria-hidden='true'>").addClass(image));
  return link.prop('outerHTML');
}

// Watch clicks on watch_selector for any enabled checkboxes and enable/disable
// the button in response.
rekall.utils.watch_checkboxes_to_disabled_button = function(
    watch_selector, button_seletor) {
  $(watch_selector).on("click", function() {
    var checked = false;

    $(this).find("input[type=checkbox]").each(function () {
      if (this.checked) checked=true;
    });

    if (checked) {
      $(button_seletor).removeClass("disabled");
    } else {
      $(button_seletor).addClass("disabled");
    }
  });
}

rekall.utils.update_badge = function() {
  rekall.utils.call({
    api: '/users/notifications/count',
    success: function(count) {
      if (count == 0) count = "";
      $("#notifications").text(count);
    },
    error: function() {}, // Ignore errors.
  });
}

// Escape text to html safely.
rekall.utils.safe_html = function(text) {
  return $("<div>").text(text).html();
}

rekall.utils.checkbox_tristate = function () {
  if (this.readOnly) this.checked=this.readOnly=false;
  else if (!this.checked) this.readOnly=this.indeterminate=true;
}

rekall.utils.error = function(jqXHR) {
  var description;

  if (jqXHR.responseJSON) {
    description = rekall.cell_renderers.generic_json_renderer(
        jqXHR.responseJSON);
  } else {
    description = rekall.utils.safe_html(jqXHR.responseText);
  }

  $("#modalContainer").html(
      rekall.templates.modal_template(
          description,
          "Error: " + jqXHR.statusText,
          ));
  $("#modal").modal("show");
}

rekall.utils.error_container = function(jqXHR) {
  if (jqXHR.responseJSON) {
    $("#error_message").text(jqXHR.responseJSON.error);
  } else {
    $("#error_message").text(jqXHR.responseText);
  }
  $("#error_message_container").show();
}

rekall.utils.editor_popup = function(text, type) {
  type = type || "yaml";
  var save = $('<button type="button" class="btn btn-default" id="save">Save</button>');

  $("#modalContainer").html(
      rekall.templates.modal_template(
          $('<div class="editor" id="editor">').text(text).prop("outerHTML"),
          "Title", save));
  $("#modal").modal("show");

  var editor = ace.edit("editor");
  editor.setTheme("ace/theme/monokai");
  editor.getSession().setMode("ace/mode/" + type);

  save.click(function () {
    rekall.utils.download_to_browser("download.sh", editor.getValue());
    return false;
  });
}

rekall.utils.download_to_browser = function(filename, text) {
  var element = document.createElement('a');
  element.setAttribute('href', 'data:text/plain;charset=utf-8,' +
      encodeURIComponent(text));
  element.setAttribute('download', filename);

  element.style.display = 'none';
  document.body.appendChild(element);

  element.click();

  document.body.removeChild(element);
}

rekall.utils.parseParams = function (str) {
  return str.split('&').reduce(function (params, param) {
    var paramSplit = param.split('=').map(function (value) {
      return decodeURIComponent(value.replace('+', ' '));
    });
    params[paramSplit[0]] = paramSplit[1];
    return params;
  }, {});
}


// Templates. We use jquery native templates because these are faster and safer
// than other javascript based templates.
rekall.templates = {}
rekall.templates.modal_template = function(body, title, footer) {
  var result = $(`
  <div class="modal fade" id="modal" tabindex="-1" role="dialog"
       aria-labelledby="myModalLabel">
    <div class="modal-dialog modal-lg" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <button type="button" class="close" data-dismiss="modal"
                  aria-label="Close">
             <span aria-hidden="true">&times;</span>
          </button>
          <h4 class="modal-title"></h4>
        </div>
        <div class="modal-body">
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-default"
                  data-dismiss="modal">Close</button>
        </div>
      </div>
    </div>
  </div>
`);
  result.find(".modal-title").text(title);
  result.find(".modal-body").html(body);
  if (footer) {
    result.find(".modal-footer").append(footer);
  }

  return result;
}

rekall.templates.mint_token = function(roles) {
  var result = $(`
<div class="panel panel-danger">
 <div class="panel-heading">
    <h3 class="panel-title">Mint an access token</h3>
 </div>

 <div class="panel-body">
   To access the API without authentication you will need to obtain an access
   token. The token is time limited and restricts access to a set of roles and
   resources.

   <div class="input-group input-group-sm">
      <div class="input-group-btn">
        <button type="button" class="btn btn-default" id="role">All</button>
        <button type="button" class="btn btn-default dropdown-toggle"
                data-toggle="dropdown" aria-haspopup="true"
                aria-expanded="false"><span class="caret"></span></button>
        <ul class="dropdown-menu">
        </ul>
      </div>
      <input type="text" id="resource" name="resource" class="form-control"
             placeholder="Resource path...">
   </div>
   <div class="input-group input-group-lg">
     <div class="input-group-btn">
       <button type="button" class="btn btn-default" id="get_mint">Mint</button>
     </div>
     <input type="text" id="token" class="form-control"
            placeholder="Click to generate..."">
   </div>
 </div>
</div>
`);

  var ul = result.find("ul");
  for (var i=0; i<roles.length; i++) {
    var link = $("<a href='#'>").click(function () {
      $("#role").text($(this).text());
      return false;
    });
    link.text(roles[i]).appendTo($("<li>").appendTo(ul));
  }

  result.find("#get_mint").click(function () {
    var role = $("#role").text();
    var resource = $("#resource").val();
    if (!resource) {
      resource = "/";
    }

    $.ajax(rekall.utils.call({
      api: '/users/tokens/mint',
      data: {
        role: role,
        resource: resource,
      },
      success: function(mint) {
        $("#token").val("token=" + mint.token).show();
      },
      error: function(jqXHR) {
        $("#token").val(jqXHR.responseJSON.error).show().addClass(
            "alert-danger");
      },
    }));
    return false;
  });

  return rekall.templates.modal_template(result, "Mint Access Token");
}

rekall.templates.save_flows = function(canned_flow) {
  var form = $(`
<form id="canned_flow_form" class="form-horizontal">
<div id="canned_flow"></div>
<div class="form-group">
 <label class="col-sm-2 control-label" for="name"
  title="The name of the canned flow">Name</label>
 <div class="col-sm-7">
   <input class="form-control" id="name" type="text">
 </div>
</div>
<div class="form-group">
 <label class="col-sm-2 control-label" for="category"
  title="The name of the canned flow">Category</label>
 <div class="col-sm-7">
   <input class="form-control" id="category" type="text">
 </div>
</div>
<div class="form-group">
 <label class="col-sm-2 control-label" for="description"
  title="A description of this canned flow.">Description</label>
 <div class="col-sm-7">
   <input class="form-control" id="description" type="text">
 </div>
</div>
</form>`).append(rekall.templates.error_message_container());
  form.find("#canned_flow").html(
      rekall.cell_renderers.generic_json_renderer(canned_flow));

  return form;
}

rekall.templates.error_message_container = function() {
  return $(`
<div class="alert alert-danger" role="alert"
  id="error_message_container" style="display: none">
  <span class="glyphicon glyphicon-exclamation-sign"
   aria-hidden="true"></span>
  <span class="sr-only">Error:</span>
  <div id="error_message"></div>
</div>
`);
}

rekall.templates.load_precanned_flow_template = function(client_id) {
  var table = $(`
<div class="table-container">
  <table id="canned" class="display" cellspacing="0" width="100%"></table>
</div>
`).append(rekall.templates.error_message_container());

  table.find("#canned").DataTable({
    ajax: rekall.utils.call({
      api: "/flows/list_canned",
      error: rekall.utils.error,
    }),
    columns: [
      {
        title: '',
        data: "name",
        sortable: false,
        render: function(name, type, row, meta) {
          var link = $('<a href="#">');
          link.attr("data-name", name);
          var img = $("<img class='icon'>")
              .attr("src", rekall.globals.image_dir + 'launch-icon.png')
              .appendTo(link);

          return link.prop("outerHTML");
        }
      },
      {
        title: "Category",
        data: "category"
      },
      {
        title: "Name",
        data: "name"
      },
      {
        title: "Description",
        data: "description",
      },
    ]
  });

  table.on("click", "a[data-name]", function() {
    $.ajax(rekall.utils.call({
      api: "/flows/launch_canned",
      data: {
        client_id: client_id,
        name: $(this).data("name"),
      },
      error: rekall.utils.error_container,
      success: function() {
        rekall.utils.load(window.location.href);
        $("#modal").modal("hide");
      }
    }));
  });

  return table;
}

rekall.templates.flow_download_script = function(metadatas) {
  var result = "";
  var sanitize = function(str) {
    str = str + "";
    var regex = /[^a-zA-Z0-9-_/:&]/g;
    return str.replace(regex, ".");
  }

  var strict_sanitize = function(str) {
    str = str + "";
    var regex = /[^a-zA-Z0-9-_]/g;
    return str.replace(regex, ".");
  }

  for (var i=0; i<metadatas.length; i++) {
    var metadata = metadatas[i];
    var api_endpoint = sanitize(rekall.globals.api_route);
    var client_id = sanitize(metadata.client_id);
    var flow_id = sanitize(metadata.name);
    var token = sanitize(metadata.token);

    result += "\r\n\r\necho Fetching flow " + sanitize(flow_id) + "\r\n" +
        "mkdir -p '" + flow_id + "'    '" +
        flow_id + "/collections/'" + "    '" +
        flow_id + "/uploads/'" + " \r\n\r\n";

    if (metadata.collection_ids) {
      for (var i=0; i<metadata.collection_ids.length; i++) {
        var collection_id = metadata.collection_ids[i];
        result += ("wget --output-document='" + flow_id +
            "/collections/" + collection_id + ".json' \\\n" +
            '  "' + api_endpoint + "/collections/get?client_id=" +
            client_id + "&collection_id=" + collection_id +
            "&token=" + token + '" \n');
      }
    };

    if (metadata.file_infos) {
      for (var i=0; i<metadata.file_infos.length; i++) {
        var file_info = metadata.file_infos[i];
        var upload_id = sanitize(file_info.upload_id);
        var filename = "";

        if (file_info.file_information && file_info.file_information.filename) {
          filename = file_info.file_information.filename;
        }

        result += ("# For " + sanitize(file_info.file_information.filename) +
            "\r\nwget --output-document='" + flow_id +
            "/uploads/" + upload_id + strict_sanitize(filename) + "' \\\n" +
            '  "' + api_endpoint + "/uploads/download?upload_id=" +
            upload_id + "&token=" + token + '" \n')
      }
    }
  }

  return result;
}


rekall.templates.render_client_info = function(client_info) {
  return rekall.cell_renderers.generic_json_renderer(client_info);
}

rekall.templates.label_clients = function(client_ids, labels) {
  var form = $("<form><input type='text' name='labels'>")
      .append(rekall.templates.error_message_container());

  $(labels).each(function () {
    var checkbox = $("<input type='checkbox' name='existing'>")
        .attr("value", this)
        .prop("indeterminate", true);
    form.append(checkbox).append($("<div>").text(this));
  });

  $(form).find("input[name=existing]").click(
      rekall.utils.checkbox_tristate);

  return form;
}

rekall.templates.create_hunt_from_flows = function(labels, flow_ids) {
  var result=$(`
<div>
  <div class="input-group ui-widget">
    <span class="input-group-addon" id="basic-addon1">Label</span>
    <input type="text" class="form-control" id="labels"
     placeholder="Comma separated list of labels.">
     <span class="input-group-addon" id="label_complete">
       <span class="caret"></span>
     </span>
  </div>
  <div class="input-group ui-widget">
    <span class="input-group-addon" id="basic-addon1">Approvers</span>
    <select multiple class="form-control" id="approvers"
     placeholder="Comma separated list of approvers.">
  </div>
</div>
`).append(rekall.templates.error_message_container());

  function split( val ) {
    return val.split( /,\s*/ );
  }
  function extractLast( term ) {
    return split( term ).pop();
  }

  $.ajax(rekall.utils.call({
    api: "/client/approver/list",
    error: rekall.utils.error_container,
    success: function(data) {
      var selector = $("#approvers");
      for (var i=0; i<data.data.length; i++) {
        var user = data.data[i];
        selector.append($("<option>").attr("value", user).text(user));
      }
    }
  }));

  var labels_input = result.find("#labels");
  result.find("#label_complete").click(function () {
    labels_input.trigger(jQuery.Event("keydown"));
    return false;
  });
   // don't navigate away from the field on tab when selecting an item
  labels_input.on( "keydown", function( event ) {
    if ( event.keyCode === $.ui.keyCode.TAB &&
        $( this ).autocomplete( "instance" ).menu.active ) {
      event.preventDefault();
    }
  }).autocomplete({
    classes: {
      "ui-autocomplete": "modal-autocomplete",
    },
    minLength: 0,
    source: function( request, response ) {
      // delegate back to autocomplete, but extract the last term
      response( $.ui.autocomplete.filter(
          labels, extractLast( request.term ) ) );
    },
    focus: function() {
      // prevent value inserted on focus
      return false;
    },
    select: function( event, ui ) {
      var terms = split( this.value );
      // remove the current input
      terms.pop();
      // add the selected item
      terms.push( ui.item.value );
      // add placeholder to get the comma-and-space at the end
      terms.push( "" );
      this.value = terms.join( ", " );
      return false;
    },
  });

  var button = $("<button class='btn btn-default' id='launch'>")
      .text("Propose")
      .click(function() {
        var labels = split($("#labels").val());
        var approvers = $("#approvers").val();
        if (labels && approvers) {
          $.ajax(rekall.utils.call({
            api: "/hunts/propose",
            data: {
              labels: labels,
              flow_ids: flow_ids,
              approvers: approvers,
            },
            error: rekall.utils.error_container,
            success: function() {
              rekall.utils.load(rekall.globals.controllers.hunts_view);
            }
          }));
        };
      });

  return rekall.templates.modal_template(result, "Run Flow as Hunt", button);
}


rekall.api = {}
rekall.api.list = function(selector) {
  $(selector).DataTable({
    ajax: rekall.utils.call({
      api: '/list',
    }),
    columns: [
      {
        title: "",
        data: "method",
        render: function(method, type, row, meta) {
          return rekall.utils.make_link(
              rekall.globals.controllers.api_call + "?" + $.param({
                method: method
              }),
              'launch-icon.png');
        }
      },
      {
        title: "Method",
        data: "method",
      },
      {
        title: "Description",
        data: "doc",
      },
      {
        title: "Args",
        data: "args",
        width: "40%",
        render: function(args, type, row, meta) {
          var result = $("<table>");
          for (var key in args) {
            if (args.hasOwnProperty(key)) {
              var row = $("<tr>");
              $("<td>").text(key).appendTo(row);
              $("<td>").text(args[key]).appendTo(row);
              result.append(row);
            }
          }

          return result.prop('outerHTML');
        }
      }
    ]
  });
}

rekall.api.mint_token = function() {
  $.ajax(rekall.utils.call({
    api: '/users/roles/list',
    success: function(roles) {
      $("#modalContainer").html(rekall.templates.mint_token(roles));
      $("#modal").modal("show");
    }
  }));
}

rekall.api.call = function(form_selector, button_selector, method) {
  $(button_selector).click(function () {
    $.ajax(rekall.utils.call({
      api: method,
      data: $(form_selector).serializeArray(),
      method: "POST",
      success: function(result) {
        $("#modalContainer").html(
            rekall.templates.modal_template(
                rekall.cell_renderers.generic_json_renderer(result),
                "API Result",
                ));
        $("#modal").modal("show");
      },
      error: rekall.utils.error,
    }));

    return false;
  });
}

rekall.artifacts = {}

rekall.artifacts.list = function(selector) {
  var dataset = {};

  $(selector).DataTable({
    ajax: rekall.utils.call({
      api: '/artifacts/list',
      error: rekall.utils.error,
    }),
    columns: [
      {
        title: "Artifact",
        data: "artifact",
        render: function(artifact, type, row, meta) {
          var text = artifact.name;
          return rekall.cell_renderers.generic_json_pp(
              dataset, text, "artifact",
              artifact, type, row, meta);
        }
      },
      {
        title: "Description",
        data: "artifact.doc"
      },
    ]});

  rekall.cell_renderers.generic_json_pp_clicks(
      dataset, "artifact", "Artifact", selector);
}

rekall.artifacts.upload = function(artifact) {
  $.ajax(rekall.utils.call({
    method: "POST",
    api: '/artifacts/add',
    data: {
      artifact: artifact
    },
    error: rekall.utils.error,
    success: function() {
      rekall.utils.load(rekall.globals.controllers.artifact_list);
    }
  }));
}

// Client controller.
rekall.clients = {}

rekall.client_lru = []
rekall.clients.add_to_client_lru = function (client_id) {
  var new_client_lru = []
  var length = rekall.client_lru.length;
  for (var i=Math.max(0, length-10); i<length; i++) {
    if (rekall.client_lru[i] != client_id) {
      new_client_lru.push(rekall.client_lru[i]);
    }
  }

  new_client_lru.push(client_id);
  rekall.client_lru = new_client_lru;

  // Rebuild the LRU list DOM.
  var dom_lru = $("#client_lru").parent().find("ul");
  dom_lru.html("");

  for (var i=0; i<rekall.client_lru.length; i++) {
    var client_id = rekall.client_lru[i];
    var inspect_link = $("<a class='link'>")
        .text(client_id)
        .attr("href", rekall.globals.controllers.inspect_list + "?" +
        $.param({client_id: client_id}));

    dom_lru.append($("<li>").append(inspect_link));
  }
}

rekall.clients.view_modal = function(client_id) {
  $.ajax(rekall.utils.call({
    api: "/client/search",
    data: {
      query: client_id
    },
    error: rekall.utils.error,
    success: function(results) {
      if (results.data.length > 0) {
        html = rekall.templates.render_client_info(results.data[0]);
      } else {
        html = "Not found";
      }

      $("#modalContainer").html(
          rekall.templates.modal_template(
              html,
              "Client " + client_id,
              ));
      $("#modal").modal("show");
    }
  }));
}

rekall.clients.render_client_info = function(client_id, selector) {
  $.ajax(rekall.utils.call({
    api: '/client/search',
    data: {
      query: client_id
    },
    success: function(client_info) {
      // There should be some results.
      if (client_info.data.length > 0) {
        $(selector).html(
            rekall.cell_renderers.generic_json_renderer(
                client_info.data[0]));
      }
    },
    error: rekall.utils.error,
  }));
}

rekall.clients.search_clients = function (query, selector) {
  var dataset_cache = {}

  $(selector).DataTable({
    ajax: rekall.utils.call({
      api: '/client/search',
      data: {
        query: query
      },
      error: rekall.utils.error,
    }),
    columns: [
      {
        title: '<input id="select_all" type="checkbox">',
        data: "client_id",
        sortable: false,
        render: function(client_id, type, row, meta) {
          var checkbox = $('<input name="client_ids" type="checkbox">');
          checkbox.attr("value", client_id);
          checkbox.attr("data_labels", row.labels.join(","));
          return checkbox.prop("outerHTML");
        }
      },
      {
        title: "Flows",
        data: "client_id",
        searchable: false,
        orderable: false,
        render: function(client_id, type, row, meta) {
          var link = $(`
<a class='client_id_link rekall-glyphicon'>
  <span class='glyphicon glyphicon glyphicon-tasks'
        aria-hidden='true'>`).attr("data_client_id", client_id);

          return link.prop('outerHTML');
        },
      },
      {
        title: "Client ID",
        data: "summary.client_id",
        searchable: false,
        orderable: false,
      },
      {
        title: "Last",
        data: "last",
        type: "unix",
      },
      {
        title: "System",
        data: "summary.system_info",
        render: function(cell_data, type, row, meta) {
          var text = (cell_data.system + " " +
              cell_data.release + " " +
              cell_data.version + " " +
              "(" + cell_data.kernel + ")");

          return $("<div>").text(text).html();
        }
      },
      {
        title: "Client Information",
        data: "summary",
        render: function(cell_data, type, row, meta) {
          var text = cell_data.system_info.fqdn;
          return rekall.cell_renderers.generic_json_pp(
              dataset_cache, text, "summary",
              cell_data, type, row, meta);
        }
      },
      {
        title: "Labels",
        data: "labels",
        render: function(labels, type, row, meta) {
          return labels.join(",");
        },
      },
    ],
  });

  rekall.cell_renderers.generic_json_pp_clicks(
      dataset_cache, "summary", "Summary", selector);

  $(selector).on("click", "a.client_id_link", function (event) {
    var client_id = $(this).attr("data_client_id");

    rekall.clients.add_to_client_lru(client_id);
    rekall.utils.load(rekall.globals.controllers.inspect_list,
                      {client_id: client_id});

    event.preventDefault();
  });

}

rekall.clients.label = function(selector) {
  var selected_client_ids = [];
  var labels = new Set();

  $(selector).find("input[name=client_ids]").each(function () {
    if (this.checked) {
      selected_client_ids.push(this.value);
      var entry_labels = $(this).attr("data_labels").split(",");
      $(entry_labels).each(function () {
        labels.add(this);
      });
    }
  });

  if (selected_client_ids.length == 0) {
    return;
  }

  var button = $('<button class="btn btn-default">Label</button>');
  button.click(function () {
    var labels = [];
    $("input[name=labels]").each(function () {
      labels.push($(this).val());
    });

    $.ajax(rekall.utils.call({
      api: "/client/label",
      data: {
        client_ids: selected_client_ids,
        labels: labels,
      },
      error: rekall.utils.error_container,
      success: function() {
        rekall.utils.load(window.location.href);
      }
    }));
  });

  $("#modalContainer").html(
      rekall.templates.modal_template(
          rekall.templates.label_clients(
              selected_client_ids, Array.from(labels)),
          "Label clients", button
          ));
  $("#modal").modal("show");

  return false;
}


// Pops the client info in a modal box.
rekall.clients.show_info = function(client_id) {
  $.ajax(rekall.utils.call({
    api: '/client/search',
    data: {
      query: client_id
    },
    success: function(data) {
      var summary = data.data[0];
      if (summary) {
        var button = $("<button class='btn btn-default'>")
            .click(function() {
              rekall.utils.load(rekall.globals.inspect_list,
                                {client_id: client_id});
              return false;
            });

        $("#modalContainer").html(
            rekall.templates.modal_template(
                rekall.cell_renderers.generic_json_renderer(summary),
                "Client: " + client_id,
                ));
        $("#modal").modal("show");
      }
    },
    error: rekall.utils.error,
  }));
}


rekall.flows = {}
rekall.flows.list_plugins = function(launch_url, client_id, selector) {
  $(selector).DataTable( {
    ajax: rekall.utils.call({
      api: "/plugin/list",
    }),
    columns: [
      {
        data: "plugin",
        searchable: false,
        render: function (plugin, type, full, meta) {
          var link = $(`<a class='link rekall-glyphicon'>
  <span class='glyphicon glyphicon-pencil'
        aria-hidden='true'>`).attr("href", launch_url + "?" + $.param({
          plugin: plugin,
          client_id: client_id
        }));
          return link.prop("outerHTML");
        },
      },
      {
        title: "Plugin",
        data: "plugin",
        render: function (plugin, type, full, meta) {
          var result = $('<div class="collection_cell_rich plugin">');
          result.text(plugin);
          return result.prop('outerHTML');
        },
      },
      {
        title: "Name",
        data: "name",
      },
    ]
  });

  // Place a single click handler on the table and use sub-selector to only
  // activate when the click happened on a rich cell.
  $(selector).on("click", ".collection_cell_rich.plugin", function (){
    var plugin = $(this).text();

    $.ajax(rekall.utils.call({
      api: "/plugin/get",
      data: {plugin: plugin},
      success: function(data) {
        $("#modalContainer").html(
            rekall.templates.modal_template(
                rekall.cell_renderers.generic_json_renderer(data),
                "Plugin " + plugin,
                ));
        $("#modal").modal("show");
      }
    }));
  });
}

rekall.flows.list_flows_for_client = function(client_id, selector) {
  var flow_cache = {};
  var status_cache = {};

  $(selector).DataTable({
    ajax: rekall.utils.call({
      api: "/flows/list",
      data: {
        client_id: client_id
      },
      error: function(jqXHR) {
        // Permission denied means the user has no access to the client. Launch
        // the approval workflow.
        if (jqXHR.status == 403) {
          rekall.utils.load(rekall.globals.controllers.request_approval,
                            {client_id: client_id});
        } else {
          rekall.utils.error(jqXHR);
        };
      },
    }),
    order: [[ 1, 'desc' ]],
    columns: [
      {
        title: '<input id="select_all" type="checkbox">',
        data: "flow",
        sortable: false,
        render: function(flow, type, row, meta) {
          var checkbox = $('<input name="flow_ids" type="checkbox">');
          checkbox.attr("value", flow.flow_id);
          return checkbox.prop("outerHTML");
        }
      },
      {
        title: 'View',
        data: "flow",
        sortable: false,
        render: function(flow, type, row, meta) {
          return rekall.utils.make_link(
              rekall.globals.controllers.describe_flow + "?" + $.param({
                client_id: client_id,
                flow_id: flow.flow_id
              }), 'glyphicon-search');
        }
      },
      {
        title: "Time",
        data: "flow.created_time",
        render: function(timestamp, type, row, meta) {
          return rekall.cell_renderers.unixtimestamp(timestamp, type);
        }
      },
      {
        title: "Flow",
        data: "flow",
        render: function(flow, type, row, meta) {
          var text = flow.name;
          if (!text) {
            text = rekall.cell_renderers.flow_summary_renderer(flow);
          }
          return rekall.cell_renderers.generic_json_pp(
              flow_cache, text, "flow",
              flow, type, row, meta);
        }
      },
      {
        title: "Creator",
        data: "creator",
      },
      {
        title: "Status",
        data: "status",
        render: function(status, type, row, meta) {
          var text = status.status;
          return rekall.cell_renderers.generic_json_pp(
              status_cache, text, "status",
              status, type, row, meta);
        }
      },
      {
        title: "Total Uploads",
        data: "status",
        searchable: false,
        render: function(status, type, row, meta) {
          if (status && status.total_uploaded_files) {
            return status.total_uploaded_files;
          }
          return "";
        }
      },
    ],
  });

  rekall.cell_renderers.generic_json_pp_clicks(
      flow_cache, "flow", "Flow Information", selector);

  rekall.cell_renderers.generic_json_pp_clicks(
      status_cache, "status", "Flow Status", selector,
      rekall.cell_renderers.status_detailed_renderer);

  $("#select_all").click(function() {
    var state = this.checked;
    $("input[name=flow_ids]").each(function () {this.checked = state});
    return false;
  });

  $("#save").click(function () {
    rekall.flows.save_flows("#flows", client_id);
    return false;
  });

  $("#load").click(function () {
    $("#modalContainer").html(
        rekall.templates.modal_template(
            rekall.templates.load_precanned_flow_template(client_id),
            "Load a Pre-Canned Flow"));
    $("#modal").modal("show");
    return false;
  });
};

// View for views.flows.describe
rekall.flows.describe_flow = function(client_id, flow_id) {
  $.ajax(rekall.utils.call({
    api: "/flows/describe",
    data: {
      client_id: client_id,
      flow_id: flow_id
    },
    error: rekall.utils.error,
    success: function(description) {
      $("#desc .panel-body").html(
          rekall.cell_renderers.generic_json_renderer(description.flow));

      $("#collections .panel-body").html(
          rekall.cell_renderers.collection_ids_renderer(
              description.collection_ids));

      // If no files are available, disable the tab.
      if (description.file_infos.length == 0) {
        $("#files-tab").addClass("disabled");
        $("#files-tab").find("a").removeAttr("role").removeAttr("href");

      } else {
        $("#files .panel-body").find("table").DataTable({
          data: description.file_infos,
          columns: [
            {
              title: "View",
              data: "upload_id",
              sortable: false,
              searchable: false,
              render: function(upload_id, type, row, meta) {
                return rekall.utils.make_link(
                    rekall.globals.controllers.hex_view + "?" + $.param({
                      upload_id: upload_id,
                    }), "glyphicon-file");
              }
            },
            {
              title: "Filename",
              data: "file_information.filename",
            },
            {
              title: "Size",
              data:"file_information.st_size",
            }
          ]});
      };

      $(".nav-tabs").on("click", "a[role=tab]", function() {
        $(this).tab('show');
        return false;
      });


      $("#desc-tab").find("a").tab('show');
    }
  }));
}

rekall.flows.save_flows = function(selector, client_id) {
  var selected_flow_ids = [];
  $(selector).find("input[name=flow_ids]").each(function () {
    if (this.checked) selected_flow_ids.push(this.value);
  });

  if (selected_flow_ids.length == 0) {
    return;
  }

  $.ajax(rekall.utils.call({
    api: "/flows/make_canned",
    data: {
      client_id: client_id,
      flow_ids: selected_flow_ids,
    },
    error: rekall.utils.error,
    success: function(canned_flow) {
      var form = rekall.templates.save_flows(canned_flow);
      var submit = $(
          "<button type='button' class='btn btn-default'>Save</button>")
              .click(function () {
                canned_flow.name = form.find("#name").val();
                canned_flow.description = form.find("#description").val();
                canned_flow.category = form.find("#category").val();

                $.ajax(rekall.utils.call({
                  method: "POST",
                  api: "/flows/save_canned",
                  data: {
                    canned_flow: JSON.stringify(canned_flow),
                  },
                  success: function() {
                    $("#modal").modal("hide");
                  },
                  error: rekall.utils.error_container
                }));

                return false;
              });

      $("#modalContainer").html(
          rekall.templates.modal_template(form, "Save Flow", submit));
      $("#modal").modal("show");
    },
  }));
}

rekall.flows.list_canned_flows = function(selector) {
  $(selector).DataTable({
    ajax: rekall.utils.call({
      api: "/flows/list_canned",
      error: rekall.utils.error,
    }),
    columns: [
      {
        title: '<input id="select_all" type="checkbox">',
        data: "name",
        sortable: false,
        render: function(name, type, row, meta) {
          var checkbox = $('<input name="names" type="checkbox">');
          checkbox.attr("value", name);
          return checkbox.prop("outerHTML");
        }
      },
      {
        title: "Category",
        data: "category"
      },
      {
        title: "Name",
        data: "name"
      },
      {
        title: "Description",
        data: "description",
      },
    ]
  });

  $("#select_all").click(function() {
    var state = this.checked;
    $("input[name=names]").each(function () {this.checked = state});

    return false;
  });

  rekall.utils.watch_checkboxes_to_disabled_button(selector, "#delete");

  $("#delete").click(function() {
    rekall.flows.delete_canned_flows(selector);

    return false;
  });
}

rekall.flows.delete_canned_flows = function(selector) {
  var selected_names = [];
  $(selector).find("input[name=names]").each(function () {
    if (this.checked) selected_names.push(this.value);
  });

  $.ajax(rekall.utils.call({
    api: "/flows/delete_canned",
    data: {
      names: selected_names,
    },
    error: rekall.utils.error,
    success: function() {
      rekall.utils.load(window.location.href);
    }
  }));
}

rekall.flows.delete_canned_flows = function(selector) {
  var selected_names = [];
  $(selector).find("input[name=names]").each(function () {
    if (this.checked) selected_names.push(this.value);
  });

  $.ajax(rekall.utils.call({
    api: "/flows/delete_canned",
    data: {
      names: selected_names,
    },
    error: rekall.utils.error,
    success: function() {
      rekall.utils.load(window.location.href);
    }
  }));
}

rekall.flows.download = function (client_id, selector) {
  var selected_flow_ids = [];
  $(selector).find("input[name=flow_ids]").each(function () {
    if (this.checked) selected_flow_ids.push(this.value);
  });

  if (selected_flow_ids.length == 0) {
    return;
  }

  $.ajax(rekall.utils.call({
    api: "/flows/download",
    data: {
      client_id: client_id,
      flow_ids: selected_flow_ids
    },
    success: function(metadata) {
      rekall.utils.editor_popup(
          rekall.templates.flow_download_script(metadata.data),
          "sh");
    },
    error: rekall.utils.error,
  }));

  return false;
}

rekall.hunts = {}
rekall.hunts.create_from_flows = function(client_id, selector) {
  var selected_flow_ids = [];
  $(selector).find("input[name=flow_ids]").each(function () {
    if (this.checked) selected_flow_ids.push(this.value);
  });

  if (selected_flow_ids.length == 0) {
    return;
  }

  $.ajax(rekall.utils.call({
    api: "/labels/list",
    error: rekall.utils.error,
    success: function(labels) {
      $("#modalContainer").html(
          rekall.templates.create_hunt_from_flows(labels.data, selected_flow_ids));
      $("#modal").modal("show");
    }
  }));
  return false;
}

rekall.hunts.view = function(selector) {
  var flow_cache = {};
  var status_cache = {};

  $(selector).DataTable({
    ajax: rekall.utils.call({
      api: "/hunts/list",
    }),
    order: [[ 2, 'desc' ]],
    columns: [
      {
        title: '<input id="select_all" type="checkbox">',
        data: "flow",
        sortable: false,
        render: function(flow, type, row, meta) {
          var checkbox = $('<input name="flow_ids" type="checkbox">');
          checkbox.attr("value", flow.flow_id);
          return checkbox.prop("outerHTML");
        }
      },
      {
        title: "",
        data: "flow",
        render: function(flow, type, row, meta) {
          return rekall.utils.make_link(
              rekall.globals.controllers.hunts_list + "?" + $.param({
                hunt_id: flow.flow_id
              }),
              'launch-icon.png');
        }
      },
      {
        title: "Created",
        data: "timestamp",
        render: function(timestamp, type, row, meta) {
          return rekall.cell_renderers.unixtimestamp(timestamp, type)
        }
      },
      {
        title: "Hunt Id",
        data: "flow",
        render: function(flow, type, row, meta) {
          var text = flow.name;
          if (!text) {
            text = rekall.cell_renderers.flow_summary_renderer(flow);
          }
          return rekall.cell_renderers.generic_json_pp(
              flow_cache, text, "flow",
              flow, type, row, meta);
        }
      },
      {
        title: "Labels",
        data: "labels",
        render: function(labels, type, row, meta) {
          return labels.join(",");
        },
      },
      {
        title: "State",
        data: "state",
      },
      {
        title: "Status",
        data: "status",
        render: function(status, type, row, meta) {
          var text = "Total " + (status.total_clients || 0) +
              " (Errors: " + (status.total_errors || 0) + " )";
          return rekall.cell_renderers.generic_json_pp(
              status_cache, text, "status",
              status, type, row, meta);
        }
      },
    ]
  });

  rekall.cell_renderers.generic_json_pp_clicks(
      flow_cache, "flow", "Flow Information", selector);

  rekall.cell_renderers.generic_json_pp_clicks(
      status_cache, "status", "Flow Status", selector,
      rekall.cell_renderers.status_detailed_renderer);
}


rekall.hunts.results = function(selector, hunt_id) {
  var status_cache = {};

  $(selector).DataTable({
    ajax: rekall.utils.call({
      api: "/hunts/results",
      data: {
        hunt_id: hunt_id
      },
    }),
    columns: [
      {
        title: "Client",
        data: "client_id",
      },
      {
        title: "Status",
        data: "status",
        render: function(status, type, row, meta) {
          var text = status.status;
          return rekall.cell_renderers.generic_json_pp(
              status_cache, text, "status",
              status, type, row, meta);
        },
      },
      {
        title: "Collections",
        data: "collection_ids",
        render: rekall.cell_renderers.collection_ids_renderer,
      },
    ]
  });

  rekall.cell_renderers.generic_json_pp_clicks(
      status_cache, "status", "Flow Status", selector,
      rekall.cell_renderers.status_detailed_renderer);
}



rekall.uploads = {}
rekall.uploads.list_uploads_for_flow = function(flow_id, selector) {
  var file_info_cache = {};

  $(selector).DataTable({
    ajax: rekall.utils.call({
      api: "/uploads/list",
      data: {
        flow_id: flow_id
      }
    }),
    columns: [
      {
        title: "filename",
        data: "file_information",
        render: function(file_info, type, row, meta) {
          var text = file_info.filename;
          return rekall.cell_renderers.generic_json_pp(
              file_info_cache, text, "finfo",
              file_info, type, row, meta);
        }
      },
      {
        title: "Download",
        data: "upload_id",
        render: function(upload_id, type, row, meta) {
          var filename = row.file_information.filename;
          if (!filename) {
            filename = "download_" + upload_id;
          }
          return rekall.utils.make_link(
              rekall.globals.controllers.download + "?" + $.param({
                upload_id: upload_id,
                filename: filename}),
              'launch-icon.png');
        }
      },
      {
        title: "HexView",
        data: "upload_id",
        render: function(upload_id, type, row, meta) {
          return rekall.utils.make_link(
              rekall.globals.controllers.hex_view + "?" + $.param({
                upload_id: upload_id}), 'launch-icon.png');
        }
      },
    ]
  });

  rekall.cell_renderers.generic_json_pp_clicks(
      file_info_cache, "finfo", "File Information", selector);
}

rekall.uploads.build_pagination = function(offset, length, page_size) {
  var number_of_pages = 10;
  var max_pages = Math.min(number_of_pages, parseInt(length / page_size));
  var current_page = parseInt(offset / page_size);

  var result = $('<ul class="pagination-sm pagination">');
  var first = $('<li class="page-item first">');
  if (current_page == 0) first.addClass("disabled");
  first.append('<a href="#" class="page-link" data-page="0">First</a>');

  var prev = $('<li class="page-item prev">');
  if (current_page == 0) prev.addClass("disabled");
  prev.append($('<a href="#" class="page-link">Prev</a>')
      .attr("data-page", Math.max(0, current_page-1)));

  var next = $('<li class="page-item next">');
  if (current_page == max_pages) next.addClass("disabled");
  next.append($('<a href="#" class="page-link">Next</a>')
      .attr("data-page", Math.min(max_pages, current_page+1)));

  var last = $('<li class="page-item last">');
  if (current_page == max_pages) last.addClass("disabled");
  last.append($('<a href="#" class="page-link">Last</a>')
      .attr("data-page", max_pages));

  result.append(first);
  result.append(prev);

  var first_page = Math.max(0, current_page - number_of_pages / 2);
  var last_page = Math.min(first_page + number_of_pages, max_pages);

  for (var i=first_page; i<=last_page; i++) {
    var link = $("<a href='#' class='page-link'>").attr('data-page', i).text(i);
    var button = $('<li class="page-item">').append(link);
    if (current_page == i) button.addClass("active");
    result.append(button);
  }

  result.append(next);
  result.append(last);

  return result;
}


rekall.uploads.hex_view = function(upload_id, offset, selector) {
  var width = 32;
  var height = 200;
  var page_size = width * height;

  $.ajax(rekall.utils.call({
    api: "/uploads/download",
    data: {
      upload_id: upload_id,
    },
    type: "POST",
    responseType: 'arraybuffer',
    dataType: "binary",
    headers: {
      "Range": ("bytes=" + parseInt(offset) + "-" + (offset + page_size)),
    },
    success: function(result, textStatus, request){
      var content_range = request.getResponseHeader('Content-Range');
      var match = new RegExp(" ([0-9]+)-([0-9]+)/([0-9]+)$").exec(
          content_range || "");
      if (match) {
        var start = parseInt(match[1]);
        var end = parseInt(match[2]);
        var total_length = parseInt(match[3]);
      }
      var bytes = new Uint8Array(result);
      var text = "";
      var hex = "";
      for (var i=0; i<bytes.length; i++) {
        if (i > 0 && (i % width) == 0) {
          hex += "\n";
          text += "\n";
        }

        var chr = bytes[i];
        var hex_string = chr.toString(16);
        if (hex_string.length == 1) {
          hex_string = "0" + hex_string;
        }
        hex += hex_string + " ";
        if (chr < 32 || chr > 127) {
          text += ".";
        } else {
          text += String.fromCharCode(chr);
        };
      }

      var result = $("<div class='row'>");
      result.append($("<pre class='col-xs-4 col-md-7'></pre>").text(hex));
      result.append($("<pre class='col-xs-4 col-md-4'></pre>").text(text));

      $(selector).html(result);
      if(match) {
        $("#description").text(
            "Showing content " + start + " - " + end + " / " + total_length);

        var paginator = rekall.uploads.build_pagination(
            start, total_length, page_size);
        paginator.on('click', 'a.page-link', function () {
          var page = $(this).attr('data-page');
          if (page != null) {
            rekall.uploads.hex_view(upload_id, page * page_size, '#plugins');
          }
          return false;
        });
        $("#pagination").html(paginator);

      }
    }
  }));
}

// Cell renderers for DataTables
rekall.cell_renderers = {}
rekall.cell_renderers.generic_json_pp = function(
    dataset_cache,
    text,
    cls,
    cell_data,
    type, row, meta) {
  var result = $('<div class="collection_cell_rich">');
  result.addClass(cls);
  var key = meta.row.toString() + "," + meta.col.toString();
  dataset_cache[key] = cell_data;
  result.attr('data-key', key);
  result.text(text);

  return result.prop('outerHTML');
}

rekall.cell_renderers.generic_json_pp_clicks = function(
    dataset_cache,
    cls,
    title,
    selector,
    detailed_renderer) {

  if (detailed_renderer == null) {
    detailed_renderer = rekall.cell_renderers.generic_json_renderer;
  }

  // Place a single click handler on the table and use sub-selector to only
  // activate when the click happened on a rich cell.
  $(selector).on("click", ".collection_cell_rich" + "." + cls, function (){
    var key = $(this).data('key');
    var cell_data = dataset_cache[key];

    $("#modalContainer").html(
        rekall.templates.modal_template(
            detailed_renderer(cell_data),
            title,
            ));

    $("#modal").modal("show");
  });
}


rekall.cell_renderers.unixtimestamp = function(timestamp, type) {
  // Sort by timestamp not the string representation.
  if (type == "sort") {
    return timestamp;
  }
  return new Date(timestamp * 1000).toUTCString();
}

rekall.cell_renderers.generic_ajax_clicks = function(
    dataset_cache, // The cache object used to keep table references.
    cls,           // The dom class to apply to.
    title,         // A title appearing in the modal box.
    selector,      // The selector to attach the click event.
    ajax_cb,       // A callback used to formulate the ajax call. This should be
                   // of the form function (cell_data) -> {url: ...., data:
                   // {x=y}}.
    detailed_renderer, // Additional renderer to be attached to the result of
                       // the ajax call.
    ) {
  if (detailed_renderer == null) {
    detailed_renderer = rekall.cell_renderers.generic_json_renderer;
  }

  $(selector).on("click", ".collection_cell_rich", function (){
    var key = $(this).data('key');
    var data_cell = dataset_cache[key];

    var ajax = ajax_cb(data_cell);

    ajax.success = function(data) {
      $("#modalContainer").html(
          rekall.templates.modal_template(
              detailed_renderer(data),
              title,
              ));
      $("#modal").modal("show");
    };

    $.ajax(ajax);
  });


}

rekall.cell_renderers.generic_json_renderer = function(obj) {
  return $("<pre>").RekallJsonViewer(obj, {collapsed: false});
}

rekall.cell_renderers.status_detailed_renderer = function(status) {
  var json = $("<pre>").RekallJsonViewer(status, {collapsed: false});

  if (status.status == "Error") {
    var result = $(`<span><h3>Backtrace</h3><pre></pre>
      <a class="btn btn-primary" role="button"
         data-toggle="collapse"
         href="#jsonDetails" aria-expanded="false"
         aria-controls="jsonDetails">
        More details
        </a>
      <div class="collapse" id="jsonDetails"></div>`);
    result.find("pre").text(status.backtrace);
    result.find("#jsonDetails").append(json);
    return result;
  }

  return json;
}

// A renderer to show some important information about the flow.
rekall.cell_renderers.flow_summary_renderer = function(flow) {
  var result = "";

  for (var i=0; i<flow.actions.length; i++) {
    var action = flow.actions[i];

    if (action.__type__ == "PluginAction") {
      result += "PluginAction(" + action.plugin + ") ";
    }
  }

  return rekall.utils.escape_text(result);
}

rekall.cell_renderers.collection_ids_renderer = function(
    collection_ids, type, row, meta) {
  var result = "";
  if (!collection_ids) {
    return result;
  }

  for (var i=0; i<collection_ids.length; i++) {
    result += rekall.utils.make_link(
        rekall.globals.controllers.collection_view + "?" + $.param({
          collection_id: collection_ids[i],
        }),
        "glyphicon-book");
  }

  return result;
}

// Render the message in the table. Note that the message can not be an
// arbitrary format. It is a reference into a named template which is used to
// expand the args. This allows us to include HTML safely without worrying about
// XSS from the sender of the message.
rekall.cell_renderers.notification_message = function(
    message_id, type, row, meta) {
  if (message_id == "APPROVAL_REQUEST") {
    var result = $("<div>Please <a class='link'>approve</a> client <b></b>.</div>");
    client_id = rekall.utils.get(row.args, "client_id", "");
    user = rekall.utils.get(row.args, "user", "");
    role = rekall.utils.get(row.args, "role", "");
    result.find("b").text(client_id);
    result.find("a").attr(
        "href", rekall.globals.controllers.approve_request + "?" + $.param({
          client_id: client_id,
          user: user,
          role: role
        }));

    return result.html();
  }

  if (message_id == "HUNT_APPROVAL_REQUEST") {
    var result = $("<div>Please <a class='link'>approve</a> hunt <b></b>.</div>");
    hunt_id = rekall.utils.get(row.args, "hunt_id", "");
    user = rekall.utils.get(row.args, "user", "");
    result.find("b").text(hunt_id);
    result.find("a").attr(
        "href",
        rekall.globals.controllers.approve_hunt_request + "?" + $.param({
          hunt_id: hunt_id,
          user: user,
        }));
    return result.html();
  }

  // Message id not recognized so we just include it as text.
  return rekall.utils.safe_html(message_id);
}

// User management.
rekall.users = {}

rekall.users.list_users = function (selector) {
  var user_cache = {};
  var roles_cache = {};

  $(selector).DataTable({
    ajax: rekall.utils.call({
      api: "/users/list",
      error: rekall.utils.error,
    }),
    columns: [
      {
        title: "",
        data: "user",
        render: function(user, type, row, meta) {
          var checkbox = $('<input type="checkbox">');
          checkbox.attr("data-user", row.user);
          checkbox.attr("data-resource", row.resource);
          checkbox.attr("data-role", row.role);
          return checkbox.prop("outerHTML");
        }
      },
      {
        title: "User",
        data: "user",
      },
      {
        title: "Resource",
        data: "resource",
      },
      {
        title: "Roles",
        data: "role",
        render:  function(role, type, row, meta) {
          return rekall.cell_renderers.generic_json_pp(
              roles_cache, role, "role",
              role, type, row, meta);
        },
      },
      {
        title: "Conditions",
        data: "conditions",
        defaultContent: "<i>Not set</i>"
      }
    ]
  });

  rekall.cell_renderers.generic_ajax_clicks(
      roles_cache,
      "role",
      "Role Description",
      selector,
      function (role) {
        return rekall.utils.call({
          api: "/users/roles/get",
          data: {role: role}
        })
      });
}


rekall.users.remove_users = function(selector) {
  var counter = 0;

  $(selector).find("input[type=checkbox]").each(function () {
    var self = $(this);
    if (this.checked) {
      counter++;
      $.ajax(rekall.utils.call({
        api: "/users/delete",
        data: {
          user: self.attr("data-user"),
          resource: self.attr("data-resource"),
          role: self.attr("data-role"),
        },
        success: function() {
          counter--;
          if (counter == 0) {
            rekall.utils.load(window.location.href);
          };
        },
      }));
    }
  });
}

rekall.users.show_notifications = function() {
  var button = $(
      `<button type="button" class="btn btn-default"
         data-dismiss="modal" id="clear">Clear</button>
      `).on("click", function() {
        $.ajax(rekall.utils.call({
          api: "/users/notifications/clear",
          error: function() {}, // Ignore errors.
          success: function() {},
        }));
      });

  var table = rekall.templates.modal_template(
      '<table class="display" cellspacing="0" width="80%"></table>',
      "Notifications", button);
  table.find("table").DataTable({
    ajax: rekall.utils.call({
      api: "/users/notifications/read",
    }),
    order: [[ 1, 'desc' ]],
    columns: [
      {
        title: "From",
        data: "from_user"
      },
      {
        title: "Timestamp",
        data: "timestamp",
      },
      {
        title: "Message",
        data: "message_id",
        render: rekall.cell_renderers.notification_message,
      }
    ]
  });

  $("#modalContainer").html(table);
  $("#modal").modal("show");
}

rekall.collections = {}
rekall.collections.build_table_from_collection = function (
    client_id, collection_id, selector) {
  $.ajax(rekall.utils.call({
    xhr: function() {
      var xhr = new window.XMLHttpRequest();
      xhr.addEventListener("progress", function(evt){
        // Adjust the progress bar as we load the collection file.
        if (evt.lengthComputable) {
          var percentComplete = parseInt(evt.loaded / evt.total * 100) + "%";
          $("#progressbar .progress-bar").css('width', percentComplete).text(
              percentComplete);
        }
      }, false);

      return xhr;
    },
    api: "/collections/get",
    data: {
      client_id: client_id,
      collection_id: collection_id,
      part: 0
    },
    error: rekall.utils.error,
    success: function (data) {
      var nav_tabs = $('<ul class="nav nav-tabs" role="tablist">');
      var tab_content = $("<div class='tab-content'>");

      rekall.utils.get(data, "tables", []).forEach(function (table) {
        var table_dom = $('<table class="display" cellspacing="0">')
            .attr("id", table.name);

        var id = "pane_" + table.name;

        nav_tabs.append(
            $('<li role="presentation">').append(
                $("<a role='tab'>")
                    .attr("href", "#" + id)
                    .text(table.name)
                ));

        tab_content.append(
            $("<div class='tab-pane' role='tabpanel'>")
                .attr("id", id).append(
                    $("<div class='panel panel-default'>").append(
                        $("<div class='panel-body'>")
                            .append(table_dom))));

        var columns = [];
        var dataset_cache = {};

        rekall.utils.get(table, "columns", []).forEach(function (column) {
          var name = column.name;
          var cell_type = column.type;

          columns.push({title: name,
                        render: function(cell_data, type, row, meta) {
                          if (cell_data == null) {
                            return "";
                          }

                          // We would like to use templates but this is a really
                          // hot function and templates are just too slow.
                          if (cell_type == "any") {
                            if (type != "display" ||
                                cell_data.text == cell_data.data) {
                              return cell_data.text;
                            };

                            return rekall.cell_renderers.generic_json_pp(
                                dataset_cache, cell_data.text, "collection",
                                cell_data, type, row, meta);
                          }

                          if (cell_type == "epoch") {
                            return rekall.cell_renderers.unixtimestamp(
                                cell_data, type);
                          }

                          return $("<div>").text(cell_data).html();
                        }});
        });

        var dataset = data.table_data[table.name];
        var data_table = $(table_dom).DataTable({
          //dom: '<"top"ifp<"clear">>rt<"bottom"lp<"clear">>',
          dom: 'Bfrtlip',
          buttons: [
            'copy', 'csv', 'excel', 'pdf', 'print'
          ],

          data: dataset,
          columns: columns,
          deferRender: false,
          bProcessing: true,
          bSortClasses: false,
        });

        rekall.cell_renderers.generic_json_pp_clicks(
            dataset_cache, "collection", "Exported Data", table_dom);
      });

      $(selector)
          .append(nav_tabs)
          .append(tab_content);

      $(selector + ' a').click(function (e) {
        $(this).tab('show')

        return false;
      }).first().click();

      $("#progressbar").hide();
    }
  }));
}

rekall.collections.describe_collection = function(
    client_id, collection_id, callback) {
  $.ajax(rekall.utils.call({
    api: '/collections/metadata',
    data: {
      collection_id: collection_id,
      client_id: client_id
    },
    success: function(metadata) {
      callback(rekall.cell_renderers.flow_summary_renderer(metadata.flow));
    }
  }));
}


// Hexviewer developed using information from:
// http://www.henryalgus.com/reading-binary-files-using-jquery-ajax/

// use this transport for "binary" data type
$.ajaxTransport("+binary", function(options, originalOptions, jqXHR){
  // check for conditions and support for blob / arraybuffer response type
  if (window.FormData &&
      ((options.dataType && (options.dataType == 'binary')) ||
      (options.data &&
      ((window.ArrayBuffer && options.data instanceof ArrayBuffer) ||
      (window.Blob && options.data instanceof Blob)))))
  {
    return {
      // create new XMLHttpRequest
      send: function(headers, callback){
        // setup all variables
        var xhr = new XMLHttpRequest(),
        url = options.url,
        type = options.type,
        async = options.async || true,
        // blob or arraybuffer. Default is blob
        dataType = options.responseType || "blob",
        data = options.data || null,
        username = options.username || null,
        password = options.password || null;

        xhr.addEventListener('load', function(){
          var data = {};
          data[options.dataType] = xhr.response;
          // make callback and send data
          callback(xhr.status, xhr.statusText, data, xhr.getAllResponseHeaders());
        });

        xhr.open(type, url, async, username, password);

        // setup custom headers
        for (var i in headers ) {
          xhr.setRequestHeader(i, headers[i] );
        }

        xhr.responseType = dataType;
        xhr.send(data);
      },
      abort: function(){
        jqXHR.abort();
      }
    };
  }
});

window.onpopstate = function(event) {
  if (event.state) {
    console.log(event.currentTarget.location.href);
    var data = event.state.data;
    var method = event.state.method || "GET";

    // Deliberately do not replay POST data.
    if (method == "POST") {
      data = {},
      method = "GET"
    }
    $(".loading").toggleClass("disabled", false);
    $.ajax({
      url: event.state.url,
      method: method,
      data: data,
      headers: {
        "x-rekall-bare-layout": 1,
      },
      success: function(data) {
        $("#main").html(data);
        $(".loading").toggleClass("disabled", true);
      }
    });
    event.preventDefault();
  }
};


/**
 * jQuery json-viewer based on original code by
 * @author: Alexandre Bodelot <alexandre.bodelot@gmail.com>
 * https://github.com/abodelot/jquery.json-viewer
 */
(function($) {

  /**
   * Check if arg is either an array with at least 1 element, or a dict with at least 1 key
   * @return boolean
   */
  function isCollapsable(arg) {
    return arg instanceof Object && Object.keys(arg).length > 0;
  }

  /**
   * Check if a string represents a valid url
   * @return boolean
   */
  function isUrl(string) {
     var regexp = /^(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?/;
     return regexp.test(string);
  }

  function formatTimeStamp(value) {
    if (value > 1400000000 && value < 2000000000) {
      var d = new Date(value * 1000);
      var result = document.createElement("span");
      result.setAttribute("class", "json-date");
      result.innerText = "  " + d.toISOString();

      return result;
    }
  }

  function filterKey(key) {
    if (key == "__type__") {
      return true;
    }
    return false;
  }

  // We use direct DOM manipulation because it is much faster than jquery and
  // this might encode a very large json object.
  function json2html(json, depth) {
    var result = document.createElement('span');
    var child;

    result.setAttribute("class", "control collapsed");
    if (typeof json === 'string') {
      if (isUrl(json)) {
        child = document.createElement("a");
        child.setAttribute("class", "json-string");
        child.setAttribute("href", "json");
        child.innerText = json;
      } else {
        child = document.createElement("span");
        child.setAttribute("class", "json-string");
        child.innerText = json;
      }
      result.appendChild(child);

    } else if (typeof json === 'number') {
      child = document.createElement('span');
      child.setAttribute("class", "json-string");
      child.innerText = json;
      result.appendChild(child);

      var timestamp = formatTimeStamp(json);
      if (timestamp) {
        result.appendChild(timestamp);
      }
    } else if (typeof json === 'boolean') {
      child = document.createElement('span');
      child.setAttribute("class", "json-literal");
      child.innerText = json;

      result.appendChild(child);

    } else if (json === null) {
      child = document.createElement('span');
      child.setAttribute("class", "json-null");
      child.innerText = "null";

      result.appendChild(child);

    } else if (json instanceof Array) {
      result.appendChild(document.createTextNode("["));

      if (json.length > 0) {
        var ol = document.createElement("ol");
        ol.setAttribute("class", "json-array");
        for (var i = 0; i < json.length; ++i) {
          var li = document.createElement("li");

          /* Add toggle button if item is collapsable */
          if (isCollapsable(json[i])) {
            var a = document.createElement("a")
            a.setAttribute("class", "json-toggle collapsed");
            li.appendChild(a);
          }
          li.appendChild(json2html(json[i], depth+1));
          /* Add comma if item is not last */
          if (i < json.length - 1) {
            li.appendChild(document.createTextNode(','));
          }
          ol.appendChild(li);
        }
        result.appendChild(ol);

        var placeholder = json.length + (json.length > 1 ? ' items' : ' item');
        var a = document.createElement("a");
        a.setAttribute("class", "json-placeholder");
        a.innerText = placeholder;
        result.appendChild(a);
      }
      result.appendChild(document.createTextNode("]"));

    } else if (typeof json === 'object') {
      result.appendChild(document.createTextNode("{"));
      var keys = [];
      for (var key in json) {
        if (json.hasOwnProperty(key) && !filterKey(key)) {
          keys.push(key);
        }
      }
      if (keys.length > 0) {
        var ul = document.createElement("ul");
        ul.setAttribute("class", "json-dict");

        for (var i=0; i < keys.length; i++) {
          var key = keys[i];
          var li = document.createElement("li");
          /* Add toggle button if item is collapsable */
          if (isCollapsable(json[key])) {
            var a = document.createElement("a");
            a.setAttribute("class", "json-toggle collapsed");
            a.innerText = key;
            li.appendChild(a);
          }
          else {
            li.innerText = key;
          }
          li.appendChild(document.createTextNode(": "));
          li.appendChild(json2html(json[key], depth+1));
          ul.appendChild(li);
        }
        result.appendChild(ul);

        var placeholder = keys.length + (keys.length > 1 ? ' items' : ' item');
        var a = document.createElement("a");
        a.setAttribute("class", "json-placeholder");
        a.innerText = placeholder;
        result.appendChild(a);
      }
      result.appendChild(document.createTextNode("}"));
    }
    return result;
  };

  /**
   * jQuery plugin method
   * @param json: a javascript object
   */
  $.fn.RekallJsonViewer = function(json) {

    /* jQuery chaining */
    return this.each(function() {
      /* Transform to HTML */
      var html = json2html(json, 0);
      /* Insert HTML in target DOM element */
      $(this).append(html);
      if (isCollapsable(json)) {
        $(this).prepend('<a href="#" class="json-toggle root">');
      }

      /* Bind click on toggle buttons */
      $(this).off('click');
      var toggler = function(element) {
        $(element).toggleClass("collapsed");
        $(element).siblings("span.control").toggleClass("exposed");
        $(element).siblings("span.control").toggleClass("collapsed");
      };

      $(this).on('click', 'a.json-toggle', function() {
        toggler(this);
        return false;
      });

      /* Simulate click on toggle button when placeholder is clicked */
      $(this).on('click', 'a.json-placeholder', function() {
        $(this).parent().siblings('a.json-toggle').click();
        return false;
      });

      toggler($(this).find("a.root"));
    });
  };
})(jQuery);

// Setup code- parse the URL into the page state.
$(function () {
  // Push the current URL into the window history to allow back button to work.
  var url = window.location.href;
  if( !window.history.state || window.history.state.url != url) {
    window.history.pushState({url: url}, "", url);
  }

  var params = rekall.utils.parseParams(window.location.search.substring(1));
  if (params.client_id) {
    rekall.clients.add_to_client_lru(params.client_id);
  }
});
