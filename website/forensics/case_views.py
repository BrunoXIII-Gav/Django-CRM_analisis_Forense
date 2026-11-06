"""Read-only case viewer plus a permission-checked queue submission interface."""
from datetime import timezone as datetime_timezone

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from forensic_lab.job_queue import JobQueue, QueueError
from website.models import AuditEvent

from .cases import CaseReader, list_cases
from .procedure_forms import NewCaseForm

TABS = (("procedimiento", "Procedimiento"), ("evidencias", "Evidencias"),
        ("reconstruccion", "Reconstrucción"), ("informe", "Informe"))


def check_access(user):
    if not user.is_staff or not user.has_perm("website.view_auditevent"):
        raise PermissionDenied


def runner_context(user):
    enabled = settings.FORENSIC_RUNNER_ENABLED
    queue = JobQueue(settings.FORENSIC_JOBS_ROOT)
    return {"runner_enabled": enabled, "runner_ready": enabled and queue.health(),
            "can_run": user.is_superuser, "workflows": queue.list()[:20] if enabled else []}


def present_workflow(job):
    active = any(s["state"] in ("queued", "running") for s in job["steps"])
    failed = any(s["state"] == "failed" for s in job["steps"])
    labels = {"pending": "Pendiente", "queued": "En cola", "running": "En ejecución",
              "succeeded": "Terminada", "failed": "Fallida"}
    for index, step in enumerate(job["steps"]):
        step["state_label"] = labels.get(step["state"], "Sin información")
        step["can_start"] = (not active and not failed and step["state"] == "pending" and
                             all(s["state"] == "succeeded" for s in job["steps"][:index]))
    job["active"], job["failed"] = active, failed
    job["complete"] = all(s["state"] == "succeeded" for s in job["steps"])
    return job


@login_required
@never_cache
@require_GET
def case_list(request):
    check_access(request.user)
    cases, root_available = list_cases()
    page = Paginator(cases, 20).get_page(request.GET.get("page"))
    return render(request, "website/forensics/case_list.html", {
        "page_obj": page, "root_available": root_available, **runner_context(request.user),
    })


@login_required
@never_cache
@require_GET
def case_detail(request, case_id):
    check_access(request.user)
    try:
        case = CaseReader(settings.FORENSIC_CASES_ROOT, case_id).load()
    except (FileNotFoundError, OSError, ValueError):
        raise Http404("Expediente no disponible")
    tab = request.GET.get("tab", "procedimiento")
    if tab not in dict(TABS):
        tab = "procedimiento"
    query = request.GET.get("q", "")[:200].strip()
    events = case["events"]
    if query:
        events = [e for e in events if query.casefold() in " ".join(
            e[key] for key in ("event_id", "actor_username", "record_id", "channel", "session_correlation_id", "request_id")
        ).casefold()]
    page = Paginator(events, 25).get_page(request.GET.get("page"))
    return render(request, "website/forensics/case_detail.html", {
        "case": case, "tab": tab, "tabs": TABS, "events_page": page, "query": query,
    })


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def new_case(request):
    check_access(request.user)
    if not request.user.is_superuser:
        raise PermissionDenied
    context = runner_context(request.user)
    initial = {"operator": request.user.get_full_name() or request.user.get_username(),
               "interval_end": timezone.now(),
               "interval_start": AuditEvent.objects.order_by("timestamp").values_list("timestamp", flat=True).first() or timezone.now()}
    form = NewCaseForm(request.POST if request.method == "POST" else None, initial=initial)
    if request.method == "POST" and form.is_valid():
        if not context["runner_enabled"] or not context["runner_ready"]:
            form.add_error(None, "El ejecutor no está disponible. Inicia el servicio forensic-worker y vuelve a intentarlo.")
        else:
            spec = dict(form.cleaned_data, requested_by=request.user.get_username())
            for key in ("interval_start", "interval_end"):
                spec[key] = spec[key].astimezone(datetime_timezone.utc).isoformat()
            try:
                job = JobQueue(settings.FORENSIC_JOBS_ROOT).create(spec, settings.FORENSIC_CASES_ROOT)
            except (QueueError, OSError):
                form.add_error(None, "No se pudo abrir el caso. Comprueba que el identificador sea nuevo y que la cola esté disponible.")
            else:
                return redirect("forensic_workflow", case_id=job["case_id"])
    return render(request, "website/forensics/new_case.html", {"form": form, **context})


@login_required
@never_cache
@require_GET
def workflow_detail(request, case_id):
    check_access(request.user)
    if not settings.FORENSIC_RUNNER_ENABLED:
        raise Http404
    try:
        job = present_workflow(JobQueue(settings.FORENSIC_JOBS_ROOT).get(case_id))
    except (QueueError, OSError):
        raise Http404("Corrida no disponible")
    return render(request, "website/forensics/workflow.html", {"job": job, **runner_context(request.user)})


@login_required
@never_cache
@require_POST
def start_phase(request, case_id, phase):
    check_access(request.user)
    if not request.user.is_superuser:
        raise PermissionDenied
    queue = JobQueue(settings.FORENSIC_JOBS_ROOT)
    if not settings.FORENSIC_RUNNER_ENABLED or not queue.health():
        messages.error(request, "El ejecutor no está disponible. La fase no se envió.")
    else:
        try:
            queue.enqueue(case_id, phase, request.user.get_username())
        except QueueError as error:
            messages.error(request, str(error))
        except OSError:
            messages.error(request, "No se pudo guardar la solicitud de ejecución.")
        else:
            messages.success(request, "Fase enviada al ejecutor.")
    return redirect("forensic_workflow", case_id=case_id)
