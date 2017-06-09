

rekall.utils.api = function(endpoint) {
  return rekall.globals.api_route + endpoint;
}

rekall.utils.escape_text = function(text) {
  return $("<div>").text(text).html();
}


rekall.utils.error_modal = function (text) {
  $("#modalContainer").html($.templates("#modal_template").render({
    body: text,
    title: "Error",
  }));
  $("#modal").modal("show");
}

rekall.utils.get = function(obj, item, def) {
  var result = obj[item];
  if (result === undefined) {
    return def;
  }
  return result;
}

rekall.utils.make_link = function(url, image) {
  var link = $("<a>");
  link.attr("href", url);
  var img = $("<img class='icon'>");
  img.attr("src", rekall.globals.image_dir + image);
  link.append(img);
  return link.prop('outerHTML');
}


rekall.utils.build_table_from_collection = function (url, selector) {
  $.ajax({
    dataType: "json",
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
    url: url,
    error: function (xhr, ajaxOptions, thrownError) {
      rekall.utils.error_modal(xhr.status + " Error: " + thrownError);
    },
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
                            return new Date(cell_data * 1000).toUTCString();
                          }

                          return $("<div>").text(cell_data).html();
                        }});
        });

        var dataset = data.table_data[table.name];
        var data_table = $(table_dom).DataTable({
          dom: '<"top"ifp<"clear">>rt<"bottom"lp<"clear">>',
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
        e.preventDefault()
        $(this).tab('show')
      }).first().click();

      $("#progressbar").hide();
    }
  });
}

rekall.utils.describe_collection = function(collection_id, callback) {
  $.ajax({
    dataType: "json",
    url: rekall.utils.api('/collections/metadata'),
    data: {
      collection_id: collection_id
    },
    success: function(metadata) {
      callback(rekall.cell_renderers.flow_summary_renderer(metadata.flow));
    }
  });
}

rekall.utils.jsonSyntaxHighlight = function (json) {
  json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  var result = json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
    var cls = 'number';
    if (/^"/.test(match)) {
      if (/:$/.test(match)) {
        cls = 'key';
      } else {
        cls = 'string';
      }
    } else if (/true|false/.test(match)) {
      cls = 'boolean';
    } else if (/null/.test(match)) {
      cls = 'null';
    }
    return '<span class="' + cls + '">' + match + '</span>';
  });

  return "<pre>" + result + "</pre>";
}


// Client controller.

rekall.clients.search_clients = function (query, selector) {
  var dataset_cache = {}

  $(selector).DataTable({
    ajax: {
      url: rekall.utils.api('/client/search'),
      data: {
        query: query
      },
    },
    columns: [
      {
        title: "Flows",
        data: "flows_link",
        searchable: false,
        orderable: false,
        render: function(cell_data, type, row, meta) {
          var link = $("<a>");
          link.attr("href", cell_data);
          var img = $("<img class='icon'>");
          img.attr("src", rekall.globals.image_dir + 'launch-icon.png');
          link.append(img);
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
      }
    ],
  });

  rekall.cell_renderers.generic_json_pp_clicks(
      dataset_cache, "summary", "Summary", selector);
}


rekall.flows.list_plugins = function(launch_url, client_id, selector) {
  $(selector).DataTable( {
    ajax: {
      url: rekall.utils.api("/plugin/list"),
    },
    columns: [
      {
        data: "plugin",
        searchable: false,
        render: function (plugin, type, full, meta) {
          var img = $("<img class='icon'>");
          img.attr("src", rekall.globals.image_dir + 'launch-icon.png');
          var link = $("<a>");
          link.append(img);
          link.attr("href", launch_url + "?plugin=" + encodeURIComponent(
              plugin) + "&client_id=" + encodeURIComponent(client_id));
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

    $.getJSON(rekall.utils.api("/plugin/get"), {plugin: plugin},
              function(data) {
                $("#modalContainer").html(
                    $.templates("#modal_template").render({
                      body: rekall.cell_renderers.generic_json_renderer(data),
                      title: "Plugin " + plugin,
                    }));
                $("#modal").modal("show");
              });
  });
}


rekall.flows.list_flows_for_client = function(client_id, selector) {
  var flow_cache = {};
  var status_cache = {};

  $(selector).DataTable({
    ajax: {
      url: rekall.utils.api("/flows/list"),
      data: {
        client_id: client_id
      }
    },
    columns: [
      {
        title: "",
        data: "flow",
        render: function(flow, type, row, meta) {
          var checkbox = $('<input name="flow_ids" type="checkbox">');
          checkbox.attr("value", flow.flow_id);
          return checkbox.prop("outerHTML");
        }
      },
      {
        title: "Time",
        data: "timestamp",
        type: "unix",
      },
      {
        title: "Flow",
        data: "flow",
        render: function(flow, type, row, meta) {
          var text = rekall.cell_renderers.flow_summary_renderer(flow);
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
        title: "Collections",
        data: "status.collection_ids",
        render: rekall.cell_renderers.collection_ids_renderer,
      },
      {
        title: "Files",
        data: "flow",
        render: function(flow, type, row, meta) {
          return rekall.utils.make_link(
              rekall.globals.controllers.uploads_view + "?flow_id=" +
                  flow.flow_id, "launch-icon.png");
        }
      },
    ],
  });
  rekall.cell_renderers.generic_json_pp_clicks(
      flow_cache, "flow", "Flow Information", selector);

  rekall.cell_renderers.generic_json_pp_clicks(
      status_cache, "status", "Flow Status", selector,
      rekall.cell_renderers.status_detailed_renderer);
}


rekall.uploads.list_uploads_for_flow = function(flow_id, selector) {
  var file_info_cache = {};

  $(selector).DataTable({
    ajax: {
      url: rekall.utils.api("/uploads/list"),
      data: {
        flow_id: flow_id
      }
    },
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
              rekall.globals.controllers.download + "?upload_id=" +
                  upload_id + "&filename=" + encodeURIComponent(filename),
              'launch-icon.png');
        }
      },
      {
        title: "HexView",
        data: "upload_id",
        render: function(upload_id, type, row, meta) {
          return rekall.utils.make_link(
              rekall.globals.controllers.hex_view + "?upload_id=" +
                  upload_id, 'launch-icon.png');
        }
      },
    ]
  });

  rekall.cell_renderers.generic_json_pp_clicks(
      file_info_cache, "finfo", "File Information", selector);
}


rekall.uploads.hex_view = function(upload_id, selector) {
  var width = 32;
  var height = 200;

  var url = (rekall.globals.controllers.download +
      "?upload_id=" + upload_id);
  $.ajax({
    url: url,
    type: "GET",
    responseType: 'arraybuffer',
    dataType: "binary",
    headers: {
      "Range": ("bytes=0-" + (width * height)),
    },
    processData: false,
    success: function(result, textStatus, request){
      var content_range = request.getResponseHeader('Content-Range');
      var match = new RegExp(".+([0-9]+)-([0-9]+)/([0-9]+)$").exec(content_range || "");
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
        $(selector).before($("<div>").text(
            "Showing content " + start + " - " + end + " / " + total_length));
      }
    }
  });
}


// Cell renderers for DataTables
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

    $("#modalContainer").html($.templates("#modal_template").render({
      body: detailed_renderer(cell_data),
      title: title,
    }));

    $("#modal").modal("show");
  });
}

rekall.cell_renderers.generic_json_renderer = function(obj) {
  return rekall.utils.jsonSyntaxHighlight(
      JSON.stringify(obj, undefined, 4))
}

rekall.cell_renderers.status_detailed_renderer = function(status) {
  var result = "";

  var json = rekall.utils.jsonSyntaxHighlight(
      JSON.stringify(status, undefined, 4));

  if (status.status == "Error") {
    var pre = $("<pre>");
    pre.text(status.backtrace);
    result += "<h3>Backtrace</h2>";
    result += pre.prop("outerHTML");
    result += `<a class="btn btn-primary" role="button" data-toggle="collapse"
        href="#jsonDetails" aria-expanded="false" aria-controls="jsonDetails">
        More details
        </a>`;

    result += '<div class="collapse" id="jsonDetails">';
    result += json;
    result += '</div>';

  } else {
    result +=  json;
  }

  return result;
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
        rekall.globals.controllers.collection_view + "/" +
            collection_ids[i], "launch-icon.png");
  }

  return result;
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
