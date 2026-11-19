"""Errores del kernel, sin dependencias de HTTP (formato de respuesta: manejadores_http)."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

_LIMA = timezone(timedelta(hours=-5))  # Lima no tiene horario de verano


def asesorias_vivas_en_lima(detalle: str | None) -> list[dict[str, Any]]:
    """El `detail` JSON de BG004/BG005 (asesorias vivas) con `inicio` en hora de Lima."""
    vivas: list[dict[str, Any]] = json.loads(detalle or "[]")
    for v in vivas:
        v["inicio"] = datetime.fromisoformat(v["inicio"]).astimezone(_LIMA).isoformat()
    return vivas


class ErrorDeNegocio(Exception):
    codigo = "error_de_negocio"
    estado_http = 400

    def __init__(self, mensaje: str, detalles: dict[str, Any] | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalles = detalles  # serializable a JSON; la respuesta lo incluye solo si existe


class NoAutenticado(ErrorDeNegocio):
    codigo = "no_autenticado"
    estado_http = 401


class NoEncontrado(ErrorDeNegocio):
    codigo = "no_encontrado"
    estado_http = 404


class AutenticacionNoDisponible(ErrorDeNegocio):
    codigo = "autenticacion_no_disponible"
    estado_http = 503


class SinPermiso(ErrorDeNegocio):
    codigo = "sin_permiso"
    estado_http = 403


class Conflicto(ErrorDeNegocio):
    codigo = "conflicto"
    estado_http = 409


class UltimoAdministrador(Conflicto):
    codigo = "ultimo_administrador"

    def __init__(self) -> None:
        super().__init__("No puede quedar el sistema sin administradores.")


class ClienteConOperaciones(Conflicto):
    codigo = "cliente_con_operaciones"

    def __init__(self, detalles: dict[str, Any]) -> None:
        super().__init__(
            "El usuario tiene reservas, creditos, pagos o devoluciones vivos como cliente.",
            detalles,
        )


class ProfesionalConAsesorias(Conflicto):
    codigo = "profesional_con_asesorias"

    def __init__(self, detalles: dict[str, Any]) -> None:
        super().__init__("El profesional tiene asesorias vivas.", detalles)


class VerificacionNoValida(Conflicto):
    codigo = "verificacion_no_valida"

    def __init__(self) -> None:
        super().__init__("La sesion no viene de un enlace de correo ni de Google.")


class CampoNoPermitido(ErrorDeNegocio):
    codigo = "campo_no_permitido"
    estado_http = 422


class DatosInvalidos(ErrorDeNegocio):
    codigo = "datos_invalidos"
    estado_http = 422


class ItseVencido(DatosInvalidos):
    codigo = "itse_vencido"


class TramoInvalido(DatosInvalidos):
    codigo = "tramo_invalido"


class ServicioNoReservable(DatosInvalidos):
    codigo = "servicio_no_reservable"


class FeriadoRepetido(Conflicto):
    codigo = "feriado_repetido"


class FranjaSolapada(Conflicto):
    codigo = "franja_solapada"


class FranjaConReservas(Conflicto):
    codigo = "franja_con_reservas"


class CierreConReservas(Conflicto):
    codigo = "cierre_con_reservas"


class RangoInvalido(DatosInvalidos):
    codigo = "rango_invalido"


class DuracionInvalida(DatosInvalidos):
    codigo = "duracion_invalida"


class AnticipacionInsuficiente(DatosInvalidos):
    codigo = "anticipacion_insuficiente"


class AnticipacionExcesiva(DatosInvalidos):
    codigo = "anticipacion_excesiva"


class FueraDeFranja(DatosInvalidos):
    codigo = "fuera_de_franja"


class EnsayoNoDisponible(SinPermiso):
    codigo = "ensayo_no_disponible"


class TramoNoDisponible(Conflicto):
    codigo = "tramo_no_disponible"


class NivelCambiado(Conflicto):
    codigo = "nivel_cambiado"


class AvisoInvalido(DatosInvalidos):
    codigo = "aviso_invalido"


class ToleranciaNoCumplida(Conflicto):
    codigo = "tolerancia_no_cumplida"


class NoAplicable(Conflicto):
    codigo = "no_aplicable"


class ExcepcionNoAplicable(Conflicto):
    codigo = "excepcion_no_aplicable"


class ExcepcionYaAplicada(Conflicto):
    codigo = "excepcion_ya_aplicada"


class CreditoInsuficiente(Conflicto):
    codigo = "credito_insuficiente"


class NoPagable(Conflicto):
    codigo = "no_pagable"


class MontoInvalido(DatosInvalidos):
    codigo = "monto_invalido"


class MotivoRequerido(DatosInvalidos):
    codigo = "motivo_requerido"


class DevolucionNoPermitida(Conflicto):
    codigo = "devolucion_no_permitida"


class DevolucionPendiente(Conflicto):
    codigo = "devolucion_pendiente"


class CreditoNoVigente(Conflicto):
    codigo = "credito_no_vigente"


class DevolucionDecidida(Conflicto):
    codigo = "devolucion_decidida"


class DevolucionNoAprobada(Conflicto):
    codigo = "devolucion_no_aprobada"


class NotaRequerida(DatosInvalidos):
    codigo = "nota_requerida"


class NoCancelable(Conflicto):
    codigo = "no_cancelable"


class ReprogramacionNoPermitida(Conflicto):
    codigo = "reprogramacion_no_permitida"


class LimiteReprogramaciones(Conflicto):
    codigo = "limite_reprogramaciones"


class PrecioCambiado(Conflicto):
    codigo = "precio_cambiado"


class EleccionNoDisponible(Conflicto):
    codigo = "eleccion_no_disponible"


class AlmacenamientoNoDisponible(ErrorDeNegocio):
    codigo = "almacenamiento_no_disponible"
    estado_http = 503


class ArchivoMuyGrande(ErrorDeNegocio):
    codigo = "archivo_muy_grande"
    estado_http = 413


class FormatoNoAdmitido(DatosInvalidos):
    codigo = "formato_no_admitido"


class MetodoNoDisponible(DatosInvalidos):
    codigo = "metodo_no_disponible"


class PagoEnValidacion(Conflicto):
    codigo = "pago_en_validacion"


class CuotaPagada(Conflicto):
    codigo = "cuota_pagada"


class CuotaNoPagable(Conflicto):
    codigo = "cuota_no_pagable"


class OperacionDuplicada(Conflicto):
    codigo = "operacion_duplicada"


class PagoYaValidado(Conflicto):
    codigo = "pago_ya_validado"


class ConfirmacionRequerida(ErrorDeNegocio):
    codigo = "confirmacion_requerida"
    estado_http = 428

    def __init__(self, campos: list[str]) -> None:
        super().__init__("Este cambio necesita vista previa y confirmación.", {"campos": campos})


class SinCambios(DatosInvalidos):
    codigo = "sin_cambios"


class PlazosIncoherentes(DatosInvalidos):
    codigo = "plazos_incoherentes"


class PalabraIncorrecta(DatosInvalidos):
    codigo = "palabra_incorrecta"


class ConfirmacionNoValida(Conflicto):
    codigo = "confirmacion_no_valida"


class CambioDesactualizado(Conflicto):
    codigo = "cambio_desactualizado"


class VersionInvalida(DatosInvalidos):
    codigo = "version_invalida"


class AvisoInsuficiente(DatosInvalidos):
    codigo = "aviso_insuficiente"


class VersionProgramada(Conflicto):
    codigo = "version_programada"


class VersionVigente(Conflicto):
    codigo = "version_vigente"


class TextoDesactualizado(Conflicto):
    codigo = "texto_desactualizado"


class DeclaracionRequerida(Conflicto):
    codigo = "declaracion_requerida"


class ReaceptacionRequerida(Conflicto):
    codigo = "reaceptacion_requerida"


class PerfilIncompleto(Conflicto):
    codigo = "perfil_incompleto"


class AutorizacionMenorPendiente(Conflicto):
    codigo = "autorizacion_menor_pendiente"


class TelefonoRequerido(DatosInvalidos):
    codigo = "telefono_requerido"


class ConfirmacionDeHojaRequerida(Conflicto):
    codigo = "confirmacion_requerida"

    def __init__(self) -> None:
        super().__init__("Confirma la hoja antes de enviarla.")


class DemasiadasSolicitudes(ErrorDeNegocio):
    codigo = "demasiadas_solicitudes"
    estado_http = 429


class YaRespondida(Conflicto):
    codigo = "ya_respondida"


class AdjuntoMuyGrande(ErrorDeNegocio):
    codigo = "adjunto_muy_grande"
    estado_http = 413


class AdjuntoNoPermitido(DatosInvalidos):
    codigo = "adjunto_no_permitido"


class FechaOriginalInvalida(DatosInvalidos):
    codigo = "fecha_original_invalida"


class DemasiadosAdjuntos(DatosInvalidos):
    codigo = "demasiados_adjuntos"


class EspecialidadDuplicada(Conflicto):
    codigo = "especialidad_duplicada"


class PerfilExistente(Conflicto):
    codigo = "perfil_existente"


class RolNoAdmitido(DatosInvalidos):
    codigo = "rol_no_admitido"


class HorarioSolapado(Conflicto):
    codigo = "horario_solapado"


class HorarioConAsesorias(Conflicto):
    codigo = "horario_con_asesorias"


class HorarioNoDisponible(Conflicto):
    codigo = "horario_no_disponible"


class DuracionNoOfrecida(Conflicto):
    codigo = "duracion_no_ofrecida"


class FueraDeHorario(DatosInvalidos):
    codigo = "fuera_de_horario"


class NoEditable(Conflicto):
    codigo = "no_editable"


class EnlaceInvalido(DatosInvalidos):
    codigo = "enlace_invalido"
