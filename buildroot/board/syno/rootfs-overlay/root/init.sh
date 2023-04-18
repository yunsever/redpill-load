#!/bin/bash

LOG_FILE="/temp1/boot.log"
rm -tf "${LOG_FILE}" 
echo "START /root/init.sh" > "${LOG_FILE}"

if grep </proc/cmdline -q "whosyourdaddy"; then
  # TODO add ttyd and lrzsz, first need some nic driver
  echo "Debug mode, you will stay at the first kernel"
  exit 0
fi

# Args: $1 vid $2 pid $3 synoboot_satadom $4 dom_szmax
get_synoboot() {
  local usbfs
  if [[ ${3:-"0"} = "0" ]]; then
    dev=$(udevadm trigger -v -n -s block -p ID_VENDOR_ID="$1" -p ID_MODEL_ID="$2" | head -n 1)
    if [[ ! "${dev}" = "" ]]; then
      usbfs=/dev/"${dev##*/}"
    fi
  else
    # satadom size <= 1024 MB or dom_szmax
    devs=$(find /sys/block/sd*)
    for dev in $devs; do
      if [[ $(cat "$dev"/size) -le $((${4:-1024} * 1024 * 1024 / 512)) ]]; then
        usbfs=/dev/"${dev##*/}"
        break
      fi
    done
  fi
  echo "$usbfs"
}

CMDLINE=$(cat /proc/cmdline)
echo "${CMDLINE}" >> "${LOG_FILE}"

vid=$(for x in $CMDLINE; do
  [[ $x = vid=* ]] || continue
  echo "${x#vid=}" | cut -b 3-6
done)
pid=$(for x in $CMDLINE; do
  [[ $x = pid=* ]] || continue
  echo "${x#pid=}" | cut -b 3-6
done)
synoboot_satadom=$(for x in $CMDLINE; do
  [[ $x = synoboot_satadom=* ]] || continue
  echo "${x#synoboot_satadom=}"
done)
dom_szmax=$(for x in $CMDLINE; do
  [[ $x = dom_szmax=* ]] || continue
  echo "${x#dom_szmax=}"
done)

cd "$(dirname "$0")" || exit
mkdir /temp1
mkdir /temp2

# found synoboot
usbfs=$(get_synoboot "$vid" "$pid" "$synoboot_satadom" "$dom_szmax")
wait_time=30
time_counter=0
while [ "${usbfs}" = "" ] && [ $time_counter -lt $wait_time ]; do
  sleep 1
  usbfs=$(get_synoboot "$vid" "$pid" "$synoboot_satadom" "$dom_szmax")
  echo "Still waiting for boot device (waited $((time_counter = time_counter + 1)) of ${wait_time} seconds)"
done
echo "usbfs=${usbfs}" >> "${LOG_FILE}"

mount "${usbfs}"1 /temp1
mount "${usbfs}"2 /temp2

# patch zImage
./bzImage-to-vmlinux.sh /temp2/zImage vmlinux >> "${LOG_FILE}" 2>&1
./kpatch vmlinux vmlinux-mod >"${LOG_FILE}" 2>&1
rm vmlinux
./vmlinux-to-bzImage.sh vmlinux-mod zImage-mod >>"${LOG_FILE}" 2>&1
rm vmlinux-mod

mkdir "ramdisk"
cd "ramdisk" || exit
unlzma </temp2/rd.gz | cpio -idmuv
unlzma </temp1/custom.gz | cpio -idmuv
# rd.gz + custom.gz
#find . 2>/dev/null | cpio -o -H newc -R root:root | xz -9 --format=lzma >../rd.gz
find . 2>/dev/null | cpio -o -H newc -R root:root >../rd.gz
cd ..
rm -rf ramdisk

umount /temp1
umount /temp2

# start
kexec -d -l ./zImage-mod --initrd=./rd.gz --reuse-cmdline >> "${LOG_FILE}" 2>&1
kexec -d -e
