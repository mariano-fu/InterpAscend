# your_app/management/commands/import_medicare_glossary.py

import csv
from django.core.management.base import BaseCommand
from terminology.models import MedicareGlossaryTerm  # ← change to your model

class Command(BaseCommand):
    help = "Import Medicare glossary terms (English Term, Spanish Term) into MedicareGlossaryTerm"

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help="Path to your Medicare glossary CSV (must have 'English Term' and 'Spanish Term')"
        )

    def handle(self, *args, **options):
        path = options['csv_file']
        self.stdout.write(f"Importing Medicare glossary terms from {path!r}…")
        count = 0

        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            missing = [col for col in ('English Term', 'Spanish Term') if col not in reader.fieldnames]
            if missing:
                self.stderr.write(self.style.ERROR(
                    f"CSV is missing column(s): {', '.join(missing)}"
                ))
                return

            for row in reader:
                eng = row['English Term'].strip()
                spa = row['Spanish Term'].strip()
                if not eng:
                    continue

                obj, created = MedicareGlossaryTerm.objects.update_or_create(
                    english_term=eng,
                    defaults={'spanish_term': spa}
                )
                verb = "Created" if created else "Updated"
                self.stdout.write(f"  {verb}: {eng}")
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {count} Medicare glossary terms."))
