from abc import ABCMeta, abstractmethod
from asyncio import Task
from datetime import timedelta
from typing import Callable, List, Set

from .actor import Actor
from .invoker import AbstractInvoker
from .mailbox.messages import SuspendMailbox, ResumeMailbox
from .messages import Started, Stop, Terminated, Watch, Unwatch, Failure,\
    Restart, Stopping
from .pid import PID
from .props import Props
from .restart_statistics import RestartStatistics


class AbstractContext(metaclass=ABCMeta):

    @property
    def parent(self) -> PID:
        return self.__parent

    @property
    def my_self(self) -> PID:
        return self.__my_self

    @property
    def actor(self) -> Actor:
        return self.__actor

    @property
    @abstractmethod
    def sender(self) -> PID:
        raise NotImplementedError("Should Implement this method")

    @property
    @abstractmethod
    def message(self) -> object:
        raise NotImplementedError("Should Implement this method")

    @property
    @abstractmethod
    def receive_timeout(self) -> timedelta:
        raise NotImplementedError("Should Implement this method")

    @property
    @abstractmethod
    def children(self):
        raise NotImplementedError("Should Implement this method")

    @property
    @abstractmethod
    def stash(self):
        raise NotImplementedError("Should Implement this method")

    @abstractmethod
    def respond(self, message: object):
        raise NotImplementedError("Should Implement this method")

    @abstractmethod
    def spawn(self, props: Props) -> PID:
        raise NotImplementedError("Should Implement this method")

    @abstractmethod
    def spawn_prefix(self, props: Props, prefix: str) -> PID:
        raise NotImplementedError("Should Implement this method")

    @abstractmethod
    def spawn_named(self, props: Props, name: str) -> PID:
        raise NotImplementedError("Should Implement this method")

    @abstractmethod
    def set_behavior(self, behavior: Callable[[Actor, 'AbstractContext'], Task]):
        raise NotImplementedError("Should Implement this method")

    @abstractmethod
    def push_behavior(self, behavior: Callable[[Actor, 'AbstractContext'], Task]):
        raise NotImplementedError("Should Implement this method")

    @abstractmethod
    def pop_behavior(self) -> Callable[[Actor, 'AbstractContext'], Task]:
        raise NotImplementedError("Should Implement this method")

    @abstractmethod
    def watch(self, pid: PID):
        raise NotImplementedError("Should Implement this method")

    @abstractmethod
    def unwatch(self, pid: PID):
        raise NotImplementedError("Should Implement this method")

    @abstractmethod
    def set_receive_timeout(self, duration):
        raise NotImpementedError("Should implemnent this method")


class LocalContext(AbstractContext, AbstractInvoker):
    def __init__(self, producer: Callable[[], Actor], supervisor_strategy,
                 middleware, parent: PID) -> None:
        self.__producer = producer
        self.__supervisor_strategy = supervisor_strategy
        self.__middleware = middleware
        self.__parent = parent

        self.__stopping: bool = False
        self.__restarting: bool = False
        self.__receive: Callable[[Actor, AbstractContext], Task] = None
        self.__restart_statistics: RestartStatistics = None

        self.__behaviour: List[Callable[[Actor, AbstractContext], Task]] = []
        self.__incarnate_actor()

    @property
    def stash(self):
        raise NotImplementedError("Should Implement this method")

    @property
    def sender(self) -> PID:
        raise NotImplementedError("Should Implement this method")

    @property
    def message(self) -> object:
        raise NotImplementedError("Should Implement this method")

    @property
    def receive_timeout(self) -> timedelta:
        raise NotImplementedError("Should Implement this method")

    @property
    def children(self) -> Set[PID]:
        raise NotImplementedError("Should Implement this method")

    def watch(self, pid: PID):
        raise NotImplementedError("Should Implement this method")

    def pop_behavior(self) -> Callable[[Actor, AbstractContext], Task]:
        raise NotImplementedError("Should Implement this method")

    def unwatch(self, pid: PID):
        raise NotImplementedError("Should Implement this method")

    def spawn(self, props: Props) -> PID:
        raise NotImplementedError("Should Implement this method")

    def set_behavior(self, receive: Callable[[Actor, AbstractContext], Task]):
        self.__behaviour.clear()
        self.__behaviour.append(receive)
        self.__receive = receive

    def respond(self, message: object):
        raise NotImplementedError("Should Implement this method")

    def spawn_named(self, props: Props, name: str) -> PID:
        raise NotImplementedError("Should Implement this method")

    def push_behavior(self, behavior: Callable[[Actor, AbstractContext], Task]):
        raise NotImplementedError("Should Implement this method")

    def spawn_prefix(self, props: Props, prefix: str) -> PID:
        raise NotImplementedError("Should Implement this method")

    # def __actor_receive(self, context: AbstractContext):
    #     return self.actor.receive(context)

    def __incarnate_actor(self):
        self.__restarting = False
        self.__stopping = False
        self.actor = self.__producer()
        self.set_behavior(self.actor.receive)

    # AbstractInvoker Methods
    async def invoke_system_message(self, message: object) -> None:
        try:
            if isinstance(message, Started):
                await self.invoke_user_message(message)
            elif isinstance(message, Stop):
                await self.__handle_stop()
            elif isinstance(message, Terminated):
                await self.__handle_terminated()
            elif isinstance(message, Watch):
                await self.__handle_watch(message)
            elif isinstance(message, Unwatch):
                await self.__handle_unwatch(message)
            elif isinstance(message, Failure):
                await self.__handle_failure(message)
            elif isinstance(message, Restart):
                await self.handle_restart()
            elif isinstance(message, SuspendMailbox):
                pass
            elif isinstance(message, ResumeMailbox):
                pass
            else:
                pass
        except Exception as e:
            self.escalate_failure(e, message)

    async def invoke_user_message(self, message: object) -> None:
        raise NotImplementedError("Should Implement this method")

    def escalate_failure(self, reason: Exception) -> None:
        """Escalate a failure and store restart statistics. If a parent process
        does not exist then handle it as a root failure, since there is no
        parent responsible for that child process. If a parent process exists
        then suspend the mailbox and send the failure to myself."""

        if not self.__restart_statistics:
            self.__restart_statistics = RestartStatistics(1, None)
        failure = Failure(self.myself, reason, self.__restart_statistics)
        if not self.__parent:
            self.__handle_root_failure(failure)
        else:
            self.myself.send_system_message(SuspendMailbox())
            self.parent.send_system_message(failure)

    def escalate_failure_from_pid(self, who: PID, reason: Exception):
        """Escalate a failure by sending a system message to suspend the current
        process' mailbox and a failure message to its parent process, which will
        update the restart statistics as well."""

        self.myself.send_system_message(SuspendMailbox())
        self.parent.send_system_message(Failure(who, reason, self.__restart_statistics))

    def stop_children(self, *pids):
        """Stop execution of all children."""
        for i in pids:
            i.send_system_message(Stop())

    def resume_children(self, *pids):
        """Resume execution of all children."""
        for i in pids:
            i.send_system_message(ResumeMailbox())

    def restart_children(self, *pids):
        for i in pids:
            i.send_system_message(Restart())

    def set_receive_timeout(self, duration):
        if duration == self.receive_timeout:
            return
        if duration > 0:
            pass # stop receive timeout

        self.__receive_timeout = duration
        if self.receive_timeout > 0:
            pass



    async def __handle_stop(self):
        self.__restarting = False
        self.__stopping = True
        await self.invoke_user_message(Stopping())
        if self.children:
            for child in self.children:
                child.stop()

        await self.__try_restart_or_terminate()

    async def __handle_terminated(self):
        raise NotImplementedError("Should Implement this method")

    async def __handle_watch(self, message: object):
        raise NotImplementedError("Should Implement this method")

    async def __handle_unwatch(self, message: object):
        raise NotImplementedError("Should Implement this method")

    def __handle_root_failure(self, message: Failure):
        raise NotImplementedError("Should Implement this method")

    async def handle_restart(self):
        raise NotImplementedError("Should Implement this method")

    def __try_restart_or_terminate(self):
        raise NotImplementedError("Should Implement this method")
