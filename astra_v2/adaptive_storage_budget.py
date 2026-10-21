"""Fail-closed storage admission model; no provider writes."""
from dataclasses import dataclass


@dataclass(frozen=True)
class StorageBudget:
    capacity: int
    used: int
    reserved: int = 0
    safety: int = 0

    def __post_init__(self):
        for value in (self.capacity, self.used, self.reserved, self.safety):
            if type(value) is not int or value < 0:
                raise ValueError('invalid_storage_budget')

    @property
    def available(self):
        return max(0, self.capacity - self.used - self.reserved - self.safety)

    def reserve(self, size):
        if type(size) is not int or size <= 0:
            raise ValueError('invalid_reservation_size')
        if size > self.available:
            raise RuntimeError('storage_budget_exhausted')
        return StorageBudget(self.capacity, self.used, self.reserved + size, self.safety)
