from datetime import datetime
from uuid import UUID

from bugalu.compartido.errores import DuracionNoOfrecida, NoEncontrado, SinPermiso
from bugalu.compartido.plazos import calcular_vence_pago
from bugalu.modulos.asesorias.aplicacion.consultar.caso_de_uso import ObtenerAsesoria
from bugalu.modulos.asesorias.dominio import agenda
from bugalu.modulos.asesorias.dominio.asesoria import Asesoria, NuevaAsesoria, RepositorioAgenda
from bugalu.modulos.asesorias.dominio.precios import duraciones
from bugalu.modulos.reservas.dominio import reserva as reglas
from bugalu.modulos.reservas.dominio.disponibilidad import calcular_limites


class AgendarAsesoria:
    def __init__(self, repo: RepositorioAgenda) -> None:
        self._repo = repo

    async def ejecutar(
        self,
        id_cliente: UUID,
        id_profesional: UUID,
        inicio: datetime,
        duracion: int,
        modalidad: str,
        version_condiciones: str,
        ahora: datetime,
    ) -> Asesoria:
        repo = self._repo
        if await repo.es_profesional():
            raise SinPermiso("Un profesional no agenda asesorias.")
        reglas.exigir_requisitos(await repo.requisitos_para_reservar(), version_condiciones)
        agenda.exigir_inicio(inicio)
        fin = agenda.fin_de(inicio, duracion)
        profesional = await repo.obtener_profesional(id_profesional)
        if profesional is None or not profesional.publicado:
            raise NoEncontrado("No existe el profesional.")
        ofrecidas = [
            d
            for d in duraciones(profesional.precios, await repo.obtener_impuestos())
            if d.minutos == duracion
        ]
        if not ofrecidas:
            raise DuracionNoOfrecida("El profesional no ofrece esa duracion.")
        minima, maxima = await repo.limites_reserva()
        reglas.exigir_anticipacion(inicio, calcular_limites(ahora, minima, maxima))
        bloques = await repo.listar_horarios(id_profesional, inicio, fin)
        agenda.bloque_que_contiene(inicio, fin, bloques)
        d = ofrecidas[0]
        dias, horas = await repo.plazos_pago()
        precio = {
            "total": str(d.precio),
            "impuesto": {
                "nombre": "IGV",
                "porcentaje": str(d.igv.porcentaje),
                "incluido": d.igv.incluido,
                "base": str(d.igv.base),
                "monto": str(d.igv.monto),
            },
        }
        id_asesoria = await repo.insertar_asesoria(
            NuevaAsesoria(
                id_profesional,
                inicio,
                fin,
                modalidad,
                d.precio,
                precio,
                calcular_vence_pago(ahora, inicio, dias, horas),
            )
        )
        await repo.aceptar_condiciones(id_asesoria, version_condiciones)  # misma transaccion
        await repo.encolar_aviso(id_asesoria)
        return await ObtenerAsesoria(repo).ejecutar(id_cliente, id_asesoria)
