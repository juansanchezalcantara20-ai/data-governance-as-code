"""Readability rules for everything the demo app says (Spanish first): no snake_case and no unexplained acronyms
outside technical sections, both languages with the same keys, and complete labels for what the engine exports."""

import json
import re
from html.parser import HTMLParser

from tests.conftest import ROOT

APP = ROOT / "app"
SNAKE = re.compile(r"\b[a-z0-9]+_[a-z0-9_]+\b")
ACRONYM = re.compile(r"\b[A-Z]{2,}\b(?!-\d)")
EXEMPT_SECTIONS = {"tecnico", "meta"}   # technical labels and the language switch
ALLOWED_ACRONYMS = {"S.A.C."}           # explained in "jargon" with its dots


def _load(lang):
    return json.loads((APP / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))


def _strings(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _strings(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _strings(v, path + (str(i),))
    elif isinstance(node, str):
        yield path, re.sub(r"\{\w+\}", "", node)   # {placeholders} are replaced before display


def _keys(node, path=""):
    if isinstance(node, dict):
        return {k for key, v in node.items() for k in _keys(v, f"{path}.{key}")} | {path}
    if isinstance(node, list):
        return {f"{path}[{len(node)}]"} | {k for i, v in enumerate(node) for k in _keys(v, f"{path}[{i}]")}
    return {path}


def test_spanish_texts_have_no_snake_case():
    bad = [(".".join(p), s) for p, s in _strings(_load("es")) if p[0] not in EXEMPT_SECTIONS and SNAKE.search(s)]
    assert bad == []


def test_every_acronym_is_explained():
    es = _load("es")
    explained = set(es["jargon"]) | ALLOWED_ACRONYMS
    missing = sorted({a for p, s in _strings(es) if p[0] not in EXEMPT_SECTIONS for a in ACRONYM.findall(s)} - explained)
    assert missing == [], f"add these to 'jargon' or reword: {missing}"


def test_both_languages_have_the_same_keys():
    assert _keys(_load("es")) == _keys(_load("en"))


def test_every_exported_identifier_has_a_label():
    es = _load("es")
    catalog = json.loads((APP / "data" / "catalog.json").read_text(encoding="utf-8"))
    for d in catalog["datasets"]:
        assert d["id"].split(".", 1)[1] in es["datasets"], d["id"]
        for c in d["columns"]:
            assert c["name"] in es["columns"], c["name"]
    for e in json.loads((APP / "data" / "lineage.json").read_text(encoding="utf-8"))["nodes"]:
        if e["kind"] == "exposure":
            assert e["id"].split(":", 1)[1] in es["exposures"]
    rules = json.loads((APP / "data" / "quality.json").read_text(encoding="utf-8"))["rules"]
    assert {r["kind"] for r in rules} <= set(es["rule_text"])
    roles = json.loads((APP / "data" / "roles.json").read_text(encoding="utf-8"))
    assert {r["id"] for r in roles["roles"]} <= set(es["roles"])
    assert {a["id"] for a in roles["raci"]} <= set(es["raci_activities"])


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "code", "pre"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "code", "pre"):
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.chunks.append(data.strip())


def test_static_html_is_readable():
    parser = _Text()
    parser.feed((APP / "index.html").read_text(encoding="utf-8"))
    text = " ".join(parser.chunks)
    assert not SNAKE.search(text)
    assert set(ACRONYM.findall(text)) <= {"EN"}
