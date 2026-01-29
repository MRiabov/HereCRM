import enum
from sqlalchemy import TypeDecorator, String, Text


class RobustEnum(str, enum.Enum):
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            value_upper = value.upper()
            for member in cls:
                if member.value.upper() == value_upper:
                    return member
        return None


class SafeSAEnum(TypeDecorator):
    """
    SQLAlchemy TypeDecorator that makes Enum handling case-insensitive on load.
    Uses String as the underlying implementation to avoid strict Enum validation
    in SQLAlchemy, allowing us to handle casing in Python.
    """

    impl = String
    cache_ok = True

    def __init__(self, enum_class, **kwargs):
        super().__init__(**kwargs)
        self.enum_class = enum_class

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                # RobustEnum._missing_ handles casing
                return self.enum_class(value)
            except ValueError:
                return value
        return value

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, enum.Enum):
                return value.value
            return str(value)
        return value
