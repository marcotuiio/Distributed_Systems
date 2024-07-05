import grpc
import addsub_pb2
import addsub_pb2_grpc

def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = addsub_pb2_grpc.AddSubStub(channel)
        while True:
            print("1. DoAdd")
            print("2. DoSub")
            print("Anything else to exit")
            rpc_call = input("Choose the operation: ")

            if rpc_call == "1":
                a = input("Value A: ")
                b = input("Value B: ")

                add_request = addsub_pb2.OpParam(val1 = int(a), val2 = int(b))
                results = stub.DoAdd(add_request)
                print("* DoAdd Response Received")
                print(f" {a} + {b} = {results.result}\n")

            elif rpc_call == "2":
                a = input("Value A: ")
                b = input("Value B: ")

                add_request = addsub_pb2.OpParam(val1 = int(a), val2 = int(b))
                results = stub.DoSub(add_request)
                print("* DoSub Response Received")
                print(f" {a} - {b} = {results.result}\n")
                
            else:
                exit()

if __name__ == "__main__":
    run()