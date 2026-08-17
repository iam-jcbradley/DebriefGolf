import pytest

from app.core.orm_typing import col, persisted


class TestPersisted:
    def test_returns_the_value_when_not_none(self) -> None:
        assert persisted(5) == 5

    def test_raises_on_none(self) -> None:
        with pytest.raises(AssertionError):
            persisted(None)


class TestCol:
    def test_returns_its_argument_unchanged(self) -> None:
        sentinel = object()
        assert col(sentinel) is sentinel
