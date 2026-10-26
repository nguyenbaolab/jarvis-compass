"""Cờ --fail-on-skip: phiên mã 0 vẫn thất bại khi có test bị skip."""

import pytest


def exit_code_for_skips(skip_count: int, current_code: int) -> int:
    """Mã khác 0 giữ nguyên. Mã 0 mà có ít nhất một skip thì trả 6."""

    if current_code != 0:
        return current_code
    if skip_count > 0:
        return 6
    return current_code


def pytest_addoption(parser: pytest.Parser) -> None:
    """Thêm cờ. Không truyền cờ thì pytest giữ hành vi cũ."""

    parser.addoption(
        "--fail-on-skip",
        action="store_true",
        default=False,
        help="Fail with exit code 6 when a passing run still skipped tests.",
    )


def _ensure_skip_reasons(config: pytest.Config) -> None:
    """In lý do skip giống -rs. a/A đã gồm skip nên không thêm nữa."""

    chars = config.option.reportchars
    if "a" not in chars and "A" not in chars and "s" not in chars:
        config.option.reportchars = chars + "s"
    reporter = config.pluginmanager.getplugin("terminalreporter")
    if reporter is None:
        return
    current = reporter.reportchars
    if "s" not in current:
        reporter.reportchars = current + "s"


def _skipped_tests(session: pytest.Session) -> int:
    """Đếm báo cáo skip đưa vào tóm tắt. xfail nằm ở nhóm khác, không đếm."""

    reporter = session.config.pluginmanager.getplugin("terminalreporter")
    if reporter is None:
        return 0
    reports = reporter.stats.get("skipped", [])
    count = 0
    for report in reports:
        if getattr(report, "count_towards_summary", True):
            count = count + 1
    return count


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    """Có cờ thì bật lý do skip. Không có cờ thì không đổi cấu hình."""

    if not config.getoption("fail_on_skip"):
        return
    _ensure_skip_reasons(config)


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Mã 0 và có skip thì in một dòng ASCII rồi đặt mã 6."""

    if not session.config.getoption("fail_on_skip"):
        return
    # exitstatus là mã lúc gọi hook. session.exitstatus là mã sau hook trước đó.
    current_code = int(session.exitstatus)
    if current_code == 0 and int(exitstatus) != 0:
        current_code = int(exitstatus)
    skip_count = _skipped_tests(session)
    new_code = exit_code_for_skips(skip_count, current_code)
    if new_code == current_code:
        return
    session.exitstatus = new_code
    line = f"fail-on-skip: {skip_count} test(s) skipped"
    reporter = session.config.pluginmanager.getplugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(line)
        return
    print(line, flush=True)
