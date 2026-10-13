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

  // Award settings: blind judging is only possible if a round is a desk review.
  // (The server checks this too; this just gives instant feedback.)
  document.querySelectorAll("form[data-award-settings]").forEach(function (form) {
    var blind = form.querySelector("input[name=blind]");
    var note = form.querySelector("[data-blind-note]");
    function update() {
      var types = Array.prototype.map.call(form.querySelectorAll("[data-round-type]"), function (s) { return s.value; });
      var possible = types.indexOf("desk") !== -1;
      blind.disabled = !possible;
      if (!possible) blind.checked = false;
      if (note) note.hidden = possible;
    }
    form.addEventListener("change", update);
    update();
  });

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

// Login, sign-up and password pages ------------------------------------------
(function () {
  // Show / hide password
  document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
    var input = document.getElementById(button.getAttribute("data-toggle-password"));
    if (!input) return;
    button.addEventListener("click", function () {
      var showing = input.type === "text";
      input.type = showing ? "password" : "text";
      button.textContent = showing ? "Show" : "Hide";
      button.setAttribute("aria-label", showing ? "Show password" : "Hide password");
      button.setAttribute("aria-pressed", showing ? "false" : "true");
    });
  });

  // Loading state: disable the button and change its text while the form is sent
  document.querySelectorAll("form[data-loading-form]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var button = form.querySelector("button[type=submit]");
      if (!button) return;
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      button.textContent = button.getAttribute("data-loading-text") || "Please wait…";
    });
  });
})();
