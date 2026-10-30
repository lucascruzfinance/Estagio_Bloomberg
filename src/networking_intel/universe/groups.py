"""Economic groups, resolved by exact evidence only.

Priority: curated registry (pilot and wave 2, pending human review) > Banco Central
prudential conglomerate (the entity's CNPJ root is an IF.data institution) > CNPJ root.
Brand-name similarity across different groups is written to a review file as a
suggestion and never changes a membership.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any

from networking_intel.universe.curated import CuratedAccount
from networking_intel.universe.geo import norm

# Legal-form and generic words that cannot identify a brand.
GENERIC_TOKENS = frozenset(
    [
        "ltda",
        "s",
        "a",
        "sa",
        "de",
        "da",
        "do",
        "dos",
        "das",
        "e",
        "em",
        "gestao",
        "gestora",
        "recursos",
        "investimentos",
        "investimento",
        "asset",
        "management",
        "capital",
        "dtvm",
        "participacoes",
        "consultoria",
        "administracao",
        "administradora",
        "brasil",
        "brazil",
        "partners",
        "group",
        "grupo",
        "banco",
        "bank",
        "corretora",
        "titulos",
        "valores",
        "mobiliarios",
        "distribuidora",
        "sociedade",
        "fundos",
        "fundo",
        "wealth",
        "private",
        "equity",
        "global",
        "sao",
        "paulo",
        "rio",
        "janeiro",
        "cambio",
        "servicos",
        "financeiros",
        "credito",
        "carteiras",
        "the",
        "of",
        "and",
    ]
)


@dataclass(frozen=True)
class Membership:
    cnpj: str
    group_key: str
    group_name: str
    basis: str
    approval_status: str
    evidence: str


def brand_token(name: str) -> str | None:
    """First distinctive word of a name, e.g. 'KAPITALO INVESTIMENTOS' -> 'kapitalo'."""
    for token in norm(name).split():
        if token not in GENERIC_TOKENS and len(token) >= 3:
            return token
    return None


def resolve_groups(
    entities: Mapping[str, str],
    curated: Iterable[CuratedAccount],
    ifdata_institutions: Iterable[Mapping[str, Any]],
) -> dict[str, Membership]:
    """entities: cnpj -> display name."""
    by_cnpj: dict[str, Membership] = {}
    for account in curated:
        for entity in account.entities:
            by_cnpj[entity.cnpj] = Membership(
                cnpj=entity.cnpj,
                group_key=f"acct:{account.account_key}",
                group_name=account.display_name,
                basis="curated_registry",
                approval_status=entity.approval_status,
                evidence=entity.relation_evidence,
            )
    institutions = list(ifdata_institutions)
    conglomerate_names = {
        row["cod_inst"]: str(row["name"]).removesuffix(" - PRUDENCIAL")
        for row in institutions
        if row["is_conglomerate"]
    }
    root_to_conglomerate = {
        row["cod_inst"]: row["prudential_conglomerate"]
        for row in institutions
        if not row["is_conglomerate"] and row["prudential_conglomerate"]
    }
    for cnpj, name in entities.items():
        if cnpj in by_cnpj:
            continue
        conglomerate = root_to_conglomerate.get(cnpj[:8])
        if conglomerate:
            by_cnpj[cnpj] = Membership(
                cnpj=cnpj,
                group_key=f"ifdata:{conglomerate}",
                group_name=conglomerate_names.get(conglomerate, conglomerate),
                basis="ifdata_conglomerate",
                approval_status="source_exact",
                evidence=f"Raiz {cnpj[:8]} pertence ao conglomerado prudencial {conglomerate} (IF.data, BCB).",
            )
            continue
        by_cnpj[cnpj] = Membership(
            cnpj=cnpj,
            group_key=f"root:{cnpj[:8]}",
            group_name=name,
            basis="cnpj_root",
            approval_status="source_exact",
            evidence=f"Mesma raiz de CNPJ {cnpj[:8]} (matriz e filiais).",
        )
    # Root groups take the name of their largest-named member deterministically.
    names_by_group: dict[str, list[str]] = defaultdict(list)
    for membership in by_cnpj.values():
        if membership.basis == "cnpj_root":
            names_by_group[membership.group_key].append(entities[membership.cnpj])
    for cnpj, membership in list(by_cnpj.items()):
        if membership.basis == "cnpj_root":
            by_cnpj[cnpj] = replace(
                membership, group_name=sorted(names_by_group[membership.group_key])[0]
            )
    return by_cnpj


def name_suggestions(
    memberships: Mapping[str, Membership], entities: Mapping[str, str]
) -> list[dict[str, Any]]:
    """Groups sharing a brand token: candidates for a human to merge (never applied)."""
    groups_by_token: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for cnpj, membership in memberships.items():
        token = brand_token(entities[cnpj])
        if token:
            groups_by_token[token][membership.group_key].append(cnpj)
    rows = []
    for token, groups in sorted(groups_by_token.items()):
        if len(groups) < 2:
            continue
        keys = sorted(groups)
        rows.append(
            {
                "brand_token": token,
                "groups": " | ".join(keys),
                "group_names": " | ".join(memberships[groups[k][0]].group_name for k in keys),
                "entities": sum(len(v) for v in groups.values()),
                "example_names": " | ".join(
                    sorted({entities[c] for k in keys for c in groups[k]})[:6]
                ),
                "status": "suggestion_pending_review",
            }
        )
    return rows
