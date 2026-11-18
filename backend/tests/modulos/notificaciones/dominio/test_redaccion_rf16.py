"""Avisos del Libro de Reclamaciones (RF-16, spec RF-16-correos.md)."""

# ruff: noqa: E501

from decimal import Decimal
from typing import Any

import pytest

from bugalu.modulos.notificaciones.dominio.formato import formatear_soles
from bugalu.modulos.notificaciones.dominio.plantilla import bloques_del_cuerpo, componer
from bugalu.modulos.notificaciones.dominio.redaccion import redactar

URL = "http://web"
HOJA: dict[str, Any] = {
    "id": "h-1",
    "numero": "000000042-2026",
    "creada_en": "2026-11-17T20:30:00+00:00",  # 15:30 en Lima
    "vence_respuesta": "2026-12-10T04:59:59+00:00",  # 9 dic en Lima
    "tipo": "reclamo",
    "nombre": "Ana Torres",
    "tipo_documento": "dni",
    "documento": "12345678",
    "domicilio": "Av. Lima 123",
    "telefono": None,
    "correo": "ana@x.pe",
    "es_menor": False,
    "representante": None,
    "bien_tipo": "servicio",
    "monto": "1250.5",
    "descripcion": None,
    "medio_respuesta": "correo",
    "adjuntos": ["foto.png", "hoja.pdf"],
    "detalle": "Linea uno.\nLinea dos.",
    "pedido": "Devolucion.",
    "con_cuenta": True,
}


def test_registrada_es_la_copia_de_la_hoja_en_el_orden_del_anexo_i() -> None:
    asunto, cuerpo = redactar("reclamacion_registrada", HOJA)
    assert asunto == "Hoja de reclamación N.º 000000042-2026"
    assert cuerpo.startswith(
        "Registramos tu reclamo en el Libro de Reclamaciones de Bugalú Studio. Esta es la copia de tu hoja. "
        "Te responderemos por correo electrónico a más tardar el 9 dic 2026."
    )
    for linea in (
        "Hoja N.º: 000000042-2026",
        "Fecha y hora: 17 nov 2026, 15:30",
        "Proveedor: Aural Perú E.I.R.L.",
        "RUC: 20615656128",
        "Domicilio del proveedor: Av. Javier Prado Este 5920, La Molina, Lima",
        "1. Identificación del consumidor reclamante",
        "Documento: DNI 12345678",
        "Teléfono: —",
        "Menor de edad: No",
        "2. Identificación del bien contratado",
        "Producto o servicio: Servicio",
        f"Monto reclamado: {formatear_soles(Decimal('1250.50'))}",
        "Descripción: —",
        "3. Detalle de la reclamación y pedido del consumidor",
        "Tipo: Reclamo",
        "Medio para la respuesta: Correo electrónico",
        "Adjuntos: foto.png, hoja.pdf",
        "Detalle:\nLinea uno.\nLinea dos.",
        "Pedido:\nDevolucion.",
        "RECLAMO: Disconformidad relacionada a los productos o servicios.",
        "El proveedor deberá dar respuesta al reclamo o queja en un plazo no mayor a quince (15) días hábiles improrrogables.",
    ):
        assert linea in cuerpo, linea
    assert "Madre, padre o tutor" not in cuerpo


def test_registrada_de_un_menor_con_carta_y_sin_marcar() -> None:
    datos = HOJA | {
        "es_menor": True,
        "representante": {
            "nombre": "Rosa",
            "domicilio": "Calle 1",
            "telefono": "999",
            "correo": "r@x.pe",
        },
        "medio_respuesta": "carta",
        "tipo": None,
        "monto": None,
        "adjuntos": [],
    }
    _, cuerpo = redactar("reclamacion_registrada", datos)
    assert cuerpo.startswith("Registramos tu hoja en el Libro")
    assert "carta a tu domicilio a más tardar el 9 dic 2026" in cuerpo
    assert (
        "Madre, padre o tutor\n\nNombre: Rosa\nDomicilio: Calle 1\nTeléfono: 999\nCorreo: r@x.pe"
        in cuerpo
    )
    for linea in (
        "Menor de edad: Sí",
        "Tipo: Sin marcar",
        "Monto reclamado: No indicado",
        "Adjuntos: Ninguno",
        "Medio para la respuesta: Carta al domicilio",
    ):
        assert linea in cuerpo


def test_los_valores_de_una_linea_no_traen_saltos_del_consumidor() -> None:
    _, cuerpo = redactar(
        "reclamacion_registrada", HOJA | {"nombre": "Ana\nTorres", "domicilio": "Av.\r\nLima"}
    )
    assert "Nombre: Ana Torres\n" in cuerpo and "Domicilio: Av. Lima\n" in cuerpo


def test_recibida_avisa_al_administrador_solo_con_el_nombre() -> None:
    datos = {
        "id": "h-1",
        "numero": "000000042-2026",
        "tipo": "queja",
        "nombre": "Ana Torres",
        "creada_en": HOJA["creada_en"],
        "vence_respuesta": HOJA["vence_respuesta"],
        "medio_respuesta": "carta",
        "adjuntos": 2,
    }
    asunto, cuerpo = redactar("reclamacion_recibida", datos)
    assert asunto == "Nueva hoja de reclamación N.º 000000042-2026"
    assert (
        "Respóndela a más tardar el 9 dic 2026: el plazo de 15 días hábiles no se prorroga."
        in cuerpo
    )
    for linea in (
        "Tipo: Queja",
        "Consumidor: Ana Torres",
        "Presentada: 17 nov 2026, 15:30",
        "Medio para la respuesta: Carta al domicilio",
        "Adjuntos: 2",
    ):
        assert linea in cuerpo
    assert "12345678" not in cuerpo
    assert "Adjuntos: Ninguno" in redactar("reclamacion_recibida", datos | {"adjuntos": 0})[1]


def test_respondida_lleva_el_texto_como_parrafo_propio() -> None:
    datos = {
        "id": "h-1",
        "numero": "000000042-2026",
        "tipo": "reclamo",
        "creada_en": HOJA["creada_en"],
        "texto": "Hola.\nTe devolvimos.",
        "enviada_en": "2026-11-20T15:00:00+00:00",
        "con_cuenta": False,
    }
    asunto, cuerpo = redactar("reclamacion_respondida", datos)
    assert asunto == "Respuesta a tu hoja de reclamación N.º 000000042-2026"
    assert cuerpo.startswith(
        "Respondimos tu reclamo N.º 000000042-2026, presentado el 17 nov 2026."
    )
    assert "Nuestra respuesta:\nHola.\nTe devolvimos." in cuerpo
    assert "Fecha de la respuesta: 20 nov 2026, 10:00" in cuerpo
    assert "La formulación del reclamo no impide acudir a otras vías" in cuerpo


def test_por_vencer_lista_vencidas_hoy_y_proximas() -> None:
    def hoja(n: str, tipo: str | None, vence: str, dias: int) -> dict[str, Any]:
        return {"id": n, "numero": n, "tipo": tipo, "vence_respuesta": vence, "dias": dias}

    datos = {
        "hojas": [
            hoja("A", "reclamo", "2026-11-10T04:59:59+00:00", -4),
            hoja("B", "queja", "2026-11-18T04:59:59+00:00", 0),
            hoja("C", None, "2026-11-24T04:59:59+00:00", 4),
        ]
    }
    asunto, cuerpo = redactar("reclamaciones_por_vencer", datos)
    assert asunto == "3 hojas de reclamación por responder"
    assert "- N.º A · Reclamo · fuera de plazo desde el 9 nov 2026" in cuerpo
    assert "- N.º B · Queja · vence hoy" in cuerpo
    assert "- N.º C · Sin marcar · vence el 23 nov 2026 (en 4 días hábiles)" in cuerpo
    assert (
        redactar("reclamaciones_por_vencer", {"hojas": datos["hojas"][:1]})[0]
        == "1 hoja de reclamación por responder"
    )


@pytest.mark.parametrize(
    ("con_cuenta", "texto", "destino"),
    [
        (True, "Ver mi hoja", f"{URL}/app/reclamos/detalle?id=h-1"),
        (False, "Escribirnos por WhatsApp", "https://wa.me/51925530800"),
    ],
)
def test_el_boton_de_la_copia_y_la_respuesta_depende_de_si_hay_cuenta(
    con_cuenta: bool, texto: str, destino: str
) -> None:
    for tipo, datos in (
        ("reclamacion_registrada", HOJA),
        (
            "reclamacion_respondida",
            {
                "id": "h-1",
                "numero": "1",
                "tipo": None,
                "creada_en": HOJA["creada_en"],
                "texto": "Respuesta larga",
                "enviada_en": HOJA["creada_en"],
            },
        ),
    ):
        datos = datos | {"con_cuenta": con_cuenta}
        asunto, cuerpo = redactar(tipo, datos)
        plano, html = componer(tipo, datos, asunto, cuerpo, URL, None)
        assert f"{texto}: {destino}" in plano
        assert f'href="{destino}"' in html and texto in html
        assert "// LIBRO DE RECLAMACIONES" in plano


def test_el_pie_reclamo_no_supone_cuenta_y_el_del_administrador_se_mantiene() -> None:
    asunto, cuerpo = redactar("reclamacion_registrada", HOJA)
    plano, html = componer("reclamacion_registrada", HOJA, asunto, cuerpo, URL, None)
    motivo = "Te enviamos este correo porque presentaste una hoja en el Libro de Reclamaciones de Bugalú Studio."
    assert motivo in plano and motivo in html
    assert "Mis reservas" not in plano and "Mis reservas" not in html
    assert "tienes una cuenta" not in plano
    assert (
        "WhatsApp" in plano
        and "Libro de Reclamaciones: http://web/libro-de-reclamaciones/" in plano
    )
    datos = {
        "id": "h-1",
        "numero": "1",
        "tipo": None,
        "nombre": "A",
        "creada_en": HOJA["creada_en"],
        "vence_respuesta": HOJA["vence_respuesta"],
        "medio_respuesta": "correo",
        "adjuntos": 0,
    }
    a, c = redactar("reclamacion_recibida", datos)
    plano, _ = componer("reclamacion_recibida", datos, a, c, URL, None)
    assert "Revisar la hoja: http://web/app/reclamos/detalle?id=h-1" in plano
    assert "eres Administrador" in plano
    plano, _ = componer("reclamaciones_por_vencer", {"hojas": []}, "x", "y", URL, None)
    assert "Ver hojas pendientes: http://web/app/reclamos/?estado=pendiente" in plano


def test_el_cuerpo_de_la_copia_se_convierte_en_tablas_y_parrafos() -> None:
    _, cuerpo = redactar("reclamacion_registrada", HOJA)
    tipos = [t for t, _ in bloques_del_cuerpo(cuerpo)]
    assert tipos.count("tabla") >= 4
