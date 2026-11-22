from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from reconcile.importer import import_all, summary_line
from reconcile.service import run_comparison


class Command(BaseCommand):
    help = "Import locations.csv, system_a.csv and system_b.csv, then find the disagreements."

    def add_arguments(self, parser):
        parser.add_argument("--data-dir", default=str(Path(settings.BASE_DIR) / "data"))

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])
        for name in ("locations.csv", "system_a.csv", "system_b.csv"):
            if not (data_dir / name).exists():
                raise CommandError(f"Missing {data_dir / name}")

        stats = import_all(data_dir)
        for line in stats["problems"]:
            self.stdout.write(self.style.WARNING("  note: " + line))
        self.stdout.write(summary_line(stats))

        if stats["a_read"] != stats["a_in_db"] or stats["b_read"] != stats["b_in_db"]:
            raise CommandError("Rows were lost: 'read' and 'in database' differ. Check for repeated IDs.")

        saved = run_comparison()
        self.stdout.write(self.style.SUCCESS(f"Comparison done: {saved} disagreements stored."))