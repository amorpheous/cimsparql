from __future__ import annotations
import datetime as dt
from cimsparql.queries import combine_statements, unionize
from typing import TYPE_CHECKING

import pandas as pd
import warnings

if TYPE_CHECKING:
    from cimsparql.graphdb import GraphDBClient

as_type_able = [int, float, str, "Int64", "Int32", "Int16"]

python_type_map = {
    "string": str,
    "integer": int,
    "boolean": lambda x: x.lower == "true",
    "float": float,
    "dateTime": dt.datetime,
}

sparql_type_map = {"literal": str, "uri": lambda x: x.split("_")[-1] if len(x) == 48 else x}


class TypeMapperQueries:
    @property
    def generals(self) -> list:
        """
        For sparql-types that are not sourced from objects of type rdf:property,
        sparql & type are required.

        sparql values should be like: http://iec.ch/TC57/2010/CIM-schema-cim15#PerCent
        this is how type or DataType usually looks like for each
        data point in the converted query result from SPARQLWrapper.

        type can be anything as long as it is represented in the python_type_map.
        """
        return [
            [
                "?sparql_type rdf:type rdfs:Datatype",
                "?sparql_type owl:equivalentClass ?range",
                'BIND(STRBEFORE(str(?range), "#") as ?prefix)',
                'BIND(STRAFTER(str(?range), "#") as ?type)',
            ]
        ]

    @property
    def prefix_general(self) -> list:
        """
        Common query used as a base for all prefix_based queries.
        """
        return [
            "?sparql_type rdf:type rdf:Property",
            "?sparql_type rdfs:range ?range",
            'BIND(STRBEFORE(str(?range), "#") as ?prefix) .',
        ]

    @property
    def prefix_based(self) -> dict:
        """
        Each prefix can have different locations of where DataTypes are described.
        Based on a object of type rdf:property & its rdfs:range, one has edit the
        query such that one ends up with the DataType.
        """
        return {
            "http://www.w3.org/2001/XMLSchema": ["?range rdfs:label ?type"],
            "http://iec.ch/TC57/2010/CIM-schema-cim15": [
                "?range owl:equivalentClass ?class",
                "?class rdfs:label ?type",
            ],
        }

    @property
    def _query(self) -> str:
        select_query = "SELECT ?sparql_type ?type ?prefix"

        grouped_generals = [combine_statements(*g, split=" .\n") for g in self.generals]
        grouped_prefixes = [
            combine_statements(*v, f'FILTER (?prefix = "{k}")', split=" .\n")
            for k, v in self.prefix_based.items()
        ]
        grouped_prefix_general = combine_statements(*self.prefix_general, split=" .\n")
        unionized_generals = unionize(*grouped_generals)
        unionized_prefixes = unionize(*grouped_prefixes)

        full_prefixes = combine_statements(grouped_prefix_general, unionized_prefixes, group=True)
        full_union = unionize(unionized_generals, full_prefixes, group=False)
        return f"{select_query}\nWHERE\n{{\n{full_union}\n}}"


class TypeMapper(TypeMapperQueries):
    def __init__(self, client: GraphDBClient, custom_additions: dict = None):
        self.prefixes = client.prefix_dict
        custom_additions = custom_additions if custom_additions is not None else {}
        self.map = {**sparql_type_map, **self.get_map(client), **custom_additions}

    @staticmethod
    def type_map(df: pd.DataFrame) -> dict:
        df["type"] = df["type"].str.lower()
        d = df.set_index("sparql_type").to_dict("index")
        return {k: python_type_map.get(v.get("type", "String")) for k, v in d.items()}

    @staticmethod
    def prefix_map(df: pd.DataFrame) -> dict:
        df = df.loc[~df["prefix"].isna()].head()
        df["comb"] = df["prefix"] + "#" + df["type"]
        df = df.drop_duplicates("comb")
        d2 = df.set_index("comb").to_dict("index")
        return {k: python_type_map.get(v.get("type", "String")) for k, v in d2.items()}

    def get_map(self, client: GraphDBClient) -> dict:
        """
        Reads all metadata from the sparql backend & creates a sparql-type -> python type map

        :param client: initialized GraphDBClient
        :return: sparql-type -> python type map
        """
        df = client.get_table(self._query, map_data_types=False)
        if df.empty:
            return {}
        type_map = self.type_map(df)
        prefix_map = self.prefix_map(df)
        return {**type_map, **prefix_map}

    def get_type(self, sparql_type, missing_return="identity", custom_maps: dict = None):
        """
        Gets the python type/function to apply on columns of the sparql_type,

        :param sparql_type:
        :param missing_return: returns the identity-function if python- type/function is not found,
            else returns None
        :param custom_maps: dictionary on the form {'sparql_data_type': function/datatype}
            overwrites the default types gained from the graphdb. Applies the function/datatype
            on all columns in the DataFrame that are of the sparql_data_type.
        :return: python datatype or function to apply on DataFrame columns
        """
        map = {**self.map, **custom_maps} if custom_maps is not None else self.map
        try:
            return map[sparql_type]
        except KeyError:
            warnings.warn(f"{sparql_type} not found in the sparql -> python type map")
            if missing_return == "identity":
                return lambda x: x
            else:
                return None

    def convert_dict(self, d: dict, drop_missing: bool = True, custom_maps: dict = None) -> dict:
        """
        Converts a col_name -> sparql_datatype map to a col_name -> python_type map

        :param d: dictionary with {'column_name': 'sparql type/DataType'}
        :param drop_missing: drops columns where no corresponding python type could be found
        :param custom_maps: dictionary on the form {'sparql_data_type': function/datatype}
            overwrites the default types gained from the graphdb. Applies the function/datatype
            on all columns in the DataFrame that are of the sparql_data_type.
        :return: col_name -> python_type/function map
        """
        missing_return = "None" if drop_missing else "identity"
        base = {
            column: self.get_type(data_type, missing_return, custom_maps)
            for column, data_type in d.items()
        }
        if drop_missing:
            return {k: v for k, v in base.items() if v is not None}
        return base

    @staticmethod
    def map_base_types(df: pd.DataFrame, type_map: dict) -> pd.DataFrame:
        """
        Maps the datatypes in type_map which can be used with the df.astype function.

        :param df:
        :param type_map: {'column_name': type/function}
            map of functions/types to apply on the columns.
        :return: mapped DataFrame
        """
        as_type_able_columns = {c for c, datatype in type_map.items() if datatype in as_type_able}
        df = df.astype({column: type_map[column] for column in as_type_able_columns})
        return df

    @staticmethod
    def map_exceptions(df: pd.DataFrame, type_map: dict) -> pd.DataFrame:
        """
        Maps the functions/datatypes in type_map which cant be done with the df.astype function.

        :param df:
        :param type_map: {'column_name': type/function}
            map of functions/types to apply on the columns.
        :return: mapped DataFrame
        """
        ex_columns = {c for c, datatype in type_map.items() if datatype not in as_type_able}
        for column in ex_columns:
            df[column] = df[column].apply(type_map[column])
        return df

    def map_data_types(
        self, df: pd.DataFrame, data_row: dict, custom_maps: dict = None, columns: dict = None
    ) -> pd.DataFrame:
        """
        Maps the dtypes of a DataFrame to the python-corresponding types of the sparql-types
        from the source data.

        :param df: DataFrame with columns to be converted
        :param data_row: a complete row with data from the source data
            of which the DataFrame is constructed from
        :param custom_maps: dictionary on the form {'sparql_data_type': function/datatype}
            overwrites the default types gained from the graphdb. Applies the function/datatype
            on all columns in the DataFrame that are of the sparql_data_type.
        :param columns: dictionary on the form {'DataFrame_column_name: function/datatype}
            overwrites the default types gained from the graphdb.
            Applies the function/datatype on the column.
        :return: mapped DataFrame
        """
        columns = {} if columns is None else columns
        col_map = {
            column: data.get("datatype", data.get("type", None))
            for column, data in data_row.items()
            if column not in columns.keys()
        }
        type_map = {**self.convert_dict(col_map, custom_maps=custom_maps), **columns}

        df = self.map_base_types(df, type_map)
        df = self.map_exceptions(df, type_map)
        return df