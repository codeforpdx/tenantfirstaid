"""Shared mock builders for the GCS provisioning script tests."""

from unittest.mock import MagicMock, patch


def patch_gcp_env(target: str):
    """Patch a script module's ``gcp_env`` with a fake project and credentials.

    ``target`` is the dotted path to the module's imported ``gcp_env``, e.g.
    "scripts.upload_to_gcs.gcp_env".

    The corpus tooling reads its GCP identity from
    :func:`tenantfirstaid.google_auth.gcp_env` rather than from the application
    configuration singleton, so that a command needing only a project and
    credentials is not gated on the model and datastore settings the chatbot
    needs. The fake mirrors that narrower surface.
    """
    env = MagicMock()
    env.project = "my-project"
    env.location = "global"
    env.credentials_source = "/fake/creds.json"
    return patch(target, return_value=env)


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
