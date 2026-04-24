from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.certificate_repository import CertificateRepository
from src.domain.certificate import CertificateStatus
from src.domain.purchase_order import PurchaseOrder
from src.product_repository import ProductRepository
from src.qualification_type_repository import QualificationTypeRepository


class CertWarningReason(str, Enum):
    MISSING = "MISSING"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class CertWarning:
    line_item_index: int
    part_number: str
    product_id: str
    qualification_type_id: str
    qualification_name: str
    reason: CertWarningReason


async def check_po_qualifications(
    po: PurchaseOrder,
    product_repo: ProductRepository,
    qualification_repo: QualificationTypeRepository,
    cert_repo: CertificateRepository,
) -> list[CertWarning]:
    # POs without a marketplace skip the gate; compliance requirements are
    # market-specific and cannot be evaluated without one.
    if not po.marketplace:
        return []

    warnings: list[CertWarning] = []

    for idx, line_item in enumerate(po.line_items):
        if not line_item.product_id:
            # Line items with no product link are legacy; skip silently.
            continue

        product = await product_repo.get_by_id(line_item.product_id)
        if product is None:
            continue

        qualifications = await qualification_repo.list_by_product(line_item.product_id)
        if not qualifications:
            continue

        certs = await cert_repo.list_by_product_and_market(line_item.product_id, po.marketplace)

        for qual in qualifications:
            # Collect all certs matching this qualification type.
            matching = [c for c in certs if c.qualification_type_id == qual.id]

            # Only VALID and non-expired certs count as coverage.
            valid_coverage = [
                c for c in matching
                if c.status is CertificateStatus.VALID and not c.is_expired()
            ]

            if valid_coverage:
                # At least one valid, non-expired cert exists for this qual.
                continue

            # Determine reason: EXPIRED when at least one cert exists but all are expired;
            # MISSING when no cert for this qual type exists at all.
            expired_coverage = [c for c in matching if c.is_expired()]

            if expired_coverage:
                reason = CertWarningReason.EXPIRED
            else:
                reason = CertWarningReason.MISSING

            warnings.append(
                CertWarning(
                    line_item_index=idx,
                    part_number=line_item.part_number,
                    product_id=line_item.product_id,
                    qualification_type_id=qual.id,
                    qualification_name=qual.name,
                    reason=reason,
                )
            )

    return warnings
