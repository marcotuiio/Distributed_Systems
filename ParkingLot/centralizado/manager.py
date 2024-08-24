
# Classe que gerencia as estações e as vagas do estacionamento

class Manager:
    def __init__(self, total_spots):
        self.total_spots = total_spots
        self.stations = {
            "Station0": {"id": "Station0", "ipaddr": "127.0.0.1", "port": 5000, "status": 0, "nspots": 0},
            "Station1": {"id": "Station1", "ipaddr": "127.0.0.1", "port": 5001, "status": 0, "nspots": 0},
            "Station2": {"id": "Station2", "ipaddr": "127.0.0.1", "port": 5002, "status": 0, "nspots": 0},
            "Station3": {"id": "Station3", "ipaddr": "127.0.0.1", "port": 5003, "status": 0, "nspots": 0},
            "Station4": {"id": "Station4", "ipaddr": "127.0.0.1", "port": 5004, "status": 0, "nspots": 0},
            "Station5": {"id": "Station5", "ipaddr": "127.0.0.1", "port": 5005, "status": 0, "nspots": 0},
            "Station6": {"id": "Station6", "ipaddr": "127.0.0.1", "port": 5006, "status": 0, "nspots": 0},
            "Station7": {"id": "Station7", "ipaddr": "127.0.0.1", "port": 5007, "status": 0, "nspots": 0},
            "Station8": {"id": "Station8", "ipaddr": "127.0.0.1", "port": 5008, "status": 0, "nspots": 0},
            "Station9": {"id": "Station9", "ipaddr": "127.0.0.1", "port": 5009, "status": 0, "nspots": 0}
        }
        self.active_stations = []
        # Dicionario que tem todas a vagas. Chave é a vaga e o valor é a estação que controla essa vaga
        self.spots = {}


    def print_stations_to_file(self):
        with open("file.txt", "w") as f:
            for station_id, station in self.stations.items():
                f.write(f"{station['id']} {station['ipaddr']} {station['port']}\n")


    def print_stations(self):
        for station_id, station in self.stations.items():
            station_spots = [spot for spot, station in self.spots.items() if station == station_id]
            print(f"Estação {station_id}: {station_spots}")


    def get_station(self, station_id):
        return self.stations[station_id]


    # Ativa a estaçao mudando seu status para 1 e adicionando ela na 
    # lista de estações ativas alem de distribuir as vagas    
    def activate_station(self, station_id):
        print(f">> Ativando estação {station_id}.")
        self.stations[station_id]["status"] = 1
        self.active_stations.append(station_id)
        # self.station_spots[station_id] = 0
        return self.distribute_spots(station_id)


    # Desativa a estação mudando seu status para 0 e removendo ela da 
    # lista de estações ativas alem de redistribuir as vagas
    def deactivate_station(self, station_id):
        print(f">> Desativando estação {station_id}.")
        self.stations[station_id]["status"] = 0
        self.active_stations.remove(station_id)
        self.redistribute_spots(station_id)


    # Aplica a lógica de distribuição de vagas, chamada quando uma estação é ativada
    def distribute_spots(self, station_id):
        
        if len(self.active_stations) == 1:
            # self.station_spots[self.active_stations[0]] = self.total_spots
            self.stations[self.active_stations[0]]["nspots"] = self.total_spots
            self.spots = {i: station_id for i in range(self.total_spots)}
            list_spots = list(self.spots.keys())
            return list_spots
        
        # Senão, busca a estação com o maior número de vagas e divide as vagas pela metade
        elif len(self.active_stations) > 1:

            # Buscando o id da estação com o maior número de vagas (se houver empate, pega o primeiro)
            max_station_id = max(self.stations, key=lambda x: self.stations[x]["nspots"])
            max_spots = self.stations[max_station_id]["nspots"]
            # print(f">> Estação com o maior número de vagas: {max_station_id} = {max_spots}")

            # Dividindo as vagas pela metade (estação com mais vagas fica com a metade + o resto)
            half_spots, remainder = divmod(max_spots, 2)
            self.stations[max_station_id]["nspots"] = half_spots + remainder
            self.stations[station_id]["nspots"] = half_spots

            # print(f">> Vagas da nova estação {station_id}: {half_spots}")

            # Atualizando o dict das vagas. As primeiras half_spots vagas ficam com a nova estação
            updated = 0
            for spot, current_station_id in self.spots.items():
                if current_station_id == max_station_id:
                    self.spots[spot] = station_id
                    updated += 1
                    if updated == half_spots:
                        break
            
            list_spots_station = [spot for spot, station in self.spots.items() if station == station_id]
            return list_spots_station
        

    # Aplica a lógica de redistribuição de vagas, chamada quando uma estação é desativada
    def redistribute_spots(self, station_id):
        # Se está desativando a última estação, todas as vagas são liberadas
        if len(self.active_stations) == 0:
            self.spots = {}
        else:
            # Buscando o id da estação que vai herdar as vagas (se houver empate, pega o primeiro) 
            # Critério de eleição: estação com menos vagas herdará as vagas
            min_station_id = min(
                (station_id for station_id in self.stations if self.stations[station_id]["status"] == 1),
                key=lambda x: self.stations[x]["nspots"]
            )
            min_spots = self.stations[min_station_id]["nspots"]

            # Transferindo as vagas da estação desativada para a estação que herdará as vagas
            for spot, current_station_id in self.spots.items():
                if current_station_id == station_id:
                    self.spots[spot] = min_station_id
                    self.stations[min_station_id]["nspots"] += 1
                    self.stations[station_id]["nspots"] -= 1
                    if self.stations[station_id]["nspots"] == 0:
                        break
