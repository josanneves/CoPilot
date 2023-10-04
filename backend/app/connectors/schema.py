from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ConnectorHistoryResponse(BaseModel):
    id: Optional[int]
    connector_id: int
    change_timestamp: datetime
    change_description: str

    class Config:
        orm_mode = True

class ConnectorResponse(BaseModel):
    id: Optional[int]
    connector_name: str
    connector_type: str
    connector_url: str
    connector_last_updated: datetime
    connector_username: Optional[str]
    connector_password: Optional[str]
    connector_api_key: Optional[str]
    connector_description: Optional[str]
    connector_supports: Optional[str]
    connector_configured: bool
    connector_verified: bool
    connector_accepts_api_key: bool
    connector_accepts_username_password: bool
    connector_accepts_file: bool
    history_logs: Optional[List[ConnectorHistoryResponse]]

    class Config:
        orm_mode = True

class ConnectorsListResponse(BaseModel):
    connectors: List[ConnectorResponse]
    success: bool
    message: str

class ConnectorListResponse(BaseModel):
    connector: ConnectorResponse
    success: bool
    message: str

class VerifyConnectorResponse(BaseModel):
    connectionSuccessful: bool
    message: str

class UpdateConnector(BaseModel):
    connector_url: str
    connector_username: Optional[str]
    connector_password: Optional[str]
    connector_api_key: Optional[str]