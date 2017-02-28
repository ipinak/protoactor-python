#!/usr/bin/env python
# -*- coding: utf-8 -*-
from asyncio import Task
from typing import Callable, List

from .actor import Actor
from .context import LocalContext, AbstractContext
from .dispatcher import AbstractDispatcher, ProcessDispatcher
from .invoker import AbstractInvoker
from .mailbox.mailbox import AbstractMailbox, Mailbox
from .mailbox.queue import UnboundedMailboxQueue
from .messages import Started
from .pid import PID
from .process import LocalProcess
from .process_registry import ProcessRegistry
from .supervision import AbstractSupervisorStrategy


# Type hints redefinition
MailboxProducer = Callable[[AbstractInvoker, AbstractDispatcher],
                            AbstractMailbox]
EmptyMailboxProducer = Callable[[], AbstractMailbox]
Middleware = List[Callable[[AbstractContext], Task]]
MiddlewareChain = Callable[[AbstractContext], Task]
Producer = Callable[[], Actor]
Spawner = Callable[[str, 'Props', PID], PID]
# TODO: move thes somewhere common for every module


def default_spawner(name: str, props: 'Props', parent: PID) -> PID:
    context = LocalContext(props.producer, props.supervisor,
                           props.middleware_chain, parent)
    mailbox = props.produce_mailbox(context, props.dispatcher)
    process = LocalProcess(mailbox)

    pid = ProcessRegistry().add(name, process)
    context.my_self = pid
    mailbox.register_handlers(context, dispatcher)

    mailbox.start()
    mailbox.post_system_message(Started())

    return pid


def default_mailbox_producer(invoker: AbstractInvoker,
                             dispatcher: AbstractDispatcher):
    return Mailbox(UnboundedMailboxQueue(), UnboundedMailboxQueue(), invoker,
                   dispatcher)


class Props:

    def __init__(self, producer: Producer = None,
                 spawner: Spawner = default_spawner,
                 mailbox_producer: MailboxProducer = default_mailbox_producer,
                 dispatcher: AbstractDispatcher = ProcessDispatcher(),
                 supervisor_strategy: AbstractSupervisorStrategy = None,
                 middleware: Middleware = None,
                 middleware_chain: MiddlewareChain = None) -> None:
        self.__producer = producer
        self.__spawner = spawner
        self.__mailbox_producer = mailbox_producer
        self.__supervisor_strategy = supervisor_strategy
        self.__dispatcher = dispatcher
        self.__middleware = middleware
        self.__middleware_chain = middleware_chain

    @property
    def producer(self):
        return self.__producer

    @property
    def supervisor(self):
        return self.__supervisor_strategy

    @property
    def middleware_chain(self):
        return self.__middleware_chain

    @property
    def dispatcher(self):
        return self.__dispatcher

    def with_producer(self, producer: Producer) -> 'Props':
        return self.__copy_with({'_Props__producer': producer})

    def with_dispatcher(self, dispatcher: AbstractDispatcher) -> 'Props':
        return self.__copy_with({'_Props__dispatcher': dispatcher})

    def with_middleware(self, middleware: Middleware) -> 'Props':
        return self.__copy_with({'_Props__middleware': middleware})

    def with_mailbox_producer(self,
                              mailbox_producer: EmptyMailboxProducer) -> 'Props':
        return self.__copy_with({'_Props__mailbox_producer': mailbox_producer})

    def with_supervisor_strategy(self, supervisor_strategy) -> 'Props':
        return self.__copy_with({
            '_Props__supervisor_strategy': supervisor_strategy
        })

    def spawn(self, id: str, parent: PID = None) -> PID:
        return self.__spawner(id, self, parent)

    def produce_mailbox(self, invoker: AbstractInvoker,
                        dispatcher: AbstractDispatcher) -> AbstractMailbox:
        return self.__mailbox_producer(invoker, dispatcher)

    def __copy_with(self, new_params: dict) -> 'Props':
        params = self.__dict__
        params.update(new_params)

        return Props(**params)
