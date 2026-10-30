"""Generate lab secrets and an original-code checkout without changing branches."""
import io
from pathlib import Path
import secrets
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "5f80cd103e32825f4504fa5e96103d56cfbd968e"


def main():
    lab = ROOT / ".lab"
    lab.mkdir(exist_ok=True)
    env = lab / "lab.env"
    if not env.exists():
        values = {name: secrets.token_hex(32) for name in (
            "LAB_ROOT_PASSWORD", "LAB_MIGRATE_PASSWORD", "LAB_RUNTIME_PASSWORD",
            "LAB_READER_PASSWORD", "LAB_SECRET_KEY", "LAB_DEMO_PASSWORD")}
        with env.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write("".join(f"{key}={value}\n" for key, value in values.items()))
        env.chmod(0o600)
    else:
        values = dict(line.split("=", 1) for line in env.read_text().splitlines() if "=" in line)
    secret_dir = lab / "secrets"
    secret_dir.mkdir(exist_ok=True)
    reader = secret_dir / "reader.cnf"
    reader.write_text("[client]\nuser=crm_reader\npassword=" + values["LAB_READER_PASSWORD"] + "\n", encoding="utf-8")
    reader.chmod(0o600)
    checkout = lab / "baseline"
    if not checkout.exists():
        archive = subprocess.check_output(["git", "archive", "--format=tar", BASELINE], cwd=ROOT)
        checkout.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(checkout, filter="data")
        dockerfile = checkout / "Dockerfile"
        text = dockerfile.read_text().replace("RUN python manage.py collectstatic --noinput || true",
            "RUN DJANGO_SETTINGS_MODULE=dcrm.settings.prod python manage.py collectstatic --noinput")
        dockerfile.write_text(text, encoding="utf-8", newline="\n")
    # Build-only overlays pin the same validated packages in both environments.
    (checkout / "requirements.lock").write_bytes((ROOT / "requirements.lock").read_bytes())
    dockerfile = checkout / "Dockerfile"
    dockerfile.write_text(dockerfile.read_text().replace("COPY requirements.txt .", "COPY requirements.lock .")
                         .replace("-r requirements.txt", "-r requirements.lock"), encoding="utf-8", newline="\n")
    print("Local lab configuration ready; baseline=" + BASELINE)


if __name__ == "__main__":
    main()
