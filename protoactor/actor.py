from abc import ABCMeta, abstractmethod
from typing import Callable

from .process import EventStream
from .process_registry import ProcessRegistry
from .props import Props
from .context import AbstractContext
from .pid import PID


class BaseActor(metaclass=ABCMeta):
    @abstractmethod
    async def receive(self, context: AbstractContext) -> None:
        pass


class EmptyActor(BaseActor):

    def __init__(self, receiveTask) -> None:
        self.__receive = receiveTask

    async def receive(self, context: AbstractContext) -> None:
        return self.__receive(context)


class Actor(BaseActor):

    def __init__(self):
        # TODO: investigate if Task.CompletedTask exists in py3
        self.event_stream = EventStream()

    @staticmethod
    def from_producer(producer: Callable):
        return Props().with_producer(producer)

    @staticmethod
    def from_func(receive) -> Props:
        return Actor.from_producer(receive)

    @staticmethod
    def spawn(props: Props) -> PID:
        name = ProcessRegistry().next_id()
        return Actor.spawned_name(props, name)

    @staticmethod
    def spawned_name(props: Props, name: str) -> PID:
        return props.spawn(name)

    @staticmethod
    def spawn_prefix(props: Props, prefix: str) -> PID:
        name = "%(prefix)s%(next_id)s" % {
            "prefix": prefix,
            "next_id": ProcessRegistry().next_id()
        }
        return Actor.spawned_name(props, name)


class ProcessNameExistException(Exception):

    def __init__(self, name: str) -> None:
        self.__name = name