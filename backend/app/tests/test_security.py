from __future__ import annotations

import pytest

from app.core.security import validate_password_policy


def test_password_policy_accepts_strong_password() -> None:
    validate_password_policy("Sup3rStrong!Pass")


@pytest.mark.parametrize(
    "password",
    [
        "short1!A",
        "alllowercase123!",
        "ALLUPPERCASE123!",
        "NoNumbers!",
        "NoSymbols123",
    ],
)
def test_password_policy_rejects_weak_password(password: str) -> None:
    with pytest.raises(ValueError):
        validate_password_policy(password)
