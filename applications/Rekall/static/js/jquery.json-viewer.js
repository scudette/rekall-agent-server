/**
 * jQuery json-viewer
 * @author: Alexandre Bodelot <alexandre.bodelot@gmail.com>
 * Local modifications scudette@gmail.com
 */
(function($){

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
      return "<span class='json-date'> " + d.toISOString() + "</span>";
    }
    return "";
  }

  /**
   * Transform a json object into html representation
   * @return string
   */
  function json2html(json, options, depth) {
    var html = '<span class="control collapsed">';
    if (typeof json === 'string') {
      /* Escape tags */
      json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      if (isUrl(json))
        html += '<a href="' + json + '" class="json-string">' + json + '</a>';
      else
        html += '<span class="json-string">"' + json + '"</span>';
    }
    else if (typeof json === 'number') {
      html += '<span class="json-literal">' + json + '</span>' + formatTimeStamp(json);
    }
    else if (typeof json === 'boolean') {
      html += '<span class="json-literal">' + json + '</span>';
    }
    else if (json === null) {
      html += '<span class="json-literal">null</span>';
    }
    else if (json instanceof Array) {
      if (json.length > 0) {
        html += '[<ol class="json-array">';
        for (var i = 0; i < json.length; ++i) {
          html += '<li>';
          /* Add toggle button if item is collapsable */
          if (isCollapsable(json[i])) {
            html += '<a href class="json-toggle collapsed"></a>';
          }
          html += json2html(json[i], options, depth+1);
          /* Add comma if item is not last */
          if (i < json.length - 1) {
            html += ',';
          }
          html += '</li>';
        }
        html += '</ol>]';

        var placeholder = json.length + (json.length > 1 ? ' items' : ' item');
        html += '<a href class="json-placeholder">' + placeholder + '</a>';
      }
      else {
        html += '[]';
      }


    }
    else if (typeof json === 'object') {
      var key_count = Object.keys(json).length;
      if (key_count > 0) {
        html += '{<ul class="json-dict">';
        for (var key in json) {
          if (json.hasOwnProperty(key)) {
            html += '<li>';
            var keyRepr = options.withQuotes ?
              '<span class="json-string">"' + key + '"</span>' : key;
            /* Add toggle button if item is collapsable */
            if (isCollapsable(json[key])) {
              html += ('<a href class="json-toggle collapsed">' +
                  keyRepr + '</a>');
            }
            else {
              html += keyRepr;
            }
            html += ': ' + json2html(json[key], options, depth+1);
            /* Add comma if item is not last */
            if (--key_count > 0)
              html += ',';
            html += '</li>';
          }
        }
        html += '</ul>}';

        key_count = Object.keys(json).length;
        var placeholder = key_count + (key_count > 1 ? ' items' : ' item');
        html += '<a href class="json-placeholder">' + placeholder + '</a>';
      }
      else {
        html += '{}';
      }
    }

    return html + "</span>";
  }

  /**
   * jQuery plugin method
   * @param json: a javascript object
   * @param options: an optional options hash
   */
  $.fn.jsonViewer = function(json, options) {
    options = options || {};

    /* jQuery chaining */
    return this.each(function() {

      /* Transform to HTML */
      var html = json2html(json, options, 0);
      if (isCollapsable(json))
        html = '<a href class="json-toggle root"></a>' + html;

      /* Insert HTML in target DOM element */
      $(this).html(html);

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
