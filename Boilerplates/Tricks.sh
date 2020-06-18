#!/usr/bin/env bash

### Permite que funções sejam chamadas via piping (STDIN) ou via parâmetros
### Somente funciona no BASH 4!
### O tempo 0.01 depende da velocidade do clock e outras variáveis. 0.01 é um bom meio-termo.
function funcPipeAndEcho () {
    if read -t 0.01 STDIN; then
        input="${STDIN}"
    else
        input="$*"
    fi
    echo "$input"
}



### Direciona todo STDOUT e STDERR a um arquivo temporário
### No final (ou se acontecer um erro) cospe uma janela do zenity para debug
tmpfile=$(mktemp)
exec > $tmpfile
exec 2>&1
function debug_std () {
    # Filtra mensagens de erros do GTK
    cat $tmpfile | grep -v 'Gtk-' | grep -v '^$' | zenity --text-info --title="Log Output"
}
trap debug_std QUIT INT TERM EXIT



### Verifica se já existe uma instância rodando
## One liner
[[ "$(pgrep -fn $0)" -ne "$(pgrep -fo $0)" ]] && echo "At least 2 copies of $0 are running." && exit

## Com lockfiles (mkdir é atomico, é o melhor jeito)
LOCKDIR="/tmp/$(basename $0)"
if ! mkdir ${LOCKDIR} 2>/dev/null; then
    echo "$LOCKDIR exists so there's another instance running." >&2
    exit 1
fi
# Não esquecer de trapear as saídas por se o script terminar prematuramente
trap "rm -rf ${LOCKDIR}" QUIT INT TERM EXIT



### Permite usar sudo em scripts não interativos
## Método 1
sudoPassword="$(zenity --password --title=Authentication)"
echo $sudoPassword | sudo COMMAND

## Método 2
sudo_password=$( gksudo --print-pass --message="Provide permission to make system changes: Type your password or press Cancel." -- : 2>/dev/null )
# Verifica entradas nulas ou cancelamento
[[ ${?} != 0 || -z ${sudo_password} ]] && exit 4
if ! sudo -kSp '' [ 1 ] <<<${sudo_password} 2>/dev/null; then
    exit 4
fi
sudo -Sp '' COMMAND <<<${sudo_password}





### Roda o script em baixas prioridades
ionice -c 3 -p $$ 1>/dev/null
renice +12  -p $$ 1>/dev/null



### Captura a área de transferência dando prioridade à seleção primária
## Assim não é necessário - porém possível - apertar CTRL+C antes de rodar o script
_primary=$(xclip -o -selection primary)
_clipboard=$(xclip -o -selection clipboard)
if   [[ "$_primary" =~ ^https*://.*ebay\.com.+$ ]]; then
    _url="$_primary"
elif [[ "$_clipboard" =~ ^https*://.*ebay\.com.+$ ]]; then
    _url="$_clipboard"
else
    echo "URL is not an eBay link!"
fi



### Creates an array with all the matches returned by a `find` command (bash 4.4 only)
readarray -d '' _FILES < <(find -iname "SEARCHSTRING" -print0)
## This way it's way easier to parse results, particularly applying different
## operations according to how many results were returned:
if [[ ${#_FILES[@]} -eq 1 ]]; then
    # There's an unique result for the argument
    echo "${results[0]}"
elif [[ ${#_FILES[@]} -eq 0 ]]; then
    # There was no result
else
    # There were multiple results, can be used with the
    # the "select_option" menu below, for example:
    select_option "${_FILES[@]}"
fi



# Amazing bash-only menu selector
# Taken from http://tinyurl.com/y5vgfon7
# Further edits by @emi
function select_option() {
    ESC=$(printf "\033")
    cursor_blink_on() { printf "$ESC[?25h"; }
    cursor_blink_off() { printf "$ESC[?25l"; }
    cursor_to() { printf "$ESC[$1;${2:-1}H"; }
    print_option() { printf "   $1 "; }
    print_selected() { printf "  $ESC[7m $1 $ESC[27m"; }
    get_cursor_row() {
        IFS=';' read -sdR -p $'\E[6n' ROW COL
        echo ${ROW#*\[}
    }
    key_input() {
        read -s -n3 key 2>/dev/null >&2
        if [[ $key == $ESC\[A ]]; then echo up; fi
        if [[ $key == $ESC\[B ]]; then echo down; fi
        if [[ $key == "" ]]; then echo enter; fi
    }
    for opt; do printf "\n"; done
    local lastrow=$(get_cursor_row)
    local startrow=$(($lastrow - $#))
    trap "cursor_blink_on; stty echo; printf '\n'; return 255" 2    # returns 255 when exit or sigint
    cursor_blink_off
    local selected=0
    while true; do
        local idx=0
        for opt; do
            cursor_to $(($startrow + $idx))
            if [ $idx -eq $selected ]; then print_selected "$opt"; else print_option "$opt"; fi
            ((idx++))
        done
        case $(key_input) in
            enter)
                break ;;
            up)
                ((selected--))
                if [ $selected -lt 0 ]; then selected=$(($# - 1)); fi ;;
            down)
                ((selected++))
                if [ $selected -ge $# ]; then selected=0; fi ;;
        esac
    done
    cursor_to $lastrow
    printf "\n"
    cursor_blink_on
    return $selected
}


### Using gnome-keyring (or any other keyring supported by the lib) in bash scripts:
## Sets a password via the keyring:
python -c "import keyring; keyring.set_password('name', 'username', '$PASSWORD')"
## Fetches the password:
python -c "import keyring; print(keyring.get_password('name', 'username'))"