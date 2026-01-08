from django.core.management.base import BaseCommand
from Bio import SeqIO
import os
from apps.plasmids.models import Plasmid, PlasmidCollection, PlasmidAnnotation

class Command(BaseCommand):
    help = 'Import GenBank files into database'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, help='Directory containing .gb files')
        parser.add_argument('--collection', type=str, default='Default Collection', help='Collection name')
        parser.add_argument('--public', action='store_true', help='Make collection public')

    def handle(self, *args, **options):
        directory = options['directory']
        collection_name = options['collection']
        is_public = options.get('public', False)
        
        # Créer ou récupérer la collection
        collection, created = PlasmidCollection.objects.get_or_create(
            name=collection_name,
            defaults={'is_public': is_public}
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Collection "{collection_name}" créée'))
        else:
            self.stdout.write(f'Collection "{collection_name}" existe déjà')
        
        # Parcourir les fichiers .gb
        count = 0
        for filename in os.listdir(directory):
            if filename.endswith('.gb') or filename.endswith('.genbank'):
                filepath = os.path.join(directory, filename)
                try:
                    self.import_genbank_file(filepath, collection)
                    count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error with {filename}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} plasmids into {collection_name}'))

    def import_genbank_file(self, filepath, collection):
        # Le nom du fichier sans extension est l'identifiant
        identifier = os.path.splitext(os.path.basename(filepath))[0]
        
        # Parser le fichier GenBank
        record = SeqIO.read(filepath, "genbank")
        
        # Créer le plasmide
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
        
        # Supprimer les anciennes annotations si mise à jour
        if not created:
            plasmid.annotations.all().delete()
        
        # Importer les annotations/features
        for feature in record.features:
            PlasmidAnnotation.objects.create(
                plasmid=plasmid,
                feature_type=feature.type,
                start=int(feature.location.start),
                end=int(feature.location.end),
                strand=feature.location.strand or 1,
                label=feature.qualifiers.get('label', [''])[0] or 
                      feature.qualifiers.get('gene', [''])[0] or '',
                qualifiers=dict(feature.qualifiers)
            )
        
        action = "Imported" if created else "Updated"
        self.stdout.write(f'  {action} {identifier}')