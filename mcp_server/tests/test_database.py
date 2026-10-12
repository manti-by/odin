import pytest

from mcp_server.tools.database import (
    APPROVED_COLUMNS,
    QUERYABLE_COLUMNS,
    TABLE_NAME_RE,
    _filter_sensitive_columns,
    _validate_column_name,
    _validate_table_name,
)
from mcp_server.tools.database import call_tool as database_call_tool


ALLOWED_TABLES = {"relays_relay", "sensors_sensor"}


class TestTableNameRegex:
    @pytest.mark.parametrize("name", ["relays_relay", "_private", "Table1"])
    def test_table_name_re__accepts_valid_identifiers(self, name):
        assert TABLE_NAME_RE.match(name)

    @pytest.mark.parametrize(
        "name",
        [
            "relays relay",
            "relays-relay",
            'relays"relay',
            "relays;DROP TABLE users",
            "1relays",
            "",
            "relays.relay",
            "public.relays",
        ],
    )
    def test_table_name_re__rejects_everything_else(self, name):
        assert not TABLE_NAME_RE.match(name)


class TestValidateTableName:
    def test_validate_table_name__returns_a_known_table(self):
        assert _validate_table_name("relays_relay", ALLOWED_TABLES) == "relays_relay"

    def test_validate_table_name__rejects_an_unknown_table(self):
        with pytest.raises(ValueError, match="Table not found"):
            _validate_table_name("auth_user", ALLOWED_TABLES)

    def test_validate_table_name__rejects_injection_attempts(self):
        for name in ("relays_relay; DROP TABLE users", "relays relay", "relays;DROP"):
            with pytest.raises(ValueError, match="Invalid table name"):
                _validate_table_name(name, ALLOWED_TABLES | {name})

    def test_validate_table_name__an_empty_allow_list_rejects_everything(self):
        """A guard that passes on an empty allow-list is not a guard."""
        with pytest.raises(ValueError, match="Table not found"):
            _validate_table_name("relays_relay", set())


class TestValidateColumnName:
    def test_validate_column_name__returns_an_approved_column(self):
        assert _validate_column_name("relay_id", {"relay_id", "name"}) == "relay_id"

    def test_validate_column_name__rejects_an_unknown_column(self):
        with pytest.raises(ValueError, match="Column not found"):
            _validate_column_name("secret_column", {"relay_id"})

    def test_validate_column_name__rejects_an_injection_attempt(self):
        with pytest.raises(ValueError, match="Invalid column name"):
            _validate_column_name('id" = $1 OR "1', {"id"})

    @pytest.mark.parametrize("column", ["password_hash", "client_secret", "ssn", "api_key"])
    def test_validate_column_name__rejects_unapproved_columns_present_in_the_table(self, column):
        """A real column the allow-list omits must still be refused as a filter."""
        with pytest.raises(ValueError, match="not approved"):
            _validate_column_name(column, {column, "id"})


class TestFilterSensitiveColumns:
    def test_filter_sensitive_columns__keeps_only_approved_columns(self):
        row = {"id": 1, "password_hash": "x", "client_secret": "y", "relay_id": "PUMP"}
        assert _filter_sensitive_columns(row) == {"id": 1, "relay_id": "PUMP"}

    def test_filter_sensitive_columns__drops_columns_it_has_never_heard_of(self):
        """Allow-list semantics: an unknown column is denied by default."""
        assert _filter_sensitive_columns({"id": 1, "brand_new_secret": "leak"}) == {"id": 1}

    def test_filter_sensitive_columns__an_approved_row_is_unchanged(self):
        row = {"id": 1, "name": "pump", "relay_id": "PUMP"}
        assert _filter_sensitive_columns(row) == row

    def test_approved_columns__cover_the_columns_the_tools_actually_use(self):
        assert {"id", "relay_id", "name", "state", "mode", "sensor_id", "temp"} <= APPROVED_COLUMNS

    def test_queryable_columns__match_the_approved_set(self):
        assert QUERYABLE_COLUMNS == APPROVED_COLUMNS

    def test_approved_columns__contain_no_obvious_secrets(self):
        for secret in ("password", "password_hash", "secret", "client_secret", "token", "api_key"):
            assert secret not in APPROVED_COLUMNS, secret

    @pytest.mark.parametrize(
        "column",
        ["password", "token", "session_data", "raw_body", "encoded_headers", "client_secret", "password_hash"],
    )
    def test_approved_columns__withhold_credential_channels(self, column):
        """Session blobs and raw request payloads can carry cookies or headers."""
        assert column not in APPROVED_COLUMNS, column


class TestCallToolValidation:
    """The database-backed tools are exercised here only up to argument checks."""

    @pytest.mark.parametrize("tool", ["get_table_definition", "get_table_count", "query_table"])
    async def test_call_tool__requires_a_table_name(self, tool, monkeypatch):
        async def _unreachable():
            raise AssertionError("the pool must not be opened for an invalid argument")

        monkeypatch.setattr("mcp_server.tools.database.get_db_pool", _unreachable)
        result = await database_call_tool(tool, {})
        assert result.is_error is True
        assert "table_name is required" in result.content[0].text

    async def test_call_tool__unknown_tool(self):
        result = await database_call_tool("database_nope", {})
        assert result.is_error is True
        assert "Unknown tool" in result.content[0].text
