import csv
from django.core.management.base import BaseCommand
from terminology.models import Medication

class Command(BaseCommand):
    help = "Import medications from a CSV into the Medication model"

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help="Path to your CSV file (e.g. drugs_with_fda_desc_clean.csv)"
        )

    def handle(self, *args, **options):
        path = options['csv_file']
        self.stdout.write(f"Loading medications from {path}…")
        count = 0

        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                obj, created = Medication.objects.update_or_create(
                    english_name=row['english_name'],
                    defaults={
                        'spanish_name':    row.get('spanish_name', ''),
                    }
                )
                count += 1
                verb = "Created" if created else "Updated"
                self.stdout.write(f"  {verb}: {obj.english_name}")

        self.stdout.write(self.style.SUCCESS(f"Imported {count} medications."))
