from bugalu.main import crear_app


def test_el_422_declara_el_esquema_real_respuesta_error() -> None:
    app = crear_app()

    @app.get("/con-parametro")
    def con_parametro(n: int) -> int:  # los 422 solo salen en rutas con entrada
        return n

    documento = app.openapi()
    assert documento["paths"]["/con-parametro"]["get"]["responses"]["422"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/RespuestaError"}
    assert "HTTPValidationError" not in documento["components"]["schemas"]
