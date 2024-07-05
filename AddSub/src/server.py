from concurrent import futures
import grpc
import addsub_pb2
import addsub_pb2_grpc

class AddSubServicer(addsub_pb2_grpc.AddSubServicer):
    
    def DoAdd(self, request, context):
        print('DoAdd Request Made:')
        print(request)

        result_reply = addsub_pb2.OpResults()
        result_reply.result = request.val1 + request.val2

        return result_reply

    def DoSub(self, request, context):
        print('DoSub Request Made:')
        print(request)

        result_reply = addsub_pb2.OpResults()
        result_reply.result = request.val1 - request.val2

        return result_reply
    
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    addsub_pb2_grpc.add_AddSubServicer_to_server(AddSubServicer(), server)
    server.add_insecure_port("localhost:50051")
    server.start()
    print("Server is up and waiting")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()