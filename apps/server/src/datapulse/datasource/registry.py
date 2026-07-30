from collections.abc import Iterable

from datapulse.datasource.connector import Connector
from datapulse.datasource.models import ConnectorType


class ConnectorNotFound(LookupError):
    pass


class ConnectorAlreadyRegistered(ValueError):
    pass


class ConnectorRegistry:
    def __init__(self, connectors: Iterable[Connector] = ()) -> None:
        self._connectors: dict[ConnectorType, Connector] = {}
        for connector in connectors:
            if connector.type in self._connectors:
                raise ConnectorAlreadyRegistered(connector.type.value)
            self._connectors[connector.type] = connector

    def get(self, connector_type: ConnectorType | str) -> Connector:
        try:
            normalized = ConnectorType(connector_type)
            return self._connectors[normalized]
        except (ValueError, KeyError) as error:
            raise ConnectorNotFound(str(connector_type)) from error
