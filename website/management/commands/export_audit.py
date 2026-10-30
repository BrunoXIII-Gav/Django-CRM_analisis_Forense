import json
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_aware
from website.forensics.export import export_bundle


class Command(BaseCommand):
    help = "Export audit, Record and relevant admin history to JSON on stdout (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("--case-tag")
        parser.add_argument("--since")
        parser.add_argument("--until")
        parser.add_argument("--record-id", type=int)

    def handle(self, **options):
        filters = {key: options[key] for key in ("case_tag", "since", "until", "record_id")}
        for key in ("since", "until"):
            if filters[key]:
                try:
                    value = parse_datetime(filters[key])
                except ValueError:
                    value = None
                if value is None or not is_aware(value):
                    raise CommandError(f"{key} must be ISO-8601 with a timezone")
                filters[key] = value
        if filters["since"] and filters["until"] and filters["since"] > filters["until"]:
            raise CommandError("since must not be after until")
        self.stdout.write(json.dumps(export_bundle(**filters), cls=DjangoJSONEncoder, ensure_ascii=False))
