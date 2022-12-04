import time
from subprocess import check_output as co
from threading import Thread as thread


MININET_WIFI_UTIL_EXE = '/home/wifi/mininet-wifi/util/m'

start_time = time.time()


class telemetry(object):
    thread_ = ''

    def start(self):
        self.thread_ = thread(target=self.run)
        self.thread_.daemon = True
        self.thread_._keep_alive = True
        self.thread_.start()
    
    def stop(self):
        self.thread_._keep_alive = False
        self.thread_._is_running = False

    def run(self):
        with open('sta1.txt', 'w') as fh:
            while True:
                rssi = get_rssi()
                if rssi != 0:
                    dt = time.time() - start_time
                    fh.write(f'{rssi},{dt}\n')
                    fh.flush()
                time.sleep(0.2)


def get_rssi():
    cmd = f"{MININET_WIFI_UTIL_EXE} sta1 iw dev sta1-wlan0 link | grep signal | tr -d signal: | awk '{{print $1 $3}}'"
    rssi = co(cmd, shell=True).decode().split("\n")
    rssi = 0 if not rssi[0] else rssi[0]
    return rssi