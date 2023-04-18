#!/usr/bin/env bash
#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
# 
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

ROOT_PATH=$PWD
TOOL_PATH="$(dirname $(readlink -f "$0"))/extractor"

GITHUB_URL="https://raw.githubusercontent.com/wjz304/redpill-load/main/ext/extractor"
[ ! -d "${TOOL_PATH}" ] && mkdir -p "${TOOL_PATH}"
for f in libcurl.so.4 libmbedcrypto.so.5 libmbedtls.so.13 libmbedx509.so.1 libmsgpackc.so.2 libsodium.so libsynocodesign-ng-virtual-junior-wins.so.7 syno_extract_system_patch; do
  [ ! -e "${TOOL_PATH}/${f}" ] && curl -skL "${GITHUB_URL}/${f}" -o "${TOOL_PATH}/${f}"
done
chmod -R +x "${TOOL_PATH}"
LD_LIBRARY_PATH="${TOOL_PATH}" "${TOOL_PATH}/syno_extract_system_patch" $@
