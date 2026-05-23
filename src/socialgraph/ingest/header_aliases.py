"""LinkedIn Connections.csv header normalization across locales.

LinkedIn exports the same data in localized column headers. This table maps
known locale variants back to canonical snake_case names used downstream.
"""
from __future__ import annotations


class UnknownHeaderError(Exception):
    """Raised in strict mode when a header has no alias mapping."""


# Locale aliases observed in LinkedIn Connections.csv exports.
# Keys are lowercased + stripped versions of the original header.
LINKEDIN_HEADER_ALIASES: dict[str, str] = {
    "first name": "first_name",
    "prénom": "first_name",
    "vorname": "first_name",
    "nombre": "first_name",
    "nome": "first_name",
    "last name": "last_name",
    "nom": "last_name",
    "nachname": "last_name",
    "apellido": "last_name",
    "cognome": "last_name",
    "url": "profile_url",
    "profile url": "profile_url",
    "email address": "email",
    "adresse e-mail": "email",
    "e-mail-adresse": "email",
    "correo electrónico": "email",
    "indirizzo email": "email",
    "company": "company",
    "entreprise": "company",
    "unternehmen": "company",
    "empresa": "company",
    "azienda": "company",
    "position": "title",
    "poste": "title",
    "berufsbezeichnung": "title",
    "cargo": "title",
    "posizione": "title",
    "connected on": "connected_on",
    "date de connexion": "connected_on",
    "verbunden am": "connected_on",
    "conectado el": "connected_on",
    "data di collegamento": "connected_on",
}


def normalize_linkedin_headers(headers: list[str], strict: bool = False) -> list[str]:
    """Map raw CSV headers to canonical snake_case names.

    Unknown headers raise `UnknownHeaderError` if `strict=True`, otherwise
    they pass through unchanged so callers can detect them downstream.
    """
    out: list[str] = []
    for h in headers:
        key = h.strip().lower()
        if key in LINKEDIN_HEADER_ALIASES:
            out.append(LINKEDIN_HEADER_ALIASES[key])
        elif strict:
            raise UnknownHeaderError(f"unknown LinkedIn CSV header: {h!r}")
        else:
            out.append(h)
    return out
