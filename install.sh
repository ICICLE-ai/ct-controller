#!/bin/bash

sudo cp ./systemd/ctcontroller.service /etc/systemd/system
sudo cp ./systemd/start-ctcontroller-container.sh /usr/local/bin/

sudo systemctl daemon-reload

sudo systemctl enable ctcontroller

echo "Reboot your machine or run \"sudo systemctl start ctcontroller\" to start the ctcontroller service"
