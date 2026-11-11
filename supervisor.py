"""
LifeOS Production Service Supervisor and Health Monitor.
Ensures high availability for LifeOS on Windows:
- Guarantees MySQL is running before Django launches.
- Verifies database connectivity.
- Starts and supervises Waitress WSGI server (serve.py).
- Auto-recovers if MySQL or Waitress crashes (with flapping protection).
- Verifies Tailscale Funnel is active on port 8000 with stable hostname.
- Runs independently of Antigravity in the background.
- Single-instance enforcement via Windows Named Mutex.
"""
import os
import sys
import time
import socket
import logging
from logging.handlers import RotatingFileHandler
import subprocess
import urllib.request
import urllib.error
import ctypes
from ctypes import wintypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "monitor.log")
PID_FILE = os.path.join(BASE_DIR, "supervisor.pid")
PYTHON_EXE = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
SERVE_SCRIPT = os.path.join(BASE_DIR, "serve.py")
MYSQLD_EXE = r"C:\xampp\mysql\bin\mysqld.exe"
MYSQL_INI = r"C:\xampp\mysql\bin\my.ini"
MYSQL_DIR = r"C:\xampp\mysql"
TAILSCALE_EXE = r"C:\Program Files\Tailscale\tailscale.exe"
PUBLIC_HOST = "laptop-lkra47mc.tail581455.ts.net"
PUBLIC_HEALTH_URL = f"https://{PUBLIC_HOST}/health/"
LOCAL_HEALTH_URL = "http://127.0.0.1:8000/health/"

# Flapping protection: maximum 5 restarts within 600 seconds (10 minutes)
MAX_RESTARTS_IN_WINDOW = 5
RESTART_WINDOW_SECONDS = 600
BACKOFF_DELAY_SECONDS = 60

# Mutex name for single instance
MUTEX_NAME = "LifeOS_Supervisor_SingleInstance_Mutex"
CREATE_NO_WINDOW = 0x08000000

# Setup Rotating Logger
logger = logging.getLogger("LifeOS_Supervisor")
logger.setLevel(logging.INFO)

rfh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
rfh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(rfh)

# Optional console logging if stdout is available
try:
    if sys.stdout and not sys.stdout.closed:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(sh)
except Exception:
    pass


class SingleInstanceLock:
    def __init__(self):
        self.mutex = None

    def acquire(self):
        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183
        self.mutex = kernel32.CreateMutexW(None, True, MUTEX_NAME)
        last_error = kernel32.GetLastError()
        if last_error == ERROR_ALREADY_EXISTS:
            logger.warning("Another LifeOS supervisor is already running. Exiting.")
            return False
        # Record PID
        try:
            with open(PID_FILE, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
        except Exception as e:
            logger.warning(f"Failed to write PID file: {e}")
        return True

    def release(self):
        if self.mutex:
            ctypes.windll.kernel32.CloseHandle(self.mutex)
            self.mutex = None
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass


class ServiceSupervisor:
    def __init__(self):
        self.waitress_proc = None
        self.restart_history = []
        self.running = True

    def is_port_listening(self, host: str, port: int, timeout: float = 2.0) -> bool:
        try:
            s = socket.create_connection((host, port), timeout=timeout)
            s.close()
            return True
        except Exception:
            return False

    def ensure_mysql(self) -> bool:
        """Verify MySQL is running; start XAMPP mysqld if not."""
        if self.is_port_listening("127.0.0.1", 3306, timeout=2.0):
            return True

        logger.info("MySQL is not listening on port 3306. Attempting to start XAMPP MySQL...")
        if not os.path.exists(MYSQLD_EXE):
            logger.error(f"MySQL binary not found at {MYSQLD_EXE}")
            return False

        cmd = [MYSQLD_EXE, f"--defaults-file={MYSQL_INI}", "--console"]
        try:
            subprocess.Popen(cmd, cwd=MYSQL_DIR, creationflags=CREATE_NO_WINDOW)
            logger.info("Spawned mysqld.exe process. Waiting for socket binding...")
        except Exception as e:
            logger.error(f"Failed to spawn mysqld: {e}")
            return False

        # Wait up to 20 seconds for port 3306
        for _ in range(20):
            time.sleep(1)
            if self.is_port_listening("127.0.0.1", 3306, timeout=1.5):
                logger.info("[OK] MySQL server is active and listening on port 3306.")
                return True

        logger.error("[ERROR] MySQL did not become available on port 3306 within 20 seconds.")
        return False

    def verify_database_connection(self) -> bool:
        """Run a lightweight Python check to ensure Django can connect to MySQL."""
        test_code = (
            "import os, django; "
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); "
            "django.setup(); "
            "from django.db import connection; "
            "cur = connection.cursor(); "
            "cur.execute('SELECT 1'); "
            "print('DB_OK')"
        )
        try:
            res = subprocess.run(
                [PYTHON_EXE, "-c", test_code],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=CREATE_NO_WINDOW
            )
            if "DB_OK" in res.stdout:
                logger.info("[OK] Database connectivity verified via Django ORM (SELECT 1 succeeded).")
                return True
            else:
                logger.error(f"Database connectivity check failed: {res.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error executing database check: {e}")
            return False

    def is_local_health_ok(self, timeout: float = 4.0) -> bool:
        try:
            req = urllib.request.Request(LOCAL_HEALTH_URL, headers={"User-Agent": "LifeOS-Supervisor/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    body = response.read().decode("utf-8")
                    return '"status": "ok"' in body or '"status":"ok"' in body
        except Exception:
            return False
        return False

    def is_public_health_ok(self, timeout: float = 6.0) -> bool:
        try:
            req = urllib.request.Request(PUBLIC_HEALTH_URL, headers={"User-Agent": "LifeOS-Supervisor/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    body = response.read().decode("utf-8")
                    return '"status": "ok"' in body or '"status":"ok"' in body
        except Exception:
            return False
        return False

    def kill_existing_port_8000(self):
        """Ensure port 8000 is clean before starting Waitress."""
        try:
            netstat_out = subprocess.check_output(
                'netstat -ano | findstr /R /C:":8000 .*LISTENING"',
                shell=True,
                text=True,
                creationflags=CREATE_NO_WINDOW
            )
            for line in netstat_out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[3] == "LISTENING":
                    pid = parts[4]
                    logger.info(f"Terminating orphan process on port 8000 (PID {pid})...")
                    subprocess.run(f"taskkill /PID {pid} /F", shell=True, creationflags=CREATE_NO_WINDOW)
            time.sleep(1)
        except Exception:
            pass

    def can_attempt_restart(self) -> bool:
        now = time.time()
        # Prune old restart entries outside window
        self.restart_history = [t for t in self.restart_history if now - t < RESTART_WINDOW_SECONDS]
        if len(self.restart_history) >= MAX_RESTARTS_IN_WINDOW:
            logger.warning(
                f"[FLAPPING DETECTED] {len(self.restart_history)} restarts within {RESTART_WINDOW_SECONDS}s. "
                f"Pausing recovery for {BACKOFF_DELAY_SECONDS}s to prevent restart loop."
            )
            return False
        return True

    def start_waitress(self) -> bool:
        if not self.can_attempt_restart():
            time.sleep(BACKOFF_DELAY_SECONDS)
            return False

        self.kill_existing_port_8000()

        logger.info(f"Starting Waitress WSGI server: {PYTHON_EXE} {SERVE_SCRIPT}")
        try:
            self.waitress_proc = subprocess.Popen(
                [PYTHON_EXE, SERVE_SCRIPT],
                cwd=BASE_DIR,
                creationflags=CREATE_NO_WINDOW
            )
            self.restart_history.append(time.time())
            logger.info(f"Waitress spawned with PID {self.waitress_proc.pid}. Waiting for readiness...")
        except Exception as e:
            logger.error(f"Failed to spawn Waitress server: {e}")
            return False

        # Wait up to 15 seconds for local health endpoint to return 200
        for _ in range(15):
            time.sleep(1)
            if self.is_local_health_ok():
                logger.info(f"[OK] Waitress server is operational and responding at {LOCAL_HEALTH_URL}")
                return True

        logger.error("[ERROR] Waitress server did not respond with HTTP 200 within 15 seconds.")
        return False

    def ensure_tailscale_funnel(self) -> bool:
        """Verify Tailscale Funnel is forwarding to port 8000; enable if not."""
        if not os.path.exists(TAILSCALE_EXE):
            logger.warning("Tailscale executable not found. Skipping Funnel verification.")
            return False

        try:
            status_res = subprocess.run(
                [TAILSCALE_EXE, "funnel", "status"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW
            )
            output = status_res.stdout + status_res.stderr
            if PUBLIC_HOST in output and "8000" in output:
                return True
        except Exception as e:
            logger.warning(f"Error checking tailscale funnel status: {e}")

        logger.info("Enabling Tailscale Funnel for port 8000 (--bg mode)...")
        try:
            run_res = subprocess.run(
                [TAILSCALE_EXE, "funnel", "--bg", "8000"],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=CREATE_NO_WINDOW
            )
            logger.info(f"Tailscale Funnel command output: {run_res.stdout.strip()}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable Tailscale Funnel: {e}")
            return False

    def run(self):
        logger.info("======================================================================")
        logger.info("           LifeOS Service Supervisor & Health Monitor Started          ")
        logger.info("======================================================================")

        # Step 1: Ensure MySQL is running
        if not self.ensure_mysql():
            logger.error("Could not initialize MySQL. Supervisor will continue trying...")

        # Step 2: Verify Database connectivity
        if self.is_port_listening("127.0.0.1", 3306):
            self.verify_database_connection()

        # Step 3: Start Waitress if not already running
        if not self.is_local_health_ok():
            self.start_waitress()
        else:
            logger.info("[OK] Existing Waitress server detected and operational on port 8000.")

        # Step 4: Ensure Tailscale Funnel
        self.ensure_tailscale_funnel()

        # Step 5: Initial health audit
        local_ok = self.is_local_health_ok()
        public_ok = self.is_public_health_ok()
        logger.info(f"[INITIAL STATUS] Local Health: {'OK' if local_ok else 'FAIL'} | Public Funnel Health: {'OK' if public_ok else 'FAIL'}")

        # Step 6: Continuous Monitoring Loop
        cycle_count = 0
        while self.running:
            try:
                time.sleep(15)
                cycle_count += 1

                # 1. Check MySQL
                if not self.is_port_listening("127.0.0.1", 3306):
                    logger.warning("[ALERT] MySQL is DOWN! Initiating recovery...")
                    self.ensure_mysql()

                # 2. Check Waitress process & health
                proc_dead = self.waitress_proc is not None and self.waitress_proc.poll() is not None
                local_unhealthy = not self.is_local_health_ok()

                if proc_dead or local_unhealthy:
                    exit_info = f"(exit code: {self.waitress_proc.returncode})" if proc_dead else "(health check failed)"
                    logger.warning(f"[ALERT] Waitress WSGI server is down or unresponsive {exit_info}! Initiating recovery...")
                    # Re-verify DB before restarting Waitress
                    self.ensure_mysql()
                    self.start_waitress()

                # 3. Check Tailscale Funnel every 4 cycles (~60 seconds)
                if cycle_count % 4 == 0:
                    pub_status = self.is_public_health_ok()
                    if not pub_status and self.is_local_health_ok():
                        logger.warning("[ALERT] Public Funnel is not responding but local server is healthy. Reasserting Funnel...")
                        self.ensure_tailscale_funnel()

                # 4. Periodic heartbeat every 20 cycles (~5 minutes)
                if cycle_count % 20 == 0:
                    loc = "OK" if self.is_local_health_ok() else "FAIL"
                    pub = "OK" if self.is_public_health_ok() else "FAIL"
                    db = "OK" if self.is_port_listening("127.0.0.1", 3306) else "FAIL"
                    logger.info(f"[HEARTBEAT] MySQL: {db} | Local: {loc} | Public Funnel ({PUBLIC_HOST}): {pub}")

            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt received. Stopping LifeOS Supervisor...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in supervisor loop: {e}", exc_info=True)
                time.sleep(5)

        logger.info("LifeOS Service Supervisor stopped.")


def main():
    lock = SingleInstanceLock()
    if not lock.acquire():
        sys.exit(0)

    try:
        supervisor = ServiceSupervisor()
        supervisor.run()
    finally:
        lock.release()


if __name__ == "__main__":
    main()
