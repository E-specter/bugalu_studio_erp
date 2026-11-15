import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from validar_docs import leer_frontmatter, validar, validar_agentes, validar_mcp  # noqa: E402

FM = "---\nid: {id}\ntitulo: T\nestado: borrador\ndepende_de: []\n---\n"
TDD = "superpowers:test-driven-development"
VERIF = "superpowers:verification-before-completion"
FILA = "| Agente | Modelo | Effort | maxTurns | Precarga | Bajo demanda | Rol |\n|---|---|---|---|---|---|---|\n"
EQUIPO = (
    "# Equipo\n\n## Sesión principal\n\n" + FILA + "| `leader` | opus | high | — | — | x | Orquesta |\n\n"
    "## Subagentes\n\n" + FILA + f"| `dev-backend` | sonnet | medium | 40 | `{TDD}`, `{VERIF}` | — | Backend |\n\n"
    "## Compuertas\n\n| `dev-audit` | opus | x | x | — | — | fuera de la sección |\n"
)
AGENTE = "---\nname: dev-backend\ndescription: d\nmodel: {model}\neffort: medium\nmaxTurns: {turnos}\nskills:\n{skills}---\n\ncuerpo\n"


class TestValidarDocs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def escribir(self, ruta, texto):
        p = self.raiz / ruta
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
        return p

    def errores(self, fuente=None):
        return "\n".join(validar(self.raiz, fuente))

    def test_frontmatter_faltante(self):
        self.escribir("a.md", "# sin frontmatter\n")
        self.assertIn("frontmatter", self.errores())

    def test_estado_invalido(self):
        self.escribir("a.md", FM.format(id="x").replace("borrador", "listo"))
        self.assertIn("estado", self.errores())

    def test_limite_lineas(self):
        self.escribir("a.md", FM.format(id="x") + "l\n" * 145)
        self.assertIn("150", self.errores())

    def test_enlace_roto(self):
        self.escribir("a.md", FM.format(id="x") + "[x](no-existe.md)\n")
        self.assertIn("no-existe.md", self.errores())

    def test_id_duplicado(self):
        self.escribir("a.md", FM.format(id="RF-01"))
        self.escribir("b.md", FM.format(id="RF-01"))
        self.assertIn("RF-01", self.errores())

    def test_ids_huerfanos(self):
        fuente = self.escribir("fuente/p.md", "| RN-01 | a |\n| RN-02 | b |\n")
        self.escribir("docs/r.md", FM.format(id="reglas") + "| RN-01 | a |\n")
        errores = "\n".join(validar(self.raiz / "docs", fuente))
        self.assertIn("RN-02", errores)
        self.assertNotIn("RN-01", errores)

    def test_arbol_valido(self):
        self.escribir("README.md", "# indice\n[a](sub/a.md)\n")
        self.escribir("sub/a.md", FM.format(id="RF-01") + "[r](#ancla) [w](https://x.y)\n")
        self.assertEqual(validar(self.raiz, None), [])

    def agentes(self, model="sonnet", turnos="40", skills=(TDD, VERIF), equipo=EQUIPO):
        lista = "".join(f"  - {s}\n" for s in skills)
        self.escribir(".claude/agents/dev-backend.md", AGENTE.format(model=model, turnos=turnos, skills=lista))
        eq = self.escribir("docs/equipo.md", equipo)
        return "\n".join(validar_agentes(self.raiz / ".claude" / "agents", eq))

    def test_frontmatter_lista_yaml(self):
        fm = leer_frontmatter(f"---\nid: x\nskills:\n  - {TDD}\n  - design:design-system\n---\n")
        self.assertEqual(fm["skills"], [TDD, "design:design-system"])

    def test_agente_coincide(self):
        self.assertEqual(self.agentes(), "")

    def test_agente_modelo_distinto(self):
        errores = self.agentes(model="opus")
        self.assertIn("model", errores)
        self.assertIn("dev-backend", errores)

    def test_agente_skills_distintas(self):
        self.assertIn("skills", self.agentes(skills=(TDD, VERIF, "design:design-system")))

    def test_agente_sin_fila(self):
        self.assertIn("dev-backend", self.agentes(equipo=EQUIPO.replace("`dev-backend` | sonnet", "`otro` | sonnet")))

    def test_fila_sin_agente(self):
        self.assertIn("otro", self.agentes(equipo=EQUIPO.replace("`dev-backend` | sonnet", "`otro` | sonnet")))

    def test_agente_valores_normalizados(self):
        self.assertEqual(self.agentes(model="Sonnet", turnos='"40"', skills=(VERIF, TDD)), "")

    def test_mcp_sin_secretos(self):
        malo = self.escribir(".mcp.json", '{"s": {"headers": {"Authorization": "Bearer abc"}}}')
        self.assertTrue(validar_mcp(malo))
        bueno = self.escribir(".mcp.json", '{"s": {"headers": {"Authorization": "Bearer ${SUPABASE_TOKEN}"}}}')
        self.assertEqual(validar_mcp(bueno), [])


if __name__ == "__main__":
    unittest.main()
