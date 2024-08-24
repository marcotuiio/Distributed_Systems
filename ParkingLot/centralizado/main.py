import threading
from manager import Manager
from station import StationMiddleware

def main():
    total_spots = 10
    manager = Manager(total_spots)
    manager.print_stations_to_file()

    # Bind das estações com zmq e manager - dormentes
    station_0 = StationMiddleware("Station0", "127.0.0.1", 5000, manager)
    station_1 = StationMiddleware("Station1", "127.0.0.1", 5001, manager)
    station_2 = StationMiddleware("Station2", "127.0.0.1", 5002, manager)
    station_3 = StationMiddleware("Station3", "127.0.0.1", 5003, manager)
    station_4 = StationMiddleware("Station4", "127.0.0.1", 5004, manager)
    station_5 = StationMiddleware("Station5", "127.0.0.1", 5005, manager)
    station_6 = StationMiddleware("Station6", "127.0.0.1", 5006, manager)
    station_7 = StationMiddleware("Station7", "127.0.0.1", 5007, manager)

    # Ativando as estações
    station_0.activate_station()
    station_1.activate_station()
    station_2.activate_station()
    station_3.activate_station()
    station_4.activate_station()
    station_5.activate_station()
    station_6.activate_station()
    station_7.activate_station()

    manager.print_stations()

    station_0.deactivate_station()
    station_4.deactivate_station()
    station_2.deactivate_station()


    manager.print_stations()

    # # Executando as estações em threads separadas
    # t0 = threading.Thread(target=station_0.run)
    # t1 = threading.Thread(target=station_1.run)
    # t0.start()
    # t1.start()

    # # Simulação básica de alocação de vagas
    # station_0.allocate_spot()
    # station_1.allocate_spot()

if __name__ == "__main__":
    main()
