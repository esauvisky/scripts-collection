#!/usr/bin/env bash

# Todas somente para bash 4 para permitir chamar a função via piping ou argumentos
# Do contrário simplificar o primeiro if read -t...

# Versão robusta printf
function rawURLEncode() {
    if read -t 0.01 STDIN; then
        local string=${STDIN}
    else
        local string="${1}"
    fi

    local strlen=${#string}
    local encoded=""
    local pos c o

    for (( pos=0 ; pos<strlen ; pos++ )); do
        c=${string:$pos:1}
        case "$c" in
            [-_.~a-zA-Z0-9] )
                o="${c}" ;;
            * )
                printf -v o '%%%02x' "'$c" ;;
        esac
        encoded+="${o}"
    done

    echo "${encoded}"
}
function rawURLDecode() {
    if read -t 0.01 STDIN; then
        printf -v decoded '%b' "${STDIN//%/\\x}"
    else
        printf -v decoded '%b' "${1//%/\\x}"
    fi

    echo "${decoded}"
}


# Versão alternativa via sed.
# Mais rápida e permite escolher que caracteres converter.
# Também é possível adicionar o regex a um arquivo.sed e usar '| sed -f arquivo.sed'
function sedURLEncode {
    if read -t 0.01 STDIN; then
        local string=${STDIN}
    else
        local string="${1}"
    fi

    echo "${string}" | sed '
    s:%:%25:g
    s: :%20:g
    s:<:%3C:g
    s:>:%3E:g
    s:#:%23:g
    s:{:%7B:g
    s:}:%7D:g
    s:|:%7C:g
    s:\\:%5C:g
    s:\^:%5E:g
    s:~:%7E:g
    s:\[:%5B:g
    s:\]:%5D:g
    s:`:%60:g
    s:;:%3B:g
    s:/:%2F:g
    s:?:%3F:g
    s^:^%3A^g
    s:@:%40:g
    s:=:%3D:g
    s:&:%26:g
    s:\$:%24:g
    s:\!:%21:g
    s:\*:%2A:g'
}