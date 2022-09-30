"""
Exceptions used by smartio.
"""
from pathlib import PurePath
from typing import Optional, Union


class UnsupportedOperationError(Exception):
    """
    Something could not be performed, in general.
    """


class FilenameSuffixError(UnsupportedOperationError):
    """
    A filename extension was not recognized.

    Attributes:
        key: The unrecognized suffix
        filename: The bad filename
    """

    def __init__(self, *args, key: Optional[str] = None, filename: Optional[str] = None):
        super().__init__(*args)
        self.key = key
        self.filename = filename


class FormatInsecureError(UnsupportedOperationError):
    """
    A requested format is less secure than required or requested.

    Attributes:
        key: The problematic format name
    """

    def __init__(self, *args, key: Optional[str] = None):
        super().__init__(*args)
        self.key = key


class ReadPermissionsError(OSError):
    """
    Couldn't read from a file.
    """

    def __init__(self, *args, key: Optional[str] = None):  # pragma: no cover
        super().__init__(*args)
        self.key = key


class WritePermissionsError(OSError):
    """
    Couldn't write to a file.
    """

    def __init__(self, *args, key: Optional[str] = None):  # pragma: no cover
        super().__init__(*args)
        self.key = key


class HashError(OSError):
    """
    Something went wrong with hash file writing or reading.
    """


class HashWriteError(HashError):
    """
    Something went wrong when writing a hash file.
    """


class HashExistsError(HashWriteError, ValueError):
    """
    A hash for the filename already exists in the directory hash list.

    Attributes:
        key: The filename (excluding parents)
        original: Hex hash found listed for the file
        new: Hex hash that was to be written
        filename: The filename of the listed file
    """

    def __init__(
        self,
        *args,
        key: Optional[str] = None,
        original: Optional[str] = None,
        new: Optional[str] = None,
    ):  # pragma: no cover
        super().__init__(*args)
        self.key = key
        self.original = original
        self.new = new


class HashContradictsExistingError(HashExistsError):
    """
    A hash for the filename already exists in the directory hash list, but they differ.

    Attributes:
        key: The filename (excluding parents)
        original: Hex hash found listed for the file
        new: Hex hash that was to be written
        filename: The filename of the listed file
    """


class HashAlgorithmMissingError(HashWriteError, LookupError):
    """
    The hash algorithm was not found in :mod:`hashlib`.

    Attributes:
        key: The missing hash algorithm
    """

    def __init__(self, *args, key: Optional[str] = None):  # pragma: no cover
        super().__init__(*args)
        self.key = key


class HashVerificationError(HashError):
    """
    Something went wrong when validating a hash.
    """


class HashDidNotValidateError(HashVerificationError):
    """
    The hashes did not validate (expected != actual).

    Attributes:
        actual: The actual hex-encoded hash
        expected: The expected hex-encoded hash
    """

    def __init__(
        self, *args, actual: Optional[str] = None, expected: Optional[str] = None
    ):  # pragma: no cover
        super().__init__(*args)
        self.actual = actual
        self.expected = expected


class HashFileInvalidError(HashVerificationError, ValueError):
    """
    The hash file could not be parsed.

    Attributes:
        key: The path to the hash file
    """

    def __init__(self, *args, key: Union[None, PurePath, str] = None):  # pragma: no cover
        super().__init__(*args)
        if isinstance(key, PurePath):
            key = str(key)
        self.key = key


class HashFileMissingError(HashVerificationError, FileNotFoundError):
    """
    The hash file does not exist.

    Attributes:
        key: The path or filename of the file corresponding to the expected hash file(s)
    """

    def __init__(self, *args, key: Optional[str] = None):  # pragma: no cover
        super().__init__(*args)
        self.key = key


class HashFilenameMissingError(HashVerificationError, LookupError):
    """
    The filename was not found listed in the hash file.

    Attributes:
        key: The filename
    """

    def __init__(self, *args, key: Optional[str] = None):  # pragma: no cover
        super().__init__(*args)
        self.key = key


class MultipleHashFilenamesError(HashVerificationError, ValueError):
    """
    There are multiple filenames listed in the hash file where only 1 was expected.

    Attributes:
        key: The filename with duplicate entries
    """

    def __init__(self, *args, key: Optional[str] = None):  # pragma: no cover
        super().__init__(*args)
        self.key = key


class HashFileExistsError(HashVerificationError, FileExistsError):
    """
    The hash file already exists and cannot be overwritten.

    Attributes:
        key: The existing hash file path or filename
    """

    def __init__(self, *args, key: Optional[str] = None):  # pragma: no cover
        super().__init__(*args)
        self.key = key


class HashEntryExistsError(HashVerificationError, FileExistsError):
    """
    The file is already listed in the hash dir, and it cannot be overwritten.

    Attributes:
        key: The existing hash dir path
    """

    def __init__(self, *args, key: Optional[str] = None):  # pragma: no cover
        super().__init__(*args)
        self.key = key


class PathNotRelativeError(ValueError):
    """
    The filename is not relative to the hash dir.

    Attributes:
        key: The filename
    """

    def __init__(self, *args, key: Optional[str] = None):  # pragma: no cover
        super().__init__(*args)
        self.key = key
