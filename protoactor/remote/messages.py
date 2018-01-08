#!/usr/bin/env python
# -*- coding: utf-8 -*-
# TODO: add types


class RemoteTerminate(object):

    def __init__(self, watcher, watchee):
        self.__watcher = watcher
        self.__watchee = watchee

    @property
    def watcher(self):
        return self.__watcher

    @property
    def watchee(self):
        return self.__watchee


class RemoteWatch(object):

    def __init__(self, watcher, watchee):
        self.__watcher = watcher
        self.__watchee = watchee

    @property
    def watcher(self):
        return self.__watcher

    @property
    def watchee(self):
        return self.__watchee


class RemoteUnwatch(object):

    def __init__(self, watcher, watchee):
        self.__watcher = watcher
        self.__watchee = watchee

    @property
    def watcher(self):
        return self.__watcher

    @property
    def watchee(self):
        return self.__watchee


class RemoteDeliver(object):

    def __init__(self, header, message, target, sender, serializer_id):
        self.__header = header
        self.__message = message
        self.__target = target
        self.__sender = sender
        self.__serializer_id = serializer_id

    @property
    def header(self):
        return self.__header

    @property
    def message(self):
        return self.__message

    @property
    def target(self):
        return self.__target

    @property
    def sender(self):
        return self.__sender

    @property
    def serializer_id(self):
        return self.__serializer_id
