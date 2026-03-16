# Domain Vocabulary

## Entities & Aggregates

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Purchase Order | A buyer's formal request to a vendor for goods. Contains header, trade details, and one or more line items. Aggregate root. | Procurement |
| Line Item | A single product/material entry on a PO: part number, description, quantity, UoM, unit price, HS code, country of origin. Child entity of Purchase Order. | Procurement |
| Vendor | The supplier fulfilling the purchase order. | Procurement |
| Rejection Record | A timestamped comment captured when a vendor rejects a PO. Append-only; accumulated across reject/revise cycles. Value object owned by Purchase Order. | Procurement |

## PO Header Fields

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| PO Number | Unique system-generated identifier for a purchase order. Format: `PO-YYYYMMDD-XXXX`, sequential per day. | Procurement |
| Ship-to Address | The physical delivery address for the goods. | Procurement |
| Payment Terms | How and when payment is made (LC, TT, DA, DP). | Procurement |
| Currency | The currency in which the PO is denominated. | Procurement |
| Issued Date | Date the PO was formally issued. | Procurement |
| Required Delivery Date | Date by which goods must be delivered. | Procurement |
| Total Value | Sum of all line item values on the PO. | Procurement |
| Terms and Conditions | Full text of the legal terms governing the PO. | Procurement |

## Trade Fields

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Incoterm | International commercial term defining delivery obligations (FOB, CIF, EXW, etc.). | Trade |
| Port of Loading | The port where goods are loaded onto the export carrier. | Trade |
| Port of Discharge | The port where goods are unloaded at destination. | Trade |
| Country of Origin | The country where goods were manufactured or produced. Applies at PO header and per line item. | Trade |
| Country of Destination | The country where goods are ultimately delivered. | Trade |

## Line Item Fields

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Part Number | Identifier for the product or material. | Procurement |
| Unit of Measure | The measurement unit for a line item quantity (e.g., pcs, kg, m). | Procurement |
| HS Code | Harmonized System tariff classification code for a product. Used for customs declarations. | Trade |

## Compliance (deferred)

| Term | Definition | Bounded Context |
|------|-----------|-----------------|
| Letter of Credit Number | Reference to the LC issued by the buyer's bank to guarantee payment. | Compliance |
| Export License Number | Government-issued license permitting export of controlled goods. | Compliance |
| Packing List Reference | Pointer to the document detailing how goods are packed for shipment. | Compliance |
| Bill of Lading Reference | Pointer to the carrier-issued document acknowledging receipt of goods for shipment. | Compliance |

## PO Lifecycle

| Status | Definition |
|--------|-----------|
| Draft | PO is being composed, not yet visible to vendor. |
| Pending | PO submitted to vendor, awaiting accept or reject. |
| Accepted | Vendor formally accepted. Terminal. |
| Rejected | Vendor rejected with mandatory comment. |
| Revised | Previously rejected PO updated and resubmitted, awaiting vendor action. |

### Status Transitions

| From | To | Trigger |
|------|----|---------|
| Draft | Pending | PO submitted to vendor |
| Pending | Accepted | Vendor accepts |
| Pending | Rejected | Vendor rejects with comment |
| Rejected | Revised | Creator updates PO fields |
| Revised | Pending | Revised PO resubmitted to vendor |

### State Diagram

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Pending : Submit to vendor
    Pending --> Accepted : Vendor accepts
    Pending --> Rejected : Vendor rejects (with comment)
    Rejected --> Revised : Creator updates fields
    Revised --> Pending : Resubmitted to vendor
    Accepted --> [*]
```
