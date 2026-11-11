"""
LifeOS Production WSGI Server (Waitress)
Binds to 0.0.0.0:8000 for multi-threaded serving on Windows.
Supports local browser, Wi-Fi LAN access (phones/tablets), and Cloudflare Tunnel.
"""
import os
import sys
import socket
import logging

def get_lan_ip():
    """Detect the local Wi-Fi / LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Does not actually send data; used to determine outbound routing interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django
    django.setup()

    from config.wsgi import application
    import waitress

    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    lan_ip = get_lan_ip()

    banner = f"""
======================================================================
  _      _  __        ____   _____ 
 | |    (_)/ _|      / __ \\ / ____|
 | |     _| |_ ___  | |  | | (___  
 | |    | |  _/ _ \\ | |  | |\\___ \\ 
 | |____| | |  __/  | |__| |____) |
 |______|_|_| \\___|  \\____/|_____/ 
                                   
  LifeOS Production Server Running (Waitress WSGI)
======================================================================

  [Local Access]
    http://localhost:{port}
    http://127.0.0.1:{port}

  [Wi-Fi / LAN Access for Mobile & Other Devices]
    http://{lan_ip}:{port}
    (Ensure devices are connected to the same Wi-Fi network)

  [Health Check]
    http://localhost:{port}/health/

  [Public Tunnel Access]
    Run 'start_tunnel.bat' in a separate terminal to generate a
    free, secure public HTTPS URL (via Cloudflare Quick Tunnel)
    to share with friends.

  [Mobile PWA Note]
    Open http://{lan_ip}:{port} on your phone's browser, then tap
    "Add to Home Screen" or "Install App" to use LifeOS as a PWA!

  Press Ctrl+C to stop the server safely.
======================================================================
"""
    try:
        if sys.stdout and not sys.stdout.closed:
            print(banner)
    except Exception:
        pass

    # Configure waitress logging to both file and console
    log_handlers = []
    try:
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        log_handlers.append(file_handler)
    except Exception:
        pass

    try:
        if sys.stdout and not sys.stdout.closed:
            stream_handler = logging.StreamHandler(sys.stdout)
            log_handlers.append(stream_handler)
    except Exception:
        pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=log_handlers if log_handlers else None
    )

    logging.info("Starting LifeOS Waitress server on %s:%d", host, port)

    waitress.serve(
        application,
        host=host,
        port=port,
        threads=6,
        channel_timeout=60,
        cleanup_interval=30,
        ident="LifeOS/1.0 (Waitress)"
    )

if __name__ == "__main__":
    main()
