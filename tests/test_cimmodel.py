from mock import Mock, patch

from cimsparql.model import CimModel


class CimModelTest(CimModel):
    @staticmethod
    def _setup_client(*args, **kwargs):
        pass


def test_map_data_types(monkeypatch):
    def cim_init(self, *args):
        self._mapper = Mock(have_cim_version=Mock(return_value=True))
        self._prefixes = {"cim": None}

    monkeypatch.setattr(CimModelTest, "__init__", cim_init)
    cim_model = CimModelTest()
    assert cim_model.map_data_types


def test_not_map_data_types(monkeypatch):
    def cim_init(self, *args):
        self._mapper = Mock(have_cim_version=Mock(return_value=False))
        self._prefixes = {"cim": None}

    monkeypatch.setattr(CimModelTest, "__init__", cim_init)
    cim_model = CimModelTest()
    assert not cim_model.map_data_types


@patch.object(CimModelTest, "__init__", new=Mock(return_value=None))
def test_not_map_data_types_on_exception():
    cim_model = CimModelTest()
    assert not cim_model.map_data_types
