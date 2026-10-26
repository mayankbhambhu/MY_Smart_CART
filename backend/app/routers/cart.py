from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Store
from ..schemas import QuoteLine, QuoteRequest, QuoteResponse
from ..services.catalog import product_out
from ..services.orders import resolve_lines, totals
from ..services.pricing import compute_bill

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/quote", response_model=QuoteResponse)
def quote(body: QuoteRequest, db: Session = Depends(get_db)):
    """Price a cart with live prices and stock. The cart itself lives on the client."""
    if db.get(Store, body.store_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Store not found")
    lines, issues = resolve_lines(db, body.store_id, body.items)
    item_total, mrp_total = totals(lines)
    return QuoteResponse(
        store_id=body.store_id,
        fulfillment=body.fulfillment,
        lines=[
            QuoteLine(
                product=product_out(line.inventory.product, line.inventory),
                quantity=line.quantity,
                available_quantity=line.available,
                line_total_paise=line.inventory.product.price_paise * line.quantity,
                line_mrp_paise=line.inventory.product.mrp_paise * line.quantity,
            )
            for line in lines
        ],
        bill=compute_bill(body.fulfillment, item_total, mrp_total),
        issues=issues,
        can_checkout=bool(lines) and not issues,
    )
