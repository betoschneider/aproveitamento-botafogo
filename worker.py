import time
from extrair_dados import init_db, get_partidas, get_tecnicos

INTERVALO_MINUTOS = 1440  # 24 horas

while True:
    init_db()
    get_partidas()
    get_tecnicos()
    time.sleep(INTERVALO_MINUTOS * 60)