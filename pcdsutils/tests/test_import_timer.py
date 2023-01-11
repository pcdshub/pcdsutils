from ..import_timer import (ImportTimeStats, ModuleStatsSummary,
                            display_summarized_import_stats, get_import_chain,
                            get_import_stats, get_import_time_text,
                            interpret_import_time, main,
                            summarize_import_stats)


def test_import_time_stats_from_line():
    line = 'import time:      1848 |       2848 |     pcdsdevices.stopper'
    stats = ImportTimeStats.from_line(line)
    assert stats.module == 'pcdsdevices.stopper'
    assert stats.root_module == 'pcdsdevices'
    assert stats.self_time_raw == 1848
    assert stats.self_time == 0.001848
    assert stats.cumulative_time_raw == 2848
    assert stats.cumulative_time == 0.002848
    assert stats.indent_level == 2


def test_module_stats_summary_from_stats():
    stats = ImportTimeStats(
        module='pcdsdevices.signal',
        root_module='pcdsdevices',
        self_time_raw=1000,
        self_time=0.001,
        cumulative_time_raw=2000,
        cumulative_time=0.002,
        indent_level=1,
    )
    summary = ModuleStatsSummary.from_stats([stats, stats, stats])
    assert summary.root_module == 'pcdsdevices'
    assert summary.self_time_raw == 3000
    assert summary.self_time == 0.003
    assert summary.cumulative_time_raw == 2000
    assert summary.cumulative_time == 0.002
    assert summary.submodule_stats == tuple([stats, stats, stats])
    summary.show_detailed_summary()


def test_get_import_time_text():
    text = get_import_time_text('sys')
    assert len(text) > 10
    for line in text:
        assert line.startswith('import time:')


def test_interpret_import_time():
    stats1 = ImportTimeStats(
        module='pcdsdevices.signal',
        root_module='pcdsdevices',
        self_time_raw=1000,
        self_time=0.001,
        cumulative_time_raw=2000,
        cumulative_time=0.002,
        indent_level=1,
    )
    stats2 = ImportTimeStats(
        module='ophyd.signal',
        root_module='ophyd',
        self_time_raw=1000,
        self_time=0.001,
        cumulative_time_raw=2000,
        cumulative_time=0.002,
        indent_level=1,
    )
    summaries = interpret_import_time(
        [stats1, stats2, stats1, stats2, stats2]
    )
    assert len(summaries['pcdsdevices'].submodule_stats) == 2
    assert len(summaries['ophyd'].submodule_stats) == 3


def test_get_import_stats_smoke():
    # No specifics in this test, the output differs for different envs
    get_import_stats('sys')


def test_summarize_import_stats():
    # No specifics in this test, the output differs for different envs
    summarize_import_stats('sys')


def test_display_summarized_import_stats():
    # No specifics in this test, the output differs for different envs
    summaries = summarize_import_stats('pcdsutils')
    display_summarized_import_stats(summaries)
    display_summarized_import_stats(summaries, focus_on='pcdsutils')


def test_get_import_chain():
    # No specifics in this test, the output differs for different envs
    get_import_chain('pcdsutils', 'sys')


def test_main():
    # No specifics in this test, the output differs for different envs
    main('sys')
    main('sys', sort_key='cumulative_time')
    main('pcdsutils', focus_on='pcdsutils')
    main('pcdsutils.import_timer', chain='typing')
