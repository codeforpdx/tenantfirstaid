def test_flask_app_startup():
    import tenantfirstaid.app as mod
    assert mod.app is not None
    from tenantfirstaid.app import app
    assert app is not None
    assert app.name == "tenantfirstaid.app"