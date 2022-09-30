"""
Tools for IO.
"""
from __future__ import annotations

import enum
import os
import sys
from collections.abc import Set
from datetime import datetime
from pathlib import Path, PurePath
from typing import Optional, Union, NamedTuple

from pandas.io.common import get_handle

from smartio._errors import (
    ReadPermissionsError,
    UnsupportedOperationError,
    WritePermissionsError,
)


class _Enum(enum.Enum):
    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __new__(cls):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj


class BaseCompression(NamedTuple):
    base: Path
    compression: CompressionFormat


class CompressionFormat(_Enum):
    """
    A compression scheme or no compression: gzip, zip, bz2, xz, and none.
    These are the formats supported by Pandas for read and write.
    Provides a few useful functions for calling code.

    Examples:
        - ``CompressionFormat.strip("my_file.csv.gz")  # Path("my_file.csv")``
        - ``CompressionFormat.from_path("myfile.csv")  # CompressionFormat.none``
    """

    #brotli = ()
    gz = ()
    zip = ()
    bz2 = ()
    xz = ()
    zstd = ()
    lz4 = ()
    none = ()

    @classmethod
    def list(cls) -> Set[CompressionFormat]:
        """
        Returns the set of CompressionFormats.
        Works with static type analysis.
        """
        return set(cls)

    @classmethod
    def list_non_empty(cls) -> Set[CompressionFormat]:
        """
        Returns the set of CompressionFormats, except for ``none``.
        Works with static type analysis.
        """
        return {c for c in cls if c is not cls.none}

    @classmethod
    def of(cls, t: Union[str, CompressionFormat]) -> CompressionFormat:
        """
        Returns a FileFormat from a name (e.g. "gz" or "gzip").
        Case-insensitive.

        Example:
            ``CompressionFormat.of("gzip").suffix  # ".gz"``
        """
        if isinstance(t, CompressionFormat):
            return t
        try:
            return CompressionFormat[str(t).strip().lower()]
        except KeyError:
            for f in CompressionFormat.list():
                if t == f.full_name:
                    return f
            raise  # pragma: no cover

    @property
    def full_name(self) -> str:
        """
        Returns a more-complete name of this format.
        For example, "gzip" "bzip2", "xz", and "none".
        """
        return {CompressionFormat.gz: "gzip", CompressionFormat.bz2: "bzip2"}.get(self, self.name)

    @property
    def is_compressed(self) -> bool:
        """
        Shorthand for ``fmt is not CompressionFormat.none``.
        """
        return self is not CompressionFormat.none

    @classmethod
    def all_suffixes(cls) -> Set[str]:
        """
        Returns all suffixes for all compression formats.
        """
        return {c.suffix for c in cls}

    @property
    def name_or_none(self) -> Optional[str]:
        """
        Returns the name, or ``None`` if it is not compressed.
        """
        return None if self is CompressionFormat.none else self.name

    @property
    def pandas_value(self) -> Optional[str]:
        """
        Returns the value that should be passed to Pandas as ``compression``.
        Returns an empty string if Pandas does not support the format directly.
        """
        if self is CompressionFormat.none:
            return None
        if self is CompressionFormat.gz:
            return "gzip"
        if self is CompressionFormat.lz4:
            return ""
        return self.name

    @property
    def suffix(self) -> str:
        """
        Returns the single Pandas-recognized suffix for this format.
        This is just "" for CompressionFormat.none.
        """
        if self is CompressionFormat.none:
            return ""
        if self is CompressionFormat.zstd:
            return ".zst"
        return "." + self.name

    @classmethod
    def strip_suffix(cls, path: PathLike) -> Path:
        """
        Returns a path with any recognized compression suffix (e.g. ".gz") stripped.
        """
        path = Path(path)
        for c in CompressionFormat.list_non_empty():
            if path.name.endswith(c.suffix):
                return path.parent / path.name[: -len(c.suffix)]
        return path

    @classmethod
    def split(cls, path: PathLike) -> BaseCompression:
        path = str(path)
        for c in CompressionFormat.list_non_empty():
            if path.endswith(c.suffix):
                return BaseCompression(Path(path[: -len(c.suffix)]), c)
        return BaseCompression(Path(path), CompressionFormat.none)

    @classmethod
    def from_path(cls, path: PathLike) -> CompressionFormat:
        """
        Returns the compression scheme from a path suffix.
        """
        path = Path(path)
        if path.name.startswith(".") and path.name.count(".") == 1:
            suffix = path.name
        else:
            suffix = path.suffix
        return cls.from_suffix(suffix)

    @classmethod
    def from_suffix(cls, suffix: str) -> CompressionFormat:
        """
        Returns the recognized compression scheme from a suffix.
        """
        for c in CompressionFormat:
            if suffix == c.suffix:
                return c
        return CompressionFormat.none


PathLike = str | PurePath

try:
    import lz4.frame
except ImportError:  # pragma: no cover
    class lz4:
        frame = None


class SmartIo:
    @classmethod
    def verify_can_read_files(
        cls,
        *paths: Union[str, Path],
        missing_ok: bool = False,
        attempt: bool = False,
    ) -> None:
        """
        Checks that all files can be written to, to ensure atomicity before operations.

        Args:
            *paths: The files
            missing_ok: Don't raise an error if a path doesn't exist
            attempt: Actually try opening

        Returns:
            ReadPermissionsError: If a path is not a file (modulo existence) or doesn't have 'W' set
        """
        paths = [Path(p) for p in paths]
        for path in paths:
            if path.exists() and not path.is_file():
                raise ReadPermissionsError(f"Path {path} is not a file", key=str(path))
            if (not missing_ok or path.exists()) and not os.access(path, os.R_OK):
                raise ReadPermissionsError(f"Cannot read from {path}", key=str(path))
            if attempt:
                try:
                    with open(path, "r"):
                        pass
                except OSError:
                    raise WritePermissionsError(f"Failed to open {path} for read", key=str(path))

    @classmethod
    def verify_can_write_files(
        cls,
        *paths: Union[str, Path],
        missing_ok: bool = False,
        attempt: bool = False,
    ) -> None:
        """
        Checks that all files can be written to, to ensure atomicity before operations.

        Args:
            *paths: The files
            missing_ok: Don't raise an error if a path doesn't exist
            attempt: Actually try opening

        Returns:
            WritePermissionsError: If a path is not a file (modulo existence) or doesn't have 'W' set
        """
        paths = [Path(p) for p in paths]
        for path in paths:
            if path.exists() and not path.is_file():
                raise WritePermissionsError(f"Path {path} is not a file", key=str(path))
            if (not missing_ok or path.exists()) and not os.access(path, os.W_OK):
                raise WritePermissionsError(f"Cannot write to {path}", key=str(path))
            if attempt:
                try:
                    with open(path, "a"):  # or w
                        pass
                except OSError:
                    raise WritePermissionsError(f"Failed to open {path} for write", key=str(path))

    @classmethod
    def verify_can_write_dirs(cls, *paths: Union[str, Path], missing_ok: bool = False) -> None:
        """
        Checks that all directories can be written to, to ensure atomicity before operations.

        Args:
            *paths: The directories
            missing_ok: Don't raise an error if a path doesn't exist

        Returns:
            WritePermissionsError: If a path is not a directory (modulo existence) or doesn't have 'W' set
        """
        paths = [Path(p) for p in paths]
        for path in paths:
            if path.exists() and not path.is_dir():
                raise WritePermissionsError(f"Path {path} is not a dir", key=str(path))
            if missing_ok and not path.exists():
                continue
            if not os.access(path, os.W_OK):
                raise WritePermissionsError(f"{path} lacks write permission", key=str(path))
            if not os.access(path, os.X_OK):
                raise WritePermissionsError(f"{path} lacks access permission", key=str(path))

    @classmethod
    def write(
        cls, path_or_buff, content, *, mode: str = "w", atomic: bool = False, **kwargs
    ) -> Optional[str]:
        """
        Writes using Pandas's ``get_handle``.
        By default (unless ``compression=`` is set), infers the compression type from the filename suffix
        (e.g. ``.csv.gz``).
        """
        if path_or_buff is None:
            return content
        compression = cls.path_or_buff_compression(path_or_buff, kwargs)
        if compression is CompressionFormat.lz4:
            if "a" in mode:
                raise UnsupportedOperationError("Can't append to lz4 (yet)")
            # let's hope it's a path
            path = Path(path_or_buff)
            tmp = cls.tmp_path(path)
            with get_handle(tmp, mode, **kwargs) as f:
                f.handle.write(content)
            if atomic:
                tmp = cls.tmp_path(path)
                with lz4.frame.open(str(tmp), mode="wb") as fp:
                    fp.write()
                os.replace(tmp, path)
            else:
                with lz4.frame.open(str(path), mode="wb") as fp:
                    fp.write()
        else:
            kwargs = {**kwargs, "compression": compression.pandas_value}
            if atomic and isinstance(path_or_buff, PathLike):
                if "a" in mode:
                    raise UnsupportedOperationError("Can't append in atomic write")
                path = Path(path_or_buff)
                tmp = cls.tmp_path(path)
                with get_handle(tmp, mode, **kwargs) as f:
                    f.handle.write(content)
                    os.replace(tmp, path)
            else:
                with get_handle(path_or_buff, mode, **kwargs) as f:
                    f.handle.write(content)

    @classmethod
    def read(cls, path_or_buff, *, mode: str = "r", **kwargs) -> str:
        """
        Reads using Pandas's ``get_handle``.
        By default (unless ``compression=`` is set), infers the compression type from the filename suffix.
        (e.g. ``.csv.gz``).
        """
        compression = cls.path_or_buff_compression(path_or_buff, kwargs)
        if compression is CompressionFormat.lz4:
            # let's hope it's a path
            path = Path(path_or_buff)
            with lz4.frame.open(str(path)) as fp:
                path_or_buff = fp.read()
        else:
            kwargs = {**kwargs, "compression": compression.pandas_value}
        with get_handle(path_or_buff, mode, **kwargs) as f:
            return f.handle.read()

    @classmethod
    def path_or_buff_compression(cls, path_or_buff, kwargs) -> CompressionFormat:
        if "compression" in kwargs:
            return CompressionFormat.of(kwargs["compression"])
        elif isinstance(path_or_buff, (PurePath, str)):
            return CompressionFormat.from_path(path_or_buff)
        return CompressionFormat.none

    @classmethod
    def tmp_path(cls, path: PathLike, extra: str = "tmp") -> Path:
        now = datetime.now().isoformat(timespec="ns").replace(":", "").replace("-", "")
        path = Path(path)
        suffix = "".join(path.suffixes)
        return path.parent / (".__" + extra + "." + now + suffix)

    @classmethod
    def get_encoding(cls, encoding: str = "utf-8") -> str:
        """
        Returns a text encoding from a more flexible string.
        Ignores hyphens and lowercases the string.
        Permits these nonstandard shorthands:

          - ``"platform"``: use ``sys.getdefaultencoding()`` on the fly
          - ``"utf8(bom)"``: use ``"utf-8-sig"`` on Windows; ``"utf-8"`` otherwise
          - ``"utf16(bom)"``: use ``"utf-16-sig"`` on Windows; ``"utf-16"`` otherwise
          - ``"utf32(bom)"``: use ``"utf-32-sig"`` on Windows; ``"utf-32"`` otherwise
        """
        encoding = encoding.lower().replace("-", "")
        if encoding == "platform":
            encoding = sys.getdefaultencoding()
        if encoding == "utf8(bom)":
            encoding = "utf-8-sig" if os.name == "nt" else "utf-8"
        if encoding == "utf16(bom)":
            encoding = "utf-16-sig" if os.name == "nt" else "utf-16"
        if encoding == "utf32(bom)":
            encoding = "utf-32-sig" if os.name == "nt" else "utf-32"
        return encoding

    @classmethod
    def get_encoding_errors(cls, errors: Optional[str]) -> Optional[str]:
        """
        Returns the value passed as``errors=`` in ``open``.
        Raises:
            ValueError: If invalid
        """
        if errors is None:
            return "strict"
        if errors in (
            "strict",
            "ignore",
            "replace",
            "xmlcharrefreplace",
            "backslashreplace",
            "namereplace",
            "surrogateescape",
            "surrogatepass",
        ):
            return errors
        raise ValueError(f"Invalid value {errors} for errors")


__all__ = ["SmartIo"]
