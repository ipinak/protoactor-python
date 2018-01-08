# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

import protos_pb2 as protos__pb2


class RemotingStub(object):
  # missing associated documentation comment in .proto file
  pass

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.Connect = channel.unary_unary(
        '/remote.Remoting/Connect',
        request_serializer=protos__pb2.ConnectRequest.SerializeToString,
        response_deserializer=protos__pb2.ConnectResponse.FromString,
        )
    self.Receive = channel.stream_stream(
        '/remote.Remoting/Receive',
        request_serializer=protos__pb2.MessageBatch.SerializeToString,
        response_deserializer=protos__pb2.Unit.FromString,
        )


class RemotingServicer(object):
  # missing associated documentation comment in .proto file
  pass

  def Connect(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def Receive(self, request_iterator, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_RemotingServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'Connect': grpc.unary_unary_rpc_method_handler(
          servicer.Connect,
          request_deserializer=protos__pb2.ConnectRequest.FromString,
          response_serializer=protos__pb2.ConnectResponse.SerializeToString,
      ),
      'Receive': grpc.stream_stream_rpc_method_handler(
          servicer.Receive,
          request_deserializer=protos__pb2.MessageBatch.FromString,
          response_serializer=protos__pb2.Unit.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'remote.Remoting', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
