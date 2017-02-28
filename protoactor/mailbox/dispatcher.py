#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod, abstractproperty
from typing import Callable

import asyncio


class AbstractDispatcher(metaclass=ABCMeta):

	@abstractproperty
	def througput(self):
		raise NotImplementedError("This should be implemented")

	@abstractmethod
	def schedule(self, runner):
		raise NotImplementedError("This should be implemented")


class ThreadPoolDispatcher(AbstractDispatcher):

	def __init__(self):
		self.__throughput = 300

	@property
	def througput(self):
		return self.__throughput

	@throughput.setter
	def througput(self, value):
		self.__throughput = value

	def schedule(self, runner: Callable):
		loop = asyncio.get_event_loop()

		if asyncio.iscoroutine(runner):
			asyncio.ensure_future(runner, loop)
		raise TypeError("The `runner` you are passing is not a coroutine")

	def _schedule(self, runner: Callable):
		loop = asyncio.get_event_loop()

    	if callable(runner):
	        return loop.run_in_executor(executor, target)
		raise TypeError("The `runner` you are passing is not callable")