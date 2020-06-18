#!/bin/bash
AUTH='esauvisky@gmail.com'
DESC=''
VERS='0.1'

# [XXX] Constants, variables and options
_clear='\E[0m'
_bold='\E[1m'
_red='\E[31m'
_deps=( "" )
_basename=$(basename "${BASH_SOURCE[0]}")
_dirname=$(dirname "${BASH_SOURCE[0]}")
printDebug=false
benchmark=false
debugLine=0
set -o errexit
set -o nounset

# [XXX] Debugging functions
function debug {
    if $printDebug; then
        timeNow=$(echo "($(date +%s)*1000000000) + $(date +%N); scale=0" | bc)
        timeDeltaBuffer=$(echo "($timeNow-$timeBefore)/1000000; scale=0" | bc)
        timeBefore=$timeNow
        if $benchmark; then
            echo -n $timeDeltaBuffer','
        else
            timeDelta=$(printf "%4d" $timeDeltaBuffer)
            let debugLine+=1
            echo -en "${_bold}$debugLine: (+${timeDelta}ms)${_clear} $@\n" ;fi;fi;}
function error {
    echo >&2 -en "${_bold}${_red}ERROR: ${_clear}$@\n"
    exit 1 ;}
function usage {
    echo -e "Usage: ${_bold}$_basename [OPTION] ${_clear}"
    [[ ! -z ${DESC:-} ]] && echo -e "$DESC. Version $VERS"
    echo -e "\nOptions:"
    echo -e "  -d, --debug              Verbose mode"
    echo -e "      --benchmark          Verbose timing mode, for creating benchmark"
    echo -e "                           files (implies -d)."
    echo -e "      --parse FILE         Parses a benchmark file based on --benchmark."
    echo -e "\nAuthor: $AUTH" ;}

# [XXX] Check requirements
for dep in ${_deps[@]}; do
    hash $dep &>/dev/null || error "${_bold}$dep${_clear} was not found. Please install it and try again."; done

# Parse arguments
for (( n = 1; n <= $#; n++ )); do
    case "${!n}" in
        -h | --help )
            usage
            exit ;;
        -d | --debug )
            printDebug=true
            timeStart=$(echo "($(date +%s)*1000000000)+$(date +%N);scale=0" | bc)
            timeBefore=$timeStart ;;
        --benchmark )
            benchmark=true
            printDebug=true
            timeStart=$(echo "($(date +%s)*1000000000)+$(date +%N);scale=0" | bc)
            timeBefore=$timeStart ;;
        --parse )
            let n+=1; [[ -z ${!n:-} || ! -f ${!n} ]] && error "You must specify a valid file to benchmark"
            # TODO: ignore outliers (replace for zero or whatever)
            cat "${!n}" | awk -F ',' '{ for(i=1; i<=NF; i++) {    \
                                          if ($i>0) arr[i]+=$i}    \
                                      } END {
                                        for( i=1; i<=NF; i++) \
                                          if (i==NF) printf("%5s: %4dms\n", "Total", arr[i] / NR)
                                          else printf("%5d: %4dms\n", i, arr[i] / NR) }'
            exit ;;
        * )
            error "Invalid option '${!n}'\n$(usage)" ;;esac;done

# Main code
cd $_dirname
echo -e "${_bold}$_basename: $DESC${_clear}"



# [XXX] Debugging functions
if $printDebug; then
    timeEnd=$(echo "( $(date +%s) * 1000000000 ) + $(date +%N); scale=0" | bc)
    timeTotal=$( echo "($timeEnd - $timeStart)/1000000; scale=0" | bc)
    if $benchmark; then
        echo $timeTotal
    else
        echo -e "${_bold}Total script runtime: ${timeTotal}ms${_clear}" ;fi;fi

