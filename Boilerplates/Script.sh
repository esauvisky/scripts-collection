#!/usr/bin/env bash
## Author: Emiliano Sauvisky (esauvisky@gmail.com)
## Name:
## Description:
## Version:

## Nível de logging (pode ser setado como variavel de ambiente)
LOG_LEVEL="${LOG_LEVEL:-7}"
## Dependências
__deps=( "sed" "grep" )

#############################################################################
####### Funções e configurações (normalmente não é necessário editar) #######
#############################################################################
## Parâmetros posicionais do bash
set -o errexit  # Exit on error. Append "|| true" if you expect an error.
set -o errtrace # Exit on error inside any functions or subshells.
set -o nounset  # Do not allow use of undefined vars. Use ${VAR:-} to use an undefined VAR
#set -o pipefail # Catch the error in case mysqldump fails (but gzip succeeds) in `mysqldump |gzip`
#set -o xtrace  # Turn on traces, useful while debugging.

## Variáveis mágicas
__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#__dir="$(cd "$(dirname $(realpath "${BASH_SOURCE[0]}"))" && pwd)" # com resolução de Symlinks
__base=$(basename "${BASH_SOURCE[0]}")

## Funções de Logging
function __log () {
    local log_level="${1}"; shift; local color_debug="\x1b[35m"; local color_info="\x1b[32m"; local color_notice="\x1b[34m"; local color_warning="\x1b[33m"; local color_error="\x1b[31m"; local color_critical="\x1b[1;31m"; local color_alert="\x1b[1;33;41m"; local color_emergency="\x1b[1;4;5;33;41m"; local colorvar="color_${log_level}"; local color="${!colorvar:-$color_error}"; local color_reset="\x1b[0m"; local log_line=""
    while IFS=$'\n' read -r log_line; do
        echo -e "${__base}: ${color}$(printf "[%9s]" ${log_level})${color_reset} $log_line" 1>&2
    done <<< "${@:-}"
}
function emergency () {                                $(__log emergency "${@}") || true; exit 1; }
function alert ()     { [ "${LOG_LEVEL:-0}" -ge 1 ] && $(__log alert "${@}") || true; exit 1; }
function critical ()  { [ "${LOG_LEVEL:-0}" -ge 2 ] && $(__log critical "${@}") || true; exit 1; }
function error ()     { [ "${LOG_LEVEL:-0}" -ge 3 ] && $(__log error "${@}") || true; }
function warning ()   { [ "${LOG_LEVEL:-0}" -ge 4 ] && $(__log warning "${@}") || true; }
function notice ()    { [ "${LOG_LEVEL:-0}" -ge 5 ] && $(__log notice "${@}") || true; }
function info ()      { [ "${LOG_LEVEL:-0}" -ge 6 ] && $(__log info "${@}") || true; }
function debug ()     { [ "${LOG_LEVEL:-0}" -ge 7 ] && $(__log debug "${@}") || true; }

## Verifica se dependências existem em $PATH
for dep in ${__deps[@]}; do
    hash $dep &>/dev/null || emergency "$dep was not found. Please install it and try again.";
done

#############################################################################
#######                           Argumentos                          #######
#############################################################################
function usage {
    echo -e "Usage: ${__base} [OPTIONS]"
    echo -e "\nOptions:"
    echo -e "  -h, --help               This page"
}
for (( n = 1; n <= $#; n++ )); do
    case "${!n}" in
        -h | --help )
            usage
            exit ;;
        # -f | --file )
        #     let n+=1; [[ ${n} -gt $# ]] && let n-=1 # if greater than number of arguments
        #     _file=${!n}
        #     exit ;;
        * )
            error "Invalid option ${!n}"
            usage
            exit ;;
    esac
done

#############################################################################
#######                  Runtime (Código Principal)                   #######
#############################################################################
debug "__dir: ${__dir}"
debug "__base: ${__base}"
