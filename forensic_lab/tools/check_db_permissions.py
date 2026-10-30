"""Run with the runtime account. Statements affect no rows, but MySQL checks privileges."""
import os
import sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dcrm.settings.lab")
import django
django.setup()
from django.db import connection, DatabaseError

if connection.vendor != "mysql":
    raise RuntimeError("Privilege validation requires MySQL")
with connection.cursor() as cursor:
    cursor.execute("SELECT CURRENT_USER()")
    account = cursor.fetchone()[0]
    if not account.startswith("crm_runtime@"):
        raise RuntimeError("Expected runtime account")
    cursor.execute("SELECT COUNT(*) FROM website_auditevent")
    for sql in ("UPDATE website_auditevent SET username=username WHERE 1=0", "DELETE FROM website_auditevent WHERE 1=0"):
        try:
            cursor.execute(sql)
        except DatabaseError as error:
            if error.args[0] != 1142:
                raise
        else:
            raise RuntimeError("Runtime account unexpectedly has mutation permission")
print("MySQL runtime SELECT allowed; AuditEvent UPDATE and DELETE denied (1142)")
