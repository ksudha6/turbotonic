from __future__ import annotations

from src.certificate_repository import CertificateRepository
from src.domain.certificate import CertificateStatus
from src.domain.shipment import Shipment
from src.domain.shipment_document_requirement import (
    DocumentRequirementStatus,
    ReadinessResult,
    ShipmentDocumentRequirement,
)
from src.packaging_repository import PackagingSpecRepository
from src.qualification_type_repository import QualificationTypeRepository


def create_default_requirements(shipment_id: str) -> list[ShipmentDocumentRequirement]:
    # Auto-generate PACKING_LIST and COMMERCIAL_INVOICE requirements on transition
    # to DOCUMENTS_PENDING; both are always satisfied because PDFs generate on demand.
    return [
        ShipmentDocumentRequirement.create(
            shipment_id=shipment_id,
            document_type="PACKING_LIST",
            is_auto_generated=True,
        ),
        ShipmentDocumentRequirement.create(
            shipment_id=shipment_id,
            document_type="COMMERCIAL_INVOICE",
            is_auto_generated=True,
        ),
    ]


async def check_readiness(
    shipment: Shipment,
    requirements: list[ShipmentDocumentRequirement],
    cert_repo: CertificateRepository,
    packaging_repo: PackagingSpecRepository,
    qt_repo: QualificationTypeRepository,
) -> ReadinessResult:
    # Documents check: auto-generated requirements are always ready;
    # user-defined requirements must be COLLECTED.
    missing_documents: list[str] = [
        req.document_type
        for req in requirements
        if not req.is_auto_generated and req.status is DocumentRequirementStatus.PENDING
    ]
    documents_ready = len(missing_documents) == 0

    # Collect unique product_ids from shipment line items
    product_ids: list[str] = [
        li.product_id
        for li in shipment.line_items
        if li.product_id is not None
    ]

    # Certificates check: each product must have APPROVED certs for all required qualifications
    missing_certificates: list[dict[str, str]] = []
    if product_ids:
        qt_by_product = await qt_repo.list_by_products(product_ids)
        for product_id in product_ids:
            qualifications = qt_by_product.get(product_id, [])
            for qt in qualifications:
                certs = await cert_repo.list_by_product_and_market(
                    product_id, shipment.marketplace
                )
                valid = any(
                    c.qualification_type_id == qt.id
                    and c.status is CertificateStatus.APPROVED
                    for c in certs
                )
                if not valid:
                    missing_certificates.append(
                        {"product_id": product_id, "qualification_type": qt.name}
                    )
    certificates_ready = len(missing_certificates) == 0

    # Packaging check: each product must have at least one packaging spec with a document
    # for the shipment's marketplace.
    missing_packaging: list[dict[str, str]] = []
    for product_id in product_ids:
        specs = await packaging_repo.list_by_product_and_marketplace(
            product_id, shipment.marketplace
        )
        has_file = any(spec.document_id is not None for spec in specs)
        if not has_file:
            missing_packaging.append(
                {"product_id": product_id, "marketplace": shipment.marketplace}
            )
    packaging_ready = len(missing_packaging) == 0

    is_ready = documents_ready and certificates_ready and packaging_ready
    return ReadinessResult(
        documents_ready=documents_ready,
        certificates_ready=certificates_ready,
        packaging_ready=packaging_ready,
        is_ready=is_ready,
        missing_documents=missing_documents,
        missing_certificates=missing_certificates,
        missing_packaging=missing_packaging,
    )
