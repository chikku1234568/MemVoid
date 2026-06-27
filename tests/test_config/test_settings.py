from __future__ import annotations

from mem_void.config import Settings


class TestSettings:
    def test_defaults(self) -> None:
        settings = Settings(_env_file=None)
        assert settings.neo4j_uri == "bolt://localhost:7687"
        assert settings.neo4j_user == "neo4j"
        assert settings.neo4j_database == "neo4j"

    def test_constructor_override(self) -> None:
        settings = Settings(
            neo4j_uri="bolt://example.com:7687",
            neo4j_user="admin",
            neo4j_password="secret",
            _env_file=None,
        )
        assert settings.neo4j_uri == "bolt://example.com:7687"
        assert settings.neo4j_user == "admin"
        assert settings.neo4j_password == "secret"

    def test_empty_password_by_default(self) -> None:
        settings = Settings(_env_file=None)
        assert settings.neo4j_password == ""
