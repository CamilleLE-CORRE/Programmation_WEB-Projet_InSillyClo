from django.core.management.base import BaseCommand
from Bio import SeqIO
import os

from apps.plasmids.models import Plasmid, PlasmidCollection, PlasmidAnnotation


class Command(BaseCommand):
    help = 'Import GenBank files into database'

    def add_arguments(self, parser):
        parser.add_argument(
            'directory',
            type=str,
            help='Directory containing .gb or .genbank files'
        )
        parser.add_argument(
            '--collection',
            type=str,
            help='Collection name (default: directory name)'
        )
        parser.add_argument(
            '--public',
            action='store_true',
            help='Make collection public'
        )

    def handle(self, *args, **options):
        directory = options['directory']
        is_public = options.get('public', False)

        if not os.path.isdir(directory):
            self.stderr.write(self.style.ERROR(f'"{directory}" is not a valid directory'))
            return

        # Nom de la collection :
        # - argument --collection si fourni
        # - sinon nom du dossier
        collection_name = options.get('collection') or os.path.basename(
            os.path.normpath(directory)
        )

        # Create or get collection
        collection, created = PlasmidCollection.objects.get_or_create(
            name=collection_name,
            defaults={'is_public': is_public}
        )

        if created:
            self.stdout.write(self.style.SUCCESS(
                f'Collection "{collection_name}" créée'
            ))
        else:
            self.stdout.write(
                f'Collection "{collection_name}" existe déjà'
            )

        # Browse GenBank files
        count = 0
        for filename in os.listdir(directory):
            if filename.endswith(('.gb', '.genbank')):
                filepath = os.path.join(directory, filename)
                try:
                    self.import_genbank_file(filepath, collection)
                    count += 1
                except Exception as e:
                    self.stderr.write(
                        self.style.ERROR(f'Error with {filename}: {str(e)}')
                    )

        self.stdout.write(self.style.SUCCESS(
            f'Successfully imported {count} plasmids into "{collection_name}"'
        ))

    def import_genbank_file(self, filepath, collection):
        identifier = os.path.splitext(os.path.basename(filepath))[0]

        record = SeqIO.read(filepath, "genbank")

        plasmid, created = Plasmid.objects.update_or_create(
            identifier=identifier,
            collection=collection,
            defaults={
                'name': record.name or identifier,
                'sequence': str(record.seq),
                'length': len(record.seq),
                'description': record.description,
                'genbank_data': {
                    'topology': record.annotations.get('topology', 'linear'),
                    'molecule_type': record.annotations.get('molecule_type', ''),
                    'date': record.annotations.get('date', ''),
                }
            }
        )

        if not created:
            plasmid.annotations.all().delete()

        for feature in record.features:
            PlasmidAnnotation.objects.create(
                plasmid=plasmid,
                feature_type=feature.type,
                start=int(feature.location.start),
                end=int(feature.location.end),
                strand=feature.location.strand or 1,
                label=(
                    feature.qualifiers.get('label', [''])[0]
                    or feature.qualifiers.get('gene', [''])[0]
                    or ''
                ),
                qualifiers=dict(feature.qualifiers)
            )

        action = "Imported" if created else "Updated"
        self.stdout.write(f'  {action} {identifier}')
