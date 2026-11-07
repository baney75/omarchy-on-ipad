/* Progressive enhancement only. The page is complete without this file.
   Adds a relative age ("3 hours ago") after any <time data-relative>. */
(function () {
  "use strict";
  if (!("Intl" in window) || !Intl.RelativeTimeFormat) return;

  var rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  var units = [
    ["year", 31536000], ["month", 2592000], ["week", 604800],
    ["day", 86400], ["hour", 3600], ["minute", 60]
  ];

  function ago(date) {
    var seconds = (date.getTime() - Date.now()) / 1000;
    for (var i = 0; i < units.length; i++) {
      if (Math.abs(seconds) >= units[i][1]) {
        return rtf.format(Math.round(seconds / units[i][1]), units[i][0]);
      }
    }
    return "just now";
  }

  var nodes = document.querySelectorAll("time[data-relative]");
  for (var i = 0; i < nodes.length; i++) {
    var el = nodes[i];
    var when = new Date(el.getAttribute("datetime"));
    if (isNaN(when.getTime())) continue;
    var tag = document.createElement("span");
    tag.className = "relative";
    tag.textContent = " (" + ago(when) + ")";
    el.parentNode.insertBefore(tag, el.nextSibling);
  }
})();
