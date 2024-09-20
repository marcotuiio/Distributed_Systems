#include "car.h"

#include <chrono>  // For time functions
#include <fstream>
#include <iostream>
#include <random>  // For random number generation
#include <string>
// #include "base.h"
// using namespace std;
using namespace std;

Car::Car() {
    outResultFile.open("output.txt");
}

Car::~Car() {
    outResultFile.close();
}

void Car::carThread(string dest_IP, int dest_Port, string exit_IP, int exit_Port, string carID) {
    // send RV
    //  gerar ID para carro aleatorio IDcarro

    auto start = std::chrono::high_resolution_clock::now();
    std::cout << "Dest_IP: " << dest_IP << " Dest_port: " << dest_Port << std::endl;
    std::cout << "Exit station Port: " << exit_Port << "\n" << std::endl;
    Communication::sendMessage(dest_IP, dest_Port, "RV." + carID);
    // wait
    // Create a random number generator
    std::random_device rd;                         // Seed for the random number engine
    std::mt19937 gen(rd());                        // Mersenne Twister engine
    std::uniform_int_distribution<> dist(30, 60);  

    // Generate a random sleep duration
    int sleepTime = dist(gen);

    // Sleep for the generated duration
    std::this_thread::sleep_for(std::chrono::seconds(sleepTime));

    // select a station to leave
    Communication::sendMessage(exit_IP, exit_Port, "LV." + carID);
    auto end = std::chrono::high_resolution_clock::now();
    auto elapsedTime = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();

    writeToFile(std::to_string(elapsedTime));
    outResultFile << std::to_string(elapsedTime) << "\n";
}

void Car::writeToFile(string text) {
    outResultFile << text << "\n";
}

void Car::writeVDToFile(string text, int station) {
    // cout << "Escrevendo no arquvio de resultado" << text << "\n" << endl;

    outResultFile << "(VD "<< station << ") Active stations (ID, VagasTotais, VagasOcupadas, VagasVazias):" << "\n";
    outResultFile << text << "\n";
}