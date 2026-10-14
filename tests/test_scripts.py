import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cc = _load("check_consistency")
rp = _load("retry_plan")


def test_retry_list_maps_workbook_names_to_cli_slugs():
    labels = {"5-11Oct26", "6-12Oct25"}
    empty = [("Totals", "Home page", "Paid Search", "Mobile", "Begin checkout", "5-11Oct26")]
    country = [(("Route page", "Direct", "Desktop", "Start Search", "6-12Oct25"), 114, 132)]
    got = cc.retry_list([], country, empty, labels)
    assert got == [
        {"page": "begin_checkout", "period": "current", "group": "home"},
        {"page": "start_search", "period": "prior", "group": "route"},
    ]


def test_retry_list_dedupes():
    labels = {"5-11Oct26", "6-12Oct25"}
    empty = [
        ("Totals", "Home page", "Direct", "Mobile", "Searches", "5-11Oct26"),
        ("Totals", "Home page", "Paid Search", "Total", "Searches", "5-11Oct26"),
    ]
    assert len(cc.retry_list([], [], empty, labels)) == 1


def _data(status):
    return {"pages": {"purchases": {"periods": {"current": {"groups": {
        "All landing pages": {"status": status},
        "Home page": {"status": "ok"},
    }}}}}}


def test_plan_picks_non_ok_combinations():
    assert rp.plan(_data("quota_error")) == [("purchases", "all")]


def test_plan_merges_gate_and_dedupes():
    gate = {"retry": [{"page": "purchases", "period": "prior", "group": "all"},
                      {"page": "searches", "period": "current", "group": "home"}]}
    assert rp.plan(_data("quota_error"), gate) == [("purchases", "all"), ("searches", "home")]


def test_plan_empty_when_all_ok():
    assert rp.plan(_data("ok")) == []
