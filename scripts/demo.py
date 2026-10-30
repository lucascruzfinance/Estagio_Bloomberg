"""One command to run the offline demo from the versioned snapshot.

    python scripts/demo.py              # seed + API + dashboard, Ctrl+C to stop
    python scripts/demo.py --check      # same, then verify every layer and exit
    python scripts/demo.py --database-url postgresql+psycopg://.../networking_demo

Steps: create the database if missing -> migrate -> deterministic seed of the 12
pilot accounts from files in the repository (no network) -> content fingerprint ->
build the dashboard -> start the API (APP_DATA_MODE=demo) and the dashboard.
The basemap is the only online dependency; without internet the map still shows
the offices over a plain background and says so.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from networking_intel.config import get_settings  # noqa: E402
from networking_intel.etl.load import run_etl  # noqa: E402
from networking_intel.etl.load_enriched import run_enriched_load  # noqa: E402

FINGERPRINT_QUERIES = {
    "organizations": "SELECT account_id, cnpj, legal_name FROM organizations ORDER BY account_id",
    "legal_entities": "SELECT cnpj, relation, legal_name, phone_official FROM legal_entities ORDER BY cnpj",
    "offices": (
        "SELECT office_key, office_kind, geocode_precision, geocode_is_exact, "
        "round(ST_X(location)::numeric, 6), round(ST_Y(location)::numeric, 6) "
        "FROM offices ORDER BY office_key"
    ),
    "funds": "SELECT cnpj, is_active, classification FROM funds ORDER BY cnpj",
    "fund_metrics": (
        "SELECT f.cnpj, m.subclass_id, m.return_12m, m.net_flow_12m_brl FROM fund_metrics m "
        "JOIN funds f ON f.id = m.fund_id ORDER BY f.cnpj, m.subclass_id"
    ),
    "observations": "SELECT count(*), min(observation_date), max(observation_date) FROM fund_observations",
    "scores": (
        "SELECT unit_key, rank, tier, priority_point, fit_point, timing_point, confidence "
        "FROM opportunity_scores ORDER BY unit_key"
    ),
}


def log(message: str) -> None:
    print(f"[demo] {message}", flush=True)


def ensure_database(url: str) -> None:
    parsed = make_url(url)
    admin = create_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": parsed.database}
            ).scalar()
            if not exists:
                log(f"criando banco {parsed.database}")
                connection.execute(text(f'CREATE DATABASE "{parsed.database}"'))
    finally:
        admin.dispose()


def migrate(url: str) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.attributes["database_url"] = url
    command.upgrade(config, "head")


def fingerprint(url: str) -> tuple[str, dict[str, int]]:
    engine = create_engine(url)
    digest = hashlib.sha256()
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for name, sql in FINGERPRINT_QUERIES.items():
            rows = connection.execute(text(sql)).all()
            counts[name] = len(rows) if name != "observations" else int(rows[0][0])
            digest.update(name.encode())
            digest.update(json.dumps([list(r) for r in rows], default=str).encode())
    engine.dispose()
    return digest.hexdigest(), counts


def seed(url: str) -> tuple[str, dict[str, int]]:
    log("migrando o esquema")
    migrate(url)
    log("seed das 12 contas (planilha tratada)")
    run_etl(ROOT / "data/staging/pilot_accounts.csv", url)
    log("carga do enriquecimento e dos scores versionados (sem rede)")
    run_enriched_load(ROOT, url)
    return fingerprint(url)


def get_json(url: str, timeout: float = 5) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read())


def wait_for(url: str, seconds: float) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"{url} não respondeu em {seconds:.0f}s")


def stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False
        )
    else:
        process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def build_frontend() -> None:
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm não encontrado: instale Node.js 20+ para o dashboard")
    frontend = ROOT / "frontend"
    if not (frontend / "node_modules").exists():
        log("instalando dependências do dashboard (npm ci)")
        subprocess.run([npm, "ci"], cwd=frontend, check=True)
    log("compilando o dashboard")
    result = subprocess.run([npm, "run", "build"], cwd=frontend, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout[-4000:] + result.stderr[-4000:])
        raise RuntimeError("o build do dashboard falhou (saída acima)")


def check(api: str, web: str) -> list[str]:
    problems: list[str] = []
    ready = get_json(f"{api}/ready")
    if ready["status"] != "ready":
        problems.append(f"/ready: {ready}")
    meta = get_json(f"{api}/api/v1/meta")
    if meta["data_mode"] != "demo":
        problems.append("API não está em modo demo")
    scores = get_json(f"{api}/api/v1/scores?page_size=200")
    if scores["meta"]["total"] != 22:
        problems.append(f"esperava 22 unidades pontuadas, veio {scores['meta']['total']}")
    accounts = get_json(f"{api}/api/v1/accounts?page_size=200")
    if accounts["meta"]["total"] != 12:
        problems.append(f"esperava 12 contas, veio {accounts['meta']['total']}")
    offices = get_json(f"{api}/api/v1/map/offices")
    if offices["meta"]["count"] == 0:
        problems.append("nenhum escritório georreferenciado")
    if web:
        with urllib.request.urlopen(f"{web}/", timeout=5) as response:
            html = response.read().decode()
            if "Content-Security-Policy" not in html:
                problems.append("dashboard sem CSP no build de produção")
        proxied = get_json(f"{web}/api/v1/meta")
        if proxied["data_mode"] != "demo":
            problems.append("proxy do dashboard não chega à API")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--database-url", default=None, help="padrão: DATABASE_URL do .env")
    parser.add_argument("--check", action="store_true", help="verificar tudo e encerrar")
    parser.add_argument("--no-frontend", action="store_true")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--web-port", type=int, default=4173)
    args = parser.parse_args()

    url = args.database_url or get_settings().database_url
    log(f"banco {make_url(url).render_as_string(hide_password=True)}")
    ensure_database(url)
    digest, counts = seed(url)
    log(f"impressão digital do seed {digest[:16]} {json.dumps(counts)}")

    api_url = f"http://127.0.0.1:{args.api_port}"
    web_url = "" if args.no_frontend else f"http://127.0.0.1:{args.web_port}"
    environment = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "src"),
        "DATABASE_URL": url,
        "APP_DATA_MODE": "demo",
    }
    processes: list[subprocess.Popen[bytes]] = []
    try:
        log("subindo a API")
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "networking_intel.api.app:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.api_port),
                    "--log-level",
                    "warning",
                    "--no-server-header",
                ],
                cwd=ROOT,
                env=environment,
            )
        )
        wait_for(f"{api_url}/health", 60)
        if web_url:
            build_frontend()
            vite = ROOT / "frontend/node_modules/vite/bin/vite.js"
            log("subindo o dashboard")
            processes.append(
                subprocess.Popen(
                    [
                        "node",
                        str(vite),
                        "preview",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(args.web_port),
                        "--strictPort",
                    ],
                    cwd=ROOT / "frontend",
                    env={**environment, "API_ORIGIN": api_url},
                )
            )
            wait_for(f"{web_url}/", 60)
        if args.check:
            problems = check(api_url, web_url)
            for problem in problems:
                log(f"FALHA: {problem}")
            log("verificação concluída sem falhas" if not problems else f"{len(problems)} falha(s)")
            return 1 if problems else 0
        log(f"pronto: abra {web_url or api_url + '/docs'} (Ctrl+C para encerrar)")
        while all(process.poll() is None for process in processes):
            time.sleep(1)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        for process in reversed(processes):
            stop(process)


if __name__ == "__main__":
    raise SystemExit(main())
