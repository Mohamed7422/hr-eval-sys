from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from evaluation_app.models import Employee

def employee_list(request):
    qs = Employee.objects.all().order_by("id")
    return render(request, "employee_list.html", {"employees": qs})

@require_http_methods(["POST"])
def employee_create(request):
    name  = request.POST["name"]
    email = request.POST["email"]
    Employee.objects.create(name=name, email=email)
    # Return only the refreshed table HTML (partial) ─ HTMX swaps it in.
    qs = Employee.objects.all().order_by("id")
    return render(request, "partials/employee_rows.html", {"employees": qs})
