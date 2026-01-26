from django.core.management.base import BaseCommand
from Bio import SeqIO
import os

from apps.plasmids.models import Plasmid, PlasmidCollection, PlasmidAnnotation

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

    # Supprimer les anciennes annotations si elles existent
    if not created:
        plasmid.annotations.all().delete()

    # Dictionnaire pour suivre les labels existants
    label_counts = {}

    for feature in record.features:
        # Récupérer le label ou le nom du gène
        raw_label = (
            feature.qualifiers.get('label', [''])[0]
            or feature.qualifiers.get('gene', [''])[0]
            or ''
        ).strip()

        # Toujours garder le label exact, sans suffixes
        label = raw_label

        # Créer l'annotation
        PlasmidAnnotation.objects.create(
            plasmid=plasmid,
            feature_type=feature.type,
            start=int(feature.location.start),
            end=int(feature.location.end),
            strand=feature.location.strand or 1,
            label=label,
            qualifiers=dict(feature.qualifiers)
        )

    action = "Imported" if created else "Updated"
    self.stdout.write(f'  {action} {identifier}')
