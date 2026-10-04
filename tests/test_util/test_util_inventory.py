"""Test inventory util functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import sphinx.locale
from sphinx.testing.util import SphinxTestApp
from sphinx.util.inventory import InventoryFile, _InventoryItem

from tests.test_util.intersphinx_data import (
    INVENTORY_V1,
    INVENTORY_V2,
    INVENTORY_V2_AMBIGUOUS_TERMS,
    INVENTORY_V2_NO_VERSION,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_read_inventory_v1() -> None:
    inv = InventoryFile.loads(INVENTORY_V1, uri='/util')
    assert inv['py:module', 'module'] == _InventoryItem(
        project_name='foo',
        project_version='1.0',
        uri='/util/foo.html#module-module',
        display_name='-',
    )
    assert inv['py:class', 'module.cls'] == _InventoryItem(
        project_name='foo',
        project_version='1.0',
        uri='/util/foo.html#module.cls',
        display_name='-',
    )


def test_read_inventory_v2() -> None:
    inv = InventoryFile.loads(INVENTORY_V2, uri='/util')

    assert len(inv.data['py:module']) == 2
    assert inv['py:module', 'module1'] == _InventoryItem(
        project_name='foo',
        project_version='2.0',
        uri='/util/foo.html#module-module1',
        display_name='Long Module desc',
    )
    assert inv['py:module', 'module2'] == _InventoryItem(
        project_name='foo',
        project_version='2.0',
        uri='/util/foo.html#module-module2',
        display_name='-',
    )
    assert inv['py:function', 'module1.func'].uri == ('/util/sub/foo.html#module1.func')
    assert inv['c:function', 'CFunc'].uri == '/util/cfunc.html#CFunc'
    assert inv['std:term', 'a term'].uri == '/util/glossary.html#term-a-term'
    assert inv['std:term', 'a term including:colon'].uri == (
        '/util/glossary.html#term-a-term-including-colon'
    )


def test_read_inventory_v2_not_having_version() -> None:
    inv = InventoryFile.loads(INVENTORY_V2_NO_VERSION, uri='/util')
    assert inv['py:module', 'module1'] == _InventoryItem(
        project_name='foo',
        project_version='',
        uri='/util/foo.html#module-module1',
        display_name='Long Module desc',
    )


def test_read_toml_inventory() -> None:
    content = b"""\
__project__ = "lua"
__version__ = "5.5"

[lua.function]
assert = "manual.html#pdf-assert"
debug.debug = "manual.html#pdf-debug.debug"
anchored = "api.html#$"

[py.function]
some_func = ["SomeFunc", "not-even-a-thing.html#nowhere"]

[lua.module]
manual = "manual.html#module-manual"
"""
    inv = InventoryFile.loads(content, uri='https://example.org/docs/')

    assert inv['lua:function', 'assert'] == _InventoryItem(
        project_name='lua',
        project_version='5.5',
        uri='https://example.org/docs/manual.html#pdf-assert',
        display_name='-',
    )
    assert inv['lua:function', 'debug.debug'] == _InventoryItem(
        project_name='lua',
        project_version='5.5',
        uri='https://example.org/docs/manual.html#pdf-debug.debug',
        display_name='-',
    )
    assert inv['py:function', 'some_func'] == _InventoryItem(
        project_name='lua',
        project_version='5.5',
        uri='https://example.org/docs/not-even-a-thing.html#nowhere',
        display_name='SomeFunc',
    )
    assert inv['lua:module', 'manual'].uri == (
        'https://example.org/docs/manual.html#module-manual'
    )
    assert inv['lua:function', 'anchored'].uri == (
        'https://example.org/docs/api.html#anchored'
    )

    inv = InventoryFile.loads(
        b'__project__ = ""\n__version__ = ""\n[lua.function]\nassert = "manual.html"',
        uri='https://example.org/docs/',
    )
    assert inv['lua:function', 'assert'].project_name == ''
    assert inv['lua:function', 'assert'].project_version == ''


@pytest.mark.parametrize(
    ('content', 'error'),
    [
        (b'not = [valid TOML', 'invalid TOML inventory'),
        (b'\xff', 'invalid TOML inventory'),
        (b'__version__ = "1.0"\n[py.function]\nname = "name.html"', '__project__'),
        (
            b'__project__ = "project"\n[py.function]\nname = "name.html"',
            '__version__',
        ),
        (
            b'__project__ = 1\n__version__ = "1.0"\n[py.function]\nname = "name.html"',
            '__project__',
        ),
        (
            b'__project__ = "project"\n__version__ = []\n[py.function]\nname = "name.html"',
            '__version__',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n[py.function]\nname = 1',
            'invalid entry',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n[py.function]\nname = ["only one"]',
            'invalid entry',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n[py.function]\nname = ["", "name.html"]',
            'invalid entry',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n[py.function]\nname = ""',
            'invalid entry',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\npy = 1',
            'invalid domain table',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n[py]\nname = "name.html"',
            'invalid object table',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\npy = { function = "invalid" }',
            'invalid object table',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n[py.function]\n"" = "name.html"',
            'empty object name',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n["bad:domain".function]\nname = "name.html"',
            'invalid domain name',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n["".function]\nname = "name.html"',
            'invalid domain name',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n["bad domain".function]\nname = "name.html"',
            'invalid domain name',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n[py."bad:type"]\nname = "name.html"',
            'invalid object type',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n[py.""]\nname = "name.html"',
            'invalid object type',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n[py."bad type"]\nname = "name.html"',
            'invalid object type',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n[py]',
            'invalid domain table',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n[py.function]',
            'invalid object table',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n[py.function.empty]',
            'empty object table',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"',
            'at least one domain and object',
        ),
        (
            b'__project__ = "project"\n__version__ = "1.0"\n[py.function]\na.b = "one"\n"a.b" = "two"',
            'duplicate object name',
        ),
    ],
)
def test_read_invalid_toml_inventory(content: bytes, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        InventoryFile.loads(content, uri='https://example.org/docs/')


@pytest.mark.sphinx('html', testroot='root')
def test_ambiguous_definition_warning(app: SphinxTestApp) -> None:
    InventoryFile.loads(INVENTORY_V2_AMBIGUOUS_TERMS, uri='/util')

    def _multiple_defs_notice_for(entity: str) -> str:
        return f'contains multiple definitions for {entity}'

    # was warning-level; reduced to info-level
    # See: https://github.com/sphinx-doc/sphinx/issues/12613
    mult_defs_a, mult_defs_b = (
        _multiple_defs_notice_for('std:term:a'),
        _multiple_defs_notice_for('std:term:b'),
    )
    assert mult_defs_a not in app.warning.getvalue().lower()
    assert mult_defs_a not in app.status.getvalue().lower()
    assert mult_defs_b not in app.warning.getvalue().lower()
    assert mult_defs_b in app.status.getvalue().lower()


def _write_appconfig(dir: Path, language: str, prefix: str | None = None) -> Path:
    prefix = prefix or language
    (dir / prefix).mkdir(parents=True, exist_ok=True)
    (dir / prefix / 'conf.py').write_text(f'language = "{language}"', encoding='utf8')
    (dir / prefix / 'index.rst').write_text('index.rst', encoding='utf8')
    assert sorted(p.name for p in (dir / prefix).iterdir()) == ['conf.py', 'index.rst']
    assert (dir / prefix / 'index.rst').exists()
    return dir / prefix


def _build_inventory(srcdir: Path) -> Path:
    app = SphinxTestApp(srcdir=srcdir)
    app.build()
    sphinx.locale.translators.clear()
    return app.outdir / 'objects.inv'


def test_inventory_localization(tmp_path: Path) -> None:
    # Build an app using Estonian (EE) locale
    srcdir_et = _write_appconfig(tmp_path, 'et')
    inventory_et = _build_inventory(srcdir_et)

    # Build the same app using English (US) locale
    srcdir_en = _write_appconfig(tmp_path, 'en')
    inventory_en = _build_inventory(srcdir_en)

    # Ensure that the inventory contents differ
    assert inventory_et.read_bytes() != inventory_en.read_bytes()
