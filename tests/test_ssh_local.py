import os
import pytest

from cimsparql.graphdb import GraphDBClient
from cimsparql.url import service
from cimsparql import queries, ssh_queries

n_lim = 100


@pytest.fixture(scope="module")
def gcli_eq():
    server = os.environ["GRAPHDB_LOCAL_TEST_SERVER"]
    return GraphDBClient(service=service(server=server, repo=1, protocol="http"))


@pytest.fixture(scope="module")
def gcli_ssh():
    server = os.environ["GRAPHDB_LOCAL_TEST_SERVER"]
    return GraphDBClient(service=service(server=server, repo=2, protocol="http"))


def test_connectivity_names(gcli_eq):
    connectivity_names = gcli_eq.get_table(queries.connectivity_names(), index="mrid", limit=n_lim)
    assert connectivity_names.shape == (n_lim, 1)


def test_disconnected_disconnectors_and_terminals(gcli_ssh):
    disconnected = gcli_ssh.get_table(
        ssh_queries.disconnected(gcli_ssh._cim_version), index="mrid", limit=n_lim
    )
    assert len(disconnected) == n_lim


def test_connections_disconnector(gcli_eq):
    cim_version = gcli_eq._cim_version
    rdf_types = ["cim:Disconnector"]
    connections = gcli_eq.get_table(
        queries.connection_query(cim_version=cim_version, rdf_types=rdf_types, region=None),
        limit=n_lim,
    )
    assert len(connections) == n_lim


def test_connections_breaker(gcli_eq):
    cim_version = gcli_eq._cim_version
    rdf_types = ["cim:Breaker"]
    connections = gcli_eq.get_table(
        queries.connection_query(cim_version=cim_version, rdf_types=rdf_types, region=None),
        limit=n_lim,
    )
    assert len(connections) == n_lim


def test_connections_combined(gcli_eq):
    rdf_types = ["cim:Disconnector", "cim:Breaker"]
    connections = gcli_eq.get_table(
        queries.connection_query(
            cim_version=gcli_eq._cim_version, rdf_types=rdf_types, region=None
        ),
        limit=n_lim,
    )
    assert len(connections) == n_lim