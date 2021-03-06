# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: tests/remote/messages/protos.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from protoactor.actor import protos_pb2 as protoactor_dot_actor_dot_protos__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='tests/remote/messages/protos.proto',
  package='remote_test_messages',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=_b('\n\"tests/remote/messages/protos.proto\x12\x14remote_test_messages\x1a\x1dprotoactor/actor/protos.proto\"\x07\n\x05Start\")\n\x0bStartRemote\x12\x1a\n\x06Sender\x18\x01 \x01(\x0b\x32\n.actor.PID\"\x17\n\x04Ping\x12\x0f\n\x07message\x18\x01 \x01(\t\"\x17\n\x04Pong\x12\x0f\n\x07message\x18\x01 \x01(\tb\x06proto3')
  ,
  dependencies=[protoactor_dot_actor_dot_protos__pb2.DESCRIPTOR,])




_START = _descriptor.Descriptor(
  name='Start',
  full_name='remote_test_messages.Start',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=91,
  serialized_end=98,
)


_STARTREMOTE = _descriptor.Descriptor(
  name='StartRemote',
  full_name='remote_test_messages.StartRemote',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='Sender', full_name='remote_test_messages.StartRemote.Sender', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=100,
  serialized_end=141,
)


_PING = _descriptor.Descriptor(
  name='Ping',
  full_name='remote_test_messages.Ping',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='message', full_name='remote_test_messages.Ping.message', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=143,
  serialized_end=166,
)


_PONG = _descriptor.Descriptor(
  name='Pong',
  full_name='remote_test_messages.Pong',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='message', full_name='remote_test_messages.Pong.message', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=168,
  serialized_end=191,
)

_STARTREMOTE.fields_by_name['Sender'].message_type = protoactor_dot_actor_dot_protos__pb2._PID
DESCRIPTOR.message_types_by_name['Start'] = _START
DESCRIPTOR.message_types_by_name['StartRemote'] = _STARTREMOTE
DESCRIPTOR.message_types_by_name['Ping'] = _PING
DESCRIPTOR.message_types_by_name['Pong'] = _PONG
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Start = _reflection.GeneratedProtocolMessageType('Start', (_message.Message,), dict(
  DESCRIPTOR = _START,
  __module__ = 'tests.remote.messages.protos_pb2'
  # @@protoc_insertion_point(class_scope:remote_test_messages.Start)
  ))
_sym_db.RegisterMessage(Start)

StartRemote = _reflection.GeneratedProtocolMessageType('StartRemote', (_message.Message,), dict(
  DESCRIPTOR = _STARTREMOTE,
  __module__ = 'tests.remote.messages.protos_pb2'
  # @@protoc_insertion_point(class_scope:remote_test_messages.StartRemote)
  ))
_sym_db.RegisterMessage(StartRemote)

Ping = _reflection.GeneratedProtocolMessageType('Ping', (_message.Message,), dict(
  DESCRIPTOR = _PING,
  __module__ = 'tests.remote.messages.protos_pb2'
  # @@protoc_insertion_point(class_scope:remote_test_messages.Ping)
  ))
_sym_db.RegisterMessage(Ping)

Pong = _reflection.GeneratedProtocolMessageType('Pong', (_message.Message,), dict(
  DESCRIPTOR = _PONG,
  __module__ = 'tests.remote.messages.protos_pb2'
  # @@protoc_insertion_point(class_scope:remote_test_messages.Pong)
  ))
_sym_db.RegisterMessage(Pong)


# @@protoc_insertion_point(module_scope)
