import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import HTTPException
from loguru import logger

from app.connectors.graylog.routes.monitoring import get_all_event_notifications
from app.connectors.graylog.schema.management import UrlWhitelistEntryResponse
from app.connectors.graylog.schema.monitoring import GraylogEventNotificationsResponse
from app.connectors.graylog.services.collector import get_url_whitelist_entries
from app.connectors.graylog.utils.universal import send_post_request
from app.connectors.graylog.utils.universal import send_put_request
from app.integrations.monitoring_alert.schema.provision import (
    GraylogAlertProvisionConfig,
)
from app.integrations.monitoring_alert.schema.provision import (
    GraylogAlertProvisionFieldSpecItem,
)
from app.integrations.monitoring_alert.schema.provision import (
    GraylogAlertProvisionModel,
)
from app.integrations.monitoring_alert.schema.provision import (
    GraylogAlertProvisionNotification,
)
from app.integrations.monitoring_alert.schema.provision import (
    GraylogAlertProvisionNotificationSettings,
)
from app.integrations.monitoring_alert.schema.provision import (
    GraylogAlertProvisionProvider,
)
from app.integrations.monitoring_alert.schema.provision import (
    GraylogAlertWebhookNotificationModel,
)
from app.integrations.monitoring_alert.schema.provision import (
    GraylogUrlWhitelistEntries,
)
from app.integrations.monitoring_alert.schema.provision import (
    GraylogUrlWhitelistEntryConfig,
)
from app.integrations.monitoring_alert.schema.provision import (
    ProvisionMonitoringAlertRequest,
)
from app.integrations.monitoring_alert.schema.provision import (
    ProvisionWazuhMonitoringAlertResponse,
)

load_dotenv()
import uuid


async def convert_seconds_to_milliseconds(seconds: int) -> int:
    """
    Convert seconds to milliseconds.

    Args:
        seconds (int): The seconds to convert.

    Returns:
        int: The milliseconds.
    """
    return seconds * 1000


async def generate_random_id() -> str:
    """
    Generate a random id.

    Returns:
        str: The random id.
    """
    return str(uuid.uuid4())


async def check_if_url_whitelist_entry_exists(url: str) -> bool:
    """
    Check if the url whitelist entry exists.

    Args:
        url (str): The url to check.

    Returns:
        bool: True if the url whitelist entry exists, False otherwise.
    """
    url_whitelist_entries_response = await get_url_whitelist_entries()
    if not url_whitelist_entries_response.success:
        raise HTTPException(status_code=500, detail="Failed to collect url whitelist entries")
    url_whitelist_entries_response = UrlWhitelistEntryResponse(**url_whitelist_entries_response.dict())
    logger.info(f"Url whitelist entries collected: {url_whitelist_entries_response.url_whitelist_entries}")
    if url in [url_whitelist_entry.value for url_whitelist_entry in url_whitelist_entries_response.url_whitelist_entries.entries]:
        logger.info(f"Url whitelist entry {url} already exists")
        return True
    return False


async def get_notification_id(notification_title: str) -> Optional[str]:
    """
    Get the notification id.

    Args:
        notification_title (str): The notification title.

    Returns:
        Optional[str]: The notification id if it exists, None otherwise.
    """
    event_notifications_response = await get_all_event_notifications()
    if not event_notifications_response.success:
        raise HTTPException(status_code=500, detail="Failed to collect event notifications")
    event_notifications_response = GraylogEventNotificationsResponse(**event_notifications_response.dict())
    logger.info(f"Event notifications collected: {event_notifications_response.event_notifications}")
    for event_notification in event_notifications_response.event_notifications.notifications:
        if event_notification.title == notification_title:
            return event_notification.id
    return None


async def build_url_whitelisted_entries(whitelist_url_model: GraylogUrlWhitelistEntryConfig) -> GraylogUrlWhitelistEntries:
    """
    Builds the URL Whitelisted Entries model.

    Returns:
        GraylogUrlWhitelistEntries: The URL Whitelisted Entries model.
    """
    url_whitelist_entries_response = await get_url_whitelist_entries()
    if not url_whitelist_entries_response.success:
        raise HTTPException(status_code=500, detail="Failed to collect url whitelist entries")
    url_whitelist_entries_response = UrlWhitelistEntryResponse(**url_whitelist_entries_response.dict())
    logger.info(f"Url whitelist entries collected: {url_whitelist_entries_response}")
    url_whitelist_entries = url_whitelist_entries_response.url_whitelist_entries.entries
    url_whitelist_entries.append(whitelist_url_model)
    return GraylogUrlWhitelistEntries(
        entries=url_whitelist_entries,
        disabled=False,
    )


async def provision_webhook_url_whitelist(whitelist_url_model: GraylogUrlWhitelistEntries) -> bool:
    """
    Provisions a webhook URL for Graylog.

    Args:
        whitelist_url_model (GraylogUrlWhitelistEntryConfig): The webhook URL model.

    Returns:
        bool: True if the webhook URL was provisioned successfully, False otherwise.
    """
    logger.info(f"Provisioning URL Whitelist: {whitelist_url_model.dict()}")
    response = await send_put_request(endpoint="/api/system/urlwhitelist", data=whitelist_url_model.dict())
    logger.info(f"URL Whitelist provisioned: {response}")
    if response["success"]:
        return True
    raise HTTPException(status_code=500, detail="Failed to provision URL Whitelist")


async def check_if_event_notification_exists(event_notification: str) -> bool:
    """
    Check if the event notification exists.

    Args:
        event_notification (str): The event notification to check.

    Returns:
        bool: True if the event notification exists, False otherwise.
    """
    event_notifications_response = await get_all_event_notifications()
    if not event_notifications_response.success:
        raise HTTPException(status_code=500, detail="Failed to collect event notifications")
    event_notifications_response = GraylogEventNotificationsResponse(**event_notifications_response.dict())
    logger.info(f"Event notifications collected: {event_notifications_response.event_notifications}")
    if event_notification in [
        event_notification.title for event_notification in event_notifications_response.event_notifications.notifications
    ]:
        return True
    return False


async def provision_webhook(webhook_model: GraylogAlertWebhookNotificationModel) -> Optional[str]:
    """
    Provisions a webhook for Graylog alerts.

    Args:
        webhook_model (GraylogAlertWebhookNotificationModel): The webhook model.

    Returns:
        bool: True if the webhook was provisioned successfully, False otherwise.
    """
    response = await send_post_request(endpoint="/api/events/notifications", data=webhook_model.dict())
    if response["success"]:
        logger.info(f"response: {response}")
        return response["data"]["id"]
    raise HTTPException(status_code=500, detail="Failed to provision webhook")


async def provision_alert_definition(alert_definition_model: GraylogAlertProvisionModel) -> bool:
    """
    Provisions an alert definition for Graylog.

    Args:
        alert_definition_model (GraylogAlertProvisionModel): The alert definition model.

    Returns:
        bool: True if the alert definition was provisioned successfully, False otherwise.
    """
    response = await send_post_request(endpoint="/api/events/definitions", data=alert_definition_model.dict())
    if response["success"]:
        return True
    raise HTTPException(status_code=500, detail="Failed to provision alert definition")


async def provision_wazuh_monitoring_alert(request: ProvisionMonitoringAlertRequest) -> ProvisionWazuhMonitoringAlertResponse:
    """
    Provisions Wazuh monitoring alerts.

    Returns:
        ProvisionWazuhMonitoringAlertResponse: The response indicating the success of provisioning the monitoring alerts.
    """
    #
    logger.info(f"Invoking provision_wazuh_monitoring_alert with request: {request.dict()}")
    notification_exists = await check_if_event_notification_exists("SEND TO COPILOT")
    if not notification_exists:
        url_whitelisted = await check_if_url_whitelist_entry_exists(f"http://{os.getenv('SERVER_IP')}:5000/monitoring_alert/create")
        if not url_whitelisted:
            logger.info("Provisioning URL Whitelist")
            whitelisted_urls = await build_url_whitelisted_entries(
                whitelist_url_model=GraylogUrlWhitelistEntryConfig(
                    id=await generate_random_id(),
                    value=f"http://{os.getenv('SERVER_IP')}:5000/monitoring_alert/create",
                    title="SEND TO COPILOT",
                    type="literal",
                ),
            )
            await provision_webhook_url_whitelist(whitelisted_urls)

        logger.info("Provisioning SEND TO COPILOT Webhook")
        notification_id = await provision_webhook(
            GraylogAlertWebhookNotificationModel(
                title="SEND TO COPILOT",
                description="Send alert to Copilot",
                config={"url": f"http://{os.getenv('SERVER_IP')}:5000/monitoring_alert/create", "type": "http-notification-v1"},
            ),
        )
        logger.info(f"SEND TO COPILOT Webhook provisioned with id: {notification_id}")
        await provision_alert_definition(
            GraylogAlertProvisionModel(
                title="WAZUH SYSLOG LEVEL ALERT",
                description="Alert on Wazuh syslog level equal to ALERT",
                priority=2,
                config=GraylogAlertProvisionConfig(
                    type="aggregation-v1",
                    query="syslog_level:ALERT AND syslog_type:wazuh",
                    query_parameters=[],
                    streams=[],
                    group_by=[],
                    series=[],
                    conditions={
                        "expression": None,
                    },
                    search_within_ms=await convert_seconds_to_milliseconds(request.search_within_last),
                    execute_every_ms=await convert_seconds_to_milliseconds(request.execute_every),
                ),
                field_spec={
                    "ALERT_ID": GraylogAlertProvisionFieldSpecItem(
                        data_type="string",
                        providers=[
                            GraylogAlertProvisionProvider(
                                type="template-v1",
                                template="${source._id}",
                                require_values=True,
                            ),
                        ],
                    ),
                    "CUSTOMER_CODE": GraylogAlertProvisionFieldSpecItem(
                        data_type="string",
                        providers=[
                            GraylogAlertProvisionProvider(
                                type="template-v1",
                                template="${source.agent_labels_customer}",
                                require_values=True,
                            ),
                        ],
                    ),
                    "ALERT_SOURCE": GraylogAlertProvisionFieldSpecItem(
                        data_type="string",
                        providers=[
                            GraylogAlertProvisionProvider(
                                type="template-v1",
                                template="WAZUH",
                                require_values=True,
                            ),
                        ],
                    ),
                },
                key_spec=[],
                notification_settings=GraylogAlertProvisionNotificationSettings(
                    grace_period_ms=0,
                    backlog_size=None,
                ),
                notifications=[
                    GraylogAlertProvisionNotification(
                        notification_id=notification_id,
                    ),
                ],
                alert=True,
            ),
        )

    return ProvisionWazuhMonitoringAlertResponse(success=True, message="Wazuh monitoring alerts provisioned successfully")


async def provision_suricata_monitoring_alert(request: ProvisionMonitoringAlertRequest) -> ProvisionWazuhMonitoringAlertResponse:
    """
    Provisions Suricata monitoring alerts.

    Returns:
        ProvisionWazuhMonitoringAlertResponse: The response indicating the success of provisioning the monitoring alerts.
    """
    #
    logger.info(f"Invoking provision_suricata_monitoring_alert with request: {request.dict()}")
    notification_exists = await check_if_event_notification_exists("SEND TO COPILOT")
    if not notification_exists:
        url_whitelisted = await check_if_url_whitelist_entry_exists(f"http://{os.getenv('SERVER_IP')}:5000/monitoring_alert/create")
        if not url_whitelisted:
            logger.info("Provisioning URL Whitelist")
            whitelisted_urls = await build_url_whitelisted_entries(
                whitelist_url_model=GraylogUrlWhitelistEntryConfig(
                    id=await generate_random_id(),
                    value=f"http://{os.getenv('SERVER_IP')}:5000/monitoring_alert/create",
                    title="SEND TO COPILOT",
                    type="literal",
                ),
            )
            await provision_webhook_url_whitelist(whitelisted_urls)

        logger.info("Provisioning SEND TO COPILOT Webhook")
        notification_id = await provision_webhook(
            GraylogAlertWebhookNotificationModel(
                title="SEND TO COPILOT",
                description="Send alert to Copilot",
                config={"url": f"http://{os.getenv('SERVER_IP')}:5000/monitoring_alert/create", "type": "http-notification-v1"},
            ),
        )
        logger.info(f"SEND TO COPILOT Webhook provisioned with id: {notification_id}")
    notification_id = await get_notification_id("SEND TO COPILOT")
    await provision_alert_definition(
        GraylogAlertProvisionModel(
            title="SURICATA ALERT SEVERITY 1",
            description="Alert on Suricata alerts",
            priority=2,
            config=GraylogAlertProvisionConfig(
                type="aggregation-v1",
                query="alert_severity:1 AND syslog_type:suricata",
                query_parameters=[],
                streams=[],
                group_by=[],
                series=[],
                conditions={
                    "expression": None,
                },
                search_within_ms=await convert_seconds_to_milliseconds(request.search_within_last),
                execute_every_ms=await convert_seconds_to_milliseconds(request.execute_every),
            ),
            field_spec={
                "ALERT_ID": GraylogAlertProvisionFieldSpecItem(
                    data_type="string",
                    providers=[
                        GraylogAlertProvisionProvider(
                            type="template-v1",
                            template="${source._id}",
                            require_values=True,
                        ),
                    ],
                ),
                "CUSTOMER_CODE": GraylogAlertProvisionFieldSpecItem(
                    data_type="string",
                    providers=[
                        GraylogAlertProvisionProvider(
                            type="template-v1",
                            template="${source.agent_labels_customer}",
                            require_values=True,
                        ),
                    ],
                ),
                "ALERT_SOURCE": GraylogAlertProvisionFieldSpecItem(
                    data_type="string",
                    providers=[
                        GraylogAlertProvisionProvider(
                            type="template-v1",
                            template="SURICATA",
                            require_values=True,
                        ),
                    ],
                ),
            },
            key_spec=[],
            notification_settings=GraylogAlertProvisionNotificationSettings(
                grace_period_ms=0,
                backlog_size=None,
            ),
            notifications=[
                GraylogAlertProvisionNotification(
                    notification_id=notification_id,
                ),
            ],
            alert=True,
        ),
    )

    return ProvisionWazuhMonitoringAlertResponse(success=True, message="Suricata monitoring alerts provisioned successfully")
