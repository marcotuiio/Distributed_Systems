from manager import Manager
from station import Station
import threading

manager = Manager(total_spots=10)
manager_thread = threading.Thread(target=manager.run)
manager_thread.start()

manager.print_stations_to_file()

station = Station(station_id="Station1", ipaddr="127.0.0.1", port=5001, manager_ip="127.0.0.1", manager_port=15555)
station_thread = threading.Thread(target=station.run)
station_thread.start()