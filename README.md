# SOA Cluster Manager

Platforma orientata pe servicii pentru gestiunea unui cluster de calculatoare simulate in Docker.

## Structura

| Folder | Continut |
|---|---|
| `proto/` | `idm.proto` - contractul gRPC al serviciului IDM |
| `infra/mariadb/init/` | Scripturile SQL rulate la prima pornire a MariaDB |
| `idm-service/` | Serviciul IDM (Python, gRPC): conturi, autentificare, token-uri JWS |
| `idm-client/` | Biblioteca client IDM, aplicatia consola si scenariul de test |

## Cerinte

- Docker Desktop
- Python 3.14 (64 biti) si [uv](https://docs.astral.sh/uv/)

## Pornire serviciu IDM

1. Configurare: copiaza `.env.example` in `.env` si completeaza parolele si `IDM_JWT_SECRET`.
2. Baza de date:
   ```bash
   docker compose up -d
   ```
3. Serviciul IDM (din folderul `idm-service/`):
   ```bash
   uv venv --python 3.14
   uv pip install -r requirements.txt
   .venv/Scripts/python generate_grpc.py
   .venv/Scripts/python server.py
   ```
4. Clientul (din folderul `idm-client/`, intr-un alt terminal):
   ```bash
   uv venv --python 3.14
   uv pip install -r requirements.txt
   .venv/Scripts/python generate_grpc.py
   .venv/Scripts/python console.py
   ```

Primul cont, `admin`, exista deja in baza de date, dar este inactiv: din consola alege **Activare cont** si seteaza-i parola.

## Testare automata

Cu serviciul IDM pornit, din `idm-client/`:
```bash
.venv/Scripts/python scenario.py
```
Scenariul verifica toate cele 7 metode si codurile de eroare gRPC. La prima rulare activeaza contul `admin` cu parola introdusa.

## Resetarea bazei de date

```bash
docker compose down -v
```
Sterge volumul cu date; la urmatorul `docker compose up -d` scripturile din `infra/mariadb/init/` ruleaza din nou.
