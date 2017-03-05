from abc import ABCMeta, abstractmethod
from typing import Callable

from . import process_registry, props, context, pid


class Actor(metaclass=ABCMeta):
    @abstractmethod
    async def receive(self, context: context.AbstractContext) -> None:
        pass

    @staticmethod
    def from_func(receive) -> 'Props':
        return Actor.from_producer(receive)

    @staticmethod
    def spawn(properties: props.Props) -> 'PID':
        name = ProcessRegistry().next_id()
        return Actor.spawned_name(properties, name)

    @staticmethod
    def spawned_name(properties: props.Props, name: str) -> 'PID':
        return properties.spawn(name)

    @staticmethod
    def spawn_prefix(properties: props.Props, prefix: str) -> 'PID':
        name = "%(prefix)s%(next_id)s" % {
            "prefix": prefix,
            "next_id": ProcessRegistry().next_id()
        }
        return Actor.spawned_name(properties, name)
