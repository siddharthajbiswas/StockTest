"""Battery-aware throttle for the lab.

Every 30 s it reads `pmset -g batt` and decides how many of the 12 global
backtest slots the research may use; it occupies the rest by holding their
file locks (which costs no CPU). Running tasks always finish; only the number
of tasks that can START is limited. Status goes to power_throttle.json/.log.

    python3 power_throttle.py          # run in the background; kill to stop
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import threading
import time

SLOT_DIR = "/Users/siddhartha/dev/StockTest/research/lab/.slots"
HERE = os.path.dirname(os.path.abspath(__file__))
N = 12
ORDER = list(range(N - 1, -1, -1))     # occupy high-numbered slots first

held: dict = {}
lock = threading.Lock()
target_hold = [N - 2]                  # start conservative until the first reading
paused: set = set()                    # pids we SIGSTOPped (low battery, unplugged)
PAUSE_BELOW, RESUME_AT = 10, 15        # % battery while unplugged (hysteresis)


def battery():
    out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    ac = "AC Power" in out
    m = re.search(r"(\d+)%;\s*([^;]+);", out)
    pct = int(m.group(1)) if m else None
    state = m.group(2).strip() if m else "unknown"
    return ac, pct, state


def allowed(ac: bool, pct: int | None) -> int:
    """Backtests allowed to run at once (of 12). The user asked to spend as
    much power as needed (2026-10-05): full power on AC at any charge, and on
    battery too, with only a safety net so a dead battery cannot kill the
    session (4 slots below 20%; below 10% research freezes, see main())."""
    if pct is None or ac:
        return N
    if pct < 10:
        return 0
    if pct < 20:
        return 4
    return N


def research_pids() -> list:
    """Research processes the agents run (never this throttle, the renice
    loop, or the lead's own _lead/ scripts)."""
    out = subprocess.run(["pgrep", "-f", r"research/lab|research\.lab"], capture_output=True,
                         text=True).stdout.split()
    me = os.getpid()
    keep = []
    for p in out:
        pid = int(p)
        if pid == me:
            continue
        cmd = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True,
                             text=True).stdout
        if "_lead/" in cmd or not cmd.strip():
            continue
        keep.append(pid)
    return keep


def pause_all():
    import signal
    for pid in research_pids():
        try:
            os.kill(pid, signal.SIGSTOP)
            paused.add(pid)
        except ProcessLookupError:
            pass


def resume_all():
    import signal
    for pid in list(paused):
        try:
            os.kill(pid, signal.SIGCONT)
        except ProcessLookupError:
            pass
        paused.discard(pid)
    # safety net: anything of ours left stopped
    for pid in research_pids():
        st = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True,
                            text=True).stdout.strip()
        if st.startswith("T"):
            try:
                os.kill(pid, signal.SIGCONT)
            except ProcessLookupError:
                pass


def manager():
    while True:
        with lock:
            need = target_hold[0] - len(held)
            if need < 0:
                for idx in sorted(held)[: -need]:
                    fd = held.pop(idx)
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    os.close(fd)
                need = 0
            elif need > 0:
                for idx in ORDER:
                    if need <= 0:
                        break
                    if idx in held:
                        continue
                    fd = os.open(f"{SLOT_DIR}/cpu{idx}", os.O_CREAT | os.O_RDWR)
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        held[idx] = fd
                        need -= 1
                    except BlockingIOError:
                        os.close(fd)
        time.sleep(0.005 if need > 0 else 0.5)


def main():
    os.makedirs(SLOT_DIR, exist_ok=True)
    ac0, pct0, _ = battery()
    target_hold[0] = N - allowed(ac0, pct0)     # first reading before grabbing slots
    threading.Thread(target=manager, daemon=True).start()
    last = None
    pausing = False
    while True:
        ac, pct, state = battery()
        a = allowed(ac, pct)
        target_hold[0] = N - a
        # Unplugged and low: freeze every research process (SIGSTOP keeps all
        # state; nothing is lost). Plugged in, or recharged: thaw them.
        if not ac and pct is not None and pct < PAUSE_BELOW:
            pausing = True
        elif ac or (pct is not None and pct >= RESUME_AT):
            if pausing or paused:
                resume_all()
            pausing = False
        if pausing:
            pause_all()
        with lock:
            h = len(held)
        status = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "ac_power": ac, "battery_pct": pct,
                  "state": state, "allowed_backtests": 0 if pausing else a,
                  "research_paused": pausing, "paused_processes": len(paused),
                  "slots_held_now": h}
        with open(os.path.join(HERE, "power_throttle.json"), "w") as fh:
            json.dump(status, fh)
        if (ac, a, pausing) != last:
            with open(os.path.join(HERE, "power_throttle.log"), "a") as fh:
                fh.write(json.dumps(status) + "\n")
            last = (ac, a, pausing)
        time.sleep(30)


if __name__ == "__main__":
    main()
