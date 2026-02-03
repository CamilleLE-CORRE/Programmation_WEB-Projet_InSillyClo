from django.db import models
from django.conf import settings  

class CampaignTemplate(models.Model):
    """
    Modèle pour stocker les templates de campagne "officiels" (fichiers Excel types).
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name="Nom du Template")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # C'est ici qu'on stocke le fichier Excel du template
    file = models.FileField(
        upload_to='campaign_templates/', 
        verbose_name="Fichier Excel",
        help_text="Le fichier modèle .xlsx ou .csv"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Campaign(models.Model):
    """
    Modèle représentant une simulation lancée par un utilisateur.
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name="Nom de la Campagne")
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Référence propre à ton modèle User personnalisé
        on_delete=models.CASCADE,
        related_name='campaigns'
    )

    # 1. Le lien vers le Template officiel (Optionnel)
    # null=True : permet de stocker NULL dans la BDD
    # blank=True : permet de laisser le champ vide dans l'admin/formulaire
    template = models.ForeignKey(
        CampaignTemplate,
        on_delete=models.SET_NULL, # Si le template est supprimé, on garde la campagne
        related_name='campaigns',
        null=True,
        blank=True,
        verbose_name="Template utilisé (Optionnel)"
    )

    # 2. Le fichier Excel spécifique utilisé pour CETTE simulation
    # (Indispensable pour l'historique si l'utilisateur a uploadé son propre fichier)
    input_file = models.FileField(
        upload_to='campaign_inputs/%Y/%m/', # Range par année/mois
        null=True,
        blank=True,
        verbose_name="Fichier d'entrée utilisé"
    )

    # 3. L'Identifiant unique de la simulation (UUID)
    # Permet de retrouver le dossier physique dans media/simulations/
    run_id = models.CharField(
        max_length=50, 
        unique=True, 
        null=True, 
        blank=True,
        verbose_name="ID d'exécution (Dossier)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # Relations avec les Plasmides
    produced_plasmids = models.ManyToManyField(
        'plasmids.Plasmid',
        related_name='campaigns',
        blank=True
    )

    collections_used = models.ManyToManyField(
        'plasmids.PlasmidCollection',
        blank=True,
        related_name='campaigns'
    )

    # Champs JSON pour stocker les données techniques
    parameters = models.JSONField(default=dict, blank=True, verbose_name="Paramètres de simulation")
    results_data = models.JSONField(default=dict, blank=True, verbose_name="Données de résultats")
    output_files = models.JSONField(default=dict, blank=True, verbose_name="Liste des fichiers générés")

    class Meta:
        ordering = ('-created_at',) # Trie du plus récent au plus ancien
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"

    def __str__(self):
        date_str = self.created_at.strftime('%d/%m/%Y')
        return f"{self.name} - {date_str}"


class CampaignResult(models.Model):
    """
    Modèle optionnel si tu veux stocker des résultats détaillés séparément.
    (Peut être redondant avec Campaign.results_data, mais je le laisse pour compatibilité)
    """
    id = models.AutoField(primary_key=True)
    campaign = models.ForeignKey(
        Campaign, 
        on_delete=models.CASCADE,
        related_name='results'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='campaign_results'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('id', 'created_at')
        verbose_name = "Campaign Result"
        verbose_name_plural = "Campaign Results"

    def __str__(self):
        return f"Result of {self.campaign.name}"