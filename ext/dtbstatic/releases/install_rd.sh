#!/bin/sh

# install dtc
chmod +x dtc
cp dtc /usr/sbin/dtc

# copy file
cp -vf user_model.dtb /etc.defaults/model.dtb
cp -vf user_model.dtb /var/run/model.dtb
