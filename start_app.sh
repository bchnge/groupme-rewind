#!/bin/bash

session_name="app_groupme"

tmux new -ds $session_name
tmux send-keys -t $session_name 'cd ~/flask-apps/groupme-icu; python app/main.py' C-m
