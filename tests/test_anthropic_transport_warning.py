"""Bộ lọc cảnh báo transport Emscripten. Không dựng client và không mở mạng."""

import importlib
import warnings

import clients.anthropic_model as anthropic_model

_PREFIX = "The following transport option(s) are not supported on Emscripten"


def test_emscripten_transport_warning_is_filtered_and_another_is_kept() -> None:
    # Pytest khôi phục bộ lọc sau lúc import lúc collect, nên nạp lại module trong test.
    importlib.reload(anthropic_model)
    with warnings.catch_warnings(record=True) as ignored:
        warnings.warn(
            _PREFIX + " and will be ignored: limits, socket_options.",
            UserWarning,
        )
    assert ignored == []
    with warnings.catch_warnings(record=True) as kept:
        warnings.warn("một cảnh báo khác", UserWarning)
    assert len(kept) == 1
    assert kept[0].category is UserWarning
    assert str(kept[0].message) == "một cảnh báo khác"
