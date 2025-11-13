# Configuration du Stockage de Production pour LightRAG

Ce guide explique comment configurer LightRAG avec une architecture de stockage de production utilisant :
- **Neo4j** pour le graphe de connaissances
- **Milvus** pour le stockage vectoriel
- **Elasticsearch** pour le contenu textuel des chunks

## Architecture de Stockage

```
┌─────────────────────────────────────────────────────────────┐
│                      LightRAG System                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Elasticsearch│  │    Milvus    │  │    Neo4j     │      │
│  │              │  │              │  │              │      │
│  │ KV Storage   │  │   Vectors    │  │    Graph     │      │
│  │ Doc Status   │  │  Embeddings  │  │ Entities &   │      │
│  │ Text Chunks  │  │              │  │ Relations    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Variables d'Environnement Requises

### 1. Elasticsearch (Contenu Textuel)

**Option A : Elasticsearch Auto-hébergé**
```bash
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=votre_mot_de_passe
```

**Option B : Elastic Cloud (Recommandé)**
```bash
ELASTICSEARCH_CLOUD_ID=deployment:dXMtY2VudHJhbC0xLmF3cy5jbG91ZC5lcy5pbyQ...
ELASTICSEARCH_API_KEY=votre_clé_api
```

**Paramètres optionnels :**
```bash
ELASTICSEARCH_VERIFY_CERTS=true
ELASTICSEARCH_TIMEOUT=30
ELASTICSEARCH_WORKSPACE=production
```

### 2. Milvus (Stockage Vectoriel)

**Configuration de base :**
```bash
MILVUS_URI=http://localhost:19530
MILVUS_DB_NAME=lightrag
```

**Avec authentification (recommandé) :**
```bash
MILVUS_URI=http://localhost:19530
MILVUS_DB_NAME=lightrag
MILVUS_USER=root
MILVUS_PASSWORD=votre_mot_de_passe
# Ou avec token
MILVUS_TOKEN=votre_token
```

**Pour Zilliz Cloud (Milvus managé) :**
```bash
MILVUS_URI=https://votre-instance.zillizcloud.com:443
MILVUS_TOKEN=votre_token_zilliz
MILVUS_DB_NAME=lightrag
```

**Paramètres optionnels :**
```bash
MILVUS_WORKSPACE=production
```

### 3. Neo4j (Graphe de Connaissances)

**Configuration Neo4j Aura (Cloud - Recommandé) :**
```bash
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=votre_mot_de_passe
NEO4J_DATABASE=neo4j
```

**Configuration Neo4j Local :**
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=votre_mot_de_passe
NEO4J_DATABASE=neo4j
```

**Paramètres de pool de connexions (optionnels) :**
```bash
NEO4J_MAX_CONNECTION_POOL_SIZE=100
NEO4J_CONNECTION_TIMEOUT=30
NEO4J_CONNECTION_ACQUISITION_TIMEOUT=30
NEO4J_MAX_TRANSACTION_RETRY_TIME=30
NEO4J_MAX_CONNECTION_LIFETIME=300
NEO4J_LIVENESS_CHECK_TIMEOUT=30
NEO4J_KEEP_ALIVE=true
NEO4J_WORKSPACE=production
```

### 4. Configuration des Backends de Stockage

**Ces variables sont déjà configurées dans env.example :**
```bash
LIGHTRAG_KV_STORAGE=ElasticsearchKVStorage
LIGHTRAG_DOC_STATUS_STORAGE=ElasticsearchDocStatusStorage
LIGHTRAG_GRAPH_STORAGE=Neo4JStorage
LIGHTRAG_VECTOR_STORAGE=MilvusVectorDBStorage
```

## Configuration dans Replit Secrets

Pour configurer dans Replit :

1. Cliquez sur l'icône **Secrets** (🔒) dans le panneau de gauche
2. Ajoutez chaque variable d'environnement requise :

### Secrets Minimaux Requis

**Elasticsearch :**
- `ELASTICSEARCH_CLOUD_ID` (ou `ELASTICSEARCH_URL` pour auto-hébergé)
- `ELASTICSEARCH_API_KEY` (ou `ELASTICSEARCH_USERNAME` + `ELASTICSEARCH_PASSWORD`)

**Milvus :**
- `MILVUS_URI`
- `MILVUS_DB_NAME`
- `MILVUS_TOKEN` (pour Zilliz Cloud) ou `MILVUS_PASSWORD` (pour auto-hébergé)

**Neo4j :**
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE`

**Backends (déjà configurés dans env.example) :**
- `LIGHTRAG_KV_STORAGE=ElasticsearchKVStorage`
- `LIGHTRAG_DOC_STATUS_STORAGE=ElasticsearchDocStatusStorage`
- `LIGHTRAG_GRAPH_STORAGE=Neo4JStorage`
- `LIGHTRAG_VECTOR_STORAGE=MilvusVectorDBStorage`

## Installation des Services

### Option 1 : Services Cloud (Recommandé)

#### 1. **Elastic Cloud** 
🔗 https://cloud.elastic.co/

**Étapes :**
1. Créez un compte gratuit
2. Créez un nouveau déploiement
3. Choisissez une région proche de vous
4. Notez le **Cloud ID** et la **clé API**
5. Ajoutez-les dans Replit Secrets

**Essai gratuit :** 14 jours

#### 2. **Neo4j Aura**
🔗 https://neo4j.com/cloud/aura/

**Étapes :**
1. Créez un compte
2. Créez une instance AuraDB Free
3. Notez l'**URI de connexion**, le **username** et le **password**
4. Ajoutez-les dans Replit Secrets

**Niveau gratuit :** Disponible de manière permanente

#### 3. **Zilliz Cloud** (Milvus managé)
🔗 https://zilliz.com/

**Étapes :**
1. Créez un compte
2. Créez un cluster
3. Notez l'**endpoint URI** et le **token**
4. Ajoutez-les dans Replit Secrets

**Niveau gratuit :** Disponible avec limitations

### Option 2 : Auto-hébergé avec Docker

**Note :** Cette option nécessite Docker et n'est **pas compatible avec Replit**. Utilisez-la uniquement pour un déploiement local sur votre machine.

**Docker Compose :**
```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data

  milvus-etcd:
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
    volumes:
      - milvus-etcd:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379

  milvus-minio:
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - milvus-minio:/minio_data
    command: minio server /minio_data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  milvus:
    image: milvusdb/milvus:v2.3.3
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: milvus-etcd:2379
      MINIO_ADDRESS: milvus-minio:9000
    volumes:
      - milvus-data:/var/lib/milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - "milvus-etcd"
      - "milvus-minio"

  neo4j:
    image: neo4j:5.13
    environment:
      - NEO4J_AUTH=neo4j/password123
      - NEO4J_PLUGINS=["apoc"]
    ports:
      - "7687:7687"
      - "7474:7474"
    volumes:
      - neo4j-data:/data

volumes:
  elasticsearch-data:
  milvus-etcd:
  milvus-minio:
  milvus-data:
  neo4j-data:
```

**Démarrage :**
```bash
docker-compose up -d
```

**Configuration pour usage local :**
```bash
ELASTICSEARCH_URL=http://localhost:9200
MILVUS_URI=http://localhost:19530
MILVUS_DB_NAME=lightrag
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123
NEO4J_DATABASE=neo4j
```

## Vérification de la Configuration

Une fois configuré, démarrez LightRAG et vérifiez les logs :

```bash
# Les logs doivent montrer :
[INFO] Connected to Elasticsearch at https://xxx.es.io
[INFO] Connected to Milvus at https://xxx.zillizcloud.com
[INFO] Connected to Neo4j at neo4j+s://xxx.databases.neo4j.io
[INFO] Storage backends initialized successfully
```

## Avantages de cette Architecture

✅ **Elasticsearch** :
- Recherche full-text performante (BM25)
- Recherche hybride (BM25 + vectorielle + RRF)
- Gestion efficace des chunks textuels
- Scalabilité horizontale
- Analytique et agrégations puissantes

✅ **Milvus** :
- Optimisé pour la recherche vectorielle
- Support de milliards de vecteurs
- Indexation HNSW/IVF performante
- GPU acceleration disponible
- Scalabilité horizontale

✅ **Neo4j** :
- Graphe natif optimisé
- Traversées de graphe ultra-rapides
- Relations dynamiques et typées
- Langage Cypher puissant
- Visualisation intégrée

## Migration depuis d'Autres Backends

### Migration depuis PostgreSQL

Si vous utilisez actuellement PostgreSQL et souhaitez passer à Elasticsearch + Milvus + Neo4j :

#### ⚠️ Important : Ce qui est Préservé et Ce qui est Perdu

**✅ Préservé (via réindexation):**
- Documents sources
- Chunks de texte
- Embeddings vectoriels (recalculés)
- Graphe de connaissances de base (entités et relations extraites automatiquement)

**❌ Perdu (modifications manuelles):**
- Entités fusionnées manuellement dans le graphe
- Relations ajoutées/supprimées manuellement
- Métadonnées personnalisées non issues des documents
- Historique des modifications

Si vous avez des modifications manuelles importantes du graphe, **documentez-les avant la migration** ou **restez sur PostgreSQL**.

#### Étapes de Migration

**1. Sauvegarde Complète**
```bash
# Backup PostgreSQL (données complètes)
pg_dump $DATABASE_URL > lightrag_pg_backup_$(date +%Y%m%d).sql

# Backup du dossier de travail
cp -r ./rag_storage ./rag_storage_backup_$(date +%Y%m%d)

# Listez vos documents sources pour vérification
ls -lh ./inputs/
```

**2. Export des Modifications Manuelles (si applicable)**
```bash
# Si vous avez modifié le graphe manuellement, exportez :
# Via interface web : Graph → Export
# Ou documentez vos modifications dans un fichier texte
```

**3. Provisionner les Services Cloud**
- **Elastic Cloud** : https://cloud.elastic.co/ → Créer déploiement
- **Neo4j Aura** : https://neo4j.com/cloud/aura/ → Créer instance
- **Zilliz Cloud** : https://zilliz.com/ → Créer cluster

**4. Configuration Phase de Test (Recommandé)**

Avant de changer la production, testez avec les deux systèmes en parallèle :

```bash
# Gardez PostgreSQL actif en ajoutant simplement les nouveaux secrets cloud
# Sans changer les variables LIGHTRAG_*_STORAGE
# Cela permet de tester la connexion aux nouveaux services
```

Vérifiez les logs du serveur pour confirmer que les services cloud sont accessibles.

**5. Basculement vers Cloud**

Dans Replit Secrets, **modifiez** (ne supprimez pas les anciennes) :
```bash
# Changez ces 4 variables :
LIGHTRAG_KV_STORAGE=ElasticsearchKVStorage
LIGHTRAG_DOC_STATUS_STORAGE=ElasticsearchDocStatusStorage
LIGHTRAG_GRAPH_STORAGE=Neo4JStorage
LIGHTRAG_VECTOR_STORAGE=MilvusVectorDBStorage
```

Le serveur redémarrera automatiquement.

**6. Vérification Post-Migration**
```bash
# Vérifiez les logs :
# - "Connected to Elasticsearch at..."
# - "Connected to Milvus at..."
# - "Connected to Neo4j at..."
```

**7. Réindexation des Documents**
- Interface web → Documents → Scan → Process
- Tous les documents seront traités et le graphe reconstruit automatiquement
- Cette étape peut prendre du temps pour de grands volumes

**8. Validation**
- [ ] Tous les documents sont indexés (vérifier le statut)
- [ ] Le graphe contient les entités attendues
- [ ] Les recherches vectorielles fonctionnent
- [ ] Les requêtes RAG retournent des résultats pertinents
- [ ] (Si applicable) Réappliquer les modifications manuelles du graphe

#### Rollback vers PostgreSQL

Si vous rencontrez des problèmes après la migration :

**Option A : Rollback Simple (perte des nouvelles données)**
```bash
# Dans Replit Secrets, restaurez les 4 variables :
LIGHTRAG_KV_STORAGE=PGKVStorage
LIGHTRAG_DOC_STATUS_STORAGE=PGDocStatusStorage
LIGHTRAG_GRAPH_STORAGE=PGGraphStorage
LIGHTRAG_VECTOR_STORAGE=PGVectorStorage
# Le serveur redémarre automatiquement
# Vos données PostgreSQL sont intactes
```

**Option B : Rollback avec Restauration de Backup**
```bash
# Si vous avez supprimé des données PostgreSQL pendant la migration :
psql $DATABASE_URL < lightrag_pg_backup_YYYYMMDD.sql

# Puis restaurez les variables comme dans l'Option A
```

**Option C : Opération des Deux Systèmes en Parallèle**
```bash
# Gardez PostgreSQL actif tout en testant le cloud
# Changez les variables seulement pour un workspace de test
# Une fois validé, basculez la production
```

#### Conseils de Migration

1. **Effectuez la migration hors heures de pointe** si votre système est en production
2. **Documentez l'état actuel** avant de commencer
3. **Testez sur un workspace séparé** si possible
4. **Conservez les backups PostgreSQL** pendant au moins 30 jours
5. **Validez complètement** avant de supprimer les anciennes données

### Migration depuis le Stockage JSON

Si vous avez déjà des données dans le stockage JSON par défaut :

1. **Sauvegardez vos données** :
   ```bash
   cp -r ./rag_storage ./rag_storage.backup
   ```

2. **Configurez les nouveaux backends** (comme indiqué ci-dessus)

3. **Réindexez vos documents** via l'interface web :
   - Documents → Scan → Process

Les données seront automatiquement migrées vers les nouveaux backends.

## Dépannage

### Elasticsearch

**Erreur : "Connection refused"**
```bash
# Vérifiez l'URL et les credentials
curl -u $ELASTICSEARCH_USERNAME:$ELASTICSEARCH_PASSWORD $ELASTICSEARCH_URL
# Ou avec Cloud ID
curl -H "Authorization: ApiKey $ELASTICSEARCH_API_KEY" https://votre-cloud-id.es.io
```

**Erreur : "SSL certificate verify failed"**
```bash
# Désactivez la vérification SSL (développement uniquement)
ELASTICSEARCH_VERIFY_CERTS=false
```

### Milvus

**Erreur : "Connection timeout"**
```bash
# Vérifiez que Milvus est accessible
curl $MILVUS_URI/healthz
# Augmentez le timeout si nécessaire
```

**Erreur : "Authentication failed"**
```bash
# Vérifiez le token ou le mot de passe
# Pour Zilliz Cloud, utilisez MILVUS_TOKEN
# Pour auto-hébergé, utilisez MILVUS_PASSWORD
```

### Neo4j

**Erreur : "Connection refused"**
```bash
# Vérifiez le protocole
# Pour Neo4j Aura (cloud) : neo4j+s://
# Pour local : bolt://

# Testez la connexion
cypher-shell -a $NEO4J_URI -u $NEO4J_USERNAME -p $NEO4J_PASSWORD
```

**Erreur : "Database not found"**
```bash
# Vérifiez le nom de la base
# Par défaut : "neo4j"
# Créez une nouvelle base si nécessaire (Enterprise uniquement)
```

## Comparaison avec PostgreSQL

| Critère | Elasticsearch + Milvus + Neo4j | PostgreSQL |
|---------|-------------------------------|------------|
| **Scalabilité** | ⭐⭐⭐⭐⭐ Milliards de vecteurs | ⭐⭐⭐ Millions de vecteurs |
| **Performance Graphe** | ⭐⭐⭐⭐⭐ Natif | ⭐⭐⭐ CTE récursives |
| **Recherche Full-Text** | ⭐⭐⭐⭐⭐ BM25, analyseurs | ⭐⭐⭐ tsvector |
| **Complexité** | ⭐⭐ 3 services | ⭐⭐⭐⭐⭐ 1 service |
| **Coût** | ⭐⭐ Services cloud payants | ⭐⭐⭐⭐⭐ Gratuit sur Replit |
| **Setup Replit** | ⭐⭐⭐ Nécessite services externes | ⭐⭐⭐⭐⭐ Natif |

## Quand Utiliser Chaque Option

**Utilisez Elasticsearch + Milvus + Neo4j si :**
- Vous avez des millions/milliards de documents
- Vous avez besoin de recherche full-text avancée
- Votre graphe est très complexe avec des traversées profondes
- Vous déployez en production avec budget

**Utilisez PostgreSQL si :**
- Vous déployez sur Replit
- Vous avez moins de 100k documents
- Vous voulez une solution simple tout-en-un
- Budget limité ou développement/prototypage

## Appendice : Configuration PostgreSQL (Alternative Locale)

Si vous préférez rester sur Replit avec une solution locale sans services cloud, PostgreSQL est une excellente alternative.

### Configuration PostgreSQL sur Replit

**1. PostgreSQL est déjà provisionné** dans votre Replit avec ces variables :
- `DATABASE_URL` - URL de connexion complète
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`

**2. Configurez les backends PostgreSQL** dans Replit Secrets (🔒) :
```bash
LIGHTRAG_KV_STORAGE=PGKVStorage
LIGHTRAG_DOC_STATUS_STORAGE=PGDocStatusStorage
LIGHTRAG_GRAPH_STORAGE=PGGraphStorage
LIGHTRAG_VECTOR_STORAGE=PGVectorStorage
```

**3. L'extension pgvector** sera installée automatiquement au premier démarrage.

### Avantages PostgreSQL
- ✅ Natif dans Replit (aucune configuration externe)
- ✅ Une seule base de données à gérer
- ✅ Gratuit et sans limitation de bande passante
- ✅ pgvector pour la recherche vectorielle performante
- ✅ Support complet des features LightRAG

### Limites PostgreSQL
- Optimisé pour < 100k documents
- Recherche full-text basique vs Elasticsearch
- Performance graphe via CTE vs Neo4j natif
- Scalabilité verticale vs horizontale

### Installation Manuelle de pgvector (si nécessaire)
```bash
psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Optimisations PostgreSQL
Pour améliorer les performances :
```sql
-- Index HNSW pour les vecteurs (créés automatiquement par LightRAG)
-- Index B-tree pour les clés
-- Paramètres recommandés (si configurables):
-- shared_buffers = 256MB
-- effective_cache_size = 1GB
```

## Support

Pour toute question ou problème, consultez :
- **Elasticsearch** : https://www.elastic.co/guide/
- **Milvus** : https://milvus.io/docs
- **Neo4j** : https://neo4j.com/docs/
- **Zilliz Cloud** : https://docs.zilliz.com/
- **PostgreSQL** : https://www.postgresql.org/docs/
- **pgvector** : https://github.com/pgvector/pgvector
