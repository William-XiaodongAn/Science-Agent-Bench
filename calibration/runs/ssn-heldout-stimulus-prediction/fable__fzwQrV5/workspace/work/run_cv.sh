#!/bin/bash
cd /workspace/work
nohup sh -c 'python3 cv.py pulse 0 struct 120 > cv_pulse_struct.txt 2>&1; python3 cv.py neuron 0 struct 120 > cv_neuron_struct.txt 2>&1' >/dev/null 2>&1 &
nohup sh -c 'python3 cv.py pulse 0.3 free 120 > cv_pulse_free0.3.txt 2>&1; python3 cv.py neuron 0.3 free 120 > cv_neuron_free0.3.txt 2>&1' >/dev/null 2>&1 &
nohup sh -c 'python3 cv.py pulse 0.03 free 120 > cv_pulse_free0.03.txt 2>&1; python3 cv.py neuron 0.03 free 120 > cv_neuron_free0.03.txt 2>&1' >/dev/null 2>&1 &
nohup sh -c 'python3 cv.py pulse 3 free 120 > cv_pulse_free3.txt 2>&1; python3 cv.py neuron 3 free 120 > cv_neuron_free3.txt 2>&1' >/dev/null 2>&1 &
