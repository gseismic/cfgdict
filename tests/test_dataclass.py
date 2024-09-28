"""Demo of dataclass vs non-dataclass performance."""
import timeit

times = 200

dataclass_time = timeit.timeit("""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float
    z: float

p = Point(1, 2, 3)
""", number=times)

nondataclass_time = timeit.timeit("""
class Point:
    __match_args__ = ('x', 'y', 'z')
    __slots__ = ('x', 'y', 'z')

    def __init__(self, x: float, y: float, z: float) -> None:
        object.__setattr__(self, 'x', x)
        object.__setattr__(self, 'y', y)
        object.__setattr__(self, 'z', z)

    def __repr__(self):
        cls = type(self).__name__
        return f'{cls}(x={self.x!r}, y={self.y!r}, z={self.z!r})'

    def __eq__(self, other):
        if not isinstance(other, Point):
            return NotImplemented
        return (self.x, self.y, self.z) == (other.x, other.y, other.z)

    def __hash__(self):
        return hash((self.x, self.y, self.z))

    def __setattr__(self, name, value):
        raise AttributeError(f"Can't set attribute {name!r}")

    def __delattr__(self, name):
        raise AttributeError(f"Can't delete attribute {name!r}")

    def __getstate__(self):
        return (self.x, self.y, self.z)

    def __setstate__(self, state):
        fields = ('x', 'y', 'z')
        for field, value in zip(fields, state):
            object.__setattr__(self, field, value)

p = Point(1, 2, 3)
""", number=times)

# https://www.pythonmorsels.com/p/2cv33/
# importing 200 regular classes: 1ms
# importing 200 dataclasses: 224ms
print(f"importing 200 regular classes: {nondataclass_time*1000:.0f}ms")
print(f"importing 200 dataclasses: {dataclass_time*1000:.0f}ms")
