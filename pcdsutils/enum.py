from __future__ import annotations

import enum
from typing import Iterator, Set, Union

EnumId = Union[enum.Enum, int, str]


class CaseInsensitiveEnumMeta(enum.EnumMeta):
    def __getattr__(self, key: EnumId) -> enum.Enum:
        if hasattr(key, "lower"):
            for item in self:
                if item.name.lower() == key.lower():
                    return item
        return super().__getattr__(key)

    def __getitem__(self, key: EnumId) -> enum.Enum:
        if hasattr(key, "lower"):
            for item in self:
                if item.name.lower() == key.lower():
                    return item
        return super().__getitem__(key)


class HelpfulIntEnum(enum.IntEnum, metaclass=CaseInsensitiveEnumMeta):
    """
    IntEnum subclass with some utility extensions and case insensitivity.
    """

    @classmethod
    def from_any(cls, identifier: EnumId) -> HelpfulIntEnum:
        """
        Try all the ways to interpret identifier as the enum.

        This is intended to consolidate the try/except tree typically used
        to interpret external input as an enum.

        Parameters
        ----------
        identifier : EnumId
            Any str, int, or Enum value that corresponds with a valid value
            on this HelpfulIntEnum instance.

        Returns
        -------
        enum : HelpfulIntEnum
            The corresponding enum object associated with the identifier.

        Raises
        ------
        ValueError
            If the value is not a valid enum identifier.
        """
        try:
            return cls[identifier]
        except KeyError:
            return cls(identifier)

    @classmethod
    def include(
        cls,
        identifiers: Iterator[EnumId],
    ) -> Set[HelpfulIntEnum]:
        """
        Returns all enum values matching the identifiers given.
        This is a shortcut for calling cls.from_any many times and
        assembling a set of the results.

        Parameters
        ----------
        identifiers : Iterator[EnumId]
            Any iterable that contains strings, ints, and Enum values that
            correspond with valid values on this HelpfulIntEnum instance.

        Returns
        -------
        enums : Set[HelpfulIntEnum]
            A set whose elements are the enum objects associated with the
            input identifiers.
        """
        return {cls.from_any(ident) for ident in identifiers}

    @classmethod
    def exclude(
        cls,
        identifiers: Iterator[EnumId],
    ) -> Set[HelpfulIntEnum]:
        """
        Return all enum values other than the ones given.

        Parameters
        ----------
        identifiers : Iterator[EnumId]
            Any iterable that contains strings, ints, and Enum values that
            correspond with valid values on this HelpfulIntEnum instance.

        Returns
        -------
        enums : Set[HelpfulIntEnum]
            A set whose elements are the valid enum objects not associated
            with the input identifiers.
        """
        return set(cls.__members__.values()) - cls.include(identifiers)
