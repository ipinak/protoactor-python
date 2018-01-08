#!/usr/bin/env python
# -*- coding: utf-8 -*-
# TODO: add types
from exception import BaseException
from response_status import ResponseStatusCode
from ..actor import Actor
from ..process_registry import ProcessRegistry
from protos_pb2 import ActorPidRequest


class Activator(Actor):

    async def receive_async(self, context):
        msg = context.message
        if isinstance(msg, ActorPidRequest):
            # props = Remote.GetKnownKind(msg.kind)
            name = msg.name
            if name is None or name == "":
                name = ProcessRegistry.next_id()

            try:
                pid = None  # Actor.SpawnNamed(props, name)
                response = ActorPidResponse(pid=pid)
                context.Respond(response)
            except ProcessNameExistException as pne:
                response = ActorPidResponse(
                    pid=pne.pid,
                    status_code=ResponseStatusCode.ProcessNameAlreadyExist)
                context.Respond(response)
            except ActivatorException as ae:
                response = ActorPidResponse(
                    status_code=ae.code)
                context.Respond(response)
                if !ex.do_not_throw:
                    raise
            except:
                response = ActorPidResponse(
                    status_code=ResponseStatusCode.Error)
                context.Respond(response)
                raise
        return None


class ActivatorException(BaseException):

    def __init__(self, code, do_not_throw=False):
        self.__code = code
        self.__do_not_throw = do_not_throw

    @property
    def code(self):
        return self.__code

    @property
    def do_not_throw(self):
        return self.__do_not_throw


class ActivatorUnavailableException(ActivatorException):

    def __init__(self):
        ActivatorException.__init__(ResponseStatusCode.Unavailable, True)
