# app/services/employee_importer.py
from __future__ import annotations
from pathlib import Path
from io import TextIOWrapper
import csv, re, unicodedata
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, date

try:
    import openpyxl
except ImportError:
    openpyxl = None

from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models import Q
from evaluation_app.serializers import employee_serilized  # local import to avoid cycles

from evaluation_app.models import (
    Company, Department, Employee,
    # enums below must exist in your project
    ManagerialLevel, EmpStatus, JobType, BranchType, Gender, Role  # adjust import
)

User = get_user_model()

# ------------------ Public API ------------------

def parse_employee_rows(request) -> List[Dict[str, Any]]:
    """Return list[dict] from JSON array OR multipart CSV/XLSX under 'file' key."""
    if "file" in request.FILES:
        f = request.FILES["file"]
        suffix = Path(f.name).suffix.lower()
        if suffix == ".csv":
            text = TextIOWrapper(f.file, encoding="utf-8", newline="")
            reader = csv.DictReader(text)
            rows = list(reader)
            if not rows:
                raise ValueError("CSV appears empty.")
            return rows
        if suffix in {".xlsx", ".xls"}:
            if openpyxl is None:
                raise ValueError("XLSX import requires 'openpyxl'. Install it or upload CSV.")
            wb = openpyxl.load_workbook(f, data_only=True)
            ws = wb.active
            headers = [str(c.value).strip() if c.value is not None else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]
            rows = []
            for r in ws.iter_rows(min_row=2, values_only=True):
                if all(v is None for v in r):
                    continue
                rows.append({headers[i]: r[i] for i in range(len(headers))})
            if not rows:
                raise ValueError("XLSX sheet appears empty.")
            return rows
        raise ValueError("Unsupported file type. Upload CSV or XLSX.")
    # JSON
    data = request.data
    if not isinstance(data, list):
        raise ValueError('Expected a JSON array or upload a file as "file".')
    return data


def import_employees(rows: List[Dict[str, Any]], *, dry_run: bool = False,
                     update_existing: bool = True, upsert_by_code: bool = True) -> Dict[str, Any]:
    """
    Bulk import employees.
    Upsert key = email; optionally also match by (company, employee_code) if upsert_by_code=True.
    Companies & Departments must already exist.
    """
    cleaned, companies_needed, dept_keys = _clean_and_normalize(rows)

    # Validate presence of required cols per row
    errors = _validate_rows(cleaned)
    if errors:
        return {"status": "invalid", "errors": errors}

    # Prefetch companies
    companies = {c.name: c for c in Company.objects.filter(name__in=companies_needed)}
    missing_companies = [n for n in companies_needed if n not in companies]
    if missing_companies:
        errs = []
        for row in cleaned:
            if row["company_name"] in missing_companies:
                errs.append({"row": row["__row"], "errors": {"Company Name": [f'Company "{row["company_name"]}" does not exist. Import companies first.']}})
        return {"status": "invalid", "errors": errs}

    # Prefetch departments (by company+name)
    dept_map: Dict[Tuple[str, str], Department] = {}
    if dept_keys:
        existing_depts = Department.objects.filter(
            company__name__in=[k[0] for k in dept_keys],
            name__in=[k[1] for k in dept_keys],
        ).select_related("company")
        dept_map = {(d.company.name, d.name): d for d in existing_depts}

    # Prefetch users by email
    emails = {r["email"] for r in cleaned if r["email"]}
    users_by_email = {u.email: u for u in User.objects.filter(email__in=emails)}

    # Prefetch employees by (company, employee_code) if desired
    empcode_keys = {(row["company_name"], row["employee_code"]) for row in cleaned
                    if upsert_by_code and row.get("employee_code")}
    employees_by_code: Dict[Tuple[str, str], Employee] = {}
    if empcode_keys:
        employees = Employee.objects.filter(
            company__name__in=[k[0] for k in empcode_keys],
            employee_code__in=[k[1] for k in empcode_keys],
        ).select_related("company", "user")
        employees_by_code = {(e.company.name if e.company else "", e.employee_code): e for e in employees}

    # Prepare create/update plans
    to_create: List[Dict[str, Any]] = []
    to_update: List[Tuple[Employee, Dict[str, Any]]] = []

    # Also keep track of usernames to avoid duplicates when creating Users
    taken_usernames = set(User.objects.filter(username__in=[_username_from_email(e) for e in emails]).values_list("username", flat=True))

    row_errors = []
    for row in cleaned:
        company = companies[row["company_name"]]
        # Department resolution (optional)
        dept_obj = None
        if row["department"]:
            dkey = (company.name, row["department"])
            dept_obj = dept_map.get(dkey)
            if not dept_obj:
                row_errors.append({"row": row["__row"], "errors": {"Department": [f'Department "{row["department"]}" not found in company "{company.name}".']}})
                continue

        # Upsert resolution
        user = users_by_email.get(row["email"])
        employee = None
        if user and hasattr(user, "employee_profile"):
            employee = user.employee_profile
        elif upsert_by_code and row.get("employee_code"):
            employee = employees_by_code.get((company.name, row["employee_code"]))

        payload_emp, payload_user = _build_payloads(row, company, dept_obj, taken_usernames)

        if dry_run:
            continue  # Only validating structure; real field validity is enforced in serializer at commit-time

        if employee:
            # Update existing employee + user
            to_update.append((employee, {"user": payload_user, **payload_emp}))
        else:
            # Create new employee + user
            to_create.append({"user": payload_user, **payload_emp})

    if row_errors:
        return {"status": "invalid", "errors": row_errors}

    if dry_run:
        return {"status": "ok", "validated_count": len(cleaned)}

    created = 0
    updated = 0

    # Write all in a transaction
    with transaction.atomic():
        # Create
        for data in to_create:
            ser = employee_serilized(data=data)
            if ser.is_valid():
                ser.save()
                created += 1
            else:
                # surface the first error with a pseudo-row index if desired
                raise ValueError(f"Validation failed while creating: {ser.errors}")

        # Update
        for instance, data in to_update:
            ser = employee_serilized(instance, data=data, partial=True)
            if ser.is_valid():
                ser.save()
                updated += 1
            else:
                raise ValueError(f"Validation failed while updating: {ser.errors}")

    return {"status": "imported", "created": created, "updated": updated}


# ------------------ Helpers ------------------

def _username_from_email(email: str) -> str:
    base = (email or "").split("@")[0][:150] or "user"
    # basic cleanup
    base = re.sub(r"[^a-zA-Z0-9_.-]+", "", base)
    return base or "user"

def _unique_username(suggested: str, taken: set) -> str:
    username = suggested
    n = 1
    while username in taken or User.objects.filter(username=username).exists():
        n += 1
        username = f"{suggested}-{n}"
    taken.add(username)
    return username

def _parse_date(value) -> Optional[str]:
    if value is None or value == "":
        return None
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    # try common formats
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # last resort: let serializer fail with a clear message
    return s

def _norm_choice(value, choices) -> Optional[str]:
    """Accept value or label (case-insensitive). Return stored value or None."""
    if value is None or value == "":
        return None
    s = str(value).strip()
    by_val = {str(v).lower(): v for v, _ in choices}
    by_lbl = {str(lbl).lower(): v for v, lbl in choices}
    key = s.lower()
    return by_val.get(key) or by_lbl.get(key) or s  # let serializer complain if unknown

def _clean_and_normalize(rows: List[Dict[str, Any]]):
    def pick(d, *keys):
        for k in keys:
            if k in d and d[k] not in [None, ""]:
                return str(d[k]).strip() if not isinstance(d[k], (date, datetime)) else d[k]
        return None

    cleaned = []
    companies_needed = set()
    dept_keys = set()

    for i, r in enumerate(rows, start=1):
        row = {
            "__row": i,
            "employee_code": pick(r, "Emp Code", "EmpCode", "employee_code"),
            "name": pick(r, "Name", "Full Name", "Employee Name"),
            "email": pick(r, "Email", "E-mail"),
            "country_code": pick(r, "CountryCode", "Country Code"),
            "phone": pick(r, "Phone Number", "Phone", "Mobile"),
            "department": pick(r, "Department", "Dept"),
            "position": pick(r, "Position"),
            "role": pick(r, "Role"),
            "managerial_level": pick(r, "Managerial Level", "ManagerialLevel"),
            "company_name": pick(r, "Company Name", "Company"),
            "status": pick(r, "Status"),
            "join_date": pick(r, "Join Date", "JoinDate", "Start Date"),
            "location": pick(r, "Location"),
            "branch": pick(r, "Branch"),
            "job_type": pick(r, "Job Type", "JobType"),
            "gender": pick(r, "Gender", "Sex"),
            # ignored: Profile Image, Direct Manager\Supervisor, Head of Dep
        }
        # Post-process
        row["join_date"] = _parse_date(row["join_date"])
        # normalize choices
        row["role"] = _norm_choice(row["role"], Role.choices)
        row["managerial_level"] = _norm_choice(row["managerial_level"], ManagerialLevel.choices)
        row["status"] = _norm_choice(row["status"], EmpStatus.choices)
        row["job_type"] = _norm_choice(row["job_type"], JobType.choices)
        row["branch"] = _norm_choice(row["branch"], BranchType.choices)
        row["gender"] = _norm_choice(row["gender"], Gender.choices)

        cleaned.append(row)

        if row["company_name"]:
            companies_needed.add(row["company_name"])
        if row["company_name"] and row["department"]:
            dept_keys.add((row["company_name"], row["department"]))

    return cleaned, companies_needed, dept_keys


def _validate_rows(cleaned: List[Dict[str, Any]]):
    errs = []
    for row in cleaned:
        local = {}
        if not row["name"]:
            local.setdefault("Name", []).append("This field is required.")
        if not row["email"]:
            local.setdefault("Email", []).append("This field is required.")
        if not row["company_name"]:
            local.setdefault("Company Name", []).append("This field is required.")
        if not row["managerial_level"]:
            local.setdefault("Managerial Level", []).append("This field is required.")
        if not row["status"]:
            local.setdefault("Status", []).append("This field is required.")
        if not row["join_date"]:
            local.setdefault("Join Date", []).append("This field is required.")
        if local:
            errs.append({"row": row["__row"], "errors": local})
    return errs


def _build_payloads(row, company: Company, dept: Optional[Department], taken_usernames: set):
    # User payload
    username = _unique_username(_username_from_email(row["email"]), taken_usernames)
    user_payload = {
        "username": username,
        "name": row["name"],
        "email": row["email"],
        "phone": row.get("phone") or "",
        "country_code": row.get("country_code") or "",
        "role": row.get("role"),
        "position": row.get("position") or "",
        # Optional: include gender if your serializer exposes it
        "gender": row.get("gender"),
        # No password provided: creates an unusable password; set later via invite
    }
    # Employee payload
    emp_payload = {
        "company_id": str(company.pk),
        "department_id": str(dept.pk) if dept else None,
        "employee_code": row.get("employee_code") or "",
        "managerial_level": row["managerial_level"],
        "status": row["status"],
        "join_date": row["join_date"],  # '%Y-%m-%d'
        "job_type": row.get("job_type"),
        "location": row.get("location") or "",
        "branch": row.get("branch"),
        "user_data": user_payload,
    }
    return emp_payload, user_payload
