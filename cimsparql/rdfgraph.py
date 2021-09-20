"""RDFLib CIM sparql"""
from rdflib import Graph
import contextlib
import os
from typing import Dict, List, Tuple

import pandas as pd
import requests

from cimsparql.model import CimModel

class RdflibGraph(CimModel):
    def __init__(mapper: CimModel, infer: bool = False, sameas: bool = True) -> None:
        super().__init__(mapper, infer, sameas)

    def GraphParse() -> Graph:
        graph = Graph()
        graph.parse("/home/frsi/abot/rdfparser/graph_output.txt")
        return graph


