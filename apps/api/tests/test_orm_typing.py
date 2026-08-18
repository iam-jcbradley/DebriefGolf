import pytest

from app.core.orm_typing import col, persisted


class TestPersisted:
    def test_returns_the_value_when_not_none(self) -> None:
        assert persisted(5) == 5

    def test_falsy_but_valid_value_is_not_mistaken_for_none(self) -> None:
        # Guards against a future `if not id_` regression — 0 is a real,
        # persisted primary key, not an absent one.
        assert persisted(0) == 0

    def test_raises_on_none(self) -> None:
        with pytest.raises(AssertionError):
            persisted(None)


class TestCol:
    def test_returns_its_argument_unchanged(self) -> None:
        sentinel = object()
        assert col(sentinel) is sentinel
