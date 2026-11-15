import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from validar_docs import validar, validar_mcp  # noqa: E402

FM = "---\nid: {id}\ntitulo: T\nestado: borrador\ndepende_de: []\n---\n"


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

    def test_mcp_sin_secretos(self):
        malo = self.escribir(".mcp.json", '{"s": {"headers": {"Authorization": "Bearer abc"}}}')
        self.assertTrue(validar_mcp(malo))
        bueno = self.escribir(".mcp.json", '{"s": {"headers": {"Authorization": "Bearer ${SUPABASE_TOKEN}"}}}')
        self.assertEqual(validar_mcp(bueno), [])


if __name__ == "__main__":
    unittest.main()
