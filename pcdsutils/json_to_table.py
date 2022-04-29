#!/usr/bin/env python3
"""
Take in a JSON document with an array at the top-level and generate a
PrettyTable from it.
"""

import argparse
import dataclasses
import enum
import json
import sys
from typing import Any, BinaryIO, List, Optional, cast

import prettytable


class TableStyle(enum.Enum):
    """Table style/format to print."""
    html = enum.auto()
    csv = enum.auto()
    latex = enum.auto()

    default = enum.auto()
    msword_friendly = enum.auto()
    plain_columns = enum.auto()
    markdown = enum.auto()
    orgmode = enum.auto()
    double_border = enum.auto()
    # random = enum.auto()


@dataclasses.dataclass
class ProgramArguments:
    """Argparse arguments for json_to_table."""
    input_file: BinaryIO
    sort_key: str
    columns: List[str]
    format: str = "markdown"
    list_delimiter: str = ", "
    max_col_width: int = 80


def string_for_table(
    value: Any, max_length: int = 80, list_delimiter: str = ", "
) -> str:
    """Fix the value for display in the table."""
    if isinstance(value, list):
        result = list_delimiter.join(string_for_table(v) for v in value)
    else:
        result = str(value)

    if len(result) > max_length:
        if max_length <= 3:
            return "..."
        return result[:max_length - 3] + "..."
    return result[:max_length]


def table_from_json(
    data: List[dict],
    sort_key: str,
    columns: Optional[List[str]] = None,
    list_delimiter: str = ", ",
    max_col_width: int = 80,
) -> prettytable.PrettyTable:
    """Create a PrettyTable from the input JSON data."""
    table = prettytable.PrettyTable()
    table.field_names = columns
    for item in sorted(data, key=lambda item: item.get(sort_key, "?")):
        row = [
            string_for_table(
                item.get(key, ""),
                list_delimiter=list_delimiter,
                max_length=max_col_width,
            )
            for key in table.field_names
        ]
        table.add_row(row)

    return table


def main(args: ProgramArguments):
    data = json.load(args.input_file)
    table = table_from_json(
        data,
        sort_key=args.sort_key,
        columns=args.columns,
        list_delimiter=args.list_delimiter,
        max_col_width=args.max_col_width,
    )

    format = getattr(TableStyle, args.format)
    if format == TableStyle.csv:
        print(table.get_csv_string())
    elif format == TableStyle.html:
        print(table.get_html_string())
    elif format == TableStyle.latex:
        print(table.get_latex_string())
    else:
        table.set_style(getattr(prettytable, format.name.upper()))
        print(table)


def _create_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.description = "Format a table given JSON with PrettyTable"
    parser.add_argument("--sort-key", type=str, required=True, help="Sort key")
    parser.add_argument(
        "--columns",
        nargs="+",
        required=True,
        help="Columns to include in the table (by key name)",
    )
    parser.add_argument(
        "--list-delimiter",
        type=str,
        default=", ",
        help="Used when joining entries of a list",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=list(val.name for val in TableStyle),
        default="markdown",
        help="Used when joining entries of a list",
    )
    parser.add_argument(
        "--max-col-width",
        type=int,
        default=80,
        help="Maximum characters per column",
    )
    parser.add_argument(
        "input_file",
        type=argparse.FileType(mode="rb"),
        help="Filename to read from ('-' for stdin)",
    )
    return parser


def _entrypoint():
    parser = _create_argparser()
    args = parser.parse_args(args=sys.argv[1:])
    main(cast(ProgramArguments, args))


if __name__ == "__main__":
    _entrypoint()
