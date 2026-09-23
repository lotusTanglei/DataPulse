"""Run through the immutable Docker image and resource flags recorded in the log."""
import asyncio
import collections
import json
import os
import signal
import tempfile
import threading
import time
from pathlib import Path

signal.alarm(50)


def cgroup(name):
    return Path('/sys/fs/cgroup', name).read_text().strip()


def emit(event, **data):
    print(json.dumps({'event': event, **data}, sort_keys=True), flush=True)


def sample():
    return {
        'pids': int(cgroup('pids.current')),
        'memory_bytes': int(cgroup('memory.current')),
        'process_threads': len(list(Path('/proc/self/task').iterdir())),
    }


emit('limits', cpu_max=cgroup('cpu.max'), memory_max=cgroup('memory.max'),
     pids_max=cgroup('pids.max'), cpu_count=os.cpu_count(),
     process_cpu_count=os.process_cpu_count(), affinity=len(os.sched_getaffinity(0)), **sample())
import duckdb

emit('duckdb_import', version=duckdb.__version__, **sample())
connection = duckdb.connect(':memory:')
emit('connect_before_set',
     default_threads=connection.execute("SELECT current_setting('threads')").fetchone()[0],
     **sample())
connection.execute('SET threads=2')
emit('connect_after_set',
     configured_threads=connection.execute("SELECT current_setting('threads')").fetchone()[0],
     **sample())
connection.close()

from datapulse.filedata.duckdb_executor import DuckDBExecutor
from datapulse.settings import Settings

with tempfile.TemporaryDirectory(prefix='duckdb-capacity-') as root:
    settings = Settings(environment='test', data_dir=Path(root), duckdb_threads=2,
                        duckdb_memory_limit='512MB')
    source = settings.resolved_files_dir() / 'fixture.csv'
    source.parent.mkdir(parents=True)
    source.write_text('region,amount\nnorth,10\nsouth,20\n')
    executor = DuckDBExecutor(settings)
    original_execute_sync = executor._execute_sync
    active = 0
    peak_active = 0
    lock = threading.Lock()

    def measured_execute(*args, **kwargs):
        global active, peak_active
        with lock:
            active += 1
            peak_active = max(peak_active, active)
        try:
            return original_execute_sync(*args, **kwargs)
        finally:
            with lock:
                active -= 1

    executor._execute_sync = measured_execute
    baseline = sample()
    peaks = dict(baseline)
    stop = threading.Event()

    def monitor():
        while not stop.wait(0.001):
            for key, value in sample().items():
                peaks[key] = max(peaks[key], value)

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    errors = []
    timings = []
    started = time.perf_counter()

    async def client(identifier):
        for iteration in range(5):
            begin = time.perf_counter()
            try:
                result = await executor.execute(
                    'SELECT region, sum(amount) AS amount FROM dataset_source '
                    'GROUP BY region LIMIT 100', (), source_path=source,
                    request_id=f'client-{identifier}-{iteration}',
                    timeout_seconds=30, max_rows=100,
                )
                assert sorted(result.rows) == [('north', 10), ('south', 20)]
                timings.append((time.perf_counter() - begin) * 1000)
            except Exception as error:
                errors.append({
                    'type': type(error).__name__, 'code': getattr(error, 'code', None),
                    'message': str(error)[:250],
                    'cause_type': type(error.__cause__).__name__ if error.__cause__ else None,
                    'cause': str(error.__cause__)[:250] if error.__cause__ else None,
                })

    async def run():
        await asyncio.gather(*(client(identifier) for identifier in range(50)))
        pool = asyncio.get_running_loop()._default_executor
        emit('threadpool', max_workers=pool._max_workers, live_workers=len(pool._threads))

    asyncio.run(run())
    elapsed = time.perf_counter() - started
    stop.set()
    monitor_thread.join()
    ordered = sorted(timings)
    emit('capacity_result', clients=50, requests_per_client=5, total_requests=250,
         successful=len(timings), failed=len(errors), duration_seconds=round(elapsed, 3),
         p50_ms=round(ordered[len(ordered)//2], 3) if ordered else None,
         p95_ms=round(ordered[max(0, int(len(ordered)*.95)-1)], 3) if ordered else None,
         max_ms=round(max(ordered), 3) if ordered else None,
         peak_concurrent_sync_queries=peak_active, baseline=baseline, peaks=peaks,
         final=sample(), errors=errors[:5],
         error_counts=dict(collections.Counter(item['code'] or item['type'] for item in errors)),
         pids_events=cgroup('pids.events'), memory_events=cgroup('memory.events'))
    if errors:
        raise SystemExit(1)
