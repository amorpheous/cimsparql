"""RDFLib CIM sparql"""
from rdflib import Graph
import contextlib
import os
from typing import Dict, List, Tuple

import pandas as pd
import requests

from cimsparql.model import CimModel

class RdflibGraph(CimModel):

    def GraphParse():
        graph = Graph()
        graph.parse("/home/frsi/abot/rdfparser/graph_output.txt")


