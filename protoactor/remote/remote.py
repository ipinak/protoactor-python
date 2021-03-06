import asyncio
import logging
import threading
from typing import Dict, Any

from grpclib.client import Channel
from grpclib.const import Status
from grpclib.exceptions import GRPCError, StreamTerminatedError
from grpclib.server import Server

import protoactor.actor.message_envelope as proto
from protoactor.actor import actor_context, log
from protoactor.actor.actor import Actor
from protoactor.actor.actor_context import ProcessRegistry, GlobalRootContext, AbstractContext
from protoactor.actor.behavior import Behavior
from protoactor.actor.event_stream import GlobalEventStream
from protoactor.actor.exceptions import ProcessNameExistException
from protoactor.actor.messages import Stopped, Started, Restarting, SuspendMailbox, ResumeMailbox
from protoactor.actor.process import AbstractProcess, DeadLettersProcess
from protoactor.actor.props import Props
from protoactor.actor.protos_pb2 import Watch, Unwatch, Terminated, PID, Stop
from protoactor.actor.restart_statistics import RestartStatistics
from protoactor.actor.supervision import AbstractSupervisorStrategy, AbstractSupervisor, Supervision
from protoactor.actor.utils import Singleton
from protoactor.mailbox.dispatcher import Dispatchers
from protoactor.mailbox.mailbox import AbstractMailbox
from protoactor.mailbox.queue import UnboundedMailboxQueue
from protoactor.remote.exceptions import ActivatorException
from protoactor.remote.messages import RemoteDeliver, RemoteWatch, RemoteUnwatch, EndpointConnectedEvent, \
    EndpointTerminatedEvent, RemoteTerminate, Endpoint
from protoactor.remote.protos_remote_grpc import RemotingBase, RemotingStub
from protoactor.remote.protos_remote_pb2 import ConnectResponse, Unit, MessageHeader, MessageBatch, ConnectRequest, \
    ActorPidRequest, ActorPidResponse, MessageEnvelope
from protoactor.remote.response import ResponseStatusCode
from protoactor.remote.serialization import Serialization


class RemoteConfig():
    def __init__(self):
        self.endpoint_writer_batch_size = 1000
        self.channel_options = None
        self.call_options = None
        self.channel_credentials = None
        self.server_credentials = None
        self.advertised_hostname = None
        self.advertised_port = None


class Remote(metaclass=Singleton):
    def __init__(self):
        self._logger = log.create_logger(logging.INFO, context=Remote)
        self._server = None
        self._kinds = {}
        self._remote_config = None
        self._activator_pid = None
        self._endpoint_reader = None

    @property
    def remote_config(self) -> RemoteConfig:
        return self._remote_config

    def get_known_kinds(self) -> list:
        return list(self._kinds.keys())

    def register_known_kind(self, kind: str, props: Props) -> None:
        self._kinds[kind] = props

    def get_known_kind(self, kind: str) -> Props:
        props = self._kinds.get(kind)
        if props is None:
            raise ValueError("save must be True if recurse is True")
        return props

    def start(self, hostname: str, port: int, config: RemoteConfig = RemoteConfig()) -> None:
        self._remote_config = config
        ProcessRegistry().register_host_resolver(RemoteProcess)
        EndpointManager().start()
        self._endpoint_reader = EndpointReader()

        Dispatchers().default_dispatcher.schedule(self.__run, hostname=hostname, port=port)

        address = f'{hostname}:{port}'
        ProcessRegistry().address = address
        self.__spawn_activator()
        self._logger.debug(f'Starting Proto.Actor server on {address}')

    def shutdown(self, gracefull=True):
        try:
            if gracefull:
                EndpointManager().stop()
                self._endpoint_reader.suspend(True)
                self.__stop_activator()
                self._server.close()
            else:
                self._server.close()
            self._logger.debug(f'Proto.Actor server stopped on {ProcessRegistry().address}. Graceful: {gracefull}')
        except Exception as e:
            self._server.close()
            self._logger.exception(f'Proto.Actor server stopped on {ProcessRegistry().address}')

    def activator_for_address(self, address):
        return PID(address=address, id='activator')

    def spawn_async(self, address, kind, timeout):
        pass

    async def spawn_named_async(self, address, name, kind, timeout):
        activator = self.activator_for_address(address)
        return await GlobalRootContext.request_future(activator, ActorPidRequest(name=name, kind=kind),
                                                      timeout=timeout)

    async def send_message(self, pid, msg, serializer_id):
        message, sender, header = actor_context.MessageEnvelope.unwrap(msg)
        env = RemoteDeliver(header, message, pid, sender, serializer_id)
        await EndpointManager().remote_deliver(env)

    def __spawn_activator(self):
        props = Props().from_producer(Activator) \
            .with_guardian_supervisor_strategy(Supervision.always_restart_strategy)
        self._activator_pid = GlobalRootContext.spawn_named(props, 'activator')

    def __stop_activator(self):
        self._activator_pid.stop()

    async def __run(self, hostname: str, port: int):
        self._server = Server([self._endpoint_reader], loop=asyncio.get_event_loop())
        await self._server.start(host=hostname, port=port)
        await self._server.wait_closed()


class RemoteProcess(AbstractProcess):
    def __init__(self, pid: 'PID'):
        self._pid = pid

    async def send_user_message(self, pid: 'PID', message: object, sender: 'PID' = None):
        await self.send(message)

    async def send_system_message(self, pid: 'PID', message: object):
        await self.send(message)

    async def send(self, message: any):
        if isinstance(message, Watch):
            await EndpointManager().remote_watch(RemoteWatch(message.watcher, self._pid))
        elif isinstance(message, Unwatch):
            await EndpointManager().remote_unwatch(RemoteUnwatch(message.watcher, self._pid))
        else:
            await Remote().send_message(self._pid, message, -1)


class EndpointManager(metaclass=Singleton):
    def __init__(self):
        self._logger = log.create_logger(logging.DEBUG, prefix='EndpointManager')
        self._connections = {}
        self._endpoint_supervisor = None
        self._endpoint_term_evn_sub = None
        self._endpoint_conn_evn_sub = None

    def start(self) -> None:
        self._logger.debug('Started EndpointManager')

        props = Props().from_producer(EndpointSupervisor) \
            .with_guardian_supervisor_strategy(Supervision.always_restart_strategy)

        self._endpoint_supervisor = GlobalRootContext.spawn_named(props, 'EndpointSupervisor')
        self._endpoint_conn_evn_sub = GlobalEventStream.subscribe(self.__on_endpoint_connected,
                                                                  EndpointConnectedEvent)
        self._endpoint_term_evn_sub = GlobalEventStream.subscribe(self.__on_endpoint_terminated,
                                                                  EndpointTerminatedEvent)

    def stop(self) -> None:
        self._endpoint_conn_evn_sub.unsubscribe()
        self._endpoint_term_evn_sub.unsubscribe()
        self._connections.clear()

        self._endpoint_supervisor.stop()
        self._logger.debug('Stopped EndpointManager')

    async def remote_watch(self, msg: RemoteWatch) -> None:
        endpoint = await self.__ensure_connected(msg.watchee.address)
        await GlobalRootContext.send(endpoint.watcher, msg)

    async def remote_unwatch(self, msg: RemoteUnwatch) -> None:
        endpoint = await self.__ensure_connected(msg.watchee.address)
        await GlobalRootContext.send(endpoint.watcher, msg)

    async def remote_deliver(self, msg: RemoteDeliver) -> None:
        endpoint = await self.__ensure_connected(msg.target.address)
        await GlobalRootContext.send(endpoint.writer, msg)

    async def remote_terminate(self, msg: RemoteTerminate):
        endpoint = await self.__ensure_connected(msg.watchee.address)
        await GlobalRootContext.send(endpoint.watcher, msg)

    async def __on_endpoint_connected(self, msg: EndpointConnectedEvent) -> None:
        endpoint = await self.__ensure_connected(msg.address)
        await GlobalRootContext.send(endpoint.watcher, msg)

    async def __on_endpoint_terminated(self, msg: EndpointTerminatedEvent) -> None:
        endpoint = self._connections.get(msg.address)
        if endpoint is not None:
            await GlobalRootContext.send(endpoint.watcher, msg)
            await GlobalRootContext.send(endpoint.writer, msg)
            del self._connections[msg.address]

    async def __ensure_connected(self, address) -> Endpoint:
        endpoint = self._connections.get(address)
        if endpoint is None:
            endpoint = await GlobalRootContext.request_future(self._endpoint_supervisor, address)
            self._connections[address] = endpoint
        return endpoint


class EndpointReader(RemotingBase):
    def __init__(self):
        self._suspended = False

    async def Connect(self, stream):
        if self._suspended:
            raise GRPCError(Status.CANCELLED, "Suspended")
        await stream.send_message(ConnectResponse(default_serializer_id=Serialization().default_serializer_id))

    async def Receive(self, stream) -> None:
        targets = []
        async for batch in stream:
            if self._suspended:
                await stream.send_message(Unit())

            for i in range(len(batch.target_names)):
                targets.append(PID(address=ProcessRegistry().address, id=batch.target_names[i]))

            type_names = list(batch.type_names)
            for envelope in batch.envelopes:
                target = targets[envelope.target]
                type_name = type_names[envelope.type_id]
                message = Serialization().deserialize(type_name, envelope.message_data, envelope.serializer_id)

                if isinstance(message, Terminated):
                    await EndpointManager().remote_terminate(RemoteTerminate(target, message.who))
                elif isinstance(message, Watch):
                    await target.send_system_message(message)
                elif isinstance(message, Unwatch):
                    await target.send_system_message(message)
                elif isinstance(message, Stop):
                    await target.send_system_message(message)
                else:
                    header = None
                    if envelope.message_header is not None:
                        header = proto.MessageHeader(envelope.message_header.header_data)
                    local_envelope = proto.MessageEnvelope(message, envelope.sender, header)
                    await GlobalRootContext.send(target, local_envelope)

        await stream.send_message(Unit())

    def suspend(self, suspended) -> None:
        self._suspended = suspended


class EndpointWatcher(Actor):
    def __init__(self, address):
        self._address = address
        self._behavior = Behavior(self.connected)
        self._logger = log.create_logger(logging.INFO, context=EndpointWatcher)
        self._watched = {}

    async def receive(self, context: AbstractContext) -> None:
        await self._behavior.receive_async(context)

    async def connected(self, context: AbstractContext) -> None:
        message = context.message
        if isinstance(message, RemoteTerminate):
            await self.__process_remote_terminate_message_in_connected_state(message)
        elif isinstance(message, EndpointTerminatedEvent):
            await self.__process_endpoint_terminated_event_message_in_connected_state(context, message)
        elif isinstance(message, RemoteUnwatch):
            await self.__process_remote_unwatch_message_in_connected_state(message)
        elif isinstance(message, RemoteWatch):
            await self.__process_remote_watch_message_in_connected_state(message)
        elif isinstance(message, Stopped):
            self.__process_stopped_message_in_connected_state()

    async def terminated(self, context: AbstractContext) -> None:
        message = context.message
        if isinstance(message, RemoteWatch):
            await self.__process_remote_watch_message_in_terminated_state(message)
        elif isinstance(message, EndpointConnectedEvent):
            self.__process_endpoint_connected_event_message_in_terminated_state()

    async def __process_remote_terminate_message_in_connected_state(self, msg):
        if msg.watcher.id in self._watched:
            pid_set = self._watched[msg.watcher.id]
            pid_set.remove(msg.watchee)
            if len(pid_set) == 0:
                del self._watched[msg.watcher.id]

        await msg.watcher.send_system_message(Terminated(who=msg.watchee))

    async def __process_endpoint_terminated_event_message_in_connected_state(self, context, msg):
        self._logger.debug(f'Handle terminated address {self._address}')
        for watched_id, pid_set in self._watched.items():
            watcher_pid = PID(address=ProcessRegistry().address, id=watched_id)
            watcher_ref = ProcessRegistry().get(watcher_pid)
            if watcher_ref != DeadLettersProcess():
                for pid in pid_set:
                    await watcher_pid.send_system_message(Terminated(who=pid, address_terminated=True))

        self._watched.clear()
        self._behavior.become(self.terminated)

        await context.my_self.stop()

    async def __process_remote_unwatch_message_in_connected_state(self, msg):
        if msg.watcher.id in self._watched:
            pid_set = self._watched[msg.watcher.id]
            pid_set.remove(msg.watchee)
            if len(pid_set) == 0:
                del self._watched[msg.watcher.id]

        await Remote().send_message(msg.watchee, Unwatch(watcher=msg.watcher), -1)

    async def __process_remote_watch_message_in_connected_state(self, msg):
        if msg.watcher.id in self._watched:
            self._watched[msg.watcher.id].append(msg.watchee)
        else:
            self._watched[msg.watcher.id] = [msg.watchee]

        await Remote().send_message(msg.watchee, Watch(watcher=msg.watcher), -1)

    def __process_stopped_message_in_connected_state(self):
        self._logger.debug(f'Stopped EndpointWatcher at {self._address}')

    async def __process_remote_watch_message_in_terminated_state(self, msg):
        await msg.watcher.send_system_message(Terminated(address_terminated=True, who=msg.watchee))

    def __process_endpoint_connected_event_message_in_terminated_state(self):
        self._logger.debug(f'Handle restart address {self._address}')
        self._behavior.become(self.connected)


class EndpointWriter(Actor):
    def __init__(self, address: str, channel_options: Dict[str, str], call_options,
                 channel_credentials):
        self._serializer_id = None
        self._logger = log.create_logger(logging.INFO, context=EndpointWriter)
        self._client = None
        self._channel = None
        self._address = address
        self._channel_options = channel_options
        self._call_options = call_options
        self._channel_credentials = channel_credentials
        self._stream = None
        self._stream_writer = None

    async def receive(self, context: AbstractContext) -> None:
        message = context.message
        if isinstance(message, Started):
            await self.__started_async()
        elif isinstance(message, Stopped):
            await self.__stopped_async()
            self._logger.debug(f'Stopped EndpointWriter at {self._address}')
        elif isinstance(message, Restarting):
            await self.__restarting_async()
        elif isinstance(message, EndpointTerminatedEvent):
            context.my_self.stop()
        elif isinstance(message, list) and all(isinstance(x, RemoteDeliver) for x in message):
            envelopes = []
            type_names = {}
            target_names = {}
            type_name_list = []
            target_name_list = []

            for rd in message:
                target_name = rd.target.id
                if rd.serializer_id == -1:
                    serializer_id = self._serializer_id
                else:
                    serializer_id = rd.serializer_id

                if target_name not in target_names:
                    target_id = target_names[target_name] = len(target_names)
                    target_name_list.append(target_name)
                else:
                    target_id = target_names[target_name]

                type_name = Serialization().get_type_name(rd.message, serializer_id)
                if type_name not in type_names:
                    type_id = type_names[type_name] = len(type_names)
                    type_name_list.append(type_name)
                else:
                    type_id = type_names[type_name]

                header = None
                if rd.header is not None and len(rd.header) > 0:
                    header = MessageHeader(header_data=rd.header)

                message_data = Serialization().serialize(rd.message, serializer_id)

                envelope = MessageEnvelope(type_id=type_id,
                                           message_data=message_data,
                                           target=target_id,
                                           sender=rd.sender,
                                           serializer_id=serializer_id,
                                           message_header=header)

                envelopes.append(envelope)

            batch = MessageBatch()
            batch.target_names.extend(target_name_list)
            batch.type_names.extend(type_name_list)
            batch.envelopes.extend(envelopes)

            await self.__send_envelopes_async(batch, type_name)

    async def __started_async(self):
        self._logger.debug(f'Connecting to address {self._address}')
        host, port = self._address.split(':')
        try:
            self._channel = Channel(host=host, port=port, loop=asyncio.get_event_loop())
            self._client = RemotingStub(self._channel)
            res = await self._client.Connect(ConnectRequest())
            self._serializer_id = res.default_serializer_id
        except Exception:
            self._logger.exception(f'GRPC Failed to connect to address {self._address}')
            await asyncio.sleep(2)
            raise Exception()

        await GlobalEventStream.publish(EndpointConnectedEvent(self._address))
        self._logger.debug(f'Connected to address {self._address}')

    async def __stopped_async(self):
        self._channel.close()

    async def __restarting_async(self):
        self._channel.close()

    async def __send_envelopes_async(self, batch, context):
        try:
            await self._client.Receive([batch])
        except ConnectionRefusedError:
            await GlobalEventStream.publish(EndpointTerminatedEvent(self._address))
            self._logger.exception(f'gRPC Failed to send to address {self._address}')


class EndpointWriterMailbox(AbstractMailbox):
    def __init__(self, batch_size):
        self._batch_size = batch_size
        self._system_messages = UnboundedMailboxQueue()
        self._user_messages = UnboundedMailboxQueue()
        self._suspended = False
        self._dispatcher = None
        self._invoker = None
        self._event = threading.Event()
        self._async_event = None
        self._loop = None
        self._logger = log.create_logger(logging.INFO, context=EndpointWriterMailbox)

    def post_user_message(self, msg):
        self._user_messages.push(msg)
        self.__schedule()

    def post_system_message(self, msg):
        self._system_messages.push(msg)
        self.__schedule()

    def register_handlers(self, invoker, dispatcher):
        self._invoker = invoker
        self._dispatcher = dispatcher
        self._dispatcher.schedule(self.__run)
        self._event.wait()

    def start(self):
        pass

    def __initialize(self):
        self._loop = asyncio.get_event_loop()
        self._async_event = asyncio.Event()
        self._event.set()

    async def __run(self):
        self.__initialize()
        while True:
            await self._async_event.wait()
            await self.__process_messages()
            self._async_event.clear()

            if self._system_messages.has_messages() or self._user_messages.has_messages():
                self.__schedule()

    async def __process_messages(self):
        message = None
        try:
            batch = []
            if sys := self._system_messages.pop():
                if isinstance(sys, SuspendMailbox):
                    self._suspended = True
                elif isinstance(sys, ResumeMailbox):
                    self._suspended = False
                else:
                    message = sys
                    await self._invoker.invoke_system_message(sys)

            if not self._suspended:
                batch.clear()

            while msg := self._user_messages.pop():
                batch.append(msg)
                if len(batch) >= self._batch_size:
                    break

            if len(batch) > 0:
                message = batch
                await self._invoker.invoke_user_message(batch)
        except Exception as e:
            self._logger.exception(f'Exception in Run')
            await self._invoker.escalate_failure(e, message)

    def __schedule(self):
        self._loop.call_soon_threadsafe(lambda: self._async_event.set())


class EndpointSupervisor(Actor, AbstractSupervisorStrategy):
    async def handle_failure(self, supervisor: AbstractSupervisor, child: PID, rs: RestartStatistics, cause: Exception,
                             message:Any):
        await supervisor.restart_children(cause, child)

    async def receive(self, context: AbstractContext) -> None:
        message = context.message
        if isinstance(message, str):
            address = str(message)
            watcher = self.__spawn_watcher(address, context)
            writer = self.__spawn_writer(address, context)
            await context.respond(Endpoint(watcher, writer))

    def __spawn_watcher(self, address: str, context: AbstractContext) -> PID:
        watcher_props = Props.from_producer(lambda: EndpointWatcher(address))
        watcher = context.spawn(watcher_props)
        return watcher

    def __spawn_writer(self, address: str, context: AbstractContext) -> PID:
        writer_props = Props.from_producer(lambda: EndpointWriter(
            address,
            Remote().remote_config.channel_options,
            Remote().remote_config.call_options,
            Remote().remote_config.channel_credentials))

        writer_props = writer_props.with_mailbox(lambda: EndpointWriterMailbox(Remote()
                                                                               .remote_config
                                                                               .endpoint_writer_batch_size))
        writer = context.spawn(writer_props)
        return writer


class Activator(Actor):
    async def receive(self, context: AbstractContext) -> None:
        message = context.message
        if isinstance(message, ActorPidRequest):
            props = Remote().get_known_kind(message.kind)
            name = message.name
            if name is None:
                name = ProcessRegistry().next_id()
            try:
                pid = GlobalRootContext.spawn_named(props, name)
                response = ActorPidResponse(pid=pid)
                await context.respond(response)
            except ProcessNameExistException as ex:
                response = ActorPidResponse(pid=ex.pid, status_code=int(ResponseStatusCode.ProcessNameAlreadyExist))
                await context.respond(response)
            except ActivatorException as ex:
                response = ActorPidResponse(status_code=ex.code)
                await context.respond(response)
                if not ex.do_not_throw:
                    raise Exception()
            except Exception:
                response = ActorPidResponse(status_code=int(ResponseStatusCode.Error))
                await context.respond(response)
                raise Exception()
