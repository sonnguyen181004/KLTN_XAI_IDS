"""Local-only authenticated control plane, separate from prediction endpoints."""
import hmac
from ipaddress import ip_address
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from capture_registry import CaptureConflict


class StartCapture(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str = Field(min_length=1, max_length=128)
    interface: str = Field(min_length=1, max_length=256)


class SessionCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    run_id: str = Field(pattern=r'^[0-9a-f]{32}$')


def local_host(host):
    if host == 'localhost':
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def control_router(get_supervisor, token):
    def authorize(request: Request):
        if not token or len(token) < 32:
            raise HTTPException(503, 'Capture control disabled: configure shared local token')
        host = urlsplit('http://'+request.headers.get('host', '')).hostname
        if (not request.client or not local_host(request.client.host) or not local_host(host) or
                request.headers.get('origin') or request.headers.get('sec-fetch-site') == 'cross-site'):
            raise HTTPException(403, 'Local server-side control only; browser-origin calls refused')
        supplied = request.headers.get('x-ids-control-token', '')
        if not hmac.compare_digest(supplied.encode(), token.encode()):
            raise HTTPException(403, 'Invalid capture control token')
        supervisor = get_supervisor()
        if supervisor is None:
            raise HTTPException(503, 'Capture supervisor unavailable; check API log/ownership')
        return supervisor

    router = APIRouter(prefix='/capture', dependencies=[])

    def invoke(fn, *args):
        try:
            return fn(*args)
        except CaptureConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(404, 'Unknown capture session') from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except OSError as exc:
            raise HTTPException(503, 'Capture storage/process unavailable') from exc

    @router.get('/status')
    def status(supervisor=Depends(authorize)):
        return invoke(supervisor.status)

    @router.post('/start')
    def start(body: StartCapture, supervisor=Depends(authorize)):
        return invoke(supervisor.start, body.request_id, body.interface)

    @router.post('/stop')
    def stop(body: SessionCommand, supervisor=Depends(authorize)):
        return invoke(supervisor.stop, body.run_id)

    @router.post('/reconcile')
    def reconcile(body: SessionCommand, supervisor=Depends(authorize)):
        return invoke(supervisor.reconcile, body.run_id)

    return router
