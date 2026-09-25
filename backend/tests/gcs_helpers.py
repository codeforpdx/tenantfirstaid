"""Shared mock builders for the GCS provisioning script tests."""

from unittest.mock import MagicMock, patch

from tenantfirstaid.google_auth import GcpEnvironment


def patch_gcp_env():
    """Patch :meth:`GcpEnvironment.from_env` with a fake project and credentials.

    Takes no target. The reader is a classmethod on the class itself, so every
    importer resolves the same object and one patch covers them all -- unlike the
    module-level function it replaced, which had to be patched once per module
    that imported it.

    The corpus tooling reads its GCP identity from
    :meth:`tenantfirstaid.google_auth.GcpEnvironment.from_env` rather than from the
    application configuration singleton, so that a command needing only a project
    and credentials is not gated on the model and datastore settings the chatbot
    needs. The fake mirrors that narrower surface.
    """
    env = MagicMock()
    env.project = "my-project"
    env.location = "global"
    env.credentials_source = "/fake/creds.json"
    return patch.object(GcpEnvironment, "from_env", return_value=env)


def patch_corpus(target: str, datastores: dict[str, str] | None = None):
    """Patch a module's ``_CORPUS`` with a fake identity and datastore map.

    ``target`` is the dotted path to the module-level corpus configuration, e.g.
    "tenantfirstaid.langchain_tools._CORPUS".

    :class:`~tenantfirstaid.datastores.CorpusConfig` is frozen, so its attributes
    cannot be patched individually; the whole object is replaced instead.
    """
    corpus = MagicMock()
    corpus.gcp.project = "my-project"
    corpus.gcp.location = "global"
    corpus.gcp.credentials_source = "/fake/creds.json"
    corpus.datastores = datastores if datastores is not None else {}
    return patch(target, corpus)
