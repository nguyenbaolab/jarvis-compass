"""Định nghĩa cuối của mỗi RPC mà client.py gọi không được là void."""

from pathlib import Path
import re


def _rpc_names(source: str) -> list[str]:
    names: list[str] = []
    cursor = 0
    needle = ".rpc("
    while True:
        found = source.find(needle, cursor)
        if found < 0:
            return names
        rest = source[found + len(needle) :]
        index = 0
        while index < len(rest) and rest[index] in " \t\r\n":
            index += 1
        if index < len(rest) and rest[index] == '"':
            end = rest.find('"', index + 1)
            if end > index:
                names.append(rest[index + 1 : end])
        cursor = found + len(needle)


def _apply_migration(sql: str, filename: str, state: dict[str, tuple[str, str]]) -> None:
    pattern = re.compile(
        r"drop\s+function\s+(?:if\s+exists\s+)?public\.([A-Za-z_][A-Za-z0-9_]*)\s*\("
        r"|create\s+(?:or\s+replace\s+)?function\s+public\.([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        re.IGNORECASE,
    )
    for match in pattern.finditer(sql):
        dropped = match.group(1)
        if dropped is not None:
            state.pop(dropped, None)
            continue
        created = match.group(2)
        close = _closing_paren(sql, match.end() - 1)
        type_match = re.match(
            r"\s*returns\s+([A-Za-z_][A-Za-z0-9_]*)",
            sql[close + 1 :],
            re.IGNORECASE,
        )
        if type_match is None or created is None:
            state.pop(created, None)
            continue
        state[created] = (type_match.group(1).lower(), filename)


def _closing_paren(sql: str, open_index: int) -> int:
    depth = 0
    for index in range(open_index, len(sql)):
        if sql[index] == "(":
            depth += 1
        elif sql[index] == ")":
            depth -= 1
            if depth == 0:
                return index
    return len(sql) - 1


def rpc_definition_errors(migrations_dir: Path, client_path: Path) -> list[str]:
    names = _rpc_names(client_path.read_text(encoding="utf-8"))
    state: dict[str, tuple[str, str]] = {}
    for path in sorted(migrations_dir.glob("*.sql"), key=lambda item: item.name):
        _apply_migration(path.read_text(encoding="utf-8"), path.name, state)
    errors: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        defined = state.get(name)
        if defined is None:
            errors.append(f"{name}: không còn định nghĩa")
            continue
        return_type, filename = defined
        if return_type == "void":
            errors.append(f"{name}: định nghĩa cuối trong {filename} là void")
    return errors


def test_latest_rpc_definitions_are_not_void() -> None:
    root = Path(__file__).resolve().parents[1]
    client = root / "src" / "db" / "client.py"
    names = _rpc_names(client.read_text(encoding="utf-8"))
    assert names
    assert "claim_telegram_update" in names
    errors = rpc_definition_errors(root / "supabase" / "migrations", client)
    assert errors == []


def test_void_definition_is_rejected(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001.sql").write_text(
        "create function public.f() returns void language plpgsql as $$ begin end; $$;\n",
        encoding="utf-8",
    )
    client = tmp_path / "client.py"
    client.write_text('await client.rpc("f").execute()\n', encoding="utf-8")
    errors = rpc_definition_errors(migrations, client)
    assert any("f" in error for error in errors)


def test_boolean_after_drop_is_accepted(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001.sql").write_text(
        "create function public.f() returns void;\n",
        encoding="utf-8",
    )
    (migrations / "002.sql").write_text(
        "drop function public.f();\ncreate function public.f() returns boolean;\n",
        encoding="utf-8",
    )
    client = tmp_path / "client.py"
    client.write_text('await client.rpc("f").execute()\n', encoding="utf-8")
    assert rpc_definition_errors(migrations, client) == []


def test_missing_definition_is_rejected(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    client = tmp_path / "client.py"
    client.write_text('await client.rpc("khong_co").execute()\n', encoding="utf-8")
    errors = rpc_definition_errors(migrations, client)
    assert any("khong_co" in error for error in errors)


def test_multiline_rpc_call_is_found(tmp_path: Path) -> None:
    source = 'await client.rpc(\n    "g",\n    {"a": 1},\n).execute()\n'
    assert "g" in _rpc_names(source)
