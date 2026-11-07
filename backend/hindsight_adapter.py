"""Hindsight memory adapter supporting Cloud, Local Docker, and In-Memory fallback."""

from datetime import datetime, timezone
import os
import re
from typing import Any, Dict, List, Literal, Optional, Set, Union
import uuid
import httpx

from backend.config import (
    get_hindsight_api_key,
    get_hindsight_base_url,
    is_decision_model_enabled,
    is_decision_prune_enabled,
)

# Optional hindsight-client import; fallback to httpx REST if not present
try:
    from hindsight_client import Hindsight as HindsightSDKClient
    HINDSIGHT_CLIENT_AVAILABLE = True
except ImportError:
    HindsightSDKClient = None  # type: ignore
    HINDSIGHT_CLIENT_AVAILABLE = False


class RecallHit(dict):
    """Result hit from recall supporting both dictionary and attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'RecallHit' has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class ReflectResult(dict):
    """Result from reflect supporting both dictionary and attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'ReflectResult' has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class HindsightAdapter:
    """
    Adapter for Hindsight memory operations.

    Backend selection order:
    1. Cloud when HINDSIGHT_API_KEY is present
    2. Local Docker when http://localhost:8888 answers
    3. In-memory fallback implementing identical retain/recall/reflect semantics
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        bank_id: str = "claimshield-india",
        decision_model_enabled: Optional[bool] = None,
        enable_decision_prune: Optional[bool] = None,
    ) -> None:
        self._explicit_api_key = api_key
        self._explicit_base_url = base_url
        self.bank_id = bank_id
        self._decision_model_enabled = (
            decision_model_enabled
            if decision_model_enabled is not None
            else is_decision_model_enabled()
        )
        self._enable_decision_prune = (
            enable_decision_prune
            if enable_decision_prune is not None
            else is_decision_prune_enabled()
        )

        # In-memory storage structures
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._observations: Dict[str, Dict[str, Any]] = {}
        self._scope_to_obs: Dict[str, str] = {}

    @property
    def api_key(self) -> str:
        if self._explicit_api_key is not None:
            return self._explicit_api_key
        return get_hindsight_api_key()

    @property
    def base_url(self) -> str:
        if self._explicit_base_url is not None:
            return self._explicit_base_url
        return get_hindsight_base_url()

    @property
    def decision_model_enabled(self) -> bool:
        return self._decision_model_enabled

    @property
    def enable_decision_prune(self) -> bool:
        return self._enable_decision_prune

    def _probe_local_docker(self) -> bool:
        """Check if local Docker daemon at http://localhost:8888 is reachable."""
        try:
            target_url = (
                self.base_url
                if "localhost:8888" in self.base_url or "127.0.0.1:8888" in self.base_url
                else "http://localhost:8888"
            )
            with httpx.Client(timeout=0.25) as client:
                res = client.get(f"{target_url.rstrip('/')}/health")
                return res.status_code < 500
        except Exception:
            return False

    @property
    def backend_name(self) -> Literal["cloud", "local", "memory"]:
        """
        Return exactly one of 'cloud', 'local', or 'memory'.
        Never falsely claims cloud/local if in-memory fallback is active.
        """
        if self.api_key:
            return "cloud"
        if self._probe_local_docker():
            return "local"
        return "memory"

    # --------------------------------------------------------------------------
    # Observation & Helper Methods
    # --------------------------------------------------------------------------

    def get_observation(self, obs_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an observation by its ID."""
        return self._observations.get(obs_id)

    def supersede_observation(self, old_obs_id: str, new_obs_id: str) -> None:
        """Link an old observation to the new one that superseded it."""
        if old_obs_id in self._observations:
            self._observations[old_obs_id]["superseded_by"] = new_obs_id

    def _extract_scope_key(self, tags: List[str]) -> str:
        """Extract observation scope grouping key from tags."""
        insurer = ""
        denial_reason = ""
        diagnosis_group = ""
        for tag in tags:
            if tag.startswith("insurer:"):
                insurer = tag
            elif tag.startswith("denial_reason:"):
                denial_reason = tag
            elif tag.startswith("diagnosis_group:"):
                diagnosis_group = tag
        return f"{insurer}|{denial_reason}|{diagnosis_group}".strip("|")

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase alphanumeric words."""
        return [w for w in re.findall(r"\b\w+\b", text.lower()) if len(w) > 1]

    # --------------------------------------------------------------------------
    # Core Memory Operations: Retain, Recall, Reflect
    # --------------------------------------------------------------------------

    def retain(
        self,
        document: Union[str, Dict[str, Any]],
        tags: List[str],
        timestamp: Optional[Union[str, datetime]] = None,
    ) -> Dict[str, Any]:
        """
        Retain a claim document and update observations with proof count.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()
        elif isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()

        backend = self.backend_name

        # If Cloud or Local Docker is available, attempt remote retain
        if backend in ("cloud", "local"):
            try:
                content_str = (
                    document.get("content", "") or document.get("text", "")
                    if isinstance(document, dict)
                    else str(document)
                )
                doc_id = (
                    document.get("id") or document.get("document_id")
                    if isinstance(document, dict)
                    else f"doc_{uuid.uuid4().hex[:8]}"
                )

                if HINDSIGHT_CLIENT_AVAILABLE and HindsightSDKClient is not None:
                    client = HindsightSDKClient(
                        base_url=self.base_url,
                        api_key=self.api_key if self.api_key else None,
                        timeout=5.0,
                    )
                    resp = client.retain(
                        bank_id=self.bank_id,
                        content=content_str,
                        tags=tags,
                        timestamp=timestamp,
                        document_id=doc_id,
                    )
                    return {
                        "status": "retained",
                        "document_id": doc_id,
                        "memory_unit_count": getattr(resp, "memory_unit_count", 1),
                        "backend": backend,
                    }
                else:
                    # httpx REST fallback
                    headers = {"Content-Type": "application/json"}
                    if self.api_key:
                        headers["Authorization"] = f"Bearer {self.api_key}"
                    with httpx.Client(timeout=5.0) as client:
                        resp = client.post(
                            f"{self.base_url.rstrip('/')}/v1/default/banks/{self.bank_id}/retain",
                            json={
                                "content": content_str,
                                "tags": tags,
                                "timestamp": timestamp,
                                "document_id": doc_id,
                            },
                            headers=headers,
                        )
                        if resp.is_success:
                            data = resp.json()
                            return {
                                "status": "retained",
                                "document_id": doc_id,
                                "memory_unit_count": data.get("memory_unit_count", 1),
                                "backend": backend,
                            }
            except Exception:
                # On transient remote failure, proceed to in-memory persistence
                pass

        # In-Memory fallback implementation
        if isinstance(document, dict):
            doc_id = str(document.get("id") or document.get("document_id") or f"doc_{uuid.uuid4().hex[:8]}")
            content = str(document.get("content") or document.get("text") or "")
            passed_proof_count = document.get("proof_count")
            passed_obs = document.get("observation")
            supersedes = document.get("supersedes")
        else:
            doc_id = f"doc_{uuid.uuid4().hex[:8]}"
            content = str(document)
            passed_proof_count = None
            passed_obs = None
            supersedes = None

        # Resolve or update observation
        if isinstance(passed_obs, dict):
            obs_id = str(passed_obs.get("id") or f"obs_{uuid.uuid4().hex[:6]}")
            p_count = passed_obs.get("proof_count") or passed_proof_count or 1
            # Preserve every passed observation field (e.g. "tactic" — the
            # critic uses it to tell a superseded tactic from its replacement).
            obs_data = dict(passed_obs)
            obs_data.update({
                "id": obs_id,
                "proof_count": int(p_count),
                "superseded_by": passed_obs.get("superseded_by"),
                "content": passed_obs.get("content", content),
                "tags": tags,
            })
            self._observations[obs_id] = obs_data
        elif passed_proof_count is not None:
            obs_id = f"obs_{uuid.uuid4().hex[:6]}"
            obs_data = {
                "id": obs_id,
                "proof_count": int(passed_proof_count),
                "superseded_by": None,
                "content": content,
                "tags": tags,
            }
            self._observations[obs_id] = obs_data
        else:
            scope_key = self._extract_scope_key(tags)
            if scope_key and scope_key in self._scope_to_obs:
                obs_id = self._scope_to_obs[scope_key]
                obs_data = self._observations[obs_id]
                obs_data["proof_count"] += 1
            else:
                obs_id = f"obs_{len(self._observations) + 1:03d}"
                obs_data = {
                    "id": obs_id,
                    "proof_count": 1,
                    "superseded_by": None,
                    "content": f"Observation for {scope_key or 'claim pattern'}",
                    "tags": tags,
                }
                self._observations[obs_id] = obs_data
                if scope_key:
                    self._scope_to_obs[scope_key] = obs_id

        # Contradiction handling
        if supersedes and supersedes in self._observations:
            self._observations[supersedes]["superseded_by"] = obs_id

        doc_record = {
            "id": doc_id,
            "document_id": doc_id,
            "content": content,
            "text": content,
            "tags": list(tags) if tags else [],
            "timestamp": str(timestamp),
            "observation_id": obs_id,
            "observation": obs_data,
            "proof_count": obs_data["proof_count"],
        }
        self._documents[doc_id] = doc_record

        return {
            "status": "retained",
            "document_id": doc_id,
            "memory_unit_count": 1,
            "observation_id": obs_id,
            "proof_count": obs_data["proof_count"],
            "backend": "memory",
        }

    def recall(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[RecallHit]:
        """
        Recall memories using any_strict tag matching and keyword overlap scoring.
        When decision model is disabled, this operation never raises.
        """
        backend = self.backend_name

        if backend in ("cloud", "local"):
            try:
                if HINDSIGHT_CLIENT_AVAILABLE and HindsightSDKClient is not None:
                    client = HindsightSDKClient(
                        base_url=self.base_url,
                        api_key=self.api_key if self.api_key else None,
                        timeout=5.0,
                    )
                    resp = client.recall(
                        bank_id=self.bank_id,
                        query=query,
                        tags=tags,
                        tags_match="any_strict",
                    )
                    results: List[RecallHit] = []
                    for item in getattr(resp, "results", []):
                        hit = RecallHit({
                            "id": getattr(item, "id", ""),
                            "document_id": getattr(item, "document_id", getattr(item, "id", "")),
                            "content": getattr(item, "text", ""),
                            "text": getattr(item, "text", ""),
                            "tags": getattr(item, "tags", []),
                            "proof_count": getattr(item, "proof_count", 1),
                            "score": 1.0,
                            "observation": {"id": getattr(item, "id", ""), "proof_count": 1},
                        })
                        results.append(hit)
                    return results[:top_k]
                else:
                    # httpx REST fallback
                    headers = {"Content-Type": "application/json"}
                    if self.api_key:
                        headers["Authorization"] = f"Bearer {self.api_key}"
                    with httpx.Client(timeout=5.0) as client:
                        resp = client.post(
                            f"{self.base_url.rstrip('/')}/v1/default/banks/{self.bank_id}/recall",
                            json={
                                "query": query,
                                "tags": tags or [],
                                "tags_match": "any_strict",
                            },
                            headers=headers,
                        )
                        if resp.is_success:
                            data = resp.json()
                            results = [
                                RecallHit({
                                    "id": item.get("id", ""),
                                    "document_id": item.get("document_id", item.get("id", "")),
                                    "content": item.get("text", ""),
                                    "tags": item.get("tags", []),
                                    "proof_count": item.get("proof_count", 1),
                                    "score": item.get("score", 1.0),
                                    "observation": item.get("observation", {"proof_count": 1}),
                                })
                                for item in data.get("results", [])
                            ]
                            return results[:top_k]
            except Exception:
                # If remote fails or is unreachable, fallback to memory
                pass

        # In-Memory recall implementation
        candidates: List[RecallHit] = []
        query_tokens = self._tokenize(query)
        query_lower = query.lower()

        for doc in self._documents.values():
            doc_tags = doc.get("tags", [])

            # any_strict tag matching: untagged memories are strictly excluded
            if not doc_tags:
                continue

            if tags:
                matched_tag = False
                for q_tag in tags:
                    if q_tag.endswith("*"):
                        prefix = q_tag[:-1]
                        if any(dt.startswith(prefix) for dt in doc_tags):
                            matched_tag = True
                            break
                    elif q_tag in doc_tags:
                        matched_tag = True
                        break
                if not matched_tag:
                    continue

            # Keyword overlap scoring
            doc_content = doc.get("content", "")
            doc_tokens = set(self._tokenize(doc_content + " " + " ".join(doc_tags)))

            if query_tokens:
                matches = [t for t in query_tokens if t in doc_tokens]
                overlap = len(matches) / len(query_tokens)
                phrase_bonus = 1.0 if query_lower in doc_content.lower() else 0.0
                score = overlap + phrase_bonus + (len(matches) * 0.1)
            else:
                score = 1.0

            obs_data = self._observations.get(doc.get("observation_id", ""), doc.get("observation", {}))
            proof_count = obs_data.get("proof_count", doc.get("proof_count", 1))

            hit = RecallHit({
                "id": doc["id"],
                "document_id": doc["id"],
                "content": doc_content,
                "text": doc_content,
                "tags": doc_tags,
                "timestamp": doc.get("timestamp", ""),
                "score": float(score),
                "proof_count": proof_count,
                "observation": obs_data,
                "observation_id": doc.get("observation_id", ""),
            })
            candidates.append(hit)

        # Apply decision model pruning only if explicitly enabled
        if self.decision_model_enabled and self.enable_decision_prune and candidates:
            max_score = max(c["score"] for c in candidates)
            threshold = max(0.2, 0.4 * max_score)
            candidates = [c for c in candidates if c["score"] >= threshold]

        # Rank by score descending, then proof_count, then timestamp
        candidates.sort(
            key=lambda c: (c["score"], c.get("proof_count", 0), c.get("timestamp", "")),
            reverse=True,
        )

        return candidates[:top_k]

    def reflect(
        self,
        question: str,
        context_ids: Optional[List[str]] = None,
    ) -> ReflectResult:
        """
        Reflect over recalled context memories.
        Returns ranked causes with citations that are strictly drawn from context_ids.
        Handles contradictions via superseded_by flag.
        """
        if context_ids is None:
            context_ids = []

        valid_ids: Set[str] = set(context_ids)

        # Cloud / Local Docker remote reflect path
        backend = self.backend_name
        if backend in ("cloud", "local"):
            try:
                if HINDSIGHT_CLIENT_AVAILABLE and HindsightSDKClient is not None:
                    client = HindsightSDKClient(
                        base_url=self.base_url,
                        api_key=self.api_key if self.api_key else None,
                        timeout=5.0,
                    )
                    resp = client.reflect(
                        bank_id=self.bank_id,
                        query=question,
                    )
                    raw_text = getattr(resp, "text", "")
                    # Strictly filter citations to only valid recalled IDs
                    citations = [cid for cid in context_ids if cid in raw_text or cid in valid_ids]
                    return ReflectResult({
                        "verdict": "APPROVE" if citations else "VETO",
                        "reason": raw_text or "Reflect output generated from context.",
                        "citations": citations,
                        "ranked_causes": [{"cause": raw_text, "citations": citations, "proof_count": 1, "superseded": False}],
                        "proof_count": 1,
                        "disclaimer": "Draft for human review, not legal/medical advice. All cases SYNTHETIC.",
                    })
            except Exception:
                pass

        # In-Memory reflect implementation
        if not context_ids:
            return ReflectResult({
                "verdict": "VETO",
                "reason": "No recalled context IDs provided for reflection.",
                "citations": [],
                "ranked_causes": [],
                "proof_count": 0,
                "missing_evidence": [],
                "required_excerpt": "",
                "disclaimer": "Draft for human review, not legal/medical advice. All cases SYNTHETIC.",
            })

        matched_docs: List[Dict[str, Any]] = [
            self._documents[cid] for cid in context_ids if cid in self._documents
        ]

        if not matched_docs:
            return ReflectResult({
                "verdict": "VETO",
                "reason": "Recalled context IDs did not resolve to stored memory records.",
                "citations": [],
                "ranked_causes": [],
                "proof_count": 0,
                "disclaimer": "Draft for human review, not legal/medical advice. All cases SYNTHETIC.",
            })

        ranked_causes: List[Dict[str, Any]] = []
        cited_ids: List[str] = []

        q_lower = question.lower()
        q_tokens = self._tokenize(question)

        for doc in matched_docs:
            doc_id = doc["id"]
            obs_id = doc.get("observation_id", "")
            obs = self._observations.get(obs_id, doc.get("observation", {}))

            superseded_by = obs.get("superseded_by")
            is_superseded = superseded_by is not None
            proof_count = obs.get("proof_count", doc.get("proof_count", 1))

            # Relevance to the question
            content = doc.get("content", "")
            doc_tokens = set(self._tokenize(content))
            relevance = len([t for t in q_tokens if t in doc_tokens]) if q_tokens else 1

            cause_desc = f"{content[:120]}... (Observation {obs_id})" if len(content) > 120 else content

            cause_entry = {
                "cause": cause_desc,
                "observation_id": obs_id,
                "citations": [doc_id],
                "proof_count": proof_count,
                "superseded": is_superseded,
                "superseded_by": superseded_by,
                "relevance": relevance,
            }
            ranked_causes.append(cause_entry)

            if doc_id in valid_ids and doc_id not in cited_ids:
                cited_ids.append(doc_id)

        # Sort ranked causes: active (non-superseded) first, then proof_count, then relevance
        ranked_causes.sort(
            key=lambda c: (not c["superseded"], c["proof_count"], c["relevance"]),
            reverse=True,
        )

        for idx, cause in enumerate(ranked_causes, 1):
            cause["rank"] = idx

        # Determine overall verdict and explanation
        active_causes = [c for c in ranked_causes if not c["superseded"]]
        if active_causes:
            top_cause = active_causes[0]
            verdict = "APPROVE"
            reason = f"Winning evidence supported by {top_cause['proof_count']} proofs: {top_cause['cause']}"
            max_proof_count = top_cause["proof_count"]
        else:
            top_cause = ranked_causes[0]
            verdict = "VETO"
            reason = f"Superseded tactic: observation {top_cause['observation_id']} superseded by {top_cause.get('superseded_by')}"
            max_proof_count = top_cause["proof_count"]

        return ReflectResult({
            "verdict": verdict,
            "reason": reason,
            "citations": cited_ids,
            "ranked_causes": ranked_causes,
            "proof_count": max_proof_count,
            "missing_evidence": [],
            "required_excerpt": "",
            "disclaimer": "Draft for human review, not legal/medical advice. All cases SYNTHETIC.",
        })
