""" Generate an TASP with release date, deadlines and sequence-dependent setup times problem instance

The generation strategy is based on the following paper:
Ceyda Og˘uz et al., "Order acceptance and scheduling decisions in make-to-order systems,"
International Journal of Production Economics, Volume 125, Issue 1, 2010, Pages 200-211, ISSN 0925-5273,
https://doi.org/10.1016/j.ijpe.2010.02.002.

parameters for problem generation:
n order size, i.e., the number of TXs (excluding dummy TXs 0 and n+1)
tau tightness factor
R due date range factor
criterion one of {LEGACY, TWT}
n_sta number of stations (only for TWT)
n_slots number of slots to scale the instance to (optional)

for each TX:
r release date
p processing time
d due date
d_bar deadline
e/v revenue
w weight for tardiness
sta id of the TX belongs to
s sequence dependent setup times
""" 

import random
import numpy as np
from enum import Enum

interbeacon_time = 0.1024 #s
#CC3235S
Voltage = 3 #3 Volts Operating Voltage
idle_current = 0.05 #Ampere
tcp_tx_current = 0.232 #Ampere
on_current = 0.025 #Ampere
off_current = 0.036 #Ampere
on_time = 0.0235 #Seconds
off_time = 0.0055 #Seconds



idle_power = Voltage * idle_current
tcp_tx_power = Voltage * tcp_tx_current
E_onoff = Voltage * (on_current * on_time + off_current * off_time)

class STA_802_11_bgn(Enum): #Texas Instruments SimpleLink CC3235SF
    Voltage = 3  # 3 Volts Operating Voltage
    idle_current = 0.05  # Ampere
    tcp_tx_current = 0.232  # Ampere
    on_current = 0.025  # Ampere
    off_current = 0.036  # Ampere
    on_time = 0.0235  # Seconds
    off_time = 0.0055  # Seconds
    idle_power = Voltage * idle_current
    tcp_tx_power = Voltage * tcp_tx_current
    E_onoff = Voltage * (on_current * on_time + off_current * off_time)

class STA_802_11_bg(Enum): #RN-131G & RN-131C 802.11 b/g Wireless LAN Module
    Voltage = 3  # 3 Volts Operating Voltage
    idle_current = 0.04  # Ampere
    tcp_tx_current = 0.140 # Ampere
    on_current = 0.025  # Ampere
    off_current = 0.036  # Ampere
    on_time = 0.0235  # Seconds
    off_time = 0.0055  # Seconds
    idle_power = Voltage * idle_current
    tcp_tx_power = Voltage * tcp_tx_current
    E_onoff = Voltage * (on_current * on_time + off_current * off_time)

class STA_802_11_ac(Enum): #QCA9882 Dual-Band 2x2 MIMO 802.11ac/abgn - HT20 2.4GHz
    Voltage = 3  # 3 Volts Operating Voltage
    idle_current = 0.358 # Ampere
    tcp_tx_current = 0.573  # Ampere
    on_current = 0.025  # Ampere
    off_current = 0.036  # Ampere
    on_time = 0.0235  # Seconds
    off_time = 0.0055  # Seconds
    idle_power = Voltage * idle_current
    tcp_tx_power = Voltage * tcp_tx_current
    E_onoff = Voltage * (on_current * on_time + off_current * off_time)

class STA_802_11_ax(Enum): #QCA1062 Dual Band 2 × 2 MIMO 802.11ax + Bluetooth 5.1 - 11ax_HE40_MCS11
    Voltage = 3  # 3 Volts Operating Voltage
    idle_current = 0.294 # Ampere
    tcp_tx_current = 0.555  # Ampere
    on_current = 0.025  # Ampere
    off_current = 0.036  # Ampere
    on_time = 0.0235  # Seconds
    off_time = 0.0055  # Seconds
    idle_power = Voltage * idle_current
    tcp_tx_power = Voltage * tcp_tx_current
    E_onoff = Voltage * (on_current * on_time + off_current * off_time)



sta_models = [STA_802_11_bgn,STA_802_11_bg,STA_802_11_ac,STA_802_11_ax]


class Criterion(Enum):
    LEGACY = 1
    TWT = 2

def isvalid(instance):
    if ("p" not in instance.keys() or
            "d" not in instance.keys() or
            "r" not in instance.keys()):
        return False
    else:
        n = len(instance["p"]) - 2
        for j in range(n + 2):
            if instance["d"][j] < instance["r"][j]:
                return False
        return True


def generate_instance(n, tau, R, criterion=Criterion.TWT, n_sta=8, n_slots = None, max_value = 20, max_proc_time = None, sigma_scaling = 100000, w_fixed = None, seed = None, sta_types = None):

    if n <= 0:
        raise ValueError("n must be positive")
    if tau <= 0 or tau > 1:
        raise ValueError("tau must be between 0 and 1")
    if R <= 0 or R > 1:
        raise ValueError("R must be between 0 and 1")
    if(max_proc_time is None):
        max_proc_time = [20] * n
    elif(not isinstance(max_proc_time,list)):
        max_proc_time = [max_proc_time] * n

    if(not(seed is None)):
        random.seed(seed)

    if(sta_types is None):
        sta_types = [0] * n_sta
    
    assert criterion == Criterion.LEGACY or criterion == Criterion.TWT, \
    "Only the LEGACY and TWT criteria are implemented so far"

    instance = {}

    while not isvalid(instance):
        if criterion == Criterion.LEGACY or criterion == Criterion.TWT:
            p = [0] + [random.randint(1, max_proc_time[j]) for j in range(n)] + [0]
            r = [0] + [random.randint(0, int(tau * sum(p))) for j in range(n)]
            r = r + [max(r) + 1]
            s = [[0] + [random.randint(1, 10) for i in range(n)] + [0] for j in range(n + 1)] + [[0] * (n + 2)]

            v_min = 1
            v = [0] + [random.randint(v_min, max_value) for j in range(n)] + [0]
            d = [0]
            d_bar = [0]
            w = [0]

            for j in range(1,n+2):
                sigma = random.randint(int(sum(p) * (1 - tau - R / 2)), int(sum(p) * (1 - tau + R / 2))) / sigma_scaling
                if(j == n+1):
                    d_j = max(d_bar)+1
                    d_bar_j = d_j
                    r[j] = d_j
                else:
                    d_j = r[j] +  max(sigma, p[j])

                    d_bar_j = int(np.ceil(d_j + R * p[j]))
                if d_bar_j - d_j == 0:
                    pass
                else:
                    if(w_fixed>=0):
                        w_j = w_fixed
                    else:
                        w_j = round(v[j] / (d_bar_j - d_j),1)

                d.append(d_j)
                d_bar.append(d_bar_j)
                w.append(w_j)


        if(n_slots):
            slot_max = d_bar[n+1]
            #print("Slot Max", slot_max)
            r = [round(el * n_slots/slot_max) for el in r]
            p = [round(el * n_slots / slot_max) for el in p]
            p[1:-1] = [max(el,1) for el in p[1:-1]]
            d = [round(el * n_slots / slot_max) for el in d]
            d_bar = [round(el * n_slots / slot_max) for el in d_bar]

        if criterion == Criterion.LEGACY:
            instance = {"r": r,
                    "p": p,
                    "d": d,
                    "d_bar": d_bar,
                    "v": v,
                    "w": w,
                    "s": s}
        elif criterion == Criterion.TWT:

            sta = [0] + [random.randint(1, n_sta) for j in range(n)] + [0]

            tcp_tx_power_list = list()
            idle_power_list = list()
            E_onoff_list = list()

            for j in sta[1:-1]:
                sta_type = sta_types[j - 1]
                tcp_tx_power_list.append(sta_models[sta_type].tcp_tx_power.value)
                idle_power_list.append(sta_models[sta_type].idle_power.value)
                E_onoff_list.append((sta_models[sta_type].E_onoff.value) / (interbeacon_time / n_slots))

            s = [[0]+ tcp_tx_power_list + [0],[0] + idle_power_list + [0],[0]+[E_onoff / (interbeacon_time / n_slots) ] * (len(s)-2)+[0]]
            instance = {"r": r,
                    "p": p,
                    "d": d,
                    "d_bar": d_bar,
                    "v": v,
                    "w": w,
                    "sta": sta,
                    "s": s}
        #print(instance)
    return instance


def save_instance(filepath, instance):
    r = instance["r"]
    p = instance["p"]
    d = instance["d"]
    d_bar = instance["d_bar"]
    v = instance["v"]
    w = instance["w"]
    s = instance["s"]



    with open(filepath, 'w') as f_out:
        for el in (r,p,d,d_bar,v,w):
            str_el = ["{},".format(i) for i in el[:-1]] + [str(el[-1])+"\n"]
            f_out.writelines(str_el)
        if "sta" in instance:
            # additional line for stations related to jobs
            el = instance["sta"]
            str_el = ["{},".format(i) for i in el[:-1]] + [str(el[-1])+"\n"]
            f_out.writelines(str_el)
        for el in s:
            str_el = ["{},".format(i) for i in el[:-1]] + [str(el[-1])+"\n"]
            f_out.writelines(str_el)

def load_instance(filepath):
    with open(filepath) as f_in:
        input = [[float(i) for i in l.split(',')] for l in f_in.readlines()]
        # find out if it's an instance of TWT
        n = len(input[0]) -2
        print(n)
        print(len(input))
        # original instance without stations
        if len(input) == n + 2 + 6:
            r = input[0][:]
            p = input[1][:]
            d = input[2][:]
            d_bar = input[3][:]
            v = input[4][:]
            w = input[5][:]
            s = input[6:][:]

            instance = {"r": r,
                        "p": p,
                        "d": d,
                        "d_bar": d_bar,
                        "v": v,
                        "w": w,
                        "s": s}
        # instance with stations
        elif len(input) == n + 2 + 6 + 1 or len(input) == 6 + 1 + 3:
            r = input[0][:]
            p = input[1][:]
            d = input[2][:]
            d_bar = input[3][:]
            v = input[4][:]
            w = input[5][:]
            sta = input[6][:]
            s = input[7:][:]

            instance = {"r": r,
                        "p": p,
                        "d": d,
                        "d_bar": d_bar,
                        "v": v,
                        "w": w,
                        "sta": sta,
                        "s": s}
        else:
            instance = None
    return instance




if __name__ == "__main__":
    n_slots = 100
    max_proc_time = 20 #ms
    seed = 5
    max_time = [10,20,30,40,50,60,10,20,30,40,50,60,10,20,30,40]
    inst = generate_instance(16,0.2,0.3, Criterion.TWT, n_sta=16, n_slots=100, max_value=10, max_proc_time=max_time, sigma_scaling=4, w_fixed = 0.5, seed = seed)

    save_instance("test_instance.txt", inst)
    for key,val in inst.items():
        pass
        print(key,val)


    # This file also includes a TASP instance loader.
    # Uncomment the following lines to test the loader with the generated instance.
    #inst = load_instance(r"test_instance.txt")
    #print(inst)