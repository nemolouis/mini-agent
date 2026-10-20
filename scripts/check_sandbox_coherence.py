"""Reproducer for the host->container file-visibility lag (see miniagent/sandbox.py). Needs generated tasks.
Flow: copy a task repo, grade it in a container, replace one file on the host, grade again; count wrong second results.
Before grading used a fresh copy: about 8 of 100; after: 0 of 300.   usage: python scripts/check_sandbox_coherence.py [iterations-per-thread]"""
import shutil, sys, tempfile, threading, time
from pathlib import Path
from miniagent.eval.tasks import load_tasks
from miniagent.eval.grade import copy_repo, add_hidden, run_tests

T={t.id:t for t in load_tasks("gen_tasks")}
ids=[i for i in T if i.startswith("g-inflection-")][:6]
mode="plain"
N=int(sys.argv[1]) if len(sys.argv)>1 else 25
fails=[0]; total=[0]; lock=threading.Lock()
def worker(k):
    for n in range(N):
        t=T[ids[(k+n)%len(ids)]]
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp)/"r"; copy_repo(t.repo,w); add_hidden(t.hidden,w)
            run_tests(w,t.test_cmd,sandbox=True)                      # first container reads the buggy files
            for f in t.solution.rglob("*"):
                if f.is_file():
                    import os
                    d=w/f.relative_to(t.solution)
                    if mode in ("rename","rename+fsync"):
                        tmpf=d.with_name(d.name+".tmpw"); shutil.copy(f,tmpf)
                        if mode=="rename+fsync":
                            fd=os.open(tmpf,os.O_RDONLY); os.fsync(fd); os.close(fd)
                        os.replace(tmpf,d)
                    else:
                        shutil.copy(f,d)
                        if mode=="fsync":
                            fd=os.open(d,os.O_RDONLY); os.fsync(fd); os.close(fd)
                    if mode=="touch":
                        os.utime(d,(time.time()+5,time.time()+5))
            ok,out=run_tests(w,t.test_cmd,sandbox=True)
        with lock:
            total[0]+=1; fails[0]+= (not ok)
ts=[threading.Thread(target=worker,args=(k,)) for k in range(4)]
t0=time.time(); [t.start() for t in ts]; [t.join() for t in ts]
print(mode,"stale/failed:",fails[0],"of",total[0],f"({time.time()-t0:.0f}s)")
