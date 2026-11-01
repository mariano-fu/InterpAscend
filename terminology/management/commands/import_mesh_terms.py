

import csv
from django.core.management.base import BaseCommand
from terminology.models import MeSHTerm  # ← change this line

class Command(BaseCommand):
    help = "Import MeSH terms (Term_EN, Term_ES) into MeSHTerm"

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help="Path to your MeSH CSV (must have 'Term_EN' and 'Term_ES')"
        )

    def handle(self, *args, **options):
        path = options['csv_file']
        self.stdout.write(f"Importing MeSH terms from {path!r}…")
        count = 0

        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            missing = []
            for col in ('Term_EN', 'Term_ES'):
                if col not in reader.fieldnames:
                    missing.append(col)
            if missing:
                self.stderr.write(self.style.ERROR(
                    f"CSV is missing column(s): {', '.join(missing)}"
                ))
                return

            for row in reader:
                eng = row['Term_EN'].strip()
                spa = row['Term_ES'].strip()
                if not eng:
                    continue

                obj, created = MeSHTerm.objects.update_or_create(
                    english_term=eng,
                    defaults={'spanish_term': spa}
                )
                verb = "Created" if created else "Updated"
                self.stdout.write(f"  {verb}: {eng}")
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {count} MeSH terms."))
