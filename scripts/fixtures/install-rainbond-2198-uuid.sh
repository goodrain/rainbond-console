init_uuid() {
    OS_TYPE=$(uname -s)
    case "$OS_TYPE" in
        Linux)
            MD5_CMD='md5sum'
            ;;
        Darwin)
            MD5_CMD='md5'
            ;;
        *)
            MD5_CMD='md5sum'
            ;;
    esac
    OS_INFO=$(uname -a)
    UUID=$(echo "$OS_INFO" | "$MD5_CMD" | cut -b 1-32)
}
