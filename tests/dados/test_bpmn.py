"""O BPMN v3 (docs/bpmn/auditor_preco_justo_v3.bpmn) é XML bem formado e descreve o processo atual."""
import xml.etree.ElementTree as ET
from pathlib import Path

BPMN = Path(__file__).resolve().parents[2] / "docs" / "bpmn" / "auditor_preco_justo_v3.bpmn"
NS = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL"}


def _texto() -> str:
    return BPMN.read_text(encoding="utf-8")


def test_xml_bem_formado():
    raiz = ET.fromstring(_texto().encode("utf-8"))
    assert raiz.tag == "{%s}definitions" % NS["bpmn"]


def test_dois_participantes():
    nomes = [p.get("name") for p in ET.parse(BPMN).getroot().iter("{%s}participant" % NS["bpmn"])]
    assert len(nomes) == 2
    assert any("avaliação de um contrato" in n for n in nomes)
    assert any("equidade" in n for n in nomes)


def test_cita_o_processo_atual():
    texto = _texto().lower()
    for termo in ("revisão manual", "decisao_analista", "invariância"):
        assert termo in texto, termo
