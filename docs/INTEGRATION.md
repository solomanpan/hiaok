# Integrating your own services with hiaok

hiaok signs users in and decides what they may do. Your business services receive the user's token and need two answers: **who is this?** and **may they do this?**

## 1. The front end signs in with hiaok

```
POST /v1/api/hiaok/auth/login
{"requestId": "<id>", "reqInfo": {"orgUuid": "...", "tenantUuid": "...", "username": "...", "password": "...",
                                  "captchaId": "...", "captchaCode": "..."}}
→ {"code": 0, "resultInfo": {"accessToken": "<token>", "expiresIn": 7200, "userUuid": "..."}}
```

It then calls your services with `Authorization: Bearer <token>`. The token is opaque (not a JWT): only hiaok can resolve it.

## 2. Your service asks hiaok who the caller is

```
POST /v1/api/hiaok/auth/me        Authorization: Bearer <token>
{"requestId": "<id>", "reqInfo": {}}
→ {"code": 0, "resultInfo": {"userUuid": "...", "orgUuid": "...", "tenantUuid": "...",
                             "roleCodes": ["ORG_ADMIN"], "permissionCodes": ["order:*", "report:list"],
                             "menus": [...]}}
→ {"code": 401, ...}   unknown, expired or revoked token, or a disabled user
```

The envelope's HTTP status is 200 in both cases; read `code`.

## 3. Your service checks the permission code

Use the same rule as hiaok's guards: `<resource>:<action>` is granted by itself, by `<resource>:*` or by `*`. Create the codes your service needs as permissions in hiaok (e.g. `order:add`, `order:refund`) and grant them to roles; they do not have to be hiaok endpoints.

## Python (FastAPI)

```python
import hashlib
import time
import uuid

import httpx
from fastapi import Depends, Header, HTTPException

HIAOK = "http://hiaok:8000/v1/api/hiaok"
CACHE_SECONDS = 30  # how long a revoked token or a changed permission may still be honoured here
_cache: dict[str, tuple[float, dict]] = {}
_client = httpx.AsyncClient(timeout=3)


async def principal(authorization: str = Header(default="")) -> dict:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401)
    key = hashlib.sha256(token.encode()).hexdigest()
    hit = _cache.get(key)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    reply = (
        await _client.post(
            f"{HIAOK}/auth/me",
            json={"requestId": uuid.uuid4().hex, "reqInfo": {}},
            headers={"authorization": f"Bearer {token}"},
        )
    ).json()
    if reply.get("code") != 0:
        raise HTTPException(401)
    _cache[key] = (time.monotonic() + CACHE_SECONDS, reply["resultInfo"])
    return reply["resultInfo"]


def granted(codes: list[str], required: str) -> bool:
    resource = required.partition(":")[0]
    return any(c in (required, f"{resource}:*", "*") for c in codes)


def require(code: str):
    async def check(p: dict = Depends(principal)) -> dict:
        if not granted(p["permissionCodes"], code):
            raise HTTPException(403, f"needs {code}")
        return p

    return check


# @app.post("/orders/refund")
# async def refund(p: dict = Depends(require("order:refund"))): ...
```

## Node.js (Express)

```js
import crypto from 'node:crypto';

const HIAOK = 'http://hiaok:8000/v1/api/hiaok';
const CACHE_MS = 30_000;
const cache = new Map();

export async function principal(req, res, next) {
  const [scheme, token] = (req.headers.authorization ?? '').split(' ');
  if (scheme?.toLowerCase() !== 'bearer' || !token) return res.sendStatus(401);
  const key = crypto.createHash('sha256').update(token).digest('hex');
  const hit = cache.get(key);
  if (hit && hit.until > Date.now()) { req.principal = hit.value; return next(); }
  const reply = await fetch(`${HIAOK}/auth/me`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${token}` },
    body: JSON.stringify({ requestId: crypto.randomUUID().replaceAll('-', ''), reqInfo: {} }),
  }).then((r) => r.json());
  if (reply.code !== 0) return res.sendStatus(401);
  cache.set(key, { until: Date.now() + CACHE_MS, value: reply.resultInfo });
  req.principal = reply.resultInfo;
  next();
}

const granted = (codes, required) => {
  const resource = required.split(':')[0];
  return codes.some((c) => c === required || c === `${resource}:*` || c === '*');
};

export const require = (code) => (req, res, next) =>
  granted(req.principal.permissionCodes, code) ? next() : res.status(403).send(`needs ${code}`);

// app.post('/orders/refund', principal, require('order:refund'), handler);
```

## Choices to make

- **Cache time.** Without a cache every request costs one call to hiaok; with one, a revoked token or a removed permission is still honoured for up to the cache time. 15–60 s is a common middle ground. hiaok itself applies changes at once.
- **Organization scope.** `orgUuid` in the principal is the caller's organization; check it against the data you serve if your service holds several organizations' data. hiaok does not do row-level (data) permissions — scope rows in your service.
- **Availability.** hiaok is on the request path of every service that does this; run it with Redis and more than one instance (see [DEPLOYMENT.md](DEPLOYMENT.md)).
- **Offline verification.** If calling hiaok per request (even cached) is not acceptable, you need short-lived signed tokens (JWT / JWKS). hiaok does not issue them today; it is listed under non-goals in the README.
