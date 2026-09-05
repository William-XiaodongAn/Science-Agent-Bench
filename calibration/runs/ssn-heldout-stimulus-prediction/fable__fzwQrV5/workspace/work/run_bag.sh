#!/bin/bash
cd /workspace/work
for s in 0 1 2 3; do nohup python3 bag.py $s 0.1 > bag_$s.txt 2>&1 & done
