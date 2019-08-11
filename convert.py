#! /bin/env	python3
stepfile = open("./2. kioku/kioku.sm")
# stepfile = open("./5. gat/gat.sm")
bpms = {}
for line in stepfile:
    line = line.strip(";\n ")
    if line.startswith("#BPMS:"):
        line = line[len("#BPMS:"):]
        bpms = dict([[float(y) for y in x.split('=')]
                     for x in line.split(',')])

print(bpms)
