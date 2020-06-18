#!/bin/bash
## Author: Emiliano Sauvisky
## Name: colorecho
## Description: List of colors for bash

# ONE LINE BASIC SETUP
# end='\E[0m'; bold='\E[1m'; fred='\E[31m'; fgre='\E[32m'; fyel='\E[33m'; fblu='\E[34m'; fvio='\E[35m'; fcya='\E[36m'; fwhi='\E[37m'

# end string
end='\E[0m'

# status strings
bold='\E[1m'
dark='\E[2m'
uline='\E[4m'
mline='\E[9m'

# normal color strings
fbla='\E[30m'
fred='\E[31m'
fgre='\E[32m'
fyel='\E[33m'
fblu='\E[34m'
fvio='\E[35m'
fcya='\E[36m'
fwhi='\E[37m'

# light color strings
flbla='\E[90m'
flred='\E[91m'
flgre='\E[92m'
flyel='\E[93m'
flblu='\E[94m'
flvio='\E[95m'
flcya='\E[96m'
flwhi='\E[97m'

# normal background strings
bbla='\E[40m'
bred='\E[41m'
bgre='\E[42m'
byel='\E[43m'
bblu='\E[44m'
bvio='\E[45m'
bcya='\E[46m'
bwhi='\E[47m'

# light background strings
blbla='\E[100m'
blred='\E[101m'
blgre='\E[102m'
blyel='\E[103m'
blblu='\E[104m'
blvio='\E[105m'
blcya='\E[106m'
blwhi='\E[107m'

echo -e "\t\tNORMAL\tBOLD\tDARK\tULINE\tMLINE"
for (( R=30; R<=37; R++ )); do
	echo -ne "FORE $R:\t"
	for C in 0 1 2 4 9; do
		echo -en '\E['$C'm\E['$R'mTEXT\E[0m\t'
	done
	echo
done
for (( R=90; R<=97; R++ )); do
	echo -ne "FORE $R:\t"
	for C in 0 1 2 4 9; do
		echo -en '\E['$C'm\E['$R'mTEXT\E[0m\t'
	done
	echo
done
for (( R=40; R<=47; R++ )); do
	echo -ne "BACK $R:\t"
	for C in 0 1 2 4 9; do
		echo -en '\E['$C'm\E['$R'mTEXT\E[0m\t'
	done
	echo
done
for (( R=100; R<=107; R++ )); do
	echo -ne "BACK $R:\t"
	for C in 0 1 2 4 9; do
		echo -en '\E['$C'm\E['$R'mTEXT\E[0m\t'
	done
	echo
done