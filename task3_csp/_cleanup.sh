#!/bin/bash
# Kill stale CORAL processes
pkill -9 -f "coral.cli start" 2>/dev/null
tmux kill-session -t coral-cutting-stock-problem-20260712-045033 2>/dev/null
sleep 2
echo "Cleaned up"
