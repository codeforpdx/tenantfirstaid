def test_flask_app_startup(monkeypatch, tmpdir):
    # in testing environment, DATA_DIR (uploads) is set to a pytest provided
    # tmpdir (otherwise importing upload.py fails with a write-permission
    # error)
    monkeypatch.setenv("DATA_DIR", str(tmpdir))

    from tenantfirstaid.app import app

    assert app is not None
    assert app.name == "tenantfirstaid.app"
