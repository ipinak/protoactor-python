
input=$1

case $input in
    remote)
        cd protoactor/remote
        echo "Compiling remote messages"
        python -m grpc_tools.protoc -I. -I.. --python_out=. --grpc_python_out=. protoactor/remote/protos.proto
        ;;
    actor)
        cd protoactor
        echo "Compiling actor messages"
        protoc protos_pb2.proto -I. --python_out=.
        ;;
    *)
        echo "./build_proto.sh [remote|actor]"
        ;;
esac
