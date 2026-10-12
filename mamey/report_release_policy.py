"""Reader-facing policy provenance; never permission to transfer an artifact."""
from pathlib import Path
import hashlib
import json
from .release_policy import resolve_package_privacy_records, POLICY_VERSION

ROW_KEYS = ("release", "recorded_release", "privacy_assignment_state", "privacy_reason",
            "release_reason", "authority_sha256", "release_decision_sha256", "release_decision_json")

def _canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"))
def _digest(value): return hashlib.sha256(_canonical(value).encode()).hexdigest()

def _valid_decision(decision, policy):
    if not isinstance(decision, dict): return False
    state = decision.get("assignment_state")
    authority = decision.get("authority_sha256")
    if (not isinstance(state, str) or state not in {"DEFAULT", "EXPLICIT", "EXACT"}
            or not isinstance(authority, str)
            or (authority and (len(authority) != 64 or any(c not in "0123456789abcdef" for c in authority)))
            or not isinstance(decision.get("reason"), str) or not decision["reason"]
            or decision.get("strain_id") != policy["strain_id"]
            or decision.get("release") != policy["recorded_release"]
            or not isinstance(decision.get("refused"), bool)
            or decision.get("policy_version") != POLICY_VERSION):
        return False
    if decision["release"] == "PUBLIC":
        return ((decision["reason"] == "operator_public_override" and state == "EXPLICIT")
                or (decision["reason"] == "exact_public_assignment" and state == "EXACT" and bool(authority)))
    return True

def policy_for_records(records, fallback_id, *, unreadable=False):
    policy = resolve_package_privacy_records(records, fallback_id, unreadable=unreadable)
    policy.update(release_reason=policy["privacy_reason"], release_decision_sha256="",
                  release_decision_json="", policy_source="recorded metadata; not transfer authorization")
    decisions = [r["release_decision"] for r in records if r.get("release_decision") is not None]
    if decisions:
        unique = {_canonical(d) for d in decisions}
        valid = all(_valid_decision(d, policy) for d in decisions)
        if len(unique) != 1 or not valid:
            reason = policy["privacy_reason"] if policy["privacy_assignment_state"] == "HOLD" else "release_decision_conflict"
            policy.update(effective_release="PRIVATE", privacy_assignment_state="HOLD",
                          privacy_reason=reason, release_reason=reason)
        else:
            decision = decisions[0]
            policy.update(release_reason=str(decision.get("reason") or "not recorded"),
                          authority_sha256=str(decision.get("authority_sha256") or ""),
                          release_decision_sha256=_digest(decision), release_decision_json=_canonical(decision))
            if decision["refused"]:
                policy.update(effective_release="PRIVATE", privacy_assignment_state="REFUSED",
                              privacy_reason=policy["release_reason"])
    return policy

def policy_for_run(run):
    context = run.context
    decision = getattr(context, "release_decision", None)
    record = {"strain_id": context.strain_id}
    if decision is not None:
        record.update(release=decision.release, release_decision=decision.to_dict())
    records = [record] + [{"strain_id": context.strain_id, "release": getattr(b, "release", None)}
                          for b in run.bgcs]
    policy = policy_for_records(records, context.strain_id)
    if decision is None:
        policy.update(effective_release="PRIVATE", privacy_assignment_state="HOLD",
                      privacy_reason="run_decision_not_recorded", release_reason="run_decision_not_recorded")
    policy["policy_source"] = "run_context.release_decision and per-BGC release"
    policy["project_privacy_tier"] = str(getattr(context, "project_privacy_tier", "UNDECLARED"))
    return policy

def policy_for_package(package, fallback_id):
    package = Path(package)
    records, bindings, unreadable = [], {}, False
    sources = [package / "manifest.json", package / "manifest_short.json"]
    sources += sorted(package.glob("*_1_intake.json"))
    for path in sources:
        if not path.exists(): continue
        try:
            data = path.read_bytes()
            value = json.loads(data)
            if not isinstance(value, dict): raise ValueError("not an object")
            records.append(value)
            projection = {key: value.get(key) for key in ("strain_id", "release", "release_decision")}
            if "bgcs" in value:
                if not isinstance(value["bgcs"], list): raise ValueError("BGC metadata not a list")
                projection["bgcs"] = []
                for bgc in value["bgcs"]:
                    if not isinstance(bgc, dict) or bgc.get("release") not in ("PRIVATE", "PUBLIC"):
                        raise ValueError("BGC release not recorded")
                    projection["bgcs"].append({"bgc_id": bgc.get("bgc_id"), "release": bgc["release"]})
                    records.append({"strain_id": value.get("strain_id"), "release": bgc["release"]})
            bindings[path.name] = {"policy_fields_sha256": _digest(projection)}
        except (OSError, ValueError): unreadable = True
    policy = policy_for_records(records, fallback_id, unreadable=unreadable)
    policy["policy_source"] = _canonical(bindings) if bindings else "metadata not recorded"
    return policy

def row_policy(policy):
    return {key: policy["effective_release"] if key == "release" else policy.get(key, "") for key in ROW_KEYS}

def policy_for_master_rows(rows):
    groups, held_rows = {}, False
    for row in rows:
        strain = str(row.get("strain") or "")
        if not strain:
            held_rows = True
            continue
        record = {"strain_id": strain, "release": row.get("release")}
        encoded = row.get("release_decision_json")
        if encoded:
            try: record["release_decision"] = json.loads(encoded)
            except (TypeError, ValueError): held_rows = True
        if row.get("privacy_assignment_state") in ("HOLD", "REFUSED"): held_rows = True
        # Authority belongs to each source row; a newer row cannot clear a legacy row.
        if policy_for_records([record], strain)["effective_release"] != "PUBLIC":
            held_rows = True
        groups.setdefault(strain, []).append(record)
    policies = {strain: policy_for_records(records, strain) for strain, records in groups.items()}
    public = bool(policies) and not held_rows and all(p["effective_release"] == "PUBLIC" for p in policies.values())
    result = {"strain_id": "MASTER_SCOPE", "recorded_release": "MIXED_OR_UNRECORDED",
              "effective_release": "PUBLIC" if public else "PRIVATE",
              "privacy_assignment_state": "RECORDED" if public else "HOLD",
              "privacy_reason": "all_master_records_admitted" if public else "master_scope_private_or_unresolved",
              "release_reason": "conservative whole-master derivative policy",
              "authority_sha256": "", "release_decision_sha256": "", "release_decision_json": "",
              "policy_source": _canonical(policies)}
    return result

def describe_policy(policy):
    authority = policy["authority_sha256"] or "not recorded (operator/default or unresolved authority)"
    decision = policy["release_decision_sha256"] or "not recorded"
    return (f"Release policy: {policy['effective_release']}; recorded: {policy['recorded_release']}; "
            f"state: {policy['privacy_assignment_state']}; reason: {policy['release_reason']}; "
            f"admission: {policy['privacy_reason']}; authority SHA-256: {authority}; "
            f"decision SHA-256: {decision}; provenance: {policy['policy_source']}. "
            "Recorded policy is not transfer authorization.")

def guidance(policy, strain):
    return (describe_policy(policy) + " Review the package locally. For Sapote judgment, use the validated "
            f"local package for {strain} and the selected authoring contract. Transfer requires a separate "
            "decision under the applicable project privacy policy.")
