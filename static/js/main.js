// Small helpers for the clickable demo screens.
(function () {
  // Mobile menu
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector(".main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Buttons marked data-demo show a message instead of saving anything yet.
  var toast = document.createElement("div");
  toast.className = "toast";
  toast.setAttribute("role", "status");
  document.body.appendChild(toast);
  var timer;
  document.addEventListener("click", function (event) {
    var el = event.target.closest("[data-demo]");
    if (!el) return;
    event.preventDefault();
    toast.textContent = el.getAttribute("data-demo") || "Demo screen: this action is not saved yet.";
    toast.classList.add("show");
    clearTimeout(timer);
    timer = setTimeout(function () { toast.classList.remove("show"); }, 3000);
  });
})();
