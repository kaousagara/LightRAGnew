import os
import time
from dataclasses import dataclass, field
import numpy as np
import configparser
import asyncio
from typing import Any, Union, final

from ..base import (
    BaseKVStorage,
    BaseVectorStorage,
    DocProcessingStatus,
    DocStatus,
    DocStatusStorage,
)
from ..utils import logger, compute_mdhash_id
from ..constants import GRAPH_FIELD_SEP
from ..kg.shared_storage import get_data_init_lock, get_storage_lock, get_graph_db_lock

import pipmaster as pm

if not pm.is_installed("elasticsearch"):
    pm.install("elasticsearch")

from elasticsearch import AsyncElasticsearch, NotFoundError, helpers  # type: ignore

config = configparser.ConfigParser()
config.read("config.ini", "utf-8")


class ElasticsearchConnectionManager:
    """Manage shared Elasticsearch connection"""
    _instance = None
    _lock = asyncio.Lock()
    _ref_count = 0

    @classmethod
    async def get_client(cls) -> AsyncElasticsearch:
        async with cls._lock:
            if cls._instance is None:
                es_url = os.environ.get(
                    "ELASTICSEARCH_URL",
                    config.get("elasticsearch", "url", fallback=None),
                )
                
                # Cloud ID for Elastic Cloud
                cloud_id = os.environ.get("ELASTICSEARCH_CLOUD_ID")
                
                # Validate that at least one connection method is configured
                if not es_url and not cloud_id:
                    raise ValueError(
                        "Elasticsearch connection not configured. "
                        "Please set either ELASTICSEARCH_URL or ELASTICSEARCH_CLOUD_ID environment variable."
                    )
                
                # API key authentication (recommended for production)
                api_key = os.environ.get("ELASTICSEARCH_API_KEY")
                
                # Basic authentication (alternative)
                username = os.environ.get("ELASTICSEARCH_USERNAME")
                password = os.environ.get("ELASTICSEARCH_PASSWORD")
                
                # SSL/TLS settings
                verify_certs = os.environ.get("ELASTICSEARCH_VERIFY_CERTS", "true").lower() == "true"
                ca_certs = os.environ.get("ELASTICSEARCH_CA_CERTS")
                
                # Build connection parameters
                conn_params = {}
                
                if cloud_id:
                    conn_params["cloud_id"] = cloud_id
                else:
                    conn_params["hosts"] = [es_url]
                
                if api_key:
                    conn_params["api_key"] = api_key
                elif username and password:
                    conn_params["basic_auth"] = (username, password)
                
                conn_params["verify_certs"] = verify_certs
                if ca_certs:
                    conn_params["ca_certs"] = ca_certs
                
                # Request timeout
                timeout = int(os.environ.get("ELASTICSEARCH_TIMEOUT", "30"))
                conn_params["request_timeout"] = timeout
                
                cls._instance = AsyncElasticsearch(**conn_params)
                cls._ref_count = 0
                
                logger.info(f"Initialized Elasticsearch connection to {cloud_id if cloud_id else es_url}")
            
            cls._ref_count += 1
            return cls._instance

    @classmethod
    async def release_client(cls, client: AsyncElasticsearch):
        async with cls._lock:
            if client is not None and client is cls._instance:
                cls._ref_count -= 1
                if cls._ref_count == 0:
                    await cls._instance.close()
                    cls._instance = None


async def ensure_index_exists(
    es_client: AsyncElasticsearch,
    index_name: str,
    index_type: str = "kv"
) -> None:
    """Ensure Elasticsearch index exists with proper mappings
    
    Args:
        es_client: Elasticsearch client
        index_name: Name of the index
        index_type: Type of index ('kv', 'vector', 'doc_status')
    """
    if await es_client.indices.exists(index=index_name):
        return
    
    # Base settings for all indices
    settings = {
        "number_of_shards": int(os.environ.get("ELASTICSEARCH_SHARDS", "1")),
        "number_of_replicas": int(os.environ.get("ELASTICSEARCH_REPLICAS", "1")),
        "refresh_interval": "5s",
    }
    
    mappings = {}
    
    if index_type == "kv":
        # KV Storage for text chunks and caches
        mappings = {
            "properties": {
                "content": {"type": "text", "index": False},  # Don't index large content
                "tokens": {"type": "integer"},
                "full_doc_id": {"type": "keyword"},
                "chunk_order_index": {"type": "integer"},
                "file_path": {"type": "keyword"},
                "accreditation_level": {"type": "integer"},
                "service": {"type": "keyword"},
                "llm_cache_list": {"type": "keyword"},
                "create_time": {"type": "long"},
                "update_time": {"type": "long"},
                "return_message": {"type": "text", "index": False},
                "messages": {"type": "object", "enabled": False},
            }
        }
    
    elif index_type == "vector":
        # Vector storage for chunks, entities, relationships
        embedding_dim = int(os.environ.get("EMBEDDING_DIM", "1536"))
        
        mappings = {
            "properties": {
                "content": {"type": "text", "analyzer": "standard"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": embedding_dim,
                    "index": True,
                    "similarity": "cosine",
                    "index_options": {
                        "type": "hnsw",
                        "m": 16,
                        "ef_construction": 100
                    }
                },
                # Metadata fields
                "entity_name": {"type": "keyword"},
                "source_id": {"type": "keyword"},
                "description": {"type": "text"},
                "keywords": {"type": "keyword"},
                "weight": {"type": "float"},
                "rank": {"type": "float"},
                "full_doc_id": {"type": "keyword"},
                "chunk_order_index": {"type": "integer"},
                "file_path": {"type": "keyword"},
                # Security fields
                "accreditation_level": {"type": "integer"},
                "service": {"type": "keyword"},
                # Timestamp fields
                "create_time": {"type": "long"},
                "update_time": {"type": "long"},
            }
        }
    
    elif index_type == "doc_status":
        # Document status tracking
        mappings = {
            "properties": {
                "file_path": {"type": "keyword"},
                "status": {"type": "keyword"},
                "metadata": {"type": "object", "enabled": True},
                "error_msg": {"type": "text"},
                "accreditation_level": {"type": "integer"},
                "service": {"type": "keyword"},
                "create_time": {"type": "long"},
                "update_time": {"type": "long"},
            }
        }
    
    await es_client.indices.create(
        index=index_name,
        body={"settings": settings, "mappings": mappings}
    )
    
    logger.info(f"Created Elasticsearch index: {index_name} (type: {index_type})")


@final
@dataclass
class ElasticsearchKVStorage(BaseKVStorage):
    es_client: AsyncElasticsearch = field(default=None)
    _index_name: str = field(default="")

    def __init__(self, namespace, global_config, embedding_func, workspace=None):
        super().__init__(
            namespace=namespace,
            workspace=workspace or "",
            global_config=global_config,
            embedding_func=embedding_func,
        )
        self.__post_init__()

    def __post_init__(self):
        # Check for ELASTICSEARCH_WORKSPACE environment variable first
        es_workspace = os.environ.get("ELASTICSEARCH_WORKSPACE")
        if es_workspace and es_workspace.strip():
            effective_workspace = es_workspace.strip()
            logger.info(
                f"Using ELASTICSEARCH_WORKSPACE environment variable: '{effective_workspace}' "
                f"(overriding passed workspace: '{self.workspace}')"
            )
        else:
            effective_workspace = self.workspace
            if effective_workspace:
                logger.debug(f"Using passed workspace parameter: '{effective_workspace}'")

        # Build final_namespace with workspace prefix for data isolation
        if effective_workspace:
            self.final_namespace = f"{effective_workspace}_{self.namespace}"
            self.workspace = effective_workspace
            logger.debug(f"Final namespace with workspace prefix: '{self.final_namespace}'")
        else:
            self.final_namespace = self.namespace
            self.workspace = "_"
            logger.debug(f"[{self.workspace}] Final namespace (no workspace): '{self.namespace}'")

        # Index name: lowercase and replace underscores
        self._index_name = self.final_namespace.lower().replace("_", "-")

    async def initialize(self):
        async with get_data_init_lock():
            if self.es_client is None:
                self.es_client = await ElasticsearchConnectionManager.get_client()

            await ensure_index_exists(self.es_client, self._index_name, "kv")
            logger.debug(f"[{self.workspace}] Use Elasticsearch as KV {self._index_name}")

    async def finalize(self):
        async with get_storage_lock():
            if self.es_client is not None:
                await ElasticsearchConnectionManager.release_client(self.es_client)
                self.es_client = None

    async def get_by_id(self, id: str) -> dict[str, Any] | None:
        try:
            result = await self.es_client.get(index=self._index_name, id=id)
            doc = result["_source"]
            doc.setdefault("create_time", 0)
            doc.setdefault("update_time", 0)
            return doc
        except NotFoundError:
            return None

    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        
        try:
            result = await self.es_client.mget(
                index=self._index_name,
                body={"ids": ids}
            )
            
            doc_map: dict[str, dict[str, Any]] = {}
            for doc in result["docs"]:
                if doc.get("found"):
                    source = doc["_source"]
                    source.setdefault("create_time", 0)
                    source.setdefault("update_time", 0)
                    doc_map[doc["_id"]] = source
            
            # Return in same order as input
            ordered_results: list[dict[str, Any] | None] = []
            for id_value in ids:
                ordered_results.append(doc_map.get(id_value))
            
            return ordered_results
        except Exception as e:
            logger.error(f"Error getting documents by IDs: {e}")
            return [None] * len(ids)

    async def filter_keys(self, keys: set[str]) -> set[str]:
        """Return keys that don't exist in storage"""
        if not keys:
            return set()
        
        try:
            result = await self.es_client.mget(
                index=self._index_name,
                body={"ids": list(keys)},
                _source=False
            )
            
            existing_ids = {doc["_id"] for doc in result["docs"] if doc.get("found")}
            return keys - existing_ids
        except Exception as e:
            logger.error(f"Error filtering keys: {e}")
            return keys

    async def get_all(self) -> dict[str, Any]:
        """Get all data from storage"""
        result = {}
        
        try:
            # Use scroll API for large datasets
            response = await self.es_client.search(
                index=self._index_name,
                body={"query": {"match_all": {}}},
                scroll="2m",
                size=1000
            )
            
            scroll_id = response["_scroll_id"]
            hits = response["hits"]["hits"]
            
            while hits:
                for hit in hits:
                    doc = hit["_source"]
                    doc.setdefault("create_time", 0)
                    doc.setdefault("update_time", 0)
                    result[hit["_id"]] = doc
                
                response = await self.es_client.scroll(
                    scroll_id=scroll_id,
                    scroll="2m"
                )
                scroll_id = response["_scroll_id"]
                hits = response["hits"]["hits"]
            
            # Clear scroll
            await self.es_client.clear_scroll(scroll_id=scroll_id)
            
        except Exception as e:
            logger.error(f"Error getting all documents: {e}")
        
        return result

    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
        logger.debug(f"[{self.workspace}] Inserting {len(data)} to {self.namespace}")
        if not data:
            return

        current_time = int(time.time())
        actions = []
        
        for k, v in data.items():
            # For text_chunks namespace, ensure llm_cache_list field exists
            if self.namespace.endswith("text_chunks"):
                if "llm_cache_list" not in v:
                    v["llm_cache_list"] = []
            
            # Prepare document
            doc = v.copy()
            doc["update_time"] = current_time
            
            # Set create_time if not present (will be overwritten by existing doc if update)
            if "create_time" not in doc:
                doc["create_time"] = current_time
            
            actions.append({
                "_op_type": "index",
                "_index": self._index_name,
                "_id": k,
                "_source": doc
            })
        
        if actions:
            try:
                success, failed = await helpers.async_bulk(
                    self.es_client,
                    actions,
                    raise_on_error=False
                )
                
                if failed:
                    logger.warning(f"Failed to index {len(failed)} documents")
                    
            except Exception as e:
                logger.error(f"Error during bulk upsert: {e}")

    async def index_done_callback(self) -> None:
        # Elasticsearch handles persistence automatically
        # Optionally refresh the index to make changes immediately visible
        try:
            await self.es_client.indices.refresh(index=self._index_name)
        except Exception as e:
            logger.debug(f"Index refresh error (non-critical): {e}")

    async def delete(self, ids: list[str]) -> None:
        """Delete documents with specified IDs"""
        if not ids:
            return

        try:
            actions = [
                {
                    "_op_type": "delete",
                    "_index": self._index_name,
                    "_id": id_val,
                }
                for id_val in ids
            ]
            
            success, failed = await helpers.async_bulk(
                self.es_client,
                actions,
                raise_on_error=False
            )
            
            logger.info(
                f"[{self.workspace}] Deleted {success} documents from {self.namespace}"
            )
            
            if failed:
                logger.warning(f"Failed to delete {len(failed)} documents")
                
        except Exception as e:
            logger.error(f"[{self.workspace}] Error deleting documents: {e}")

    async def drop(self) -> dict[str, str]:
        """Drop the storage by deleting all documents in the index"""
        async with get_storage_lock():
            try:
                # Delete all documents
                result = await self.es_client.delete_by_query(
                    index=self._index_name,
                    body={"query": {"match_all": {}}}
                )
                
                deleted_count = result.get("deleted", 0)
                
                logger.info(
                    f"[{self.workspace}] Dropped {deleted_count} documents from {self._index_name}"
                )
                return {
                    "status": "success",
                    "message": f"{deleted_count} documents dropped",
                }
            except Exception as e:
                logger.error(f"[{self.workspace}] Error dropping index {self._index_name}: {e}")
                return {"status": "error", "message": str(e)}


@final
@dataclass
class ElasticsearchDocStatusStorage(DocStatusStorage):
    es_client: AsyncElasticsearch = field(default=None)
    _index_name: str = field(default="")

    def _prepare_doc_status_data(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Normalize a raw Elasticsearch document to DocProcessingStatus-compatible dict"""
        data = doc.copy()
        data.pop("_id", None)
        
        if "file_path" not in data:
            data["file_path"] = "no-file-path"
        if "metadata" not in data:
            data["metadata"] = {}
        if "error_msg" not in data:
            data["error_msg"] = None
        
        # Backward compatibility: migrate legacy 'error' field
        if "error" in data:
            if "error_msg" not in data or data["error_msg"] in (None, ""):
                data["error_msg"] = data.pop("error")
            else:
                data.pop("error", None)
        
        return data

    def __init__(self, namespace, global_config, embedding_func, workspace=None):
        super().__init__(
            namespace=namespace,
            workspace=workspace or "",
            global_config=global_config,
            embedding_func=embedding_func,
        )
        self.__post_init__()

    def __post_init__(self):
        es_workspace = os.environ.get("ELASTICSEARCH_WORKSPACE")
        if es_workspace and es_workspace.strip():
            effective_workspace = es_workspace.strip()
        else:
            effective_workspace = self.workspace

        if effective_workspace:
            self.final_namespace = f"{effective_workspace}_{self.namespace}"
            self.workspace = effective_workspace
        else:
            self.final_namespace = self.namespace
            self.workspace = "_"

        self._index_name = self.final_namespace.lower().replace("_", "-")

    async def initialize(self):
        async with get_data_init_lock():
            if self.es_client is None:
                self.es_client = await ElasticsearchConnectionManager.get_client()

            await ensure_index_exists(self.es_client, self._index_name, "doc_status")
            logger.debug(f"[{self.workspace}] Use Elasticsearch as DocStatus {self._index_name}")

    async def finalize(self):
        async with get_storage_lock():
            if self.es_client is not None:
                await ElasticsearchConnectionManager.release_client(self.es_client)
                self.es_client = None

    async def filter_keys(self, keys: set[str]) -> set[str]:
        """Return keys that should be processed (not in storage or not successfully processed)"""
        if not keys:
            return set()
        
        try:
            result = await self.es_client.mget(
                index=self._index_name,
                body={"ids": list(keys)}
            )
            
            existing_ids = {
                doc["_id"] for doc in result["docs"]
                if doc.get("found") and doc["_source"].get("status") == DocStatus.COMPLETED.value
            }
            
            return keys - existing_ids
        except Exception as e:
            logger.error(f"Error filtering keys: {e}")
            return keys

    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        
        try:
            result = await self.es_client.mget(
                index=self._index_name,
                body={"ids": ids}
            )
            
            ordered_results: list[dict[str, Any] | None] = []
            for doc in result["docs"]:
                if doc.get("found"):
                    data = self._prepare_doc_status_data(doc["_source"])
                    ordered_results.append(data)
                else:
                    ordered_results.append(None)
            
            return ordered_results
        except Exception as e:
            logger.error(f"Error getting document status by IDs: {e}")
            return [None] * len(ids)

    async def upsert(self, data: dict[str, DocProcessingStatus]) -> None:
        if not data:
            return

        current_time = int(time.time())
        actions = []
        
        for k, v in data.items():
            doc = {
                "file_path": v.file_path,
                "status": v.status.value,
                "metadata": v.metadata or {},
                "error_msg": v.error_msg,
                "accreditation_level": getattr(v, "accreditation_level", 0),
                "service": getattr(v, "service", None),
                "update_time": current_time,
                "create_time": current_time,
            }
            
            actions.append({
                "_op_type": "index",
                "_index": self._index_name,
                "_id": k,
                "_source": doc
            })
        
        if actions:
            try:
                await helpers.async_bulk(self.es_client, actions)
                logger.debug(f"[{self.workspace}] Upserted {len(data)} doc statuses")
            except Exception as e:
                logger.error(f"Error upserting doc status: {e}")

    async def get_all(self) -> dict[str, DocProcessingStatus]:
        result = {}
        
        try:
            response = await self.es_client.search(
                index=self._index_name,
                body={"query": {"match_all": {}}},
                scroll="2m",
                size=1000
            )
            
            scroll_id = response["_scroll_id"]
            hits = response["hits"]["hits"]
            
            while hits:
                for hit in hits:
                    data = self._prepare_doc_status_data(hit["_source"])
                    result[hit["_id"]] = DocProcessingStatus(**data)
                
                response = await self.es_client.scroll(scroll_id=scroll_id, scroll="2m")
                scroll_id = response["_scroll_id"]
                hits = response["hits"]["hits"]
            
            await self.es_client.clear_scroll(scroll_id=scroll_id)
            
        except Exception as e:
            logger.error(f"Error getting all doc statuses: {e}")
        
        return result

    async def index_done_callback(self) -> None:
        try:
            await self.es_client.indices.refresh(index=self._index_name)
        except Exception as e:
            logger.debug(f"Index refresh error (non-critical): {e}")

    async def drop(self) -> dict[str, str]:
        """Drop all document status records"""
        async with get_storage_lock():
            try:
                result = await self.es_client.delete_by_query(
                    index=self._index_name,
                    body={"query": {"match_all": {}}}
                )
                
                deleted_count = result.get("deleted", 0)
                
                logger.info(f"[{self.workspace}] Dropped {deleted_count} doc statuses from {self._index_name}")
                return {
                    "status": "success",
                    "message": f"{deleted_count} doc statuses dropped",
                }
            except Exception as e:
                logger.error(f"[{self.workspace}] Error dropping doc status index: {e}")
                return {"status": "error", "message": str(e)}


@final
@dataclass
class ElasticsearchVectorStorage(BaseVectorStorage):
    es_client: AsyncElasticsearch = field(default=None)
    _index_name: str = field(default="")
    _max_batch_size: int = field(default=10)

    def __init__(
        self, namespace, global_config, embedding_func, workspace=None, meta_fields=None
    ):
        super().__init__(
            namespace=namespace,
            workspace=workspace or "",
            global_config=global_config,
            embedding_func=embedding_func,
            meta_fields=meta_fields or set(),
        )
        self.__post_init__()

    def __post_init__(self):
        es_workspace = os.environ.get("ELASTICSEARCH_WORKSPACE")
        if es_workspace and es_workspace.strip():
            effective_workspace = es_workspace.strip()
            logger.info(
                f"Using ELASTICSEARCH_WORKSPACE environment variable: '{effective_workspace}' "
                f"(overriding passed workspace: '{self.workspace}')"
            )
        else:
            effective_workspace = self.workspace
            if effective_workspace:
                logger.debug(f"Using passed workspace parameter: '{effective_workspace}'")

        if effective_workspace:
            self.final_namespace = f"{effective_workspace}_{self.namespace}"
            self.workspace = effective_workspace
            logger.debug(f"Final namespace with workspace prefix: '{self.final_namespace}'")
        else:
            self.final_namespace = self.namespace
            self.workspace = "_"
            logger.debug(f"Final namespace (no workspace): '{self.final_namespace}'")

        self._index_name = self.final_namespace.lower().replace("_", "-")
        
        kwargs = self.global_config.get("vector_db_storage_cls_kwargs", {})
        cosine_threshold = kwargs.get("cosine_better_than_threshold")
        if cosine_threshold is None:
            raise ValueError(
                "cosine_better_than_threshold must be specified in vector_db_storage_cls_kwargs"
            )
        self.cosine_better_than_threshold = cosine_threshold
        self._max_batch_size = self.global_config["embedding_batch_num"]

    async def initialize(self):
        async with get_data_init_lock():
            if self.es_client is None:
                self.es_client = await ElasticsearchConnectionManager.get_client()

            await ensure_index_exists(self.es_client, self._index_name, "vector")
            logger.debug(f"[{self.workspace}] Use Elasticsearch as VDB {self._index_name}")

    async def finalize(self):
        async with get_storage_lock():
            if self.es_client is not None:
                await ElasticsearchConnectionManager.release_client(self.es_client)
                self.es_client = None

    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
        logger.debug(f"[{self.workspace}] Inserting {len(data)} to {self.namespace}")
        if not data:
            return

        current_time = int(time.time())
        
        # Extract content for embedding
        contents = [v["content"] for v in data.values()]
        batches = [
            contents[i : i + self._max_batch_size]
            for i in range(0, len(contents), self._max_batch_size)
        ]

        # Compute embeddings in batches
        embedding_tasks = [self.embedding_func(batch) for batch in batches]
        embeddings_list = await asyncio.gather(*embedding_tasks)
        embeddings = np.concatenate(embeddings_list)

        # Prepare bulk actions
        actions = []
        for idx, (k, v) in enumerate(data.items()):
            doc = {
                **{k1: v1 for k1, v1 in v.items() if k1 in self.meta_fields or k1 == "content"},
                "embedding": embeddings[idx].tolist(),
                "create_time": current_time,
                "update_time": current_time,
            }
            
            actions.append({
                "_op_type": "index",
                "_index": self._index_name,
                "_id": k,
                "_source": doc
            })

        if actions:
            try:
                await helpers.async_bulk(self.es_client, actions)
                logger.debug(f"[{self.workspace}] Upserted {len(data)} vectors")
            except Exception as e:
                logger.error(f"Error upserting vectors: {e}")

    async def query(
        self, query: str, top_k: int, query_embedding: list[float] = None
    ) -> list[dict[str, Any]]:
        """Query using hybrid search (BM25 + Vector + RRF)"""
        if query_embedding is None:
            query_embedding = await self.embedding_func([query])
            query_embedding = query_embedding[0]

        try:
            # Hybrid search with Reciprocal Rank Fusion (RRF)
            # Combining vector search (kNN) and text search (BM25)
            response = await self.es_client.search(
                index=self._index_name,
                size=top_k,
                knn={
                    "field": "embedding",
                    "query_vector": query_embedding,
                    "k": top_k,
                    "num_candidates": top_k * 10,
                },
                query={
                    "match": {
                        "content": {
                            "query": query,
                            "boost": 0.5  # Lower boost for BM25 vs vector
                        }
                    }
                },
                rank={
                    "rrf": {
                        "window_size": top_k * 2,
                        "rank_constant": 60
                    }
                }
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                doc = hit["_source"]
                doc["id"] = hit["_id"]
                doc["score"] = hit["_score"]
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"Error during hybrid search: {e}")
            return []

    async def delete_entity(self, entity_name: str) -> None:
        """Delete entity by name"""
        try:
            await self.es_client.delete_by_query(
                index=self._index_name,
                body={
                    "query": {
                        "term": {"entity_name.keyword": entity_name}
                    }
                }
            )
            logger.debug(f"Deleted entity: {entity_name}")
        except Exception as e:
            logger.error(f"Error deleting entity {entity_name}: {e}")

    async def delete_entity_relation(self, entity_name: str) -> None:
        """Delete relations for a given entity"""
        try:
            await self.es_client.delete_by_query(
                index=self._index_name,
                body={
                    "query": {
                        "bool": {
                            "should": [
                                {"term": {"src_id.keyword": entity_name}},
                                {"term": {"tgt_id.keyword": entity_name}}
                            ]
                        }
                    }
                }
            )
            logger.debug(f"Deleted relations for entity: {entity_name}")
        except Exception as e:
            logger.error(f"Error deleting relations for {entity_name}: {e}")

    async def get_by_id(self, id: str) -> dict[str, Any] | None:
        try:
            result = await self.es_client.get(index=self._index_name, id=id)
            doc = result["_source"]
            doc["id"] = result["_id"]
            return doc
        except NotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error getting document by ID {id}: {e}")
            return None

    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        
        try:
            result = await self.es_client.mget(
                index=self._index_name,
                body={"ids": ids}
            )
            
            results = []
            for doc in result["docs"]:
                if doc.get("found"):
                    data = doc["_source"]
                    data["id"] = doc["_id"]
                    results.append(data)
            
            return results
        except Exception as e:
            logger.error(f"Error getting documents by IDs: {e}")
            return []

    async def delete(self, ids: list[str]):
        """Delete vectors with specified IDs"""
        if not ids:
            return

        try:
            actions = [
                {
                    "_op_type": "delete",
                    "_index": self._index_name,
                    "_id": id_val,
                }
                for id_val in ids
            ]
            
            await helpers.async_bulk(self.es_client, actions, raise_on_error=False)
            logger.debug(f"Deleted {len(ids)} vectors")
        except Exception as e:
            logger.error(f"Error deleting vectors: {e}")

    async def get_vectors_by_ids(self, ids: list[str]) -> dict[str, list[float]]:
        """Get vectors by their IDs, returning only ID and vector data"""
        if not ids:
            return {}
        
        try:
            result = await self.es_client.mget(
                index=self._index_name,
                body={"ids": ids},
                _source=["embedding"]
            )
            
            vectors = {}
            for doc in result["docs"]:
                if doc.get("found") and "embedding" in doc["_source"]:
                    vectors[doc["_id"]] = doc["_source"]["embedding"]
            
            return vectors
        except Exception as e:
            logger.error(f"Error getting vectors by IDs: {e}")
            return {}

    async def index_done_callback(self) -> None:
        try:
            await self.es_client.indices.refresh(index=self._index_name)
        except Exception as e:
            logger.debug(f"Index refresh error (non-critical): {e}")

    async def drop(self) -> dict[str, str]:
        """Drop all vectors from the index"""
        async with get_storage_lock():
            try:
                result = await self.es_client.delete_by_query(
                    index=self._index_name,
                    body={"query": {"match_all": {}}}
                )
                
                deleted_count = result.get("deleted", 0)
                
                logger.info(
                    f"[{self.workspace}] Dropped {deleted_count} vectors from {self._index_name}"
                )
                return {
                    "status": "success",
                    "message": f"{deleted_count} vectors dropped",
                }
            except Exception as e:
                logger.error(f"[{self.workspace}] Error dropping vectors: {e}")
                return {"status": "error", "message": str(e)}
