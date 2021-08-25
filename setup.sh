#!/bin/sh
pip install --user -e .

mkdir -p $HOME/.local/share/applications
#ln -sf $PWD/data/controldeck.desktop $HOME/.local/share/applications/controldeck.desktop
cp data/controldeck.desktop.local $HOME/.local/share/applications/controldeck.desktop
sed -i "s|\${HOME}|${HOME}|" ~/.local/share/applications/controldeck.desktop
mkdir -p $HOME/.config/systemd/user
ln -sf $PWD/data/controldeck.service.local $HOME/.config/systemd/user/controldeck.service
#cp data/controldeck.service $HOME/.config/systemd/user/controldeck.service
