import type { Aisle, InStoreLine } from "../lib/types";

interface Props {
  aisles: Aisle[];
  lines: InStoreLine[];
  picked: Set<number>;
  focus?: number | null;
}

/** Top-down store plan: one column per aisle, rows stacked, with numbered stops in walking order. */
export default function StoreMap({ aisles, lines, picked, focus }: Props) {
  const stops = new Map<string, { stop: number; productId: number }[]>();
  lines.forEach((line, index) => {
    const loc = line.product.location;
    if (!loc) return;
    const key = `${loc.aisle_number}:${loc.row_number}`;
    stops.set(key, [...(stops.get(key) ?? []), { stop: index + 1, productId: line.product.id }]);
  });
  const maxRows = Math.max(1, ...aisles.map((a) => a.row_count));
  const visited = new Set(lines.map((l) => l.product.location?.aisle_number));

  return (
    <div className="store-map" role="img" aria-label="Store map showing where your items are">
      <div className="store-map-grid" style={{ gridTemplateColumns: `repeat(${aisles.length}, minmax(26px, 1fr))` }}>
        {aisles.map((aisle) => (
          <div key={aisle.number} className={`map-aisle${visited.has(aisle.number) ? " has-items" : ""}`}>
            <div className="map-aisle-head" title={aisle.name}>
              <strong>{aisle.number}</strong>
              <span>{aisle.name.split(/[,&]/)[0].trim()}</span>
            </div>
            {Array.from({ length: maxRows }, (_, i) => maxRows - i).map((row) => {
              const here = stops.get(`${aisle.number}:${row}`) ?? [];
              return (
                <div key={row} className={`map-cell${row > aisle.row_count ? " void" : ""}`}>
                  <span className="map-row-label">R{row}</span>
                  {here.map(({ stop, productId }) => (
                    <span
                      key={productId}
                      className={`map-pin${picked.has(productId) ? " done" : ""}${focus === productId ? " focus" : ""}`}
                    >
                      {picked.has(productId) ? "✓" : stop}
                    </span>
                  ))}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      <div className="map-entrance">🚪 Entrance &amp; billing counter</div>
    </div>
  );
}
