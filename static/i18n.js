(function (root) {
  "use strict";
  root.I18N = root.I18N || {};
  root.LANG = root.LANG || "en";
  root.t = function (key, vars) {
    var template = root.I18N[key] || key;
    if (!vars) return template;
    return String(template).replace(/\{(\w+)\}/g, function (_, name) {
      return vars[name] == null ? "" : String(vars[name]);
    });
  };
})(window);
