"""Pure quantity calculations for Comp Off source reconciliation.

This module does not write ledger entries or infer historical mappings. Callers
must provide verified available quantities in FIFO order and persist mappings
atomically alongside the corresponding application.
"""

from decimal import Decimal, InvalidOperation


class CompOffReconciliationError(ValueError):
    """The supplied quantities cannot be reconciled safely."""


def _quantity(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CompOffReconciliationError("Invalid Comp Off quantity") from exc
    if not amount.is_finite() or amount < 0:
        raise CompOffReconciliationError("Comp Off quantities must be finite and non-negative")
    return amount


def allocate_sources(sources, requested):
    """Allocate verified balances in the given FIFO order, including fractions.

    Each source is a pair of (request name, available quantity). Returns pairs
    of (request name, allocated Decimal). Duplicate or missing names are an
    error: silently merging them could double count an earned credit.
    """
    remaining = _quantity(requested)
    if not remaining:
        raise CompOffReconciliationError("Requested Comp Off must be greater than zero")

    seen = set()
    validated = []
    for name, available in sources:
        if not name or name in seen:
            raise CompOffReconciliationError("Missing or duplicate Comp Off source")
        seen.add(name)
        validated.append((name, _quantity(available)))

    allocations = []
    for name, available in validated:
        used = min(remaining, available)
        if used:
            allocations.append((name, used))
            remaining -= used
        if not remaining:
            break
    if remaining:
        raise CompOffReconciliationError("Insufficient reconciled Comp Off source balance")
    return allocations
