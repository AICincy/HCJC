#!/usr/bin/env python3
"""AAI Trusted Runtime Controller reference implementation.

Design target:
- Model/agent is untrusted.
- Controller is a separate process.
- Consequential effects are executable only through controller-owned adapters.
- Grants are signed by an external issuer.
- Controller revalidates exact action, scope, state, policy, schema/skill identity,
  provider capability, expiry, revocation, and replay state at commit.
- Every decision receives a hash-chained, Ed25519-signed receipt.

This is a reference monitor and test harness. Presence of the controller is not evidence that the target runtime has activated it or made it the mandatory effect boundary.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import socket
import json
import os
import secrets
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: bytes | str | Mapping[str, Any]) -> str:
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = canonical_json(value)
    return hashlib.sha256(data).hexdigest()


def b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign(private_key: Ed25519PrivateKey, payload: bytes) -> str:
    return b64e(private_key.sign(payload))


def verify(public_key: Ed25519PublicKey, payload: bytes, signature: str) -> None:
    public_key.verify(b64d(signature), payload)


@dataclass(frozen=True)
class ControllerConfig:
    root: Path
    issuer_public_key: Path
    controller_private_key: Path
    policy_file: Path
    receipts_file: Path
    status_file: Path

    @classmethod
    def from_root(cls, root: Path) -> "ControllerConfig":
        state = root / "state"
        return cls(
            root=root,
            issuer_public_key=root / "keys" / "issuer-public.pem",
            controller_private_key=root / "keys" / "controller-private.pem",
            policy_file=state / "policy.json",
            receipts_file=state / "receipts.jsonl",
            status_file=state / "status.json",
        )


def ensure_dirs(cfg: ControllerConfig) -> None:
    (cfg.root / "keys").mkdir(parents=True, exist_ok=True)
    (cfg.root / "state").mkdir(parents=True, exist_ok=True)
    (cfg.root / "effects").mkdir(parents=True, exist_ok=True)


def load_private(path: Path) -> Ed25519PrivateKey:
    raw = path.read_bytes()
    return serialization.load_pem_private_key(raw, password=None)


def load_public(path: Path) -> Ed25519PublicKey:
    raw = path.read_bytes()
    return serialization.load_pem_public_key(raw)


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp-" + secrets.token_hex(6))
    tmp.write_bytes(data)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def init_controller(root: Path) -> None:
    cfg = ControllerConfig.from_root(root)
    ensure_dirs(cfg)
    if not cfg.controller_private_key.exists():
        key = Ed25519PrivateKey.generate()
        pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        atomic_write(cfg.controller_private_key, pem, 0o600)
        pub = key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        atomic_write(root / "keys" / "controller-public.pem", pub, 0o644)
    if not cfg.issuer_public_key.exists():
        # An explicit test issuer key must be supplied. Generate one for the
        # harness only, so production deployment must replace it with the
        # external issuer's public key.
        key = Ed25519PrivateKey.generate()
        pub = key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        atomic_write(cfg.issuer_public_key, pub, 0o644)
        atomic_write(root / "keys" / "TEST-issuer-private.pem", key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ), 0o600)
    if not cfg.policy_file.exists():
        policy = {
            "policy_id": "AAI-TRUSTED-RUNTIME",
            "policy_epoch": 1,
            "environment": "test",
            "allowed_skills": {},
            "allowed_schemas": {},
            "revoked_grants": [],
            "provider_capabilities": {"mock-target": True},
        }
        atomic_write(cfg.policy_file, canonical_json(policy) + b"\n")
    if not cfg.receipts_file.exists():
        cfg.receipts_file.touch(mode=0o600)
    save_status(cfg, {
        "controller_id": sha256_hex(cfg.controller_private_key.read_bytes())[:24],
        "controller_version": "0.4.0-reference",
        "status": "INITIALIZED",
        "policy_epoch": load_policy(cfg)["policy_epoch"],
        "updated_at": time.time(),
    })


def load_policy(cfg: ControllerConfig) -> dict[str, Any]:
    return json.loads(cfg.policy_file.read_text(encoding="utf-8"))


def save_status(cfg: ControllerConfig, status: dict[str, Any]) -> None:
    atomic_write(cfg.status_file, canonical_json(status) + b"\n")


def package_gate(skill_dir: Path, expected_name: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    if not skill_dir.is_dir():
        errors.append("SKILL_DIRECTORY_MISSING")
        return {"status": "FAIL", "errors": errors}
    skill = skill_dir / "SKILL.md"
    if not skill.exists():
        errors.append("SKILL_MD_MISSING")
    text = skill.read_text(encoding="utf-8") if skill.exists() else ""
    front = {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                if ":" in line and not line.startswith(" "):
                    k, v = line.split(":", 1)
                    front[k.strip()] = v.strip().strip('"')
    if expected_name and front.get("name") != expected_name:
        errors.append("SKILL_NAME_MISMATCH")
    if "description" not in front:
        errors.append("DESCRIPTION_MISSING")
    digest = sha256_hex(text.encode("utf-8")) if skill.exists() else None
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "skill_name": front.get("name"),
        "skill_sha256": digest,
        "skill_path": str(skill.resolve()),
    }


def canonical_action(action: Mapping[str, Any]) -> dict[str, Any]:
    # Strip only transport metadata. Security-relevant content is immutable.
    allowed = {
        "operation", "resource_scope", "environment", "skill_id", "skill_hash",
        "schema_id", "schema_hash", "parameters", "provider", "target_version",
        "request_id"
    }
    return {k: action[k] for k in sorted(action) if k in allowed}


def validate_grant(cfg: ControllerConfig, grant: Mapping[str, Any], action: Mapping[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    policy = load_policy(cfg)
    try:
        issuer = load_public(cfg.issuer_public_key)
        sig = str(grant["signature"])
        unsigned = dict(grant)
        unsigned.pop("signature", None)
        verify(issuer, canonical_json(unsigned), sig)
    except Exception:
        return False, "INVALID_GRANT_SIGNATURE", policy

    now = time.time()
    if grant.get("status") != "VALID":
        return False, "GRANT_NOT_VALID", policy
    if grant.get("issuer") != grant.get("issuer_id", grant.get("issuer")):
        # The issuer name itself is advisory, but keep schema deterministic.
        pass
    if now < float(grant.get("issued_at", 0)) or now > float(grant.get("expires_at", 0)):
        return False, "GRANT_EXPIRED_OR_NOT_YET_VALID", policy
    if grant.get("grant_id") in policy.get("revoked_grants", []):
        return False, "GRANT_REVOKED", policy
    if grant.get("policy_epoch") != policy.get("policy_epoch"):
        return False, "POLICY_EPOCH_DRIFT", policy
    if grant.get("environment") != action.get("environment"):
        return False, "ENVIRONMENT_MISMATCH", policy
    if grant.get("operation") != action.get("operation"):
        return False, "OPERATION_MISMATCH", policy
    if grant.get("resource_scope") != action.get("resource_scope"):
        return False, "RESOURCE_SCOPE_MISMATCH", policy
    if grant.get("skill_id") != action.get("skill_id"):
        return False, "SKILL_ID_MISMATCH", policy
    if grant.get("skill_hash") != action.get("skill_hash"):
        return False, "SKILL_HASH_MISMATCH", policy
    if grant.get("schema_id") != action.get("schema_id"):
        return False, "SCHEMA_ID_MISMATCH", policy
    if grant.get("schema_hash") != action.get("schema_hash"):
        return False, "SCHEMA_HASH_MISMATCH", policy
    canonical = canonical_action(action)
    action_hash = sha256_hex(canonical)
    if grant.get("scope_hash") != action_hash:
        return False, "ACTION_HASH_MISMATCH", policy
    prov = action.get("parameters", {}).get("provenance")
    if grant.get("parameter_provenance") != prov:
        return False, "PARAMETER_PROVENANCE_MISMATCH", policy
    if not policy.get("provider_capabilities", {}).get(action.get("provider"), False):
        return False, "PROVIDER_CAPABILITY_INSUFFICIENT", policy
    used = set(policy.get("consumed_nonces", []))
    if grant.get("nonce") in used:
        return False, "NONCE_REPLAY", policy
    return True, "VERIFIED_AND_PERMITTED", policy


def append_receipt(cfg: ControllerConfig, result: Mapping[str, Any]) -> dict[str, Any]:
    controller_key = load_private(cfg.controller_private_key)
    prev = "GENESIS"
    if cfg.receipts_file.exists():
        lines = [x for x in cfg.receipts_file.read_text(encoding="utf-8").splitlines() if x.strip()]
        if lines:
            prev = json.loads(lines[-1])["receipt_hash"]
    body = {
        **result,
        "previous_receipt_hash": prev,
        "timestamp": time.time(),
    }
    body["receipt_hash"] = sha256_hex(canonical_json(body))
    body["controller_signature"] = sign(controller_key, canonical_json(body))
    with cfg.receipts_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n")
    return body


def consume_nonce(cfg: ControllerConfig, nonce: str) -> None:
    policy = load_policy(cfg)
    used = set(policy.setdefault("consumed_nonces", []))
    used.add(nonce)
    policy["consumed_nonces"] = sorted(used)
    atomic_write(cfg.policy_file, canonical_json(policy) + b"\n")


def revoke(cfg: ControllerConfig, grant_id: str) -> None:
    policy = load_policy(cfg)
    revoked = set(policy.setdefault("revoked_grants", []))
    revoked.add(grant_id)
    policy["revoked_grants"] = sorted(revoked)
    policy["policy_epoch"] += 1
    atomic_write(cfg.policy_file, canonical_json(policy) + b"\n")


def execute_mock(cfg: ControllerConfig, grant: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, Any]:
    ok, reason, policy = validate_grant(cfg, grant, action)
    if not ok:
        receipt = append_receipt(cfg, {
            "decision": "DENY",
            "verification_result": "REJECTED",
            "verification_reason": reason,
            "grant_id": grant.get("grant_id"),
            "operation": action.get("operation"),
            "resource_scope": action.get("resource_scope"),
            "scope_hash": grant.get("scope_hash"),
            "policy_epoch": policy.get("policy_epoch"),
            "execution_result": "NOT_EXECUTED",
        })
        return {"decision": "DENY", "reason": reason, "receipt": receipt}

    # Live-state check. The target version must be supplied and match the
    # expected version snapshot carried in the grant.
    target = cfg.root / "effects" / "mock-target.json"
    current = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {"version": 1, "value": None}
    if grant.get("target_version") != current.get("version"):
        receipt = append_receipt(cfg, {
            "decision": "DENY",
            "verification_result": "REJECTED",
            "verification_reason": "TARGET_STATE_DRIFT",
            "grant_id": grant.get("grant_id"),
            "operation": action.get("operation"),
            "resource_scope": action.get("resource_scope"),
            "scope_hash": grant.get("scope_hash"),
            "policy_epoch": policy.get("policy_epoch"),
            "execution_result": "NOT_EXECUTED",
        })
        return {"decision": "DENY", "reason": "TARGET_STATE_DRIFT", "receipt": receipt}

    params = action.get("parameters", {})
    new_value = params.get("value")
    new_version = int(current.get("version", 0)) + 1
    atomic_write(target, canonical_json({"version": new_version, "value": new_value}) + b"\n")
    consume_nonce(cfg, str(grant["nonce"]))
    receipt = append_receipt(cfg, {
        "decision": "ALLOW",
        "verification_result": "VERIFIED_AND_PERMITTED",
        "verification_reason": "EXACT_GRANT_AND_LIVE_STATE_MATCH",
        "grant_id": grant.get("grant_id"),
        "operation": action.get("operation"),
        "resource_scope": action.get("resource_scope"),
        "scope_hash": grant.get("scope_hash"),
        "policy_epoch": policy.get("policy_epoch"),
        "execution_result": "COMMITTED",
        "target_version_before": current.get("version"),
        "target_version_after": new_version,
    })
    return {"decision": "ALLOW", "reason": "VERIFIED_AND_PERMITTED", "receipt": receipt}



def dispatch_request(cfg: ControllerConfig, req: Mapping[str, Any]) -> dict[str, Any]:
    method = req.get("method")
    if method == "status":
        return status(cfg)
    if method == "execute-mock":
        return execute_mock(cfg, req["grant"], req["action"])
    if method == "revoke":
        revoke(cfg, str(req["grant_id"]))
        return {"status": "REVOKED", "grant_id": req["grant_id"], "policy_epoch": load_policy(cfg)["policy_epoch"]}
    return {"decision": "DENY", "reason": "UNKNOWN_CONTROLLER_METHOD"}


def serve_socket(cfg: ControllerConfig, socket_path: Path, socket_group: str | None = None) -> None:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        socket_path.unlink()
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(socket_path))
    os.chmod(socket_path, 0o660)
    if socket_group:
        import grp
        os.chown(socket_path, os.getuid(), grp.getgrnam(socket_group).gr_gid)
    srv.listen(32)
    while True:
        conn, _ = srv.accept()
        with conn:
            buf = b""
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    if not raw.strip():
                        continue
                    try:
                        req = json.loads(raw.decode("utf-8"))
                        out = dispatch_request(cfg, req)
                    except Exception as exc:
                        out = {"decision": "DENY", "reason": "CONTROLLER_INTERNAL_ERROR", "error": str(exc)}
                    conn.sendall(canonical_json(out) + b"\n")


def request_socket(socket_path: Path, request: Mapping[str, Any]) -> dict[str, Any]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(str(socket_path))
        client.sendall(canonical_json(request) + b"\n")
        data = b""
        while b"\n" not in data:
            chunk = client.recv(65536)
            if not chunk:
                break
            data += chunk
    return json.loads(data.split(b"\n", 1)[0].decode("utf-8"))


def status(cfg: ControllerConfig) -> dict[str, Any]:
    policy = load_policy(cfg)
    out = {
        "controller_present": cfg.controller_private_key.exists(),
        "controller_id": sha256_hex(cfg.controller_private_key.read_bytes())[:24] if cfg.controller_private_key.exists() else None,
        "issuer_verifier_present": cfg.issuer_public_key.exists(),
        "policy_epoch": policy.get("policy_epoch"),
        "status_path": str(cfg.status_file),
        "receipts_path": str(cfg.receipts_file),
        "trust_established": False,
        "note": "Controller presence is not trust evidence. Trust requires protected keys, mandatory effect mediation, and effect exclusivity at deployment time.",
    }
    save_status(cfg, out | {"updated_at": time.time()})
    return out


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    st = sub.add_parser("status")
    st.add_argument("--skill-dir")
    ss = sub.add_parser("serve")
    ss.add_argument("--socket", default=None)
    ss.add_argument("--socket-group", default=None)
    rq = sub.add_parser("request")
    rq.add_argument("--socket", required=True)
    rq.add_argument("request_json")
    pg = sub.add_parser("package-gate")
    pg.add_argument("skill_dir")
    pg.add_argument("--name")
    rg = sub.add_parser("revoke")
    rg.add_argument("grant_id")
    ex = sub.add_parser("execute-mock")
    ex.add_argument("grant_json")
    ex.add_argument("action_json")
    args = p.parse_args(argv)
    cfg = ControllerConfig.from_root(Path(args.root).resolve())
    if args.cmd == "init":
        init_controller(cfg.root)
        print(json.dumps(status(cfg), indent=2))
        return 0
    if not cfg.policy_file.exists():
        print("CONTROLLER_NOT_INITIALIZED", file=sys.stderr)
        return 2
    if args.cmd == "status":
        out=status(cfg)
        if args.skill_dir:
            out["install_check"]=package_gate(Path(args.skill_dir).resolve(), "aai-cognitive-interface")
        print(json.dumps(out, indent=2))
        return 0
    if args.cmd == "serve":
        sock=Path(args.socket) if args.socket else cfg.root/"controller.sock"
        serve_socket(cfg, sock, args.socket_group)
        return 0
    if args.cmd == "request":
        req=json.loads(Path(args.request_json).read_text(encoding="utf-8"))
        print(json.dumps(request_socket(Path(args.socket), req), indent=2))
        return 0
    if args.cmd == "package-gate":
        print(json.dumps(package_gate(Path(args.skill_dir).resolve(), args.name), indent=2))
        return 0
    if args.cmd == "revoke":
        revoke(cfg, args.grant_id)
        print(json.dumps({"status": "REVOKED", "grant_id": args.grant_id, "policy_epoch": load_policy(cfg)["policy_epoch"]}, indent=2))
        return 0
    if args.cmd == "execute-mock":
        grant = json.loads(Path(args.grant_json).read_text(encoding="utf-8"))
        action = json.loads(Path(args.action_json).read_text(encoding="utf-8"))
        print(json.dumps(execute_mock(cfg, grant, action), indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
