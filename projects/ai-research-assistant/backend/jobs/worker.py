"""Worker CLI wrapper in backend.jobs namespace."""

from backend.worker import run_worker_loop

if __name__ == "__main__":
    run_worker_loop()
