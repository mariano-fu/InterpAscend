import csv
from django.core.management.base import BaseCommand, CommandError
from terminology.models import GovernmentAgencyTerm  # make sure this model exists with fields english_name & spanish_name


class Command(BaseCommand):
    help = "Import government agencies glossary terms from a CSV into the GovernmentAgencyTerm model"

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help="Path to your CSV file (e.g. government_agencies_glossary.csv)"
        )

    def handle(self, *args, **options):
        path = options['csv_file']
        self.stdout.write(f"Loading government agency terms from {path}…")

        count = 0
        try:
            # Use utf-8-sig to strip any BOM
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

                    obj, created = GovernmentAgencyTerm.objects.update_or_create(
                        english_name=eng,
                        defaults={'spanish_name': spa},
                    )
                    verb = "Created" if created else "Updated"
                    self.stdout.write(f"  {verb}: {obj.english_name}")
                    count += 1

        except FileNotFoundError:
            raise CommandError(f"Could not find file at: {path}")

        self.stdout.write(self.style.SUCCESS(f"Imported {count} government agency terms."))
