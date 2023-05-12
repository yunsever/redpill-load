
MLINK="${1}"
MCHECKSUM="${2}"

[ -z "${MLINK}" -o -z "${MCHECKSUM}" ] && exit 1

ROOT_PATH="$(realpath $(dirname "${0}"))"
BACK_PATH="${ROOT_PATH}_bak"

if [ -d "${BACK_PATH}" ]; then
  cp -rf ${BACK_PATH}/re* ${ROOT_PATH}/
else
  cp -rf ${ROOT_PATH} ${BACK_PATH}
fi

sed -i "s|MLINK=\"\"|MLINK=\"${MLINK}\"|g; s|MCHECKSUM=\"\"|MCHECKSUM=\"${MCHECKSUM}\"|g" ${ROOT_PATH}/releases/install.sh
INST_HASH="`sha256sum ${ROOT_PATH}/releases/install.sh | awk -F' ' '{print$1}'`"

sed -i "s|@@@PATH@@@|${ROOT_PATH}|g" ${ROOT_PATH}/rpext-index.json ${ROOT_PATH}/recipes/universal.json
sed -i "s|@@@HASH@@@|${INST_HASH}|g" ${ROOT_PATH}/recipes/universal.json

echo "file://localhost${ROOT_PATH}/rpext-index.json"