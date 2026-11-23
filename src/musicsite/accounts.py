"""Cuentas del sitio (C26, C38, S99): quién es quien llama y sus preferencias.

Solo existe si `create_app` recibe una configuración de cuentas (`accounts_from_env`): sin ella,
`/api/me/*` es 404 como lo que no existe. El navegador nunca habla con Firestore (sus reglas lo
niegan): todo pasa por aquí, que entra por IAM.

- **Quién llama:** el ID token de Firebase del **grupo público** (Google y Facebook). Un token del
  tenant del equipo es válido para el proyecto y se rechaza: el equipo no es público del sitio.
  Nunca se registran ni el token ni el correo.
- **Qué se guarda:** el UID y datos del producto. Ni correo ni nombre, que quedan solo en
  Firebase Auth.
- **Cuánto:** campos conocidos y validados, 2 KB como máximo y un límite de frecuencia por persona.
"""

import json
import math
import re
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

# Proveedores del grupo público (C17). Microsoft se suma cuando exista su cliente.
PUBLIC_PROVIDERS = frozenset({"google.com", "facebook.com"})
# Versión vigente del aviso de privacidad (`web/privacidad.html` y docs/privacidad del control).
# Si cambia de forma importante, se sube y cada persona vuelve a aceptar.
NOTICE_VERSION = "2026-11-23-v2"
VERSION = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-v[0-9]{1,3}")
MAX_BODY_BYTES = 2048
RATE_LIMIT = 30  # peticiones por persona...
RATE_WINDOW_SECONDS = 60  # ...cada minuto
MAX_TRACKED_PEOPLE = 5000  # tope de la memoria del límite; se descartan las más antiguas
SLUG = re.compile(r"[a-z][a-z-]{0,23}")
UID = re.compile(r"[A-Za-z0-9]{1,128}")
INSTRUMENTS = frozenset({"guitarra", "teclado"})


class InvalidPreferences(ValueError):
    pass


def _flag(value: object) -> bool:
    if not isinstance(value, bool):
        raise InvalidPreferences("se esperaba verdadero o falso")
    return value


def _unit(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise InvalidPreferences("se esperaba un número")
    if not 0 <= value <= 1:
        raise InvalidPreferences("fuera de rango")
    return float(value)


def _slug(value: object) -> str:
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise InvalidPreferences("valor no permitido")
    return value


def _instrument(value: object) -> str:
    # Una lista no es hashable: no puede llegar al `in`.
    if not isinstance(value, str) or value not in INSTRUMENTS:
        raise InvalidPreferences("instrumento no permitido")
    return value


# Lo que hoy el reproductor guarda en cada navegador (`acordia-*`).
# Un campo nuevo se agrega aquí, con su validación.
FIELDS: dict[str, Callable[[object], object]] = {
    "muted": _flag,
    "countIn": _flag,
    "instrument": _instrument,
    "studyMode": _slug,
    "theme": _slug,
    "volMetronome": _unit,
}


def clean_preferences(raw: object) -> dict:
    """Solo campos conocidos y válidos; lo demás es un error, no se descarta en silencio."""
    if not isinstance(raw, dict):
        raise InvalidPreferences("se esperaba un objeto")
    unknown = sorted(str(key) for key in raw if key not in FIELDS)
    if unknown:
        raise InvalidPreferences(f"campos desconocidos: {', '.join(unknown)[:80]}")
    return {key: FIELDS[key](value) for key, value in raw.items()}


class TokenVerifier(Protocol):
    def verify(self, token: str) -> str | None:
        """El UID de una persona del grupo público, o `None`."""
        ...


class UserStore(Protocol):
    def get(self, uid: str) -> dict: ...

    def put(self, uid: str, preferences: dict) -> None: ...

    def get_consent(self, uid: str) -> str | None:
        """La versión del aviso que la persona aceptó, o `None`."""
        ...

    def put_consent(self, uid: str, version: str) -> None: ...


def uid_from_claims(claims: dict) -> str | None:
    """El UID de un token ya verificado, o `None` si no es de una persona del grupo público."""
    firebase = claims.get("firebase")
    if not isinstance(firebase, dict) or firebase.get("tenant"):
        return None  # un token del tenant del equipo pasa la verificación del proyecto: aquí no
    if firebase.get("sign_in_provider") not in PUBLIC_PROVIDERS:
        return None
    uid = claims.get("uid")
    return uid if isinstance(uid, str) and UID.fullmatch(uid) else None


class FirebaseApp:
    """La app de Firebase, creada en la primera petición (no encarece el arranque en frío)."""

    def __init__(self, project: str) -> None:
        self._project = project
        self._app: object | None = None
        self._lock = threading.Lock()

    def get(self) -> object:
        with self._lock:
            if self._app is None:
                import firebase_admin

                try:
                    self._app = firebase_admin.get_app()
                except ValueError:
                    self._app = firebase_admin.initialize_app(options={"projectId": self._project})
            return self._app


class FirebaseTokenVerifier:
    def __init__(self, app: FirebaseApp) -> None:
        self._app = app

    def verify(self, token: str) -> str | None:
        try:
            from firebase_admin import auth

            claims = auth.verify_id_token(token, app=self._app.get())
        except Exception:  # noqa: BLE001 - vencido, mal firmado o de otro proyecto: todo es "no"
            return None
        return uid_from_claims(claims)


class FirestoreUserStore:
    """`users/{uid}` con un mapa `preferences`. Leer no crea nada: el documento nace al escribir."""

    def __init__(self, app: FirebaseApp) -> None:
        self._app = app
        self._db: object | None = None

    def _client(self) -> object:
        if self._db is None:
            from firebase_admin import firestore

            self._db = firestore.client(app=self._app.get())
        return self._db

    def get(self, uid: str) -> dict:
        snapshot = self._client().collection("users").document(uid).get()
        data = snapshot.to_dict() if snapshot.exists else None
        found = (data or {}).get("preferences")
        return clean_preferences(found) if isinstance(found, dict) else {}

    def put(self, uid: str, preferences: dict) -> None:
        from firebase_admin import firestore

        self._client().collection("users").document(uid).set(
            {"preferences": preferences, "updatedAt": firestore.firestore.SERVER_TIMESTAMP},
            merge=True,
        )

    def get_consent(self, uid: str) -> str | None:
        snapshot = self._client().collection("users").document(uid).get()
        consent = ((snapshot.to_dict() if snapshot.exists else None) or {}).get("consent")
        version = consent.get("version") if isinstance(consent, dict) else None
        return version if isinstance(version, str) and VERSION.fullmatch(version) else None

    def put_consent(self, uid: str, version: str) -> None:
        from firebase_admin import firestore

        # La hora la pone Firestore, no el navegador. `adult` es la casilla de 14 años o más (C27):
        # no se guarda la fecha de nacimiento.
        self._client().collection("users").document(uid).set(
            {
                "consent": {
                    "version": version,
                    "adult": True,
                    "at": firestore.firestore.SERVER_TIMESTAMP,
                }
            },
            merge=True,
        )


class RateLimiter:
    """Ventana deslizante por persona, en la memoria de la instancia: frena el abuso."""

    def __init__(
        self,
        limit: int = RATE_LIMIT,
        window: float = RATE_WINDOW_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit, self._window, self._clock = limit, window, clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, who: str) -> bool:
        now = self._clock()
        with self._lock:
            hits = (
                self._hits.pop(who, None) or deque()
            )  # se reinserta al final: las más antiguas quedan primero
            while hits and now - hits[0] >= self._window:
                hits.popleft()
            allowed = len(hits) < self._limit
            if allowed:
                hits.append(now)
            if hits:
                self._hits[who] = hits
            while len(self._hits) > MAX_TRACKED_PEOPLE:
                self._hits.pop(next(iter(self._hits)))
            return allowed


@dataclass
class Accounts:
    verifier: TokenVerifier
    store: UserStore
    limiter: RateLimiter


def clean_consent(raw: object) -> str:
    """Cuerpo de `PUT /api/me/consent`: solo `version` (la vigente) y `adult` en verdadero."""
    if not isinstance(raw, dict) or set(raw) != {"version", "adult"}:
        raise InvalidPreferences("cuerpo inválido")
    if raw["adult"] is not True:
        raise InvalidPreferences("hay que tener 14 años o más")
    if raw["version"] != NOTICE_VERSION:
        raise InvalidPreferences("versión del aviso no vigente")
    return NOTICE_VERSION


def parse_body(raw: bytes) -> object:
    if len(raw) > MAX_BODY_BYTES:
        raise InvalidPreferences("demasiado grande")
    try:
        return json.loads(raw)
    except ValueError as error:
        raise InvalidPreferences("no es JSON") from error


def accounts_from_env(environ: dict[str, str]) -> Accounts | None:
    """Sin `FIREBASE_PROJECT_ID` no hay cuentas (la API da 404). No toca Firebase al arrancar."""
    project = environ.get("FIREBASE_PROJECT_ID", "").strip()
    if not project:
        return None
    app = FirebaseApp(project)
    return Accounts(FirebaseTokenVerifier(app), FirestoreUserStore(app), RateLimiter())
