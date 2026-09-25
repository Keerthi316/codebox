"""Email address checks used at registration (no email is ever sent)."""

import re

from email_validator import EmailNotValidError, EmailUndeliverableError, validate_email
from fastapi import HTTPException, status

from ..config import get_settings

# Common throwaway-inbox providers (not exhaustive).
DISPOSABLE_DOMAINS = frozenset({
    "10minutemail.com", "20minutemail.com", "33mail.com", "dispostable.com", "emailondeck.com",
    "fakeinbox.com", "getairmail.com", "getnada.com", "guerrillamail.biz", "guerrillamail.com",
    "guerrillamail.de", "guerrillamail.info", "guerrillamail.net", "guerrillamail.org",
    "guerrillamailblock.com", "sharklasers.com", "grr.la", "harakirimail.com", "inboxkitten.com",
    "mailcatch.com", "maildrop.cc", "mailinator.com", "mailinator.net", "mailnesia.com",
    "mailpoof.com", "mintemail.com", "moakt.com", "mohmal.com", "mytemp.email", "nada.email",
    "spamgourmet.com", "temp-mail.io", "temp-mail.org", "tempail.com", "tempmail.com",
    "tempmail.dev", "tempmail.net", "tempmailo.com", "tempr.email", "throwawaymail.com",
    "trashmail.com", "trashmail.de", "trashmail.net", "yopmail.com", "yopmail.fr", "yopmail.net",
    "emailfake.com", "burnermail.io", "discard.email", "spam4.me", "mail.tm", "mail7.io",
})

# Well-known mailbox providers, used to catch typos such as "gmal.co" -> "gmail.com".
POPULAR_DOMAINS = ("gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.in", "outlook.com",
                   "hotmail.com", "live.com", "icloud.com", "proton.me", "protonmail.com",
                   "aol.com", "zoho.com", "rediffmail.com")
# Real providers that happen to look like typos of the ones above.
KNOWN_PROVIDERS = frozenset(POPULAR_DOMAINS) | {
    "mail.com", "gmx.com", "gmx.net", "ymail.com", "me.com", "mac.com", "msn.com",
    "hotmail.co.uk", "yahoo.co.uk", "outlook.in", "hey.com", "fastmail.com", "tutanota.com"}


def _distance(a: str, b: str) -> int:
    """Levenshtein edit distance."""
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def suggest_domain(domain: str) -> str | None:
    """Return the popular provider `domain` is probably a typo of, if any."""
    if domain in KNOWN_PROVIDERS or domain in DISPOSABLE_DOMAINS:
        return None  # real providers, and throwaways (rejected separately with a clearer message)
    best = min(POPULAR_DOMAINS, key=lambda d: _distance(domain, d))
    return best if 0 < _distance(domain, best) <= 2 else None


GMAIL_DOMAINS = frozenset({"gmail.com", "googlemail.com"})
_GMAIL_USER = re.compile(r"^[a-z0-9](?:[a-z0-9]|\.(?!\.))*[a-z0-9]$")


def gmail_problem(local: str) -> str | None:
    """Explain why `local` can't be a Gmail username, or None if it can.
    Rules: 6-30 characters of letters, digits and dots; no leading, trailing or
    consecutive dots. A "+tag" suffix (plus addressing) is allowed."""
    username = local.split("+", 1)[0].lower()
    if not 6 <= len(username) <= 30:
        return "Gmail usernames are 6-30 characters long"
    if not _GMAIL_USER.fullmatch(username):
        return ("Gmail usernames may only contain letters, numbers and dots, and can't "
                "start or end with a dot or have two dots in a row")
    return None


def check_email_address(email: str) -> str:
    """Validate syntax (plus Gmail's own username rules), catch typos of popular
    domains, reject throwaway providers and (optionally) domains without a mail
    server. Returns the normalised address or raises a 422 with a clear message."""
    settings = get_settings()
    local, _, raw_domain = email.rpartition("@")
    suggestion = suggest_domain(raw_domain.strip().lower())
    if suggestion:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"Did you mean {local}@{suggestion}? Please check the email address.")
    try:
        result = validate_email(email, check_deliverability=settings.email_check_deliverability,
                                timeout=5)
    except EmailUndeliverableError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"This email address can't receive mail: {exc}") from exc
    except EmailNotValidError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"Invalid email address: {exc}") from exc
    domain = result.ascii_domain.lower()
    if settings.email_check_deliverability and getattr(result, "mx_fallback_type", None):
        # The domain resolves (e.g. a parked or typo website) but has no mail server (MX).
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"This email address can't receive mail: {domain} has no mail server. "
                            "Please check the address.")
    if domain in GMAIL_DOMAINS:
        problem = gmail_problem(result.local_part)
        if problem:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                f"This isn't a valid Gmail address: {problem}.")
    if domain in DISPOSABLE_DOMAINS or any(domain.endswith("." + d) for d in DISPOSABLE_DOMAINS):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Disposable email addresses aren't allowed. Please use a real inbox.")
    return result.normalized.lower()
