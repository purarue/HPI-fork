from __future__ import annotations

from .internal import assert_subpackage  # noqa: I001

assert_subpackage(__name__)

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Literal, Union, overload

from .common import PathIsh
from .compat import assert_never


def sqlite_connect_immutable(db: PathIsh) -> sqlite3.Connection:
    return sqlite3.connect(f'file:{db}?immutable=1', uri=True)


def test_sqlite_connect_immutable(tmp_path: Path) -> None:
    db = str(tmp_path / 'db.sqlite')
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE testtable (col)')

    import pytest

    with pytest.raises(sqlite3.OperationalError, match='readonly database'):
        with sqlite_connect_immutable(db) as conn:
            conn.execute('DROP TABLE testtable')

    # succeeds without immutable
    with sqlite3.connect(db) as conn:
        conn.execute('DROP TABLE testtable')


SqliteRowFactory = Callable[[sqlite3.Cursor, sqlite3.Row], Any]


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return dict(zip(fields, row))


Factory = Union[SqliteRowFactory, Literal['row', 'dict']]


@contextmanager
def sqlite_connection(db: PathIsh, *, immutable: bool = False, row_factory: Factory | None = None) -> Iterator[sqlite3.Connection]:
    dbp = f'file:{db}'
    # https://www.sqlite.org/draft/uri.html#uriimmutable
    if immutable:
        # assert results in nicer error than sqlite3.OperationalError
        assert Path(db).exists(), db
        dbp = f'{dbp}?immutable=1'
    row_factory_: Any = None
    if row_factory is not None:
        if callable(row_factory):
            row_factory_ = row_factory
        elif row_factory == 'row':
            row_factory_ = sqlite3.Row
        elif row_factory == 'dict':
            row_factory_ = dict_factory
        else:
            assert_never()

    conn = sqlite3.connect(dbp, uri=True)
    try:
        conn.row_factory = row_factory_
        with conn:
            yield conn
    finally:
        # Connection context manager isn't actually closing the connection, only keeps transaction
        conn.close()


# TODO come up with a better name?
# NOTE: this is tested by tests/sqlite.py::test_sqlite_read_with_wal
def sqlite_copy_and_open(db: PathIsh) -> sqlite3.Connection:
    """
    'Snapshots' database and opens by making a deep copy of it including journal/WAL files
    """
    dp = Path(db)
    # TODO make atomic/check mtimes or something
    dest = sqlite3.connect(':memory:')
    with TemporaryDirectory() as td:
        tdir = Path(td)
        # shm should be recreated from scratch -- safer not to copy perhaps
        tocopy = [dp] + [p for p in dp.parent.glob(dp.name + '-*') if not p.name.endswith('-shm')]
        for p in tocopy:
            shutil.copy(p, tdir / p.name)
        with sqlite3.connect(str(tdir / dp.name)) as conn:
            conn.backup(target=dest)
        conn.close()
    return dest


# NOTE hmm, so this kinda works
# V = TypeVar('V', bound=Tuple[Any, ...])
# def select(cols: V, rest: str, *, db: sqlite3.Connection) -> Iterator[V]:
# but sadly when we pass columns (Tuple[str, ...]), it seems to bind this type to V?
# and then the return type ends up as Iterator[Tuple[str, ...]], which isn't desirable :(
# a bit annoying to have this copy-pasting, but hopefully not a big issue

# fmt: off
@overload
def select(cols: tuple[str                                   ], rest: str, *, db: sqlite3.Connection) -> \
        Iterator[tuple[Any                                   ]]: ...
@overload
def select(cols: tuple[str, str                              ], rest: str, *, db: sqlite3.Connection) -> \
        Iterator[tuple[Any, Any                              ]]: ...
@overload
def select(cols: tuple[str, str, str                         ], rest: str, *, db: sqlite3.Connection) -> \
        Iterator[tuple[Any, Any, Any                         ]]: ...
@overload
def select(cols: tuple[str, str, str, str                    ], rest: str, *, db: sqlite3.Connection) -> \
        Iterator[tuple[Any, Any, Any, Any                    ]]: ...
@overload
def select(cols: tuple[str, str, str, str, str               ], rest: str, *, db: sqlite3.Connection) -> \
        Iterator[tuple[Any, Any, Any, Any, Any               ]]: ...
@overload
def select(cols: tuple[str, str, str, str, str, str          ], rest: str, *, db: sqlite3.Connection) -> \
        Iterator[tuple[Any, Any, Any, Any, Any, Any          ]]: ...
@overload
def select(cols: tuple[str, str, str, str, str, str, str     ], rest: str, *, db: sqlite3.Connection) -> \
        Iterator[tuple[Any, Any, Any, Any, Any, Any, Any     ]]: ...
@overload
def select(cols: tuple[str, str, str, str, str, str, str, str], rest: str, *, db: sqlite3.Connection) -> \
        Iterator[tuple[Any, Any, Any, Any, Any, Any, Any, Any]]: ...
# fmt: on

def select(cols, rest, *, db):
    # db arg is last cause that results in nicer code formatting..
    return db.execute('SELECT ' + ','.join(cols) + ' ' + rest)
