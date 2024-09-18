
#include "base.h"

#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>  // For time functions
#include <cstdlib>
#include <fstream>  // file stream
#include <iomanip>
#include <iostream>
#include <random>  // For random number generation
#include <string>
using namespace std;

#include <zmq.hpp>

string Communication::sendMessage(const std::string& server_ip, int server_port, const std::string& request_msg) {
    zmq::context_t context(1);
    zmq::socket_t socket(context, ZMQ_REQ);

    std::string address = "tcp://" + server_ip + ":" + std::to_string(server_port);
    socket.connect(address);

    std::string message_str = request_msg;

    std::cout << "Sending: " << message_str << std::endl;
    zmq::message_t message(message_str.size());
    memcpy(message.data(), message_str.c_str(), message_str.size());
    while (true) {
        if (socket.send(message, zmq::send_flags::none)) {
            break;
        } else {
            std::cerr << "Failed to send message" << std::endl;
            sleep(2);
        }

    }

    std::cout << "Message sent" << std::endl;

    zmq::message_t reply;
    zmq::recv_result_t result = socket.recv(reply, zmq::recv_flags::none);
    if (!result) {
        std::cerr << "Failed to receive reply" << std::endl;
        return "";
    }
    std::string response(static_cast<char*>(reply.data()), reply.size());
    std::cout << "Received: " << response << "\n" << std::endl;

    // Free the socket
    // socket.close();

    return response;
}

// string Communication::sendMessage(const std::string& server_ip, int server_port, const std::string& request_msg) {
//     int sock = 0;
//     struct sockaddr_in serv_addr;
//     char buffer[1024] = {0};

//     // Creating socket file descriptor
//     if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
//         std::cerr << "Socket creation error" << std::endl;
//         return " ";
//     }

//     serv_addr.sin_family = AF_INET;
//     serv_addr.sin_port = htons(server_port);

//     // Convert IPv4 and IPv6 addresses from text to binary form
//     if (inet_pton(AF_INET, server_ip.c_str(), &serv_addr.sin_addr) <= 0) {
//         std::cerr << "Invalid address/ Address not supported" << std::endl;
//         return " ";
//     }

//     // Connect to the server
//     if (connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
//         std::cerr << "Connection failed" << std::endl;
//         return " ";
//     }

//     // Send the request message
//     send(sock, request_msg.c_str(), request_msg.length(), 0);
//     std::cout << "Request sent: " << request_msg << std::endl;

//     // Receive the response message
//     int valread = read(sock, buffer, 1024);
//     std::cout << "Response received: " << std::string(buffer, valread) << std::endl;

//     // Close the socket
//     close(sock);

//     return (std::string(buffer, valread));
// }

string Communication::actFunction(string dest_IP, int dest_Port, string cmd) {
    string response;
    response = Communication::sendMessage(dest_IP, dest_Port, cmd);
    // sleep(5);
    return (response);
}
