import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AddRecordForm, SignUpForm
from .models import Record

logger = logging.getLogger(__name__)


def home(request):
    """Display records for authenticated users, or the login form."""
    records = Record.objects.all()

    # Search functionality
    query = request.GET.get("q", "")
    if query:
        records = records.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(city__icontains=query)
        )

    # Pagination
    paginator = Paginator(records, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Handle login POST
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "You have been logged in!")
            logger.info("User '%s' logged in.", username)
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password. Please try again.")
            logger.warning("Failed login attempt for username '%s'.", username)
            return redirect("home")

    return render(
        request, "website/home.html", {"records": page_obj, "query": query}
    )


def logout_user(request):
    """Log out the current user."""
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")


def register_user(request):
    """Register a new user account."""
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password1"]
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, "You have successfully registered!")
            logger.info("New user registered: '%s'.", username)
            return redirect("home")
    else:
        form = SignUpForm()

    return render(request, "website/register.html", {"form": form})


@login_required
def customer_record(request, pk):
    """View a single customer record."""
    record = get_object_or_404(Record, id=pk)
    return render(request, "website/record.html", {"customer_record": record})


@login_required
@require_POST
def delete_record(request, pk):
    """Delete a customer record (POST only)."""
    record = get_object_or_404(Record, id=pk)
    record.delete()
    messages.success(request, "Record deleted successfully.")
    logger.info("Record #%s deleted by user '%s'.", pk, request.user.username)
    return redirect("home")


@login_required
def add_record(request):
    """Add a new customer record."""
    form = AddRecordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        new_record = form.save()
        messages.success(request, "Record added.")
        logger.info("Record #%s created by user '%s'.", new_record.pk, request.user.username)
        return redirect("home")
    return render(request, "website/add_record.html", {"form": form})


@login_required
def update_record(request, pk):
    """Update an existing customer record."""
    current_record = get_object_or_404(Record, id=pk)
    form = AddRecordForm(request.POST or None, instance=current_record)
    if form.is_valid():
        form.save()
        messages.success(request, "Record has been updated!")
        logger.info("Record #%s updated by user '%s'.", pk, request.user.username)
        return redirect("home")
    return render(request, "website/update_record.html", {"form": form})