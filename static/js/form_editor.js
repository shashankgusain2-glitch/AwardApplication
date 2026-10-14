/*
 * Form editor (staff): add and remove questions and sections, move questions up and down.
 * On submit every row is renumbered q-0-*, q-1-*, ... in page order and given its card's
 * section name, so the server reads the questions in the order shown.
 */
(function () {
  "use strict";
  var form = document.querySelector("[data-form-editor]");
  if (!form) return;

  var sections = form.querySelector("[data-sections]");
  var questionTemplate = form.querySelector("[data-question-template]");
  var sectionTemplate = form.querySelector("[data-section-template]");

  function fromTemplate(template) {
    return template.content.firstElementChild.cloneNode(true);
  }

  function showControls(root) {
    root.querySelectorAll("[data-move], [data-remove-new], [data-add-question], [data-remove-section]")
      .forEach(function (el) { el.hidden = false; });
  }

  function renumber() {
    form.querySelectorAll("[data-question]").forEach(function (row, i) {
      row.querySelectorAll("[name^='q-']").forEach(function (input) {
        input.name = input.name.replace(/^q-[^-]+-/, "q-" + i + "-");
      });
      row.querySelector("[data-number]").textContent = i + 1;
      var card = row.closest("[data-section]");
      row.querySelector("[data-row-section]").value = card.querySelector("[data-section-name]").value.trim();
    });
    form.querySelector("[data-row-count]").value = form.querySelectorAll("[data-question]").length;
  }

  function addQuestion(card, focus) {
    var row = fromTemplate(questionTemplate);
    showControls(row);
    var rows = card.querySelector("[data-rows]");
    var last = rows.querySelector("[data-question]:last-child [name$='-subsection']");
    if (last) row.querySelector("[name$='-subsection']").value = last.value;   // same subcategory as the row above
    rows.appendChild(row);
    renumber();
    if (focus) row.querySelector("[name$='-label']").focus();
  }

  function addSection() {
    var card = fromTemplate(sectionTemplate);
    showControls(card);
    sections.appendChild(card);
    addQuestion(card, false);
    card.querySelector("[data-section-name]").focus();
  }

  function removeSection(card) {
    var existing = card.querySelectorAll("[data-existing]");
    if (!existing.length) {
      card.remove();
    } else if (window.confirm("Remove this section and all " + card.querySelectorAll("[data-question]").length +
                              " of its questions from the new version?")) {
      card.querySelectorAll("[data-question]:not([data-existing])").forEach(function (row) { row.remove(); });
      existing.forEach(function (row) {
        var box = row.querySelector("[data-remove-existing]");
        box.checked = true;
        row.style.opacity = ".45";
      });
    }
    renumber();
  }

  form.addEventListener("click", function (event) {
    var button = event.target.closest("button");
    if (!button) return;
    var card = button.closest("[data-section]");
    var row = button.closest("[data-question]");
    if (button.hasAttribute("data-add-question")) {
      addQuestion(card, true);
    } else if (button.hasAttribute("data-add-section")) {
      addSection();
    } else if (button.hasAttribute("data-remove-section")) {
      removeSection(card);
    } else if (button.hasAttribute("data-remove-new")) {
      row.remove();
      renumber();
    } else if (button.dataset.move === "up" && row.previousElementSibling) {
      row.parentNode.insertBefore(row, row.previousElementSibling);
      renumber();
    } else if (button.dataset.move === "down" && row.nextElementSibling) {
      row.parentNode.insertBefore(row.nextElementSibling, row);
      renumber();
    }
  });

  form.addEventListener("change", function (event) {
    if (event.target.matches("[data-remove-existing]")) {
      event.target.closest("[data-question]").style.opacity = event.target.checked ? ".45" : "";
    }
  });

  form.addEventListener("submit", renumber);

  showControls(sections);
  form.querySelector("[data-editor-tools]").hidden = false;
  form.querySelector("[data-no-js]").hidden = true;
  form.querySelectorAll("[data-remove-existing]:checked").forEach(function (box) {
    box.closest("[data-question]").style.opacity = ".45";
  });
})();
