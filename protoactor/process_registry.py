#!/usr/bin/env python
# -*- coding: utf-8 -*-
from multiprocessing import RLock

from .pid import PID
from .process import AbstractProcess, DeadLettersProcess
from .utils import singleton


@singleton
class ProcessRegistry(object):

    def __init__(self, resolver = None, host: str = "nonhost"):
        self._hostResolvers = [resolver]
        # python dict structure is atomic for primitive actions. Need to be checked
        self.__local_actor_refs = {}
        self.__sequence_id = 0
        self.__address = host
        self.__lock = RLock()

    @property
    def address(self) -> str:
        return self.__address

    @address.setter
    def address(self, address: str):
        self.__address = address

    def get(self, pid: PID) -> AbstractProcess:
        if pid.address != self.__address:
            for resolver in self._hostResolvers:
                reff = resolver(pid)
                if not reff:
                    continue

                pid.process = reff
                return reff

        ref = self.__local_actor_refs.get(pid.id, None)
        if ref:
            return ref

        return DeadLettersProcess()

    def add(self, id: str, ref: AbstractProcess) -> PID:
        pid = PID(address=self.address, id=id, ref=ref)
        self.__local_actor_refs[id] = ref
        return pid

    def remove(self, pid):
        self.__local_actor_refs.pop(pid.id)

    def next_id(self) -> str:
        with self.__lock:
            self.__sequence_id += 1

        return str(self.__sequence_id)
