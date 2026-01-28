import enum

class RobustEnum(str, enum.Enum):
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            value_upper = value.upper()
            for member in cls:
                if member.value.upper() == value_upper:
                    return member
        return None
