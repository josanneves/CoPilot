from typing import Dict, Any, List, Generator, Type
from sqlmodel import Session, select
from app.connectors.models import Connectors
from elasticsearch7 import Elasticsearch
from loguru import logger
from app.db.db_session import engine
import requests
from app.connectors.schema import ConnectorResponse
from app.connectors.utils import get_connector_info_from_db
from app.connectors.wazuh_indexer.schema.indices import Indices, IndexConfigModel
from datetime import datetime, timedelta
from typing import Iterable, Tuple




def verify_wazuh_indexer_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to Wazuh Indexer service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
    """
    logger.info(f"Verifying the wazuh-indexer connection to {attributes['connector_url']}")
    
    try:
        es = Elasticsearch(
            [attributes["connector_url"]],
            http_auth=(attributes["connector_username"], attributes["connector_password"]),
            verify_certs=False,
            timeout=15,
            max_retries=10,
            retry_on_timeout=False,
        )
        es.cluster.health()
        logger.debug("Wazuh Indexer connection successful")
        return {"connectionSuccessful": True, "message": "Wazuh Indexer connection successful"}
    except Exception as e:
        logger.error(f"Connection to {attributes['connector_url']} failed with error: {e}")
        return {"connectionSuccessful": False, "message": f"Connection to {attributes['connector_url']} failed with error: {e}"}
    
def verify_wazuh_indexer_connection(connector_name: str) -> str:
    """
    Returns the authentication token for the Wazuh Indexer service.

    Returns:
        str: Authentication token for the Wazuh Indexer service.
    """
    attributes = get_connector_info_from_db(connector_name)
    if attributes is None:
        logger.error("No Wazuh Indexer connector found in the database")
        return None
    return verify_wazuh_indexer_credentials(attributes)

def create_wazuh_indexer_client(connector_name: str) -> Elasticsearch:
    """
    Returns an Elasticsearch client for the Wazuh Indexer service.

    Returns:
        Elasticsearch: Elasticsearch client for the Wazuh Indexer service.
    """
    attributes = get_connector_info_from_db(connector_name)
    if attributes is None:
        logger.error("No Wazuh Indexer connector found in the database")
        return None
    return Elasticsearch(
        [attributes["connector_url"]],
        http_auth=(attributes["connector_username"], attributes["connector_password"]),
        verify_certs=False,
        timeout=15,
        max_retries=10,
        retry_on_timeout=False,
    )

def format_node_allocation(node_allocation):
        """
        Format the node allocation details into a list of dictionaries. Each dictionary contains disk used, disk available, total disk, disk
        usage percentage, and node name.

        Args:
            node_allocation: Node allocation details from Elasticsearch.

        Returns:
            list: A list of dictionaries containing formatted node allocation details.
        """
        return [
            {
                "disk_used": node["disk.used"],
                "disk_available": node["disk.avail"],
                "disk_total": node["disk.total"],
                "disk_percent": node["disk.percent"],
                "node": node["node"],
            }
            for node in node_allocation
        ]

def format_indices_stats(indices_stats):
        """
        Format the indices stats details into a list of dictionaries. Each dictionary contains the index name, the number of documents in the index,
        the size of the index, and the number of shards in the index.

        Args:
            indices_stats: Indices stats details from Elasticsearch.

        Returns:
            list: A list of dictionaries containing formatted indices stats details.
        """
        return [
            {
                "index": index["index"],
                "docs_count": index["docs.count"],
                "store_size": index["store.size"],
                "replica_count": index["rep"],
                "health": index["health"],
            }
            for index in indices_stats
        ]

def format_shards(shards):
        """
        Format the shards details into a list of dictionaries. Each dictionary contains the index name, the shard number, the shard state, the shard
        size, and the node name.

        Args:
            shards: Shards details from Elasticsearch.

        Returns:
            list: A list of dictionaries containing formatted shards details.
        """
        return [
            {
                "index": shard["index"],
                "shard": shard["shard"],
                "state": shard["state"],
                "size": shard["store"],
                "node": shard["node"],
            }
            for shard in shards
        ]

def collect_indices() -> Indices:
    """
    Collects the indices from Elasticsearch.

    Returns:
        dict: A dictionary containing the indices, shards, and indices stats.
    """
    logger.info("Collecting indices from Elasticsearch")
    es = create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        indices_dict = es.indices.get_alias("*")
        indices_list = list(indices_dict.keys())
        # Check if the index is valid
        index_config = IndexConfigModel()
        indices_list = [index for index in indices_list if index_config.is_valid_index(index)]
        return Indices(indices_list=indices_list, success=True, message="Indices collected successfully")
    except Exception as e:
        logger.error(f"Failed to collect indices: {e}")
        return Indices(message="Failed to collect indices", success=False)

class AlertsQueryBuilder:
    @staticmethod
    def _get_time_range_start(timerange: str) -> str:
        """
        Determines the start time of the time range based on the current time and the provided timerange.

        Args:
            timerange (str): The time range to collect alerts from. This is a string like "24h", "1w", etc.

        Returns:
            str: A string representing the start time of the time range in ISO format.
        """
        if timerange.endswith("h"):
            delta = timedelta(hours=int(timerange[:-1]))
        elif timerange.endswith("d"):
            delta = timedelta(days=int(timerange[:-1]))
        elif timerange.endswith("w"):
            delta = timedelta(weeks=int(timerange[:-1]))
        else:
            raise ValueError("Invalid timerange format. Expected a string like '24h', '1d', '1w', etc.")

        start = datetime.utcnow() - delta
        return start.isoformat() + "Z"  # Elasticsearch expects the time in ISO format with a Z at the end

    def __init__(self):
        self.query = {
            "query": {
                "bool": {
                    "must": [],
                },
            },
            "sort": [],
        }

    def add_time_range(self, timerange: str, timestamp_field: str):
        start = self._get_time_range_start(timerange)
        self.query["query"]["bool"]["must"].append({"range": {timestamp_field: {"gte": start, "lte": "now"}}})
        return self

    def add_matches(self, matches: Iterable[Tuple[str, str]]):
        for field, value in matches:
            self.query["query"]["bool"]["must"].append({"match": {field: value}})
        return self
    
    def add_match_phrase(self, matches: Iterable[Tuple[str, str]]):
        for field, value in matches:
            self.query["query"]["bool"]["must"].append({"match_phrase": {field: value}})
        return self

    def add_range(self, field: str, value: str):
        self.query["query"]["bool"]["must"].append({"range": {field: {"gte": value}}})
        return self

    def add_sort(self, field: str, order: str = "desc"):
        self.query["sort"].append({field: {"order": order}})
        return self

    def build(self):
        return self.query
    
class LogsQueryBuilder:
    @staticmethod
    def _get_time_range_start(timerange: str) -> str:
        """
        Determines the start time of the time range based on the current time and the provided timerange.

        Args:
            timerange (str): The time range to collect alerts from. This is a string like "24h", "1w", etc.

        Returns:
            str: A string representing the start time of the time range in ISO format.
        """
        if timerange.endswith("m"):
            delta = timedelta(minutes=int(timerange[:-1]))
        elif timerange.endswith("h"):
            delta = timedelta(hours=int(timerange[:-1]))
        elif timerange.endswith("d"):
            delta = timedelta(days=int(timerange[:-1]))
        elif timerange.endswith("w"):
            delta = timedelta(weeks=int(timerange[:-1]))
        else:
            raise ValueError("Invalid timerange format. Expected a string like '24h', '1d', '1w', '1m', etc.")

        start = datetime.utcnow() - delta
        return start.isoformat() + "Z"  # Elasticsearch expects the time in ISO format with a Z at the end

    def __init__(self):
        self.query = {
            "query": {
                "bool": {
                    "must": [],
                },
            },
            "sort": [],
        }

    def add_time_range(self, timerange: str, timestamp_field: str):
        start = self._get_time_range_start(timerange)
        self.query["query"]["bool"]["must"].append({"range": {timestamp_field: {"gte": start, "lte": "now"}}})
        return self

    def add_matches(self, matches: Iterable[Tuple[str, str]]):
        for field, value in matches:
            self.query["query"]["bool"]["must"].append({"match": {field: value}})
        return self
    
    def add_match_phrase(self, matches: Iterable[Tuple[str, str]]):
        for field, value in matches:
            self.query["query"]["bool"]["must"].append({"match_phrase": {field: value}})
        return self

    def add_range(self, field: str, value: str):
        self.query["query"]["bool"]["must"].append({"range": {field: {"gte": value}}})
        return self

    def add_sort(self, field: str, order: str = "desc"):
        self.query["sort"].append({field: {"order": order}})
        return self

    def build(self):
        return self.query
