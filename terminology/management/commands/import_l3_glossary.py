import csv
from django.core.management.base import BaseCommand, CommandError
from terminology.models import L3Term


class Command(BaseCommand):
    help = "Import L3 glossary terms from a CSV into the L3Term model"

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help="Path to your CSV file (e.g. l3_glossary.csv)"
        )

    def handle(self, *args, **options):
        path = options['csv_file']
        self.stdout.write(f"Loading L3 terms from {path}…")

        count = 0
        try:
            # Strip BOM if present
            with open(path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                # Normalize header names
                reader.fieldnames = [h.strip() for h in reader.fieldnames]
                self.stdout.write(f"DEBUG: columns = {reader.fieldnames!r}")

                for row in reader:
                    eng = row.get('English Term', '').strip()
                    spa = row.get('Spanish Term', '').strip()

                    if not eng:
                        continue

                    obj, created = L3Term.objects.update_or_create(
                        english_term=eng,
                        defaults={
                            'spanish_term': spa,
                        }
                    )
                    verb = "Created" if created else "Updated"
                    self.stdout.write(f"  {verb}: {obj.english_term}")
                    count += 1

        except FileNotFoundError:
            raise CommandError(f"Could not find file at: {path}")

        self.stdout.write(self.style.SUCCESS(f"Imported {count} L3 terms."))
