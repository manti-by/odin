import pytest

from mcp_server.tools.logs import MAX_TAIL_LINES, resolve_log_path, tail_file
from mcp_server.tools.logs import call_tool as logs_call_tool


def _write(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class TestResolveLogPath:
    def test_resolve_log_path__resolves_a_nested_file(self, log_root):
        path = _write(log_root, "sessions/abc.log", "x")
        assert resolve_log_path("sessions/abc.log") == path.resolve()

    @pytest.mark.parametrize("name", ["../../../etc/passwd", "/etc/passwd", "sessions/../../../escape.log"])
    def test_resolve_log_path__rejects_escapes(self, log_root, name):
        assert resolve_log_path(name) is None

    def test_resolve_log_path__missing_file_is_none(self, log_root):
        assert resolve_log_path("absent.log") is None

    def test_resolve_log_path__a_directory_is_not_a_log_file(self, log_root):
        (log_root / "sub").mkdir()
        assert resolve_log_path("sub") is None


class TestTailFile:
    def test_tail_file__empty_file_returns_empty_string(self, tmp_path):
        path = tmp_path / "empty.log"
        path.write_text("", encoding="utf-8")
        assert tail_file(path, 10) == ""

    def test_tail_file__returns_the_last_lines(self, tmp_path):
        path = tmp_path / "a.log"
        path.write_text("a\nb\nc\n", encoding="utf-8")
        assert tail_file(path, 2) == "b\nc"

    def test_tail_file__handles_a_missing_trailing_newline(self, tmp_path):
        path = tmp_path / "a.log"
        path.write_text("a\nb\nc", encoding="utf-8")
        assert tail_file(path, 2) == "b\nc"

    def test_tail_file__single_line_without_newline(self, tmp_path):
        path = tmp_path / "a.log"
        path.write_text("only", encoding="utf-8")
        assert tail_file(path, 5) == "only"

    def test_tail_file__requesting_more_than_exists_returns_everything(self, tmp_path):
        path = tmp_path / "a.log"
        path.write_text("a\nb\nc\n", encoding="utf-8")
        assert tail_file(path, 999) == "a\nb\nc"

    @pytest.mark.parametrize("requested", [0, -5])
    def test_tail_file__clamps_to_at_least_one_line(self, tmp_path, requested):
        path = tmp_path / "a.log"
        path.write_text("a\nb\nc\n", encoding="utf-8")
        assert tail_file(path, requested) == "c"

    def test_tail_file__clamps_to_the_maximum(self, tmp_path):
        path = tmp_path / "big.log"
        path.write_text("".join(f"line{i}\n" for i in range(1, MAX_TAIL_LINES + 50)), encoding="utf-8")
        result = tail_file(path, MAX_TAIL_LINES * 10)
        assert len(result.splitlines()) == MAX_TAIL_LINES

    def test_tail_file__reads_backwards_across_block_boundaries(self, tmp_path):
        """The file is larger than the 8192-byte read block."""
        path = tmp_path / "big.log"
        path.write_text("".join(f"line{i}\n" for i in range(1, 5001)), encoding="utf-8")
        assert tail_file(path, 2) == "line4999\nline5000"

    def test_tail_file__decodes_invalid_utf8_without_raising(self, tmp_path):
        path = tmp_path / "a.log"
        path.write_bytes(b"ok\n\xff\xfe\n")
        assert isinstance(tail_file(path, 2), str)

    def test_tail_file__first_line_is_complete_across_a_block_boundary(self, tmp_path):
        """The first requested line may straddle an 8192-byte read block."""
        path = tmp_path / "long.log"
        path.write_text("A" * 9000 + "\nB\n", encoding="utf-8")
        result = tail_file(path, 2).splitlines()
        assert len(result) == 2
        assert result[0] == "A" * 8189
        assert result[1] == "B"

    def test_tail_file__long_first_line_is_not_truncated_mid_line(self, tmp_path):
        path = tmp_path / "long.log"
        path.write_text("start\n" + "X" * 20000 + "\nsecond\nthird\n", encoding="utf-8")
        assert tail_file(path, 2) == "second\nthird"


class TestCallTool:
    async def test_call_tool__lists_log_files_with_size_and_mtime(self, log_root):
        _write(log_root, "django.log", "hello\n")
        result = await logs_call_tool("list_log_files", {})
        assert result.is_error is False
        assert "django.log" in result.content[0].text
        assert "6 bytes" in result.content[0].text

    async def test_call_tool__lists_nested_log_files(self, log_root):
        _write(log_root, "sessions/abc.log", "x\n")
        result = await logs_call_tool("list_log_files", {})
        assert "sessions/abc.log" in result.content[0].text

    async def test_call_tool__no_log_files_is_not_an_error(self, log_root):
        result = await logs_call_tool("list_log_files", {})
        assert result.is_error is False
        assert result.content[0].text == "No log files found"

    async def test_call_tool__omits_symlinks_pointing_outside_the_root(self, log_root, tmp_path):
        outside = tmp_path / "secret.log"
        outside.write_text("top secret\n", encoding="utf-8")
        (log_root / "escape.log").symlink_to(outside)
        _write(log_root, "real.log", "fine\n")

        result = await logs_call_tool("list_log_files", {})
        listed = result.content[0].text
        assert "real.log" in listed
        assert "escape.log" not in listed
        assert "top secret" not in listed

    async def test_call_tool__missing_log_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr("mcp_server.tools.logs.LOG_ROOT_RESOLVED", tmp_path / "absent")
        result = await logs_call_tool("list_log_files", {})
        assert result.is_error is True
        assert "Log directory not found" in result.content[0].text

    async def test_call_tool__tails_a_file(self, log_root):
        _write(log_root, "django.log", "a\nb\nc\n")
        result = await logs_call_tool("tail_logs", {"file_path": "django.log", "lines": 2})
        assert result.is_error is False
        assert result.content[0].text == "b\nc"

    async def test_call_tool__tail_defaults_to_100_lines(self, log_root):
        _write(log_root, "django.log", "".join(f"line{i}\n" for i in range(300)))
        result = await logs_call_tool("tail_logs", {"file_path": "django.log"})
        assert len(result.content[0].text.splitlines()) == 100

    @pytest.mark.parametrize("arguments", [{}, {"file_path": ""}, {"file_path": None}])
    async def test_call_tool__tail_requires_a_file_path(self, log_root, arguments):
        result = await logs_call_tool("tail_logs", arguments)
        assert result.is_error is True
        assert "file_path is required" in result.content[0].text

    async def test_call_tool__tail_rejects_traversal(self, log_root):
        result = await logs_call_tool("tail_logs", {"file_path": "../../../etc/passwd"})
        assert result.is_error is True
        assert "outside log directory" in result.content[0].text

    async def test_call_tool__unknown_tool(self, log_root):
        result = await logs_call_tool("logs_nope", {})
        assert result.is_error is True
        assert "Unknown tool" in result.content[0].text
