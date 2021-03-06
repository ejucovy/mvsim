/*!
 * raphaeljs.serialize
 *
 * Copyright (c) 2010 Jonathan Spies
 * Licensed under the MIT license:
 * (http://www.opensource.org/licenses/mit-license.php)
 *
 *
 * from: http://github.com/ejucovy/raphael.serialize/
 *
 *
 *
 */

Raphael.fn.serialize = {
  json: function() {
    var paper = this;
    var svgdata = [];

    for(var node = paper.bottom; node != null; node = node.next) {
      if (node && node.type) {
        switch(node.type) {
          case "image":
            if( node.node.style.display == "none" ) break;
            var object = {
              type: node.type,
              width: node.attrs['width'],
              height: node.attrs['height'],
              x: node.attrs['x'],
              y: node.attrs['y'],
              src: node.attrs['src'],
              transform: node.transformations ? node.transformations.join(' ') : ''
            };
            break;
          case "ellipse":
            if( node.node.style.display == "none" ) break;
            var object = {
              type: node.type,
              rx: node.attrs['rx'],
              ry: node.attrs['ry'],
              cx: node.attrs['cx'],
              cy: node.attrs['cy'],
              stroke: node.attrs['stroke'] === 0 ? 'none': node.attrs['stroke'],
              'stroke-width': node.attrs['stroke-width'],
              fill: node.attrs['fill']
            };
            break;
          case "circle":
            if( node.node.style.display == "none" ) break;
            if( node.attrs['opacity'] === 0 ) break;
            var object = {
              type: node.type,
              cx: node.attrs['cx'],
              cy: node.attrs['cy'],
              r: node.attrs['r'],
              stroke: node.attrs['stroke'] === 0 ? 'none': node.attrs['stroke'],
              'stroke-width': node.attrs['stroke-width'],
              fill: node.attrs['fill'],
	      opacity: node.attrs['opacity'],
            };
            break;
          case "rect":
            if( node.node.style.display == "none" ) break;
            var object = {
              type: node.type,
              x: node.attrs['x'],
              y: node.attrs['y'],
              width: node.attrs['width'],
              height: node.attrs['height'],
              stroke: node.attrs['stroke'] === 0 ? 'none': node.attrs['stroke'],
              'stroke-width': node.attrs['stroke-width'],
              fill: node.attrs['fill']
            };
            break;

          case "text":
            if( node.node.style.display == "none" ) break;
            var object = {
              type: node.type,
              font: node.attrs['font'],
              'font-family': node.attrs['font-family'],
              'font-size': node.attrs['font-size'],
              stroke: node.attrs['stroke'] === 0 ? 'none': node.attrs['stroke'],
              fill: node.attrs['fill'] === 0 ? 'none' : node.attrs['fill'],
              'stroke-width': node.attrs['stroke-width'],
              x: node.attrs['x'],
              y: node.attrs['y'],
              text: node.attrs['text'],
              'text-anchor': node.attrs['text-anchor']
            };
            break;

          case "path":
	    if( node.node.style.display == "none" ) break;
            var path = "";

            $.each(node.attrs['path'], function(i, group) {
              $.each(group,
                function(index, value) {
                  if (index < 1) {
                      path += value;
                  } else {
                    if (index == (group.length - 1)) {
                      path += value;
                    } else {
                     path += value + ',';
                    }
                  }
                });
            });

            var object = {
              type: node.type,
              fill: node.attrs['fill'],
              opacity: node.attrs['opacity'],
              translation: node.attrs['translation'],
              scale: node.attrs['scale'],
              path: path,
              stroke: node.attrs['stroke'] === 0 ? 'none': node.attrs['stroke'],
              'stroke-width': node.attrs['stroke-width'],
              transform: node.transformations ? node.transformations.join(' ') : ''
            };
        }

        if (object) {
          svgdata.push(object);
        }
      }
    }

    return(JSON.stringify(svgdata));
  },

  load_json : function(json) {
    if (typeof(json) == "string") { json = JSON.parse(json); } // allow stringified or object input

    var paper = this;
    var set = paper.set();
    $.each(json, function(index, node) {
      try {
        var el = paper[node.type]().attr(node);
        set.push(el);
      } catch(e) {}
    });
    return set;
  }
}

