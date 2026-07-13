"""Coffee tracker — reusable equipment/bean records + individual brew entries."""
from flask import (
    Flask, abort, jsonify, redirect, render_template, request, url_for,
)

import db

app = Flask(__name__)
app.teardown_appcontext(db.close_db)


# --- form configuration -----------------------------------------------------
# Single source of truth for each manageable resource: drives the management
# tables, the edit pages, and the inline "+ Add New" modals (exposed to JS).

RESOURCES = {
    "beans": {
        "table": "beans",
        "singular": "Bean",
        "plural": "Beans",
        "label_col": "display_name",
        "list_columns": [
            ("display_name", "Name"), ("roaster", "Roaster"),
            ("origin_country", "Origin"), ("roast_level", "Roast"),
            ("roast_date", "Roast date"),
        ],
        "fields": [
            {"name": "display_name", "label": "Display name", "type": "text", "required": True},
            {"name": "roaster", "label": "Roaster", "type": "text"},
            {"name": "coffee_name", "label": "Coffee / lot name", "type": "text"},
            {"name": "origin_country", "label": "Origin country", "type": "text"},
            {"name": "region", "label": "Region / farm", "type": "text"},
            {"name": "producer", "label": "Producer", "type": "text"},
            {"name": "variety", "label": "Variety", "type": "text"},
            {"name": "process", "label": "Process", "type": "text",
             "placeholder": "Washed, natural, honey, anaerobic"},
            {"name": "roast_level", "label": "Roast level", "type": "select",
             "options": ["Light", "Medium-light", "Medium", "Medium-dark", "Dark"]},
            {"name": "roast_date", "label": "Roast date", "type": "date"},
            {"name": "purchase_date", "label": "Purchase date", "type": "date"},
            {"name": "bag_weight_grams", "label": "Bag weight (g)", "type": "number"},
            {"name": "storage_method", "label": "Storage method", "type": "text",
             "placeholder": "Original bag, Airscape, vacuum, freezer"},
            {"name": "storage_location", "label": "Storage location", "type": "text",
             "placeholder": "Counter, cabinet, freezer"},
            {"name": "opened_date", "label": "Opened date", "type": "date"},
            {"name": "notes", "label": "Notes", "type": "textarea"},
        ],
    },
    "grinders": {
        "table": "grinders",
        "singular": "Grinder",
        "plural": "Grinders",
        "label_col": "name",
        "list_columns": [
            ("name", "Name"), ("brand", "Brand"),
            ("model", "Model"), ("grinder_type", "Type"),
        ],
        "fields": [
            {"name": "name", "label": "Name", "type": "text", "required": True},
            {"name": "brand", "label": "Brand", "type": "text"},
            {"name": "model", "label": "Model", "type": "text"},
            {"name": "grinder_type", "label": "Grinder type", "type": "select",
             "options": ["Electric burr", "Hand grinder", "Blade", "Other"]},
            {"name": "burr_type", "label": "Burr type", "type": "select",
             "options": ["Conical", "Flat", "Ceramic", "Steel", "Conical steel",
                         "Flat steel", "Conical ceramic", "Flat ceramic"]},
            {"name": "notes", "label": "Notes", "type": "textarea",
             "placeholder": "Calibration notes, etc."},
        ],
    },
    "brewers": {
        "table": "brewers",
        "singular": "Brewer",
        "plural": "Brewers",
        "label_col": "name",
        "list_columns": [
            ("name", "Name"), ("brand", "Brand"),
            ("method_name", "Method"), ("material", "Material"),
        ],
        "fields": [
            {"name": "name", "label": "Name", "type": "text", "required": True},
            {"name": "brand", "label": "Brand", "type": "text"},
            {"name": "model", "label": "Model", "type": "text"},
            {"name": "method_id", "label": "Default method", "type": "ref",
             "options_from": "brewing_methods"},
            {"name": "material", "label": "Material", "type": "select",
             "options": ["Plastic", "Ceramic", "Glass", "Metal", "Stainless steel"]},
            {"name": "size", "label": "Size / capacity", "type": "text"},
            {"name": "notes", "label": "Notes", "type": "textarea",
             "placeholder": "Filters, modifications, accessories"},
        ],
    },
    "methods": {
        "table": "brewing_methods",
        "singular": "Method",
        "plural": "Methods",
        "label_col": "name",
        "list_columns": [("name", "Name"), ("description", "Description")],
        "fields": [
            {"name": "name", "label": "Name", "type": "text", "required": True},
            {"name": "description", "label": "Description", "type": "textarea"},
        ],
    },
}


def _resource(slug):
    cfg = RESOURCES.get(slug)
    if cfg is None:
        abort(404)
    return cfg


def coerce(fields, form):
    """Turn a submitted form into a cleaned dict of values by field type."""
    data = {}
    for f in fields:
        raw = (form.get(f["name"]) or "").strip()
        if raw == "":
            data[f["name"]] = None
            continue
        t = f["type"]
        if t in ("ref", "int"):
            data[f["name"]] = int(raw) if raw.lstrip("-").isdigit() else None
        elif t == "number":
            try:
                data[f["name"]] = float(raw)
            except ValueError:
                data[f["name"]] = None
        else:
            data[f["name"]] = raw
    return data


def dropdown_options():
    """Active records for every dropdown on the log-brew page."""
    return {
        "beans": db.fetch_all("beans", active_only=True),
        "grinders": db.fetch_all("grinders", active_only=True),
        "methods": db.fetch_all("brewing_methods", active_only=True),
        "brewers": db.fetch_all("brewers", active_only=True),
    }


# --- log brew ---------------------------------------------------------------

@app.route("/")
def log_brew():
    opts = dropdown_options()
    return render_template(
        "log_brew.html",
        resources=RESOURCES,
        beans=opts["beans"],
        grinders=opts["grinders"],
        methods=opts["methods"],
        brewers=opts["brewers"],
    )


BREW_FIELD_TYPES = {
    "brewed_at": "text", "bean_id": "ref", "grinder_id": "ref",
    "grind_setting": "text", "grind_category": "text", "method_id": "ref",
    "brewer_id": "ref", "water_temperature": "number", "temperature_unit": "text",
    "coffee_grams": "number", "water_grams": "number",
    "brew_time_seconds": "int", "yield_grams": "number",
    "rating": "int", "notes": "text",
}


@app.route("/brew", methods=["POST"])
def add_brew():
    fields = [{"name": n, "type": t} for n, t in BREW_FIELD_TYPES.items()]
    data = coerce(fields, request.form)
    if not data.get("brewed_at"):
        data["brewed_at"] = db._now()
    else:
        data["brewed_at"] = data["brewed_at"].replace("T", " ")
    db.insert_brew(data)
    return redirect(url_for("history"))


@app.route("/history")
def history():
    return render_template("history.html", brews=db.fetch_brews())


@app.route("/brew/<int:brew_id>/delete", methods=["POST"])
def delete_brew(brew_id):
    db.delete_brew(brew_id)
    return redirect(url_for("history"))


# --- management: list / add / edit / archive --------------------------------

def _decorate(slug, records):
    """Add derived columns needed by list views (e.g. brewer's method name)."""
    if slug == "brewers":
        methods = {m["id"]: m["name"] for m in db.fetch_all("brewing_methods")}
        for r in records:
            r["method_name"] = methods.get(r.get("method_id"), "")
    return records


@app.route("/manage/<slug>")
def manage(slug):
    cfg = _resource(slug)
    records = _decorate(slug, db.fetch_all(cfg["table"]))
    return render_template(
        "manage.html", slug=slug, cfg=cfg, records=records,
        options=_ref_options(cfg),
    )


@app.route("/manage/<slug>/add", methods=["POST"])
def manage_add(slug):
    cfg = _resource(slug)
    db.insert(cfg["table"], coerce(cfg["fields"], request.form))
    return redirect(url_for("manage", slug=slug))


@app.route("/manage/<slug>/<int:row_id>/edit", methods=["GET", "POST"])
def manage_edit(slug, row_id):
    cfg = _resource(slug)
    record = db.fetch_one(cfg["table"], row_id)
    if record is None:
        abort(404)
    if request.method == "POST":
        db.update(cfg["table"], row_id, coerce(cfg["fields"], request.form))
        return redirect(url_for("manage", slug=slug))
    return render_template(
        "edit.html", slug=slug, cfg=cfg, record=record,
        options=_ref_options(cfg),
    )


@app.route("/manage/<slug>/<int:row_id>/archive", methods=["POST"])
def manage_archive(slug, row_id):
    cfg = _resource(slug)
    active = request.form.get("active") == "1"
    db.set_active(cfg["table"], row_id, active)
    return redirect(url_for("manage", slug=slug))


# --- inline "+ Add New" JSON API --------------------------------------------

@app.route("/api/<slug>", methods=["POST"])
def api_add(slug):
    cfg = _resource(slug)
    data = coerce(cfg["fields"], request.form)
    new_id = db.insert(cfg["table"], data)
    record = db.fetch_one(cfg["table"], new_id)
    return jsonify({
        "id": new_id,
        "label": record[cfg["label_col"]],
        "method_id": record.get("method_id"),
        "record": record,
    })


def _ref_options(cfg):
    """Options for any `ref`/options_from select fields in a resource form."""
    out = {}
    for f in cfg["fields"]:
        src = f.get("options_from")
        if src:
            out[src] = db.fetch_all(src, active_only=True)
    return out


@app.context_processor
def inject_nav():
    return {"nav_resources": RESOURCES}


with app.app_context():
    db.init_db()


if __name__ == "__main__":
    # Debug is OFF by default. Enable locally with KOFELOG_DEBUG=1 if needed.
    # WARNING: never run with debug enabled while binding to a public host
    # (0.0.0.0) — Flask's debugger allows arbitrary code execution.
    import os
    debug = os.environ.get("KOFELOG_DEBUG") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug)
