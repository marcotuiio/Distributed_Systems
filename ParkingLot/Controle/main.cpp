//#include "base.h"
#include "centralcontrol.h"
//#include "car.h"


int main() {


    CentralControl MainControl;
    MainControl.readfile("/home/marcotuiio/Distributed_Systems/ParkingLot/stations.txt");
    MainControl.printParkingTickets();
    MainControl.readCommandFromFile("commands.txt");

    return 0;
}
