"""
Helpers for timing how long it takes to do various imports.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from prettytable import PrettyTable


@dataclass(frozen=True)
class ImportTimeStats:
    """
    Stats about importing this module or submodule.

    Attributes
    ----------
    module : str
        The full import name, e.g. pcdsdevices.signal
    root_module : str
        The source module, e.g. pcdsdevices
    self_time_raw : int
        The time it took to import this module in microseconds, not counting
        the time it took to import other modules.
    self_time : float
        The time it took to import this module in seconds, not counting
        the time it took to import other modules.
    cumulative_time_raw : int
        The time it took to import this module in microseconds,
        including the time it took to import other modules.
    cumulative_time : float
        The time it took to import this module in seconds,
        including the time it took to import other modules.
    indent_level : int
        How deep this import was. An indent level of 0 indicates that
        this was the main import or a python internal import used to set up
        the import system itself. Each additional level means that this module
        was imported by a module one level lower. For example, a module with
        indent level 2 was imported by a module with import level 1.
    """
    module: str
    root_module: str
    self_time_raw: int
    self_time: float
    cumulative_time_raw: int
    cumulative_time: float
    indent_level: int

    @classmethod
    def from_line(cls, line: str) -> ImportTimeStats:
        """
        Assemble an ImportTimeStats from a python -X importtime output line.

        Example lines:
        import time:      2848 |       2848 |     pcdsdevices.stopper
        import time:      7611 |      10459 |   pcdsdevices.valve
        import time:      1859 |       1859 |   pcdsdevices.wfs
        import time:      2913 |   12317383 | pcdsdevices.device_types
        """
        if not line.startswith('import time'):
            raise ValueError(
                f'Recieved {line}, which is not a valid importtime output.'
            )
        line = line.split('import time:')[1]
        self_time_raw, cumulative_time_raw, module = line.split('|')
        self_time_raw = int(self_time_raw.strip())
        cumulative_time_raw = int(cumulative_time_raw.strip())
        indent_level = (module.count(' ') - 1) // 2
        module = module.strip()

        return cls(
            module=module,
            root_module=module.split('.')[0],
            self_time_raw=self_time_raw,
            self_time=self_time_raw / 1e6,
            cumulative_time_raw=cumulative_time_raw,
            cumulative_time=cumulative_time_raw / 1e6,
            indent_level=indent_level,
        )


@dataclass(frozen=True)
class ModuleStatsSummary:
    """
    For a top-level module, the total time spent on all the submodules.

    Attributes
    ----------
    root_module : str
        The source module, e.g. pcdsdevices
    self_time_raw : int
        The time it took to import this module in microseconds, not counting
        the time it took to import other modules.
    self_time : float
        The time it took to import this module in seconds, not counting
        the time it took to import other modules.
    cumulative_time_raw : int
        The time it took to import this module in microseconds,
        including the time it took to import other modules.
    cumulative_time : float
        The time it took to import this module in seconds,
        including the time it took to import other modules.
    submodule_stats : tuple of ImportTimeStats
        The stats that were used to generate this stats summary.
    """
    root_module: str
    self_time_raw: int
    self_time: float
    cumulative_time_raw: int
    cumulative_time: float
    submodule_stats: Tuple[ImportTimeStats, ...]

    @classmethod
    def from_stats(cls, stats: List[ImportTimeStats]) -> ModuleStatsSummary:
        """
        Create a ModuleStatsSummary from a list of ImportTimeStats.
        """
        self_time_raw = 0
        cumulative_time_raw = 0
        for stat in stats:
            self_time_raw += stat.self_time_raw
            cumulative_time_raw = max(
                cumulative_time_raw,
                stat.cumulative_time_raw,
            )
        return cls(
            root_module=stats[0].root_module,
            self_time_raw=self_time_raw,
            self_time=self_time_raw / 1e6,
            cumulative_time_raw=cumulative_time_raw,
            cumulative_time=cumulative_time_raw / 1e6,
            submodule_stats=tuple(stats),
        )

    def show_detailed_summary(self, sort_key: str = 'self_time') -> None:
        """
        For this module, explain the situation to stdout.
        """
        field_names = tuple(
            field for field in ImportTimeStats.__dataclass_fields__
            if 'raw' not in field
        )
        table = PrettyTable(
            field_names=field_names,
        )
        summary_row = list(
            getattr(self, attr, 'N/A')
            for attr in field_names
        )
        summary_row[0] = 'Total'
        table.add_row(summary_row)
        for stats in sorted(
            self.submodule_stats,
            key=lambda s: getattr(s, sort_key),
            reverse=True,
        ):
            table.add_row(
                tuple(
                    getattr(stats, attr)
                    for attr in field_names
                )
            )
        print(table)


def get_import_time_text(module: str) -> List[str]:
    """
    Run python -X importtime modulename in a subprocess.

    Returns the line-by-line std output from this call.
    """
    if not sys.executable:
        raise RuntimeError('Could not locate correct python executable.')
    return subprocess.check_output(
        [sys.executable, '-X', 'importtime', '-c', f'import {module}'],
        universal_newlines=True,
        stderr=subprocess.STDOUT,
    ).splitlines()


def interpret_import_time(
    stats: List[ImportTimeStats],
) -> Dict[str, ModuleStatsSummary]:
    """
    Summarize the results of the import time checker in an understandable way.

    The output is a dictionary of top-level module import name to a
    ModuleStatsSummary instance that details how much time it took to import
    that module.

    Parameters
    ----------
    stats : list of ImportTimeStats
        All of the stats objects from a particular importtime output.
    """
    stats_by_root_module = defaultdict(list)
    for stat in stats:
        stats_by_root_module[stat.root_module].append(stat)
    summaries = {}
    for root_module, stats in stats_by_root_module.items():
        summaries[root_module] = ModuleStatsSummary.from_stats(stats)
    return summaries


def get_import_stats(module: str) -> List[ImportTimeStats]:
    """
    Get the import time statistics for a given module.

    Parameters
    ----------
    module : str
        The module to import.
    """
    output = get_import_time_text(module)
    stats = []
    for line in output[1:]:
        stats.append(ImportTimeStats.from_line(line))
    return stats


def summarize_import_stats(module: str) -> Dict[str, ModuleStatsSummary]:
    """
    Summarize the import time statistics for a given module.

    Parameters
    ----------
    module : str
        The module to import.
    """
    return interpret_import_time(get_import_stats(module))


def display_summarized_import_stats(
    stats_summary: Dict[str, ModuleStatsSummary],
    sort_key: str = 'self_time',
    focus_on: Optional[str] = None,
) -> None:
    """
    Show a prettytable summary of all the import statistics.

    Parameters
    ----------
    stats_summary : dict[str, ModuleStatsSummary]
        The output from summarize_import_stats. This is a mapping from
        root module name to the module stats summary objects.
    sort_key : str, optional
        The key to sort the output table on.
    focus_on : str, optional
        A module to focus on for the output. If provided, we'll show
        a detailed breakdown of that module instead of the big table
        of all the imported modules.
    """
    # When the user only cares about dissecting a specific module.
    if focus_on is not None:
        return stats_summary[focus_on].show_detailed_summary(sort_key)
    # Sort and assemble a prettytable
    field_names = tuple(
        field for field in ModuleStatsSummary.__dataclass_fields__
        if field != 'submodule_stats'
        if 'raw' not in field
    )
    table = PrettyTable(
        field_names=field_names,
    )
    for stats in sorted(
        stats_summary.values(),
        key=lambda s: getattr(s, sort_key),
        reverse=True,
    ):
        table.add_row(
            tuple(
                getattr(stats, attr)
                for attr in field_names
            )
        )
    print(table)


def get_import_chain(
    module_to_import: str,
    submodule_to_chain: str,
) -> List[str]:
    """
    For a given import, figure out why a specific submodule is being imported.

    The return value is a list of modules that import each other in order,
    starting with the module you imported and ending with the submodule you're
    trying to track down.

    Parameters
    ----------
    module_to_import : str
        The module you are trying to import.
    submodule_to_chain : str
        The submodule that gets imported that you need to track down.

    Returns
    -------
    module_chain : list of str
        The modules that import each other in order, starting with the module
        you imported and ending with the submodule you're trying to track
        down.
    """
    chain = []
    for stats in get_import_stats(module_to_import):
        if stats.module == submodule_to_chain:
            chain = [stats]
        elif chain:
            if stats.indent_level < chain[0].indent_level:
                chain.insert(0, stats)
    return [stats.module for stats in chain]


def main(
    module: str,
    sort_key: str = 'self_time',
    focus_on: Optional[str] = None,
    chain: Optional[str] = None,
) -> None:
    if chain is not None:
        print(f'Import chain for importing dependency {chain}:')
        for submodule in get_import_chain(
            module_to_import=module,
            submodule_to_chain=chain,
        ):
            print(submodule)
        return
    stats_summary = summarize_import_stats(module)
    display_summarized_import_stats(
        stats_summary=stats_summary,
        sort_key=sort_key,
        focus_on=focus_on,
    )


def _entrypoint():
    parser = argparse.ArgumentParser(
        description='Utility to identify modules that are slow to import.',
    )
    parser.add_argument(
        'module',
        help='The module name to import.',
    )
    parser.add_argument(
        '--sort-key',
        default='self_time',
        help='The table header to sort on.',
    )
    parser.add_argument(
        '--show-module',
        default=None,
        help='A specific module to show a breakdown for in the output.',
    )
    parser.add_argument(
        '--show-chain',
        default=None,
        help=(
            'Instead, show the chain of imports that leads to a specific '
            'dependency being imported.'
        ),
    )
    args = parser.parse_args()
    main(
        module=args.module,
        sort_key=args.sort_key,
        focus_on=args.show_module,
        chain=args.show_chain,
    )


if __name__ == '__main__':
    _entrypoint()
