"""
Management command to create demo categories and decks with sample flashcards.

This command creates the logical category mappings and populates them with
sample decks using existing terminology data from the InterpAscend database.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from srs.models import Category, Deck, DeckItem
from terminology.models import (
    Medication, Diagnosis, MeSHTerm, FinancialTerm, 
    GovernmentAgencyTerm, ImmigrationTerm, L2Term, L3Term, MedicareGlossaryTerm
)


class Command(BaseCommand):
    help = 'Create demo categories and decks with sample flashcards from existing terminology'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-user',
            type=str,
            default='admin',
            help='Username of the admin user to create decks (default: admin)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Maximum number of cards per deck (default: 20)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing SRS data before creating demo data'
        )

    def handle(self, *args, **options):
        admin_username = options['admin_user']
        card_limit = options['limit']
        clear_existing = options['clear']

        try:
            admin_user = User.objects.get(username=admin_username)
        except User.DoesNotExist:
            raise CommandError(f'Admin user "{admin_username}" does not exist. Create it first or specify a different user.')

        if clear_existing:
            self.stdout.write('Clearing existing SRS data...')
            with transaction.atomic():
                DeckItem.objects.all().delete()
                Deck.objects.all().delete()
                Category.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing SRS data cleared.'))

        self.stdout.write('Creating demo categories and decks...')

        # Define category configurations
        categories_config = [
            {
                'name': 'Medical',
                'slug': 'medical',
                'description': 'Medical terminology including medications, diagnoses, and MeSH terms',
                'icon_class': 'fas fa-stethoscope',
                'color_class': 'primary',
                'display_order': 1,
                'decks': [
                    {
                        'name': 'Essential Medications',
                        'description': 'Common medications used in medical practice',
                        'model': Medication,
                        'fields': ('english_name', 'spanish_name')
                    },
                    {
                        'name': 'Common Diagnoses',
                        'description': 'Frequently encountered medical diagnoses',
                        'model': Diagnosis,
                        'fields': ('english_name', 'spanish_name')
                    },
                    {
                        'name': 'Medical Terms (MeSH)',
                        'description': 'Medical Subject Headings terminology',
                        'model': MeSHTerm,
                        'fields': ('english_term', 'spanish_term')
                    }
                ]
            },
            {
                'name': 'Financial',
                'slug': 'financial',
                'description': 'Financial and banking terminology for interpreters',
                'icon_class': 'fas fa-dollar-sign',
                'color_class': 'success',
                'display_order': 2,
                'decks': [
                    {
                        'name': 'Banking & Finance',
                        'description': 'Essential financial terminology',
                        'model': FinancialTerm,
                        'fields': ('english_term', 'spanish_term')
                    }
                ]
            },
            {
                'name': 'Immigration',
                'slug': 'immigration',
                'description': 'Immigration and legal terminology',
                'icon_class': 'fas fa-passport',
                'color_class': 'warning',
                'display_order': 3,
                'decks': [
                    {
                        'name': 'Immigration Law',
                        'description': 'Immigration legal terminology',
                        'model': ImmigrationTerm,
                        'fields': ('english_term', 'spanish_term')
                    }
                ]
            },
            {
                'name': 'Government',
                'slug': 'government',
                'description': 'Government agencies and official terminology',
                'icon_class': 'fas fa-university',
                'color_class': 'info',
                'display_order': 4,
                'decks': [
                    {
                        'name': 'Government Agencies',
                        'description': 'Names and terminology of government agencies',
                        'model': GovernmentAgencyTerm,
                        'fields': ('english_name', 'spanish_name')
                    }
                ]
            },
            {
                'name': 'Language Learning',
                'slug': 'language-learning',
                'description': 'Language proficiency levels and educational terminology',
                'icon_class': 'fas fa-graduation-cap',
                'color_class': 'secondary',
                'display_order': 5,
                'decks': [
                    {
                        'name': 'Interpreter Basics 1',
                        'description': 'Fundamental interpreter terminology and concepts',
                        'model': L2Term,
                        'fields': ('english_term', 'spanish_term')
                    },
                    {
                        'name': 'Interpreter Basics 2',
                        'description': 'Advanced interpreter terminology and concepts',
                        'model': L3Term,
                        'fields': ('english_term', 'spanish_term')
                    }
                ]
            },
            {
                'name': 'Healthcare',
                'slug': 'healthcare',
                'description': 'Medicare and healthcare system terminology',
                'icon_class': 'fas fa-heartbeat',
                'color_class': 'danger',
                'display_order': 6,
                'decks': [
                    {
                        'name': 'Medicare Terms',
                        'description': 'Medicare and healthcare terminology',
                        'model': MedicareGlossaryTerm,
                        'fields': ('english_term', 'spanish_term')
                    }
                ]
            }
        ]

        created_categories = 0
        created_decks = 0
        created_cards = 0

        with transaction.atomic():
            for cat_config in categories_config:
                # Create or get category
                category, created = Category.objects.get_or_create(
                    slug=cat_config['slug'],
                    defaults={
                        'name': cat_config['name'],
                        'description': cat_config['description'],
                        'icon_class': cat_config['icon_class'],
                        'color_class': cat_config['color_class'],
                        'display_order': cat_config['display_order'],
                        'is_active': True
                    }
                )
                
                if created:
                    created_categories += 1
                    self.stdout.write(f'Created category: {category.name}')
                else:
                    self.stdout.write(f'Category already exists: {category.name}')

                # Create decks for this category
                for deck_config in cat_config['decks']:
                    model_class = deck_config['model']
                    english_field, spanish_field = deck_config['fields']
                    
                    # Check if we have data for this model
                    total_terms = model_class.objects.count()
                    if total_terms == 0:
                        self.stdout.write(
                            self.style.WARNING(
                                f'No {model_class.__name__} data found. Skipping deck: {deck_config["name"]}'
                            )
                        )
                        continue

                    # Create or get deck
                    deck, created = Deck.objects.get_or_create(
                        name=deck_config['name'],
                        category=category,
                        defaults={
                            'description': deck_config['description'],
                            'created_by': admin_user,
                            'is_public': True,
                            'is_active': True
                        }
                    )

                    if created:
                        created_decks += 1
                        self.stdout.write(f'  Created deck: {deck.name}')
                    else:
                        self.stdout.write(f'  Deck already exists: {deck.name}')
                        # Skip creating cards if deck already exists
                        continue

                    # Get sample terms for this deck
                    terms = model_class.objects.all()[:card_limit]
                    content_type = ContentType.objects.get_for_model(model_class)

                    # Create deck items (flashcards)
                    deck_items_to_create = []
                    for term in terms:
                        # Check if both English and Spanish terms exist
                        english_text = getattr(term, english_field, None)
                        spanish_text = getattr(term, spanish_field, None)
                        
                        if not english_text or not spanish_text:
                            continue  # Skip terms without both translations

                        # Create EN->ES direction
                        deck_items_to_create.append(
                            DeckItem(
                                deck=deck,
                                content_type=content_type,
                                object_id=term.id,
                                direction='EN_TO_ES',
                                is_active=True
                            )
                        )

                        # Create ES->EN direction
                        deck_items_to_create.append(
                            DeckItem(
                                deck=deck,
                                content_type=content_type,
                                object_id=term.id,
                                direction='ES_TO_EN',
                                is_active=True
                            )
                        )

                    if deck_items_to_create:
                        DeckItem.objects.bulk_create(deck_items_to_create, ignore_conflicts=True)
                        created_cards += len(deck_items_to_create)
                        self.stdout.write(
                            f'    Created {len(deck_items_to_create)} flashcards from {len(terms)} terms'
                        )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nDemo data creation completed!\n'
                f'Categories created: {created_categories}\n'
                f'Decks created: {created_decks}\n'
                f'Flashcards created: {created_cards}\n'
            )
        )

        if created_categories > 0 or created_decks > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'You can now visit /srs/categories/ to start studying!'
                )
            )