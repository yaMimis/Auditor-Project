"""A carga macro aceita os dois nomes do arquivo da Euribor 12 meses (com e sem "_csv").

Não precisa de banco nem dos CSVs reais: os arquivos são criados vazios numa pasta
temporária e a função `carregar` é trocada por uma que só guarda o que recebeu.
"""
import sys

import pytest

from src.dados import carga_macro as cm

COM_CSV, SEM_CSV = cm.NOMES_EURIBOR_12M
OUTROS = ("ECB_Euribor_Serie-Mensal-3-Meses.csv", "BC-Selic_Acumulada_Mes_Anuzalizada_base252.csv")


def _criar(pasta, *nomes):
    pasta.mkdir(parents=True, exist_ok=True)
    for nome in nomes:
        (pasta / nome).write_text("", encoding="utf-8")


@pytest.fixture
def rodar_main(tmp_path, monkeypatch):
    """Roda o main() dentro de tmp_path e devolve os arquivos que iriam para a carga."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql://teste")
    recebido = {}
    monkeypatch.setattr(cm, "carregar", lambda dsn, ddl, arquivos: recebido.update(arquivos))

    def _rodar(*args):
        monkeypatch.setattr(sys, "argv", ["carga_macro.py", *args])
        cm.main()
        return recebido

    return _rodar


def test_primeiro_existente_respeita_a_ordem(tmp_path):
    _criar(tmp_path, COM_CSV, SEM_CSV)
    assert cm.primeiro_existente(cm.NOMES_EURIBOR_12M, tmp_path) == tmp_path / COM_CSV


def test_primeiro_existente_sem_nenhum_devolve_none(tmp_path):
    assert cm.primeiro_existente(cm.NOMES_EURIBOR_12M, tmp_path) is None


@pytest.mark.parametrize("nome", [COM_CSV, SEM_CSV])
def test_main_acha_a_euribor_12m_pelos_dois_nomes(rodar_main, tmp_path, nome):
    _criar(tmp_path / "data" / "raw", nome, *OUTROS)
    arquivos = rodar_main()
    assert arquivos["euribor_12m"].name == nome


def test_main_respeita_o_caminho_explicito(rodar_main, tmp_path):
    _criar(tmp_path / "data" / "raw", COM_CSV, *OUTROS)
    _criar(tmp_path / "outra", "euribor12.csv")
    arquivos = rodar_main("--euribor-12m", "outra/euribor12.csv")
    assert str(arquivos["euribor_12m"]).replace("\\", "/") == "outra/euribor12.csv"


def test_main_sem_euribor_12m_para_com_erro_claro(rodar_main, tmp_path):
    _criar(tmp_path / "data" / "raw", *OUTROS)
    with pytest.raises(SystemExit, match=COM_CSV):
        rodar_main()


def test_bc_20742_continua_aceitando_os_dois_nomes(rodar_main, tmp_path):
    _criar(tmp_path / "data" / "raw", SEM_CSV, *OUTROS, "bcdata_sgs_20742.csv")
    arquivos = rodar_main()
    assert arquivos["bc_credito"].name == "bcdata_sgs_20742.csv"
