import argparse
from pathlib import Path
import shutil
from case_io import ROOT, case_path, custody, one_line, sha256, verify


def transfer(case, operator, destination, sender, recipient, reason, receipt):
    entries = verify(case, operator)
    for value in (sender, recipient, reason, receipt):
        one_line(value)
    destination = destination.resolve()
    if destination.is_relative_to(ROOT) or destination.is_relative_to(case) or case.is_relative_to(destination):
        raise ValueError("Transfer destination must be separate from the case")
    destination.mkdir(mode=0o700)  # a new destination is mandatory
    for entry in entries:
        target = destination / entry["name"]
        shutil.copyfile(case / "trabajo" / entry["name"], target)
        good = sha256(target) == entry["sha256"]
        custody(case, entry["evidence_id"], "TRANSFER", operator, target, entry["sha256"],
                "OK" if good else "MISMATCH", sender, recipient, reason, receipt)
        if not good:
            raise ValueError("Transfer hash mismatch; preserve discrepant target separately")
        target.chmod(0o400)
    verify(case, operator)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for arg in ("root", "case", "operator", "sender", "recipient", "reason", "receipt"):
        parser.add_argument("--" + arg, required=True)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    transfer(case_path(args.root, args.case), args.operator, args.destination, args.sender, args.recipient, args.reason, args.receipt)
