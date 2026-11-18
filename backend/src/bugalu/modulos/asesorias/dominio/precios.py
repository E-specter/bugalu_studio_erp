from collections.abc import Mapping
from decimal import Decimal

from bugalu.modulos.asesorias.dominio.modelos import Duracion
from bugalu.modulos.catalogo.dominio.precio import ConfiguracionImpuestos, impuesto_y_total


def duraciones(precios: Mapping[int, Decimal], impuestos: ConfiguracionImpuestos) -> list[Duracion]:
    """Precio con IGV y su desglose, como RF-20 CA-02; solo las duraciones que ofrece."""
    resultado = []
    for minutos in sorted(precios):
        impuesto, total = impuesto_y_total(precios[minutos], impuestos)
        resultado.append(Duracion(minutos, total, impuesto))
    return resultado
