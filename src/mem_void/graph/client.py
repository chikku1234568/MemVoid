from __future__ import annotations

from neo4j import Driver, GraphDatabase, Session

from mem_void.config import Settings


class Neo4jClient:
    """Thin wrapper around neo4j.Driver with session management.

    Usage:
        settings = Settings()
        client = Neo4jClient(settings)
        assert client.health_check()
        with client.session() as session:
            session.run("RETURN 1")
        client.close()
    """

    def __init__(self, settings: Settings) -> None:
        self._driver: Driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        self._database: str = settings.neo4j_database

    @property
    def database(self) -> str:
        return self._database

    def health_check(self) -> bool:
        """Verify the driver can reach the Neo4j server."""
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def session(self, **kwargs: object) -> Session:
        """Get a session. Connection pooling is handled by the driver."""
        return self._driver.session(database=self._database, **kwargs)  # type: ignore[arg-type]

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> Neo4jClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
