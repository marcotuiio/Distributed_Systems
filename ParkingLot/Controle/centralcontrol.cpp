// #include <sys/socket.h>
#include <iomanip>
#include <iostream>
// #include <unistd.h>
// #include <arpa/inet.h>
#include <chrono>  // For time functions
#include <random>  // For random number generation
#include <thread>
// #include "base.h"
#include "centralcontrol.h"
using namespace std;

void CentralControl::readCommandFromFile(string cmdFile) {
    string command;
    int destination;
    ifstream inCommandFile(cmdFile, ios::in);
    if (!inCommandFile) {
        cerr << "Command File could not be opened" << endl;
        exit(EXIT_FAILURE);
    }
    // display each record in file
    while (inCommandFile >> command >> destination) {
        std::cout << "\nProcessing command: " << command << " station: " << destination << std::endl;
        this->handleCommand(command, destination, CentralControl::getIpAddress(destination), CentralControl::getPort(destination));
    }
    // Join the threads with the main thread
    for (auto& thread : newThread) {
        if (thread.joinable()) {
            thread.join();
        }
    }
}

void CentralControl::handleCommand(string cmd, int dest_index, string dest_IP, int dest_Port) {
    string response;
    if (cmd == "RV") {
        carNumber++;
        // std::cout << "Starting the car: " << carNumber << std::endl;
        string exit_name;
        string exit_ipaddr;
        int exit_port;
        selectExit(exit_name, exit_ipaddr, &exit_port);

        newThread.emplace_back(&Car::carThread, this, dest_IP, dest_Port, exit_ipaddr, exit_port, setCarID(6));
        sleep(5);
        // criar a thread carro o "LV" será enviado pelo carro

    } else if ((cmd == "AE") || (cmd == "FE") || (cmd == "VD") || (cmd == "ST")) {
        actNumber++;
        // thread.emplace_back(actFunction, dest_IP, dest_Port, cmd);

        response = Communication::actFunction(dest_IP, dest_Port, cmd);
        if (cmd == "VD") {
            // writeToFile(response);
        }
        if (cmd == "AE") {
            status[dest_index - 1] = '1';
        }
        if (cmd == "FE") {
            status[dest_index - 1] = '0';
        }
        std::cout << "Resuming the process...\n"
                  << std::endl;
        sleep(5);
    } else {
        std::cout << "Unknown command!" << std::endl;
    }
}

CentralControl::CentralControl() {
    //  ifstream inCommandFile("commands.txt", ios::in);

    actNumber = 0;
    carNumber = 0;
}

CentralControl::~CentralControl() {
}

void CentralControl::readfile(string filename) {
    ifstream inClientFile(filename, ios::in);

    // exit program if ifstream could not open file
    if (!inClientFile) {
        cerr << "File could not be opened" << endl;
        exit(EXIT_FAILURE);
    }
    int i = 0;
    while (inClientFile >> name[i] >> ipaddress[i] >> port[i]) {
        status[i] = '0';
        i++;
    }
    inClientFile.close();
}

void CentralControl::printParkingTickets() {
    for (int i = 0; i < 10; i++) {
        cout << left << setw(10) << name[i] << setw(13) << ipaddress[i]
             << setw(7) << port[i] << " Status: " << status[i] << endl;
    }
}

void CentralControl::selectExit(string& station, string& addr, int* p) {
    // Create a random number generator
    std::random_device rd;   // Seed for the random number engine
    std::mt19937 gen(rd());  // Mersenne Twister engine
    std::uniform_int_distribution<> dist(0, 8);
    // std::cout << "\nSelecting exit station...\n"
            //   << std::endl;
    // printParkingTickets();
    // std::cout << "\n"
    //           << std::endl;
    // Generate a index
    int ind = dist(gen);
    if (status[ind] == '1') {
        std::cout << "Initial selection success >>> " << name[ind] << "  " << status[ind] << std::endl;
        name[ind];
        addr = ipaddress[ind];
        *p = port[ind];

    } else {
        int attempts = 0;
        const int max_attempts = 10;  // Adjust as needed

        while (status[ind] == '0' && attempts < max_attempts) {
            ind = dist(gen);
            // std::cout << ">> Retrying selection >>> " << name[ind] << "  " << status[ind] << std::endl;
            attempts++;
        }

        if (status[ind] == '0') {
            std::cerr << "<< Error: No active stations found after " << max_attempts << " attempts." << std::endl;
            exit(-1);
        }
        std::cout << "Final selection success >>> " << name[ind] << "  " << status[ind] << std::endl;
        name[ind];
        addr = ipaddress[ind];
        *p = port[ind];
    }

}

string CentralControl::setCarID(int n) {
    string res = "";
    for (int i = 0; i < n; i++)
        res = res + alphabet[rand() % 36];

    return res;
}

string CentralControl::getName(int ind) {
    return name[ind - 1];
}

string CentralControl::getIpAddress(int ind) {
    return ipaddress[ind - 1];
}

int CentralControl::getPort(int ind) {
    return port[ind - 1];
}

char CentralControl::getStatus(int ind) {
    return status[ind - 1];
}
