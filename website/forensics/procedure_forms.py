from django import forms
from django.utils import timezone

from forensic_lab.job_queue import CASE_ID


class NewCaseForm(forms.Form):
    case_id = forms.RegexField(CASE_ID, max_length=100, label="Identificador del caso",
                               help_text="Identificador nuevo. Ejemplo: CASE-B-001.")
    operator = forms.CharField(max_length=150, label="Responsable de adquisición")
    scope = forms.CharField(max_length=1000, label="Alcance", widget=forms.Textarea(attrs={"rows": 3}),
                            help_text="Qué clientes y actividad se investigan. Usa una sola línea.")
    authorization = forms.CharField(max_length=1000, label="Autorización o referencia",
                                    help_text="Referencia real a la autorización académica o del propietario del laboratorio.")
    interval_start = forms.DateTimeField(label="Inicio del intervalo (UTC)")
    interval_end = forms.DateTimeField(label="Fin del intervalo (UTC)")
    writes_stopped = forms.BooleanField(label="He detenido nuevas modificaciones de clientes durante la adquisición.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name.startswith("interval_"):
                field.widget = forms.DateTimeInput(format="%Y-%m-%dT%H:%M:%S",
                                                    attrs={"type": "datetime-local", "step": "1"})
            field.widget.attrs["class"] = "form-check-input" if name == "writes_stopped" else "form-control"

    def clean(self):
        data = super().clean()
        start, end = data.get("interval_start"), data.get("interval_end")
        if start and end and start > end:
            self.add_error("interval_end", "El fin debe ser posterior o igual al inicio.")
        if end and end > timezone.now():
            self.add_error("interval_end", "El fin no puede estar en el futuro.")
        for key in ("operator", "scope", "authorization"):
            if key in data and any(ord(c) < 32 for c in data[key]):
                self.add_error(key, "Usa texto en una sola línea.")
        return data
