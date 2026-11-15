"""Os BPMN v3 e v4 (docs/bpmn/) são XML bem formado e descrevem o processo atual.

A v4 é a v3 com nomes curtos em cinco tarefas; os detalhes foram para a documentação delas.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

PASTA = Path(__file__).resolve().parents[2] / "docs" / "bpmn"
VERSOES = ["auditor_preco_justo_v3.bpmn", "auditor_preco_justo_v4.bpmn"]
NS = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL"}


@pytest.fixture(params=VERSOES)
def bpmn(request) -> Path:
    return PASTA / request.param


def test_xml_bem_formado(bpmn):
    raiz = ET.fromstring(bpmn.read_text(encoding="utf-8").encode("utf-8"))
    assert raiz.tag == "{%s}definitions" % NS["bpmn"]


def test_dois_participantes(bpmn):
    nomes = [p.get("name") for p in ET.parse(bpmn).getroot().iter("{%s}participant" % NS["bpmn"])]
    assert len(nomes) == 2
    assert any("avaliação de um contrato" in n for n in nomes)
    assert any("equidade" in n for n in nomes)


def test_cita_o_processo_atual(bpmn):
    texto = bpmn.read_text(encoding="utf-8").lower()
    for termo in ("revisão manual", "decisao_analista", "invariância"):
        assert termo in texto, termo
