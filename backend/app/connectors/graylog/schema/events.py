from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel


class Provider(BaseModel):
    require_values: bool
    template: str
    type: str


class FieldSpecItem(BaseModel):
    data_type: str
    providers: List[Provider]


class Conditions(BaseModel):
    expression: Optional[str]


class Config(BaseModel):
    conditions: Conditions
    execute_every_ms: int
    group_by: List[str]
    query: str
    query_parameters: List[str]
    search_within_ms: int
    series: List[str]
    streams: List[str]
    type: str


class NotificationSettings(BaseModel):
    backlog_size: int
    grace_period_ms: int


class Storage(BaseModel):
    streams: List[str]
    type: str


class EventDefinition(BaseModel):
    _scope: str
    alert: bool
    config: Config
    description: str
    field_spec: Dict[str, FieldSpecItem]
    id: str
    key_spec: List[str]
    notification_settings: NotificationSettings
    notifications: Optional[List[Dict[str, Union[str, None]]]]
    priority: int
    storage: List[Storage]
    title: str


class GraylogEventDefinitionsResponse(BaseModel):
    event_definitions: List[EventDefinition]
    message: str
    success: bool


class AlertQuery(BaseModel):
    query: Optional[str] = ""
    page: int = 1
    per_page: int = 100
    filter: Optional[Dict[str, Union[str, List[str]]]] = {"alerts": "only", "event_definitions": []}
    timerange: Optional[Dict[str, Union[int, str]]] = {"range": 86400, "type": "relative"}


class SimplifiedEventDefinition(BaseModel):
    description: str
    id: str
    title: str


class Stream(BaseModel):
    description: str
    id: str
    title: str


class Context(BaseModel):
    event_definitions: Dict[str, SimplifiedEventDefinition]
    streams: Dict[str, Stream]


class Event(BaseModel):
    alert: bool
    event_definition_id: str
    event_definition_type: str
    fields: Dict[str, str]
    group_by_fields: Dict[str, str]
    id: str
    key: Optional[str]
    key_tuple: List[str]
    message: str
    origin_context: str
    priority: int
    source: str
    source_streams: List[str]
    streams: List[str]
    timerange_end: Optional[str]
    timerange_start: Optional[str]
    timestamp: str
    timestamp_processing: str


class AlertEvent(BaseModel):
    event: Event
    index_name: str
    index_type: str


class Filter(BaseModel):
    alerts: str
    event_definitions: List[str]


class Timerange(BaseModel):
    range: int
    type: str


class Parameters(BaseModel):
    page: int
    per_page: int
    query: str
    sort_by: str
    sort_direction: str
    timerange: Timerange
    filter: Filter


class Alerts(BaseModel):
    context: Context
    duration: int
    events: List[AlertEvent]
    parameters: Parameters
    total_events: int
    used_indices: List[str]


class GraylogAlertsResponse(BaseModel):
    alerts: Alerts
    message: str
    success: bool
