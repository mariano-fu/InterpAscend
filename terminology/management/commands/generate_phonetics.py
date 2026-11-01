"""
Django management command to generate phonetic spellings for all terminology models.

This command processes all terminology models and generates IPA phonetic spellings
for both English and Spanish terms using the phonetic processing system.
"""

import logging
import time
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from terminology.models import (
    Medication, Diagnosis, MeSHTerm, FinancialTerm,
    GovernmentAgencyTerm, ImmigrationTerm, L2Term, L3Term,
    MedicareGlossaryTerm
)
from terminology.phonetics.processors import PhoneticProcessorFactory

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('phonetic_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate phonetic spellings for all terminology models'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            help='Process specific model only',
            choices=['medication', 'diagnosis', 'mesh', 'financial', 
                    'agency', 'immigration', 'l2', 'l3', 'medicare', 'all'],
            default='all'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for processing (default: 1000)'
        )
        parser.add_argument(
            '--resume',
            action='store_true',
            help='Resume processing (skip records with existing phonetics)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of existing phonetic data'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        self.setup_processors()
        
        # Model configuration: (model_class, english_field, spanish_field)
        model_map = {
            'medication': (Medication, 'english_name', 'spanish_name'),
            'diagnosis': (Diagnosis, 'english_name', 'spanish_name'),
            'mesh': (MeSHTerm, 'english_term', 'spanish_term'),
            'financial': (FinancialTerm, 'english_term', 'spanish_term'),
            'agency': (GovernmentAgencyTerm, 'english_name', 'spanish_name'),
            'immigration': (ImmigrationTerm, 'english_term', 'spanish_term'),
            'l2': (L2Term, 'english_term', 'spanish_term'),
            'l3': (L3Term, 'english_term', 'spanish_term'),
            'medicare': (MedicareGlossaryTerm, 'english_term', 'spanish_term'),
        }
        
        # Determine which models to process
        if options['model'] == 'all':
            models_to_process = model_map.items()
        else:
            if options['model'] not in model_map:
                raise CommandError(f"Unknown model: {options['model']}")
            models_to_process = [(options['model'], model_map[options['model']])]
        
        # Process each model
        total_processed = 0
        total_errors = 0
        start_time = time.time()
        
        self.stdout.write(
            self.style.SUCCESS(f"Starting phonetic generation...")
        )
        
        for model_name, (model_class, en_field, es_field) in models_to_process:
            self.stdout.write(f"\n{'-' * 50}")
            self.stdout.write(f"Processing {model_name}...")
            
            processed, errors = self.process_model(
                model_class, en_field, es_field, options
            )
            total_processed += processed
            total_errors += errors
        
        # Final summary
        elapsed_time = time.time() - start_time
        self.stdout.write(f"\n{'=' * 50}")
        self.stdout.write(
            self.style.SUCCESS(
                f"Completed! Processed: {total_processed}, "
                f"Errors: {total_errors}, Time: {elapsed_time:.2f}s"
            )
        )
        
        if total_errors > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"Check phonetic_generation.log for error details"
                )
            )
    
    def setup_processors(self):
        """Initialize phonetic processors."""
        try:
            self.en_processor = PhoneticProcessorFactory.get_english_processor()
            self.es_processor = PhoneticProcessorFactory.get_spanish_processor()
            self.stdout.write(
                self.style.SUCCESS("Phonetic processors initialized successfully")
            )
        except Exception as e:
            raise CommandError(f"Failed to initialize processors: {str(e)}")
    
    def process_model(self, model_class, en_field, es_field, options):
        """Process a single model."""
        batch_size = options['batch_size']
        resume = options['resume']
        dry_run = options['dry_run']
        force = options['force']
        
        # Build queryset
        queryset = model_class.objects.all()
        
        if resume and not force:
            # Skip records that already have phonetic data
            queryset = queryset.filter(
                Q(english_phonetic__isnull=True) | Q(english_phonetic='') |
                Q(spanish_phonetic__isnull=True) | Q(spanish_phonetic='')
            )
        
        total_count = queryset.count()
        processed_count = 0
        error_count = 0
        
        self.stdout.write(f"Total records to process: {total_count}")
        
        if total_count == 0:
            self.stdout.write("No records to process")
            return 0, 0
        
        # Process in batches
        for offset in range(0, total_count, batch_size):
            batch = list(queryset[offset:offset + batch_size])
            
            if dry_run:
                self.stdout.write(
                    f"Would process batch {offset//batch_size + 1}: "
                    f"{len(batch)} records"
                )
                processed_count += len(batch)
                continue
            
            # Process batch with transaction
            batch_processed, batch_errors = self.process_batch(
                batch, en_field, es_field, force
            )
            
            processed_count += batch_processed
            error_count += batch_errors
            
            # Progress update
            progress = (offset + len(batch)) / total_count * 100
            self.stdout.write(
                f"Progress: {progress:.1f}% "
                f"(Processed: {processed_count}, Errors: {error_count})"
            )
            
            # Brief pause to prevent overwhelming the system
            time.sleep(0.1)
        
        return processed_count, error_count
    
    def process_batch(self, batch, en_field, es_field, force):
        """Process a batch of records."""
        processed = 0
        errors = 0
        
        try:
            with transaction.atomic():
                for obj in batch:
                    try:
                        updated = False
                        
                        # Process English term
                        en_text = getattr(obj, en_field, None)
                        if en_text and (force or not obj.english_phonetic):
                            phonetic = self.en_processor.get_phonetic(en_text)
                            if phonetic:
                                obj.english_phonetic = phonetic
                                updated = True
                        
                        # Process Spanish term
                        es_text = getattr(obj, es_field, None)
                        if es_text and (force or not obj.spanish_phonetic):
                            phonetic = self.es_processor.get_phonetic(es_text)
                            if phonetic:
                                obj.spanish_phonetic = phonetic
                                updated = True
                        
                        # Save if updated
                        if updated:
                            obj.save(update_fields=['english_phonetic', 'spanish_phonetic'])
                            processed += 1
                        
                    except Exception as e:
                        errors += 1
                        logger.error(
                            f"Error processing {obj.__class__.__name__} {obj.pk}: {str(e)}"
                        )
                        
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            errors += len(batch)
        
        return processed, errors
    
    def get_model_stats(self, model_class):
        """Get statistics for a model."""
        total = model_class.objects.count()
        with_en_phonetic = model_class.objects.exclude(
            Q(english_phonetic__isnull=True) | Q(english_phonetic='')
        ).count()
        with_es_phonetic = model_class.objects.exclude(
            Q(spanish_phonetic__isnull=True) | Q(spanish_phonetic='')
        ).count()
        
        return {
            'total': total,
            'english_phonetic': with_en_phonetic,
            'spanish_phonetic': with_es_phonetic,
            'english_coverage': (with_en_phonetic / total * 100) if total > 0 else 0,
            'spanish_coverage': (with_es_phonetic / total * 100) if total > 0 else 0,
        }