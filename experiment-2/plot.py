import matplotlib.pyplot as plt


def main():
    with open('sta1.txt', 'r') as fh:
        lines = fh.readlines()

        time_list = []
        rssi_list = []
        for data in lines:
            rssi, time = data.split(",")
            time_list.append(float(time))
            rssi_list.append(int(rssi))

        fig, ax = plt.subplots()
        ax.plot(time_list, rssi_list)
        plt.ylabel('RSSI (dbm)')
        plt.xlabel('time (s)')
        fig.savefig('sta1')
        plt.close()


if __name__ == '__main__':
    main()