"""Datastore keys and locations, kept free of any environment dependency.

These live apart from :mod:`tenantfirstaid.config` because importing that
module builds the validated configuration singleton, which requires a populated
environment. The corpus tooling -- the import guardrail, the pointer reader and
the scheduled reaper -- needs to know which datastore keys are legitimate
without needing the app's runtime configuration, and the reaper in particular
runs as a Cloud Function that has no reason to carry it.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Final

from .google_auth import GcpEnvironment, gcp_env

DATASTORE_PREFIX: Final = "VERTEX_AI_DATASTORE_"
"""Environment variable prefix for Vertex AI Search datastore IDs."""

DEFAULT_VERTEX_AI_SEARCH_LOCATION: Final = "us"
"""Default multi-region location for Vertex AI Search datastores.

Distinct from the LLM compute region. It lives here rather than in
:mod:`tenantfirstaid.config` because every corpus tool uses it as an argparse
default, and reaching into ``constants`` for it would build the configuration
singleton -- which the scheduled reaper, running as a Cloud Function with no app
environment at all, cannot do."""


class DatastoreKey(StrEnum):
    """Datastore keys — must match the suffix of the corresponding VERTEX_AI_DATASTORE_<NAME> env var (lowercased).

    This enum is the single declaration of which datastore keys exist. Every
    usable datastore needs a member here, a tool built from it, and a registry
    entry, so the set of meaningful keys is closed and knowable statically.

    A member names a **slot**, not a corpus. Which jurisdiction, practice area
    and statute edition actually fill that slot is a property of the artifact
    bound to it, set per environment. The
    descriptions below therefore say what *kind* of material a slot holds, and
    deliberately avoid naming Oregon or housing: the same deployment shape
    serves a family-law instance by binding different artifacts to the same
    slots. (Issue #318 changes this for the jurisdictional slots specifically,
    folding practice area and jurisdiction into the key names themselves, at
    which point those keys stop being generic.)
    """

    LAWS = auto()
    """Primary legal source material: statutes, codes and regulations as enacted.

    The authoritative text a citation points at, as opposed to explanation of it.
    """

    OREGON_LAW_HELP = auto()
    """Secondary material: plain-language guidance explaining the law to the public.

    Named for its publisher, OregonLawHelp.org, rather than for its subject,
    because the publisher is the stable thing — it produces both housing and
    family-law guidance, and a deployment binds whichever corpus it serves.
    Distinguished from :attr:`LAWS` by authority rather than topic: guidance is
    cited as explanation, never as the law itself.
    """


def parse_datastores(env: Mapping[str, str]) -> dict[str, str]:
    """Build a datastore name→id dict from environment variables with the VERTEX_AI_DATASTORE_ prefix.

    Each variable named ``VERTEX_AI_DATASTORE_<NAME>`` becomes an entry keyed by
    ``<NAME>`` lowercased. The value may be a bare datastore ID or a full resource URI.

    No particular key is required here. Which datastores a caller cannot do without
    is the caller's own policy: the application demands :attr:`DatastoreKey.LAWS`,
    while ``vertex_ai_search --datastore <id>`` needs none of them.

    Args:
        env: Environment variable mapping to parse.

    Returns:
        Dictionary mapping lowercase datastore names to datastore IDs.

    Raises:
        ValueError: If a datastore variable has no name or is empty.
    """
    result = {}
    for key, value in env.items():
        if not key.startswith(DATASTORE_PREFIX):
            continue
        name = key.removeprefix(DATASTORE_PREFIX).lower()
        if not name:
            raise ValueError(
                f"[{key}] datastore variable has no name after the prefix."
            )
        value = value.strip()
        if not value:
            raise ValueError(f"[{key}] environment variable is set but empty.")
        if value.startswith("projects/"):
            value = value.rstrip("/").split("/")[-1]
        result[name] = value
    return result


@dataclass(frozen=True)
class CorpusConfig:
    """A GCP identity and the datastores it addresses: everything retrieval needs.

    A sibling of the model configuration in :mod:`tenantfirstaid.google_models`, not a
    layer beneath it. Retrieval needs an identity and a set of datastores;
    generation needs an identity and a model. Neither requires the other, and only
    the application requires both -- so the two are validated separately, and a tool
    that reads a datastore is not made to supply a model it never calls.
    """

    gcp: GcpEnvironment
    """The project, region and credentials the datastores are read through."""
    datastores: Mapping[str, str]
    """Datastore name -> id, parsed from every ``VERTEX_AI_DATASTORE_*`` variable."""


def corpus_env(gcp: GcpEnvironment | None = None) -> CorpusConfig:
    """Read the corpus configuration from the environment.

    Args:
        gcp: An already-read identity to reuse. The application reads one and
            passes it to both siblings, so that the two halves of its
            configuration cannot disagree about which project they address.

    Raises:
        ValueError: If a GCP identity variable is unset, or a datastore variable is
            set but empty. Never for a missing model setting, which is the point.
    """
    return CorpusConfig(
        gcp=gcp if gcp is not None else gcp_env(),
        datastores=parse_datastores(os.environ),
    )
