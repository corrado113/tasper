# TASPER: Target Wake Time Scheduling for Time-Sensitive Wi-Fi Networks

This project provides a Python-based framework and solver for generating and solving Target Wake Time (TWT) scheduling problems. It is specifically designed for Time-Sensitive Networking (TSN), Industrial IoT (IIoT), and energy-efficient Wi-Fi networks.

## Project Overview

Target Wake Time (TWT) is a crucial mechanism in modern Wi-Fi standards (such as Wi-Fi 6/6E and Wi-Fi 7) that allows devices to negotiate specific times to wake up and transmit or receive data. Efficient TWT scheduling minimizes energy consumption while guaranteeing deterministic latency for time-sensitive applications. 

**TASPER** aims to efficiently solve the scheduling and allocation problem, ensuring deterministic latency and minimal energy consumption.

## Repository Structure

The repository contains the following files:

* `tasp_instance_generator.py`: A script to generate test instances for the scheduling problem. It allows for the creation of non-trivial problem instances.
* `test_instance.txt`: An example of a generated instance file produced by the generator, containing the parameters and constraints of the scheduling problem.
* `tasper.py`: The main solver script. It parses the instance data and runs the TASPER to allocate TWT Service Periods efficiently.
* `solver_utils.py`: A module containing helper functions, mathematical models, and utility routines used by the main solver to compute the schedule.

## Getting Started

### Prerequisites

Ensure you have Python 3 installed on your system. The code has been tested with Python 3.9.25. 

The only required package is *numpy*, which can be installed via pip:
```bash
pip install numpy 
```


### Usage

1. **Generate an instance** (or use the provided `test_instance.txt`):
```bash
python tasp_instance_generator.py
```

2. **Run the TWT scheduler**:
```bash
python tasper.py
```
*(Note: Check inside `tasper.py` for specific command-line arguments).*

## 📖 Citation

If you use this code, the mathematical models, or any part of this work in your research, please consider citing the following papers:

> **F. Busacca et al.**, "Target Wake Time Scheduling for Time-Sensitive and Energy-Efficient Wi-Fi Networks," in *IEEE Transactions on Mobile Computing*, vol. 25, no. 3, pp. 3469-3487, March 2026, doi: [10.1109/TMC.2025.3617324](https://doi.org/10.1109/TMC.2025.3617324).

> **C. Puligheddu et al.**, "Target Wake Time Scheduling for Time-Sensitive Networking in the Industrial IoT," *2024 IEEE 35th International Symposium on Personal, Indoor and Mobile Radio Communications (PIMRC)*, Valencia, Spain, 2024, pp. 1-7, doi: [10.1109/PIMRC59610.2024.10817339](https://doi.org/10.1109/PIMRC59610.2024.10817339).

### BibTeX:

```bibtex
@ARTICLE{busacca2026twt,
  author={Busacca, F. and others},
  journal={IEEE Transactions on Mobile Computing}, 
  title={Target Wake Time Scheduling for Time-Sensitive and Energy-Efficient Wi-Fi Networks}, 
  year={2026},
  volume={25},
  number={3},
  pages={3469-3487},
  doi={10.1109/TMC.2025.3617324}
}

@INPROCEEDINGS{puligheddu2024twt,
  author={Puligheddu, C. and others},
  booktitle={2024 IEEE 35th International Symposium on Personal, Indoor and Mobile Radio Communications (PIMRC)}, 
  title={Target Wake Time Scheduling for Time-Sensitive Networking in the Industrial IoT}, 
  year={2024},
  pages={1-7},
  doi={10.1109/PIMRC59610.2024.10817339}
}
```
