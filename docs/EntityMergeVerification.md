# Vérification de Fusion d'Entités (Entity Merge Verification)

## 📋 Vue d'ensemble

Le système de vérification de fusion d'entités empêche la fusion incorrecte d'entités qui partagent le même nom mais représentent des concepts différents dans des contextes différents.

## 🎯 Problème résolu

**Avant** : Si deux documents mentionnent "Python", le système fusionnait automatiquement ces entités, même si l'une fait référence au langage de programmation et l'autre au serpent.

**Après** : Le système vérifie la similarité sémantique et contextuelle avant de fusionner. Si les entités sont trop différentes, elles sont gardées séparées avec des suffixes contextuels.

## ⚙️ Configuration

Ajoutez ces paramètres à votre fichier `.env` :

```bash
# Activer la vérification de similarité (par défaut: true)
ENABLE_ENTITY_MERGE_VERIFICATION=true

# Seuil de similarité pour la fusion (0.0-1.0, par défaut: 0.85)
# Plus élevé = plus strict (moins de fusions)
# Plus faible = plus permissif (plus de fusions)
ENTITY_MERGE_SIMILARITY_THRESHOLD=0.85

# Poids de la similarité contextuelle (0.0-1.0, par défaut: 0.3)
# 0.3 = 30% contexte (fichiers, sources) + 70% description
ENTITY_CONTEXT_SIMILARITY_WEIGHT=0.3
```

## 🔍 Comment ça fonctionne

### 1. Similarité de description (70% par défaut)
- Utilise les embeddings pour calculer la similarité sémantique
- Compare les descriptions des entités via cosine similarity
- Exemple : "Python is a programming language" vs "Python is a reptile" → faible similarité

### 2. Similarité contextuelle (30% par défaut)
- **File paths** : Calcule le chevauchement des fichiers sources (Jaccard similarity)
- **Source IDs** : Calcule le chevauchement des identifiants de source
- Exemple : Même fichier → haute similarité, fichiers différents → faible similarité

### 3. Score combiné
```
Score final = (Description × 0.7) + (Contexte × 0.3)
```

### 4. Décision de fusion
- **Score ≥ seuil** : Les entités sont fusionnées normalement
- **Score < seuil** : Une nouvelle entité est créée avec un suffixe contextuel

## 📊 Exemples

### Exemple 1 : Fusion acceptée
```
Document A: "Python is a high-level programming language"
Document B: "Python is widely used for web development"

Score de description: 0.92 (très similaire)
Score de contexte: 0.40 (fichiers différents)
Score final: 0.92 × 0.7 + 0.40 × 0.3 = 0.76

Résultat: Fusion si seuil ≤ 0.76
```

### Exemple 2 : Fusion refusée
```
Document A: "Python is a programming language"
Document B: "Python is a large snake species"

Score de description: 0.35 (très différent)
Score de contexte: 0.00 (aucun chevauchement)
Score final: 0.35 × 0.7 + 0.00 × 0.3 = 0.245

Résultat: Fusion refusée (< 0.85)
→ Création de "Python_document_B" comme entité séparée
```

### Exemple 3 : Même document, concepts similaires
```
Document A, section 1: "Python basics"
Document A, section 2: "Advanced Python features"

Score de description: 0.88 (similaire)
Score de contexte: 1.00 (même fichier)
Score final: 0.88 × 0.7 + 1.00 × 0.3 = 0.916

Résultat: Fusion (≥ 0.85)
```

## 🎛️ Réglage des paramètres

### Seuil de similarité

| Valeur | Usage | Comportement |
|--------|-------|--------------|
| 0.95 | Très strict | Presque aucune fusion automatique |
| 0.85 | **Recommandé** | Équilibre entre précision et fusion |
| 0.75 | Permissif | Plus de fusions, risque d'erreurs |
| 0.65 | Très permissif | Beaucoup de fusions, risque élevé |

### Poids contextuel

| Valeur | Usage | Comportement |
|--------|-------|--------------|
| 0.1 | Basé description | Fusionne si descriptions similaires |
| 0.3 | **Recommandé** | Équilibre |
| 0.5 | Équilibré | Égale importance contexte/description |
| 0.7 | Basé contexte | Fusionne surtout si même document |

## 🚀 Cas d'usage

### ✅ Utiliser la vérification pour :
- Documents multi-domaines (technologie + biologie)
- Termes ambigus ("Apple", "Java", "Mercury")
- Bases de connaissances encyclopédiques
- Agrégation de sources diverses

### ❌ Désactiver la vérification pour :
- Documents dans un seul domaine
- Petits ensembles de données homogènes
- Performance maximale requise
- Confiance totale dans l'unicité des noms

## 📈 Impact sur les performances

- **Coût** : 1 appel d'embedding supplémentaire par entité candidate à la fusion
- **Optimisation** : Les entités nouvelles (sans collision) ne déclenchent pas de vérification
- **Recommandation** : Surveiller les métriques si vous ingérez > 10 000 documents

## 🔧 Dépannage

### Trop de fusions refusées
1. Réduire `ENTITY_MERGE_SIMILARITY_THRESHOLD` (ex: 0.75)
2. Augmenter `ENTITY_CONTEXT_SIMILARITY_WEIGHT` si les entités sont dans les mêmes documents

### Trop de fusions incorrectes
1. Augmenter `ENTITY_MERGE_SIMILARITY_THRESHOLD` (ex: 0.90)
2. Réduire `ENTITY_CONTEXT_SIMILARITY_WEIGHT` pour privilégier la sémantique

### Vérifier les décisions
Les logs INFO affichent les décisions de non-fusion :
```
Entity merge verification for 'Python': 
similarity=0.245 (threshold=0.850) - 
desc=0.350, context=0.000 - 
Decision: KEEP SEPARATE
```

## 🔬 Tests recommandés

1. **Test de collision** : Insérer 2 documents avec "Python" (langue vs serpent)
2. **Test de fusion** : Insérer 2 documents avec "Python" (même contexte)
3. **Test de performance** : Mesurer le temps d'ingestion avec/sans vérification

## 📝 Notes techniques

- Les suffixes sont générés à partir du nom du fichier source (max 20 caractères)
- Les relations entre entités utilisent les IDs, donc elles restent intactes
- Le fallback en cas d'erreur est de fusionner (approche conservatrice)
- Sans fonction d'embedding, le système utilise la correspondance de type d'entité

## 🤝 Contribution

Pour améliorer cette fonctionnalité :
1. Ajouter des tests unitaires pour `_should_merge_entities`
2. Créer des benchmarks de performance
3. Proposer des stratégies de similarité alternatives
