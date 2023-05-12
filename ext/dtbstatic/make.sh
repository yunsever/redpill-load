
DTBF_PATH=${1}
[ -z "${DTBF_PATH}" ] && exit 1
[ ! -f "${DTBF_PATH}" ] && exit 2

ROOT_PATH="$(realpath $(dirname "${0}"))"
BACK_PATH="${ROOT_PATH}_bak"

if [ -d "${BACK_PATH}" ]; then
  cp -rf ${BACK_PATH}/re* ${ROOT_PATH}/
else
  cp -rf ${ROOT_PATH} ${BACK_PATH}
fi

cp -f ${DTBF_PATH} ${ROOT_PATH}/releases/user_model.dtb
DTBF_HASH="`sha256sum ${ROOT_PATH}/releases/user_model.dtb | awk -F' ' '{print$1}'`"

sed -i "s|@@@PATH@@@|${ROOT_PATH}|g" ${ROOT_PATH}/rpext-index.json ${ROOT_PATH}/recipes/universal.json
sed -i "s|@@@HASH@@@|${DTBF_HASH}|g" ${ROOT_PATH}/recipes/universal.json

echo "file://localhost${ROOT_PATH}/rpext-index.json"