import csv
from django.core.management.base import BaseCommand
from terminology.models import Diagnosis

class Command(BaseCommand):
    help = "Import diagnoses from a CSV into the Diagnosis model"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', help="Path to your diagnoses CSV")

    def handle(self, *args, **opts):
        path = opts['csv_file']
        self.stdout.write(f"Importing diagnoses from {path!r}…")
        count = 0
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                obj, created = Diagnosis.objects.update_or_create(
                    english_name=row['english_name'],
                    defaults={'spanish_name': row.get('spanish_name', '')}
                )
                verb = "Created" if created else "Updated"
                self.stdout.write(f"  {verb}: {obj.english_name}")
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} diagnoses."))
