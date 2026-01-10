# Fonctionnalités optionnelles (choisies)

> Statuts utilisés : **Prévu** / **En cours** / **Fait** / **Abandonnée**

## 1) Templates de campagne (avancé)
### 1.1 Import + mise à jour du template depuis un fichier XLSX
- Permettre de **télécharger un template (xlsx)**, le modifier (ajout/retrait de colonnes de plasmides),
  puis **mettre à jour la modélisation en base** à partir du fichier xlsx.
- **Statut : En cours**
- **Critère d’acceptation :**
  - Import d’un xlsx valide => mise à jour des colonnes en base (ajout/suppression) sans casser les campagnes existantes.
- **Risque :** parsing xlsx + gestion des migrations logiques.

---

## 2) Avantage utilisateur connecté (avancé)
### 2.1 Collections : sauvegarde + création “de novo”
- Deux possibilités : **sauvegarder une collection fournie** (archive) et **créer une collection de novo** via l’interface.
- **Statut : En cours**
- **Critère d’acceptation :**
  - Un utilisateur peut créer/nommer une collection, lister ses collections, et réutiliser une collection existante.

### 2.2 Simulation : sélection multi-sources + duplication
- Lors d’une simulation, permettre de choisir :
  - une ou plusieurs collections personnelles,
  - des collections publiques,
  - et/ou fournir une nouvelle archive (nouvelle collection temporaire).
- Étudier et **informer l’utilisateur** en cas de duplication (même séquence dans plusieurs collections).
- **Statut : En cours**
- **Critère d’acceptation :**
  - UI permettant la sélection multi-collections + message d’avertissement en cas de duplicats détectés.

### 2.3 Correspondences persistantes + gestion des conflits
- Un utilisateur connecté conserve ses **tables de correspondance** (identifiant <-> nom <-> type optionnel).
- Gérer les **conflits** (même nom -> identifiants différents / même identifiant -> noms différents),
  en tenant compte qu’une même séquence peut exister sous des identifiants différents.
- **Statut : **En cours**
- **Critère d’acceptation :**
  - Détection de conflit + message explicite (et règle de résolution documentée).

---

## 3) Gestion d’équipe (option)
### 3.1 Ressources partagées au niveau équipe
- Attacher des **collections** et **tables de correspondance** à une équipe.
- Les membres peuvent les utiliser, mais **seule la cheffe d’équipe** choisit quelles ressources sont attachées.
- **Seul le propriétaire** d’une ressource peut la modifier.
- **Statut : Prévu**
- **Critère d’acceptation :**
  - Une équipe a une page “Ressources partagées” + permissions appliquées.

### 3.2 Transfert de propriété d’équipe
- Permettre le transfert de propriété d’une équipe à un membre.
- **Statut : Prévu**
- **Critère d’acceptation :**
  - Action disponible uniquement au propriétaire actuel + historique (qui a transféré à qui).

---

## 4) Recherche plasmides (option)
### 4.1 Autocomplétion (noms / types / sites)
- Proposer l’autocomplétion en fonction des valeurs existantes dans la base
  (noms de plasmides, types, sites de fixation).
- **Statut : En cours**
- **Critère d’acceptation :**
  - Suggestions apparaissent après 2-3 caractères + possibilité de désactiver si non pertinente.

### 4.2 Recherche par similarité d’un motif
- Recherche “similarité” (à définir) entre un motif et des séquences stockées.
- **Statut : Prévu**
- **Critère d’acceptation :**
  - Définition claire (ex: distance d’édition, k-mers, % identité approximative) + résultats triés.
- **Risque :** coût de calcul et performance.

---

## 5) Extraction des données annotées (option)
### 5.1 Export multi-collections + sous-ensemble
- Extraire des séquences de plusieurs collections et **choisir un sous-ensemble** dans chacune.
- **Statut : Prévu**
- **Critère d’acceptation :**
  - UI de sélection + export (zip / fasta / genbank selon choix) des plasmides sélectionnés.

---

## 6) Publication (option)
### 6.1 Notification email aux administratrices
- Envoyer un email lorsqu’une demande de publication est faite
  (django console EmailBackend pour dev).
- **Statut : Prévu**
- **Critère d’acceptation :**
  - Une demande déclenche un email console visible dans les logs.

### 6.2 Validation en deux étapes (cheffe d’équipe puis admin)
- La demande de publication doit d’abord être validée par la cheffe d’équipe,
  ensuite seulement visible par les administratrices.
- **Statut : Prévu**
- **Critère d’acceptation :**
  - Workflow clair + historique de validation/refus + justification en cas de refus.
