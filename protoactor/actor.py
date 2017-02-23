from abc import ABCMeta, abstractmethod
from typing import Callable

from .process_registry import ProcessRegistry
from .props import Props
from .context import AbstractContext
from .pid import PID


class BaseActor(metaclass=ABCMeta):
    @abstractmethod
    async def receive(self, context: AbstractContext) -> None:
        pass


class Actor(BaseActor):

    @staticmethod
    def from_producer(cls, producer: Callable):
        return Props().with_producer(producer)

    @staticmethod
    def from_func(cls, receive) -> Props:
        return cls.from_producer(receive)

    @staticmethod
    def spawn(cls, props: Props) -> PID:
        name = ProcessRegistry().next_id()
        return Actor.spawned_name(cls, props, name)

    @staticmethod
    def spawned_name(cls, props: Props, name: str) -> PID:
        return props.spawn(name)

    @staticmethod
    def spawn_prefix(cls, props: Props, prefix: str) -> PID:
        name = "%(prefix)s%(next_id)s" % {
            "prefix": prefix,
            "next_id": ProcessRegistry().next_id()
        }
        return Actor.spawned_name(cls, props, name)
