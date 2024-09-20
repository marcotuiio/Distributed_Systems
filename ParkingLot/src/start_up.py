import os
import subprocess
import sys
import signal
from manager import *
from station import *

LOG_PATH = '/home/marcotuiio/Distributed_Systems/ParkingLot/logs'
STATION_PY_PATH = '/home/marcotuiio/Distributed_Systems/ParkingLot/src/station.py'
MANAGER_PY_PATH = '/home/marcotuiio/Distributed_Systems/ParkingLot/src/manager.py'
APP_PY_PATH = '/home/marcotuiio/Distributed_Systems/ParkingLot/src/app.py'

def start():

    if os.path.exists('/home/marcotuiio/Distributed_Systems/ParkingLot/logs/debug.txt'):
        # remover esse arquivo
        os.system('rm /home/marcotuiio/Distributed_Systems/ParkingLot/logs/debug.txt')
        
    # Start Manager
    manager_log = os.path.join(LOG_PATH, "manager_log.txt")
    with open(manager_log, "w") as log:
        print(f'* Running: {sys.executable} {MANAGER_PY_PATH}')
        manager_process = subprocess.Popen(
            [sys.executable, MANAGER_PY_PATH],
            stdout=log,
            stderr=log
        )
    time.sleep(2)


    # Getting data about stations
    path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(path, "..")
    stations_file = os.path.join(path, STATIONS_FILE)
    stations = []
    with open(stations_file, "r") as file:
        for line in file:
            station_id, ipaddr, port = line.strip().split(" ")
            stations.append((station_id, ipaddr, int(port)+1))


    # Start stations in hibernation
    processes = []
    for station_id, ipaddr, port in stations:
        log_file = os.path.join(LOG_PATH, f"log_{station_id}.txt")
        with open(log_file, "w") as log:
            print(f'* Running: {sys.executable} {APP_PY_PATH} {station_id} {ipaddr} {port}')
            process = subprocess.Popen(
                [sys.executable, APP_PY_PATH, station_id, ipaddr, str(port)],
                stdout=log,
                stderr=log
            )
            processes.append(process)
            time.sleep(0.1)
            print(f'* Running: {sys.executable} {STATION_PY_PATH} {station_id} {ipaddr} {port}')
            process = subprocess.Popen(
                [sys.executable, STATION_PY_PATH, station_id, ipaddr, str(port)],
                stdout=log,
                stderr=log
            )
            processes.append(process)



    # Wait for all processes to completea               
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()
            process.wait()
        manager_process.terminate()
        manager_process.wait()
        sys.exit(1) 

    # Ensure the manager process is also terminated
    manager_process.terminate()
    manager_process.wait()


if __name__ == "__main__":
    start()