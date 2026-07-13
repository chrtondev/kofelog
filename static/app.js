"use strict";

// ---- data embedded by the server ------------------------------------------
const readJSON = (id) => JSON.parse(document.getElementById(id).textContent);
const FORMS = readJSON("data-forms");
let METHODS = readJSON("data-methods");
let BEANS = readJSON("data-beans");
let BREWERS = readJSON("data-brewers");

const beanSelect = document.getElementById("bean-select");
const grinderSelect = document.getElementById("grinder-select");
const methodSelect = document.getElementById("method-select");
const brewerSelect = document.getElementById("brewer-select");

// ---- brewer dropdown filtered by selected method --------------------------
function rebuildBrewers(preserveId) {
  const methodVal = methodSelect.value;
  brewerSelect.innerHTML = '<option value="">Select brewer…</option>';
  let kept = "";
  BREWERS.forEach((b) => {
    const noMethod = b.method_id === null || b.method_id === undefined;
    if (!methodVal || noMethod || String(b.method_id) === methodVal) {
      const opt = document.createElement("option");
      opt.value = b.id;
      opt.textContent = b.name;
      brewerSelect.appendChild(opt);
      if (String(b.id) === String(preserveId)) kept = String(b.id);
    }
  });
  brewerSelect.value = kept;
}

if (methodSelect && brewerSelect) {
  methodSelect.addEventListener("change", () => rebuildBrewers(brewerSelect.value));
  brewerSelect.addEventListener("change", () => {
    const b = BREWERS.find((x) => String(x.id) === brewerSelect.value);
    if (b && b.method_id) methodSelect.value = String(b.method_id);
    rebuildBrewers(brewerSelect.value);
  });
  rebuildBrewers("");
}

// ---- bean summary panel ---------------------------------------------------
function showBeanSummary() {
  const panel = document.getElementById("bean-summary");
  if (!panel) return;
  const bean = BEANS.find((b) => String(b.id) === beanSelect.value);
  if (!bean) {
    panel.hidden = true;
    return;
  }
  const rows = [
    ["Roaster", bean.roaster],
    ["Origin", [bean.origin_country, bean.region].filter(Boolean).join(", ")],
    ["Variety", bean.variety],
    ["Process", bean.process],
    ["Roast", bean.roast_level],
    ["Roast date", bean.roast_date],
    ["Storage", [bean.storage_method, bean.storage_location].filter(Boolean).join(" · ")],
  ].filter(([, v]) => v);
  panel.innerHTML = rows
    .map(([k, v]) => `<div><span>${k}</span>${v}</div>`)
    .join("");
  panel.hidden = rows.length === 0;
}
if (beanSelect) beanSelect.addEventListener("change", showBeanSummary);

// ---- default brewed_at to now ---------------------------------------------
const brewedAt = document.getElementById("brewed-at");
if (brewedAt && !brewedAt.value) {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  brewedAt.value =
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// ---- inline "+ Add New" modal ---------------------------------------------
const overlay = document.getElementById("modal-overlay");
const modalForm = document.getElementById("modal-form");
const modalTitle = document.getElementById("modal-title");

function escapeAttr(s) {
  return String(s).replace(/"/g, "&quot;");
}

function fieldHTML(f) {
  const req = f.required ? "required" : "";
  const ph = f.placeholder ? `placeholder="${escapeAttr(f.placeholder)}"` : "";
  let control;
  if (f.type === "textarea") {
    control = `<textarea name="${f.name}" rows="2" ${ph}></textarea>`;
  } else if (f.type === "select") {
    const opts = ['<option value="">—</option>']
      .concat((f.options || []).map((o) => `<option>${o}</option>`))
      .join("");
    control = `<select name="${f.name}">${opts}</select>`;
  } else if (f.type === "ref") {
    const src = f.options_from === "brewing_methods" ? METHODS : [];
    const opts = ['<option value="">—</option>']
      .concat(src.map((o) => `<option value="${o.id}">${o.name}</option>`))
      .join("");
    control = `<select name="${f.name}">${opts}</select>`;
  } else if (f.type === "number") {
    control = `<input type="number" step="any" name="${f.name}" ${ph} ${req}>`;
  } else if (f.type === "date") {
    control = `<input type="date" name="${f.name}">`;
  } else {
    control = `<input type="text" name="${f.name}" ${ph} ${req}>`;
  }
  const star = f.required ? ' <span class="req">*</span>' : "";
  return `<div class="field"><label>${f.label}${star}</label>${control}</div>`;
}

let currentResource = null;

function openModal(resource) {
  const cfg = FORMS[resource];
  currentResource = resource;
  modalTitle.textContent = "Add " + cfg.singular;
  modalForm.innerHTML =
    `<div class="form-grid">${cfg.fields.map(fieldHTML).join("")}</div>` +
    `<div class="btn-row"><button type="submit" class="primary">Save ${cfg.singular}</button>` +
    `<button type="button" class="btn-secondary" data-close>Cancel</button></div>`;
  overlay.hidden = false;
  const first = modalForm.querySelector("input, select, textarea");
  if (first) first.focus();
}

function closeModal() {
  overlay.hidden = true;
  modalForm.innerHTML = "";
  currentResource = null;
}

document.querySelectorAll(".add-new").forEach((btn) => {
  btn.addEventListener("click", () => openModal(btn.dataset.resource));
});
document.getElementById("modal-close").addEventListener("click", closeModal);
overlay.addEventListener("click", (e) => {
  if (e.target === overlay || e.target.hasAttribute("data-close")) closeModal();
});

function addOption(select, id, label, select_it) {
  const opt = document.createElement("option");
  opt.value = id;
  opt.textContent = label;
  select.appendChild(opt);
  if (select_it) select.value = String(id);
}

modalForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const resource = currentResource;
  const res = await fetch(`/api/${resource}`, {
    method: "POST",
    body: new FormData(modalForm),
  });
  if (!res.ok) {
    alert("Could not save. Please check the required fields.");
    return;
  }
  const data = await res.json();

  if (resource === "beans") {
    BEANS.push(data.record);
    addOption(beanSelect, data.id, data.label, true);
    showBeanSummary();
  } else if (resource === "grinders") {
    addOption(grinderSelect, data.id, data.label, true);
  } else if (resource === "methods") {
    METHODS.push(data.record);
    addOption(methodSelect, data.id, data.label, true);
    rebuildBrewers(brewerSelect.value);
  } else if (resource === "brewers") {
    BREWERS.push(data.record);
    if (data.method_id) methodSelect.value = String(data.method_id);
    rebuildBrewers(data.id);
  }
  closeModal();
});
