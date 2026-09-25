"""Registration email checks: format, Gmail username rules, typos, mail server, throwaways."""

import pytest
from email_validator import EmailUndeliverableError

from app.config import get_settings
from app.services import email_checks
from conftest import register


def _register(client, name, email):
    return client.post("/api/v1/auth/register", json={
        "username": name, "email": email, "password": "correct-horse-1"})


# ---------------------------------------------------------------- Gmail rules

@pytest.mark.parametrize("email", [
    "keerthitummanapalli@gmail.com", "first.last@gmail.com", "abc123@gmail.com",
    "someone+codebox@gmail.com", "Mixed.Case99@Gmail.com", "legacyuser@googlemail.com",
])
def test_valid_gmail_addresses_register_and_sign_in(client, email):
    response = _register(client, "user" + str(abs(hash(email)) % 10_000), email)
    assert response.status_code == 201, response.text
    assert response.json()["access_token"]  # signed in straight away, no code


@pytest.mark.parametrize("local,reason", [
    ("abc", "6-30 characters"),                       # too short
    ("a" * 31, "6-30 characters"),                    # too long
    ("first..last", "two dots in a row"),
    (".leading", "start or end with a dot"),
    ("trailing.", "start or end with a dot"),
    ("under_score", "only contain letters, numbers and dots"),
    ("dash-name", "only contain letters, numbers and dots"),
])
def test_invalid_gmail_usernames_are_rejected(client, local, reason):
    response = _register(client, "gmailcheck", f"{local}@gmail.com")
    assert response.status_code == 422
    detail = response.json()["detail"]
    if isinstance(detail, str):  # our Gmail check
        assert detail.startswith("This isn't a valid Gmail address") and reason in detail
    else:  # generic email syntax check (e.g. dot placement) rejected it first
        assert detail[0]["loc"][-1] == "email"


def test_gmail_rule_messages():
    assert email_checks.gmail_problem("abcdef") is None
    assert email_checks.gmail_problem("abcdef+anything.goes") is None
    assert "6-30" in email_checks.gmail_problem("abc")
    assert "two dots" in email_checks.gmail_problem("ab..cdef")


# ---------------------------------------------------------------- typos

@pytest.mark.parametrize("domain,suggestion", [
    ("gmal.co", "gmail.com"), ("gmial.com", "gmail.com"), ("gmail.co", "gmail.com"),
    ("hotmial.com", "hotmail.com"), ("outlok.com", "outlook.com"), ("yaho.com", "yahoo.com"),
])
def test_typo_domains_get_a_suggestion(client, domain, suggestion):
    response = _register(client, "typo", f"keerthi@{domain}")
    assert response.status_code == 422
    assert f"Did you mean keerthi@{suggestion}?" in response.json()["detail"]


@pytest.mark.parametrize("domain", ["gmail.com", "mail.com", "gmx.com", "ymail.com", "me.com",
                                    "bvrithyderabad.edu.in", "example.org", "yopmail.com"])
def test_real_or_throwaway_domains_are_not_flagged_as_typos(domain):
    assert email_checks.suggest_domain(domain) is None


# ---------------------------------------------------------------- mail server

def test_domain_that_does_not_exist_is_rejected(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "email_check_deliverability", True)

    def fake_validate(email, **kwargs):
        assert kwargs["check_deliverability"] is True
        raise EmailUndeliverableError("The domain name no-such-domain-codebox.com does not exist.")

    monkeypatch.setattr(email_checks, "validate_email", fake_validate)
    response = _register(client, "ghost", "ghost@no-such-domain-codebox.com")
    assert response.status_code == 422
    assert "can't receive mail" in response.json()["detail"]


def test_domain_without_mail_server_is_rejected(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "email_check_deliverability", True)

    class Result:
        ascii_domain = "parked-site.com"
        normalized = "k@parked-site.com"
        local_part = "k"
        mx_fallback_type = "A"  # resolves to a website, but no MX record

    monkeypatch.setattr(email_checks, "validate_email", lambda email, **kw: Result())
    response = _register(client, "parked", "k@parked-site.com")
    assert response.status_code == 422
    assert "has no mail server" in response.json()["detail"]


# ---------------------------------------------------------------- throwaways & conflicts

@pytest.mark.parametrize("email", ["temp@mailinator.com", "x@YOPMAIL.com", "y@sub.guerrillamail.com"])
def test_disposable_addresses_are_rejected(client, email):
    response = _register(client, "tempuser", email)
    assert response.status_code == 422
    assert "Disposable" in response.json()["detail"]


def test_email_is_normalised(client, db):
    from sqlalchemy import select

    from app.models import User

    assert _register(client, "norm", "Norm@EXAMPLE.com").status_code == 201
    assert db.scalar(select(User.email).where(User.username == "norm")) == "norm@example.com"


def test_conflict_messages_say_what_is_taken(client):
    register(client, "taken", email="taken@example.com")
    by_name = _register(client, "taken", "other@example.com")
    by_email = _register(client, "other", "taken@example.com")
    assert by_name.status_code == by_email.status_code == 409
    assert "username is already taken" in by_name.json()["detail"]
    assert "email already exists" in by_email.json()["detail"]
