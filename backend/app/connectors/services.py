import os
from contextlib import contextmanager
from datetime import datetime
from typing import Generator
from typing import List
from typing import Optional
from typing import Type

from fastapi import UploadFile
from loguru import logger
from pydantic import BaseModel
from sqlmodel import Session
from sqlmodel import select
from werkzeug.utils import secure_filename

from app.connectors.cortex.utils.universal import verify_cortex_connection
from app.connectors.dfir_iris.utils.universal import verify_dfir_iris_connection
from app.connectors.graylog.utils.universal import verify_graylog_connection
from app.connectors.models import Connectors
from app.connectors.schema import ConnectorResponse
from app.connectors.shuffle.utils.universal import verify_shuffle_connection
from app.connectors.sublime.utils.universal import verify_sublime_connection
from app.connectors.velociraptor.utils.universal import verify_velociraptor_connection
from app.connectors.wazuh_indexer.utils.universal import verify_wazuh_indexer_connection
from app.connectors.wazuh_manager.utils.universal import verify_wazuh_manager_connection
from app.db.db_session import engine  # Import the shared engine

UPLOAD_FOLDER = "file-store"
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = set(["yaml"])  # replace with your allowed file extensions


# Create an interface for connector services
class ConnectorServiceInterface(BaseModel):
    def verify_authentication(self, connector: ConnectorResponse) -> Optional[ConnectorResponse]:
        raise NotImplementedError


# Wazuh Manager Service
class WazuhManagerService(ConnectorServiceInterface):
    def verify_authentication(self, connector: ConnectorResponse) -> Optional[ConnectorResponse]:
        return verify_wazuh_manager_connection(connector.connector_name)


# Wazuh Indexer Service
class WazuhIndexerService(ConnectorServiceInterface):
    def verify_authentication(self, connector: ConnectorResponse) -> Optional[ConnectorResponse]:
        return verify_wazuh_indexer_connection(connector.connector_name)


# Velociraptor Service
class VelociraptorService(ConnectorServiceInterface):
    def verify_authentication(self, connector: ConnectorResponse) -> Optional[ConnectorResponse]:
        return verify_velociraptor_connection(connector.connector_name)


# Graylog Service
class GraylogService(ConnectorServiceInterface):
    def verify_authentication(self, connector: ConnectorResponse) -> Optional[ConnectorResponse]:
        return verify_graylog_connection(connector.connector_name)


# DFIR-IRIS Service
class DfirIrisService(ConnectorServiceInterface):
    def verify_authentication(self, connector: ConnectorResponse) -> Optional[ConnectorResponse]:
        return verify_dfir_iris_connection(connector.connector_name)


# Cortex Service
class CortexService(ConnectorServiceInterface):
    def verify_authentication(self, connector: ConnectorResponse) -> Optional[ConnectorResponse]:
        return verify_cortex_connection(connector.connector_name)


# Shuffle Service
class ShuffleService(ConnectorServiceInterface):
    def verify_authentication(self, connector: ConnectorResponse) -> Optional[ConnectorResponse]:
        return verify_shuffle_connection(connector.connector_name)


# Sublime Service
class SublimeService(ConnectorServiceInterface):
    def verify_authentication(self, connector: ConnectorResponse) -> Optional[ConnectorResponse]:
        return verify_sublime_connection(connector.connector_name)


# Factory function to create a service instance based on connector name
def get_connector_service(connector_name: str) -> Type[ConnectorServiceInterface]:
    service_map = {
        "Wazuh-Manager": WazuhManagerService,
        "Wazuh-Indexer": WazuhIndexerService,
        "Velociraptor": VelociraptorService,
        "Graylog": GraylogService,
        "DFIR-IRIS": DfirIrisService,
        "Cortex": CortexService,
        "Shuffle": ShuffleService,
        "Sublime": SublimeService,
    }
    return service_map.get(connector_name, None)


class ConnectorServices:
    """
    Service class for handling operations related to connectors.
    """

    @staticmethod
    @contextmanager
    def get_session() -> Generator[Session, None, None]:
        """
        Get a new session for database interaction.

        This method is a context manager, which ensures that the session is closed
        once the operations within the context are completed.

        Yields:
            Session: The database session object.
        """
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    @classmethod
    def fetch_all_connectors(cls) -> List[ConnectorResponse]:
        """
        Fetch all connectors from the database.

        This method retrieves all connector records from the database, converts them
        to Pydantic models, and returns them as a list.

        Returns:
            List[ConnectorResponse]: A list of connectors in their Pydantic representation.
        """
        # Get a new session
        with cls.get_session() as session:
            query = select(Connectors)
            connectors = session.exec(query).all()

            # Convert the SQLModel object to a Pydantic model
            connector_responses = [ConnectorResponse.from_orm(connector) for connector in connectors]
            return connector_responses

    @classmethod
    def fetch_connector_by_id(cls, connector_id: int) -> Optional[ConnectorResponse]:
        """
        Fetch a connector by its ID from the database.

        Given a connector ID, this method retrieves the corresponding connector
        record from the database, if it exists.

        Args:
            connector_id (int): The ID of the connector to fetch.

        Returns:
            Optional[ConnectorResponse]: The connector in its Pydantic representation, or None if not found.
        """
        # Get a new session
        with cls.get_session() as session:
            query = select(Connectors).where(Connectors.id == connector_id)
            connector = session.exec(query).first()

            if not connector:
                logger.info(f"No connector found for ID: {connector_id}")
                return None

            try:
                # Convert the SQLModel object to a Pydantic model
                connector_response = ConnectorResponse.from_orm(connector)
                return connector_response
            except Exception as e:
                logger.exception(f"Failed to create ConnectorResponse object: {e}")
                return None

    @classmethod
    def verify_connector_by_id(cls, connector_id: int) -> Optional[ConnectorResponse]:
        """
        Verify a connector by making an API call to it.

        Given a connector ID, this method retrieves the corresponding connector
        record from the database, if it exists, and makes an API call to the connector.

        Args:
            connector_id (int): The ID of the connector to verify.

        Returns:
            Optional[ConnectorResponse]: The connector in its Pydantic representation, or None if not found.
        """
        # Get a new session
        with cls.get_session() as session:
            query = select(Connectors).where(Connectors.id == connector_id)
            connector = session.exec(query).first()

            if not connector:
                logger.info(f"No connector found for ID: {connector_id}")
                return None

            try:
                # Convert the SQLModel object to a Pydantic model
                connector_response = ConnectorResponse.from_orm(connector)

                # Get the appropriate service for this connector
                ServiceClass = get_connector_service(connector_response.connector_name)

                if ServiceClass is not None:
                    service_instance = ServiceClass()
                    connector_response = service_instance.verify_authentication(connector_response)
                else:
                    logger.error(f"Connector type {connector_response.connector_name} is not supported")
                    return None

                return connector_response
            except Exception as e:
                logger.exception(f"Failed to create ConnectorResponse object: {e}")
                return None

    @classmethod
    def update_connector_by_id(cls, connector_id: int, connector: ConnectorResponse) -> Optional[ConnectorResponse]:
        """
        Update a connector by its ID in the database.

        Given a connector ID and a Pydantic representation of a connector, this method
        updates the corresponding connector record in the database, if it exists.

        Args:
            connector_id (int): The ID of the connector to update.
            connector (ConnectorResponse): The updated connector in its Pydantic representation.

        Returns:
            Optional[ConnectorResponse]: The updated connector in its Pydantic representation, or None if not found.
        """
        # Get a new session
        with cls.get_session() as session:
            query = select(Connectors).where(Connectors.id == connector_id)
            connector_record = session.exec(query).first()

            if not connector_record:
                logger.info(f"No connector found for ID: {connector_id}")
                return None

            try:
                # Update the connector record
                connector_record.connector_url = connector.connector_url
                connector_record.connector_username = connector.connector_username
                connector_record.connector_password = connector.connector_password
                connector_record.connector_api_key = connector.connector_api_key
                connector_record.connector_last_updated = datetime.now()

                # Commit the changes to the database
                session.add(connector_record)
                session.commit()

                # Convert the SQLModel object to a Pydantic model
                connector_response = ConnectorResponse.from_orm(connector_record)
                return connector_response
            except Exception as e:
                logger.exception(f"Failed to update connector: {e}")
                return None

    @staticmethod
    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    @classmethod
    def save_file(cls, file: UploadFile):
        if file and cls.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)

            # Save the file
            with open(file_path, "wb") as buffer:
                buffer.write(file.file.read())

            # Update connector
            connector = cls.fetch_connector_by_id(6)
            connector.connector_configured = True
            connector.connector_api_key = file_path
            cls.update_connector_by_id(6, connector)

            connector_response = ConnectorResponse.from_orm(connector)
            return connector_response
        else:
            return False