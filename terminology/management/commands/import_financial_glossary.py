import csv
from django.core.management.base import BaseCommand, CommandError
from terminology.models import FinancialTerm

class Command(BaseCommand):
    help = "Import financial glossary terms from a CSV into the FinancialTerm model"

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help="Path to your CSV file (e.g. finance_glossary.csv)"
        )

    def handle(self, *args, **options):
        path = options['csv_file']
        self.stdout.write(f"Loading financial terms from {path}…")

        count = 0
        try:
            # Use utf-8-sig to strip any BOM if present
            with open(path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                # Normalize header names (strip whitespace)
                reader.fieldnames = [h.strip() for h in reader.fieldnames]
                self.stdout.write(f"DEBUG: columns = {reader.fieldnames!r}")

                for row in reader:
                    # Strip whitespace from both key and value just in case
                    eng = row.get('English Term', '').strip()
                    spa = row.get('Spanish Term', '').strip()
                    if not eng:
                        continue

                    obj, created = FinancialTerm.objects.update_or_create(
                        english_term=eng,
                        defaults={'spanish_term': spa},
                    )
                    verb = "Created" if created else "Updated"
                    self.stdout.write(f"  {verb}: {obj.english_term}")
                    count += 1

        except FileNotFoundError:
            raise CommandError(f"Could not find file at: {path}")

        self.stdout.write(self.style.SUCCESS(f"Imported {count} financial terms."))
