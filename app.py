from flask import Flask, render_template, request, jsonify, redirect, url_for\nimport os\nfrom pymongo import MongoClient
from datetime import datetime, timezone
import re

app = Flask(__name__)

client = MongoClient(os.getenv("MONGO_URI", "mongodb+srv://abhinayapulagam_db_user:69Gm5TSVTfyadmC3@cluster0.xxyzbss.mongodb.net/?appName=Cluster0"))
db = client["contact_manager"]
contacts_col = db["contacts"]

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
PHONE_RE = re.compile(r"^\+?[1-9]\d{6,14}$")


def now():
    return datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p")


def next_id():
    last = contacts_col.find_one({}, sort=[("_id", -1)])
    if not last or not last.get("contact_id"):
        return "C001"
    n = int(last["contact_id"][1:]) + 1
    return f"C{n:03d}"


def validate(first_name, last_name, email, phone, address):
    err = {}
    if not first_name: err["first_name"] = "First name is required."
    if not last_name:  err["last_name"]  = "Last name is required."
    if not email:
        err["email"] = "Email is required."
    elif not EMAIL_RE.match(email):
        err["email"] = "Enter a valid email address."
    if not phone:
        err["phone"] = "Phone number is required."
    elif not PHONE_RE.match(phone.replace(" ", "")):
        err["phone"] = "Enter a valid phone number."
    if not address: err["address"] = "Address is required."
    return err


def make_filter(q):
    if not q:
        return {}
    p = re.compile(re.escape(q), re.IGNORECASE)
    return {"$or": [
        {"first_name": p}, {"last_name": p},
        {"email": p}, {"phone": p}, {"address": p}
    ]}


def check_duplicates(email, phone, skip_id=None):
    """
    Check if email or phone already exist in DB.
    skip_id is used during edits so we don't flag the contact's own values.
    Returns a dict of errors (empty = no duplicates found).
    """
    err = {}
    email_query = {"email": email}
    phone_query = {"phone": phone}
    if skip_id:
        email_query["contact_id"] = {"$ne": skip_id}
        phone_query["contact_id"] = {"$ne": skip_id}

    if contacts_col.find_one(email_query):
        err["email"] = "This email is already registered. Please use a different one."
    if contacts_col.find_one(phone_query):  # separate if — checks both regardless
        err["phone"] = "This phone number already exists. Please use a different one."
    return err


@app.route("/", methods=["GET", "POST"])
def home():
    q = request.args.get("q", "").strip()
    errors = {}
    form = {k: "" for k in ["first_name", "last_name", "email", "phone", "address"]}
    msg = {"1": "Contact saved successfully.", "updated": "Contact updated successfully.", "deleted": "Contact deleted successfully."}.get(request.args.get("success", ""))

    if request.method == "POST":
        form = {
            "first_name": request.form.get("first_name", "").strip(),
            "last_name":  request.form.get("last_name", "").strip(),
            "email":      request.form.get("email", "").strip().lower(),
            "phone":      request.form.get("phone", "").strip(),
            "address":    request.form.get("address", "").strip(),
        }

        errors = validate(**form)

        # only check duplicates if format is valid
        if not errors:
            errors = check_duplicates(form["email"], form["phone"])

        if not errors:
            contacts_col.insert_one({"contact_id": next_id(), **form, "created_at": now(), "updated_at": now()})
            return redirect(url_for("home", q=q, success="1"))

    contacts = list(contacts_col.find(make_filter(q), {"_id": 0}))
    total = contacts_col.count_documents({})
    return render_template("index.html", contacts=contacts, total=total, errors=errors, form=form, message=msg, q=q)


@app.route("/edit/<contact_id>", methods=["GET", "POST"])
def edit_contact(contact_id):
    q = request.args.get("q", "").strip()
    contact = contacts_col.find_one({"contact_id": contact_id}, {"_id": 0})
    if not contact:
        return redirect(url_for("home", q=q))

    errors = {}
    form = contact

    if request.method == "POST":
        form = {
            "first_name": request.form.get("first_name", "").strip(),
            "last_name":  request.form.get("last_name", "").strip(),
            "email":      request.form.get("email", "").strip().lower(),
            "phone":      request.form.get("phone", "").strip(),
            "address":    request.form.get("address", "").strip(),
        }

        errors = validate(**form)

        if not errors:
            # pass skip_id so it won't flag the contact's own email/phone as duplicate
            errors = check_duplicates(form["email"], form["phone"], skip_id=contact_id)

        if not errors:
            contacts_col.update_one({"contact_id": contact_id}, {"$set": {**form, "updated_at": now()}})
            return redirect(url_for("home", q=q, success="updated"))

    contacts = list(contacts_col.find(make_filter(q), {"_id": 0}))
    total = contacts_col.count_documents({})
    return render_template("index.html", contacts=contacts, total=total, errors=errors, form=form, edit=contact, message=None, q=q)


@app.route("/delete/<contact_id>", methods=["POST"])
def delete_contact(contact_id):
    q = request.args.get("q", "").strip()
    result = contacts_col.delete_one({"contact_id": contact_id})
    return redirect(url_for("home", q=q, success="deleted" if result.deleted_count else None))


# ── JSON API ─────────────────────────────────────────────

@app.route("/api/contacts", methods=["GET"])
def api_get_contacts():
    return jsonify(list(contacts_col.find({}, {"_id": 0})))


@app.route("/api/contacts", methods=["POST"])
def api_add_contact():
    d = request.get_json()
    fields = {
        "first_name": d.get("first_name", "").strip(),
        "last_name":  d.get("last_name", "").strip(),
        "email":      d.get("email", "").strip().lower(),
        "phone":      d.get("phone", "").strip(),
        "address":    d.get("address", "").strip(),
    }

    errors = validate(**fields)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 422

    dup_errors = check_duplicates(fields["email"], fields["phone"])
    if dup_errors:
        return jsonify({"ok": False, "errors": dup_errors}), 409

    doc = {"contact_id": next_id(), **fields, "created_at": now(), "updated_at": now()}
    contacts_col.insert_one(doc)
    doc.pop("_id", None)
    return jsonify({"ok": True, "contact": doc}), 201


@app.route("/api/contacts/<contact_id>", methods=["PUT"])
def api_update_contact(contact_id):
    d = request.get_json()
    fields = {
        "first_name": d.get("first_name", "").strip(),
        "last_name":  d.get("last_name", "").strip(),
        "email":      d.get("email", "").strip().lower(),
        "phone":      d.get("phone", "").strip(),
        "address":    d.get("address", "").strip(),
    }

    errors = validate(**fields)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 422

    dup_errors = check_duplicates(fields["email"], fields["phone"], skip_id=contact_id)
    if dup_errors:
        return jsonify({"ok": False, "errors": dup_errors}), 409

    contacts_col.update_one({"contact_id": contact_id}, {"$set": {**fields, "updated_at": now()}})
    return jsonify({"ok": True})


@app.route("/api/contacts/<contact_id>", methods=["DELETE"])
def api_delete_contact(contact_id):
    result = contacts_col.delete_one({"contact_id": contact_id})
    if result.deleted_count == 0:
        return jsonify({"ok": False, "message": "Contact not found."}), 404
    return jsonify({"ok": True})


@app.route("/api/stats")
def api_stats():
    return jsonify({"total": contacts_col.count_documents({})})


if __name__ == "__main__":
    app.run(debug=True)