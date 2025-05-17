def test_flask_app_startup():

    from tenantfirstaid.app import app
    assert app is not None
    assert app.name == "tenantfirstaid.app"
