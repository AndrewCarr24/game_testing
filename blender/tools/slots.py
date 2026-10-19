"""A few run slots shared by every headless Blender build on this machine, so parallel agents
can't overload it: each house build (build_level.py) loads the whole level and renders with
the GPU (~2 GB each); 7 agents x several rooms at once ran a 26 GB machine out of memory.
A process takes a free slot (an flock on build/locks/<kind>_<i>.lock) or waits for one;
the slot frees itself when the process exits, however it exits."""
import fcntl
import os
import time

LOCKS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "locks"))
_held = []


def acquire(kind, n):
    os.makedirs(LOCKS, exist_ok=True)
    t0, said = time.time(), False
    while True:
        for i in range(n):
            fh = open(os.path.join(LOCKS, f"{kind}_{i}.lock"), "w")
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                fh.close()
                continue
            _held.append(fh)                      # held until the process exits
            if said:
                print(f"SLOT {kind}: got one after {time.time() - t0:.0f}s")
            return i
        if not said:
            print(f"SLOT {kind}: all {n} busy (other builds running), waiting...")
            said = True
        time.sleep(2)
