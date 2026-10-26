import { rupees } from "../lib/format";
import type { Bill } from "../lib/types";

export default function BillDetails({ bill, showDeliveryRows = true }: { bill: Bill; showDeliveryRows?: boolean }) {
  return (
    <div className="bill card">
      <h3>Bill details</h3>
      <div className="bill-row">
        <span>🧾 Items total</span>
        <span>
          {bill.savings_paise > 0 && <s className="muted">{rupees(bill.mrp_total_paise)}</s>} {rupees(bill.item_total_paise)}
        </span>
      </div>
      {showDeliveryRows && (
        <div className="bill-row">
          <span>🛵 Delivery charge</span>
          <span>{bill.delivery_fee_paise ? rupees(bill.delivery_fee_paise) : <span className="free">FREE</span>}</span>
        </div>
      )}
      {bill.handling_fee_paise > 0 && (
        <div className="bill-row">
          <span>🛍️ Handling charge</span>
          <span>{rupees(bill.handling_fee_paise)}</span>
        </div>
      )}
      {bill.small_cart_fee_paise > 0 && (
        <div className="bill-row">
          <span>🛒 Small cart charge</span>
          <span>{rupees(bill.small_cart_fee_paise)}</span>
        </div>
      )}
      <div className="bill-row total">
        <span>Grand total</span>
        <span>{rupees(bill.total_paise)}</span>
      </div>
      {bill.savings_paise > 0 && (
        <div className="savings">
          Your total savings <strong>{rupees(bill.savings_paise)}</strong>
        </div>
      )}
    </div>
  );
}
