from app.schemas.common import Money, Schema


class CategoryOut(Schema):
    id: int
    name: str
    slug: str
    parent_id: int | None
    emoji: str
    image_url: str | None
    color: str


class CategoryTree(CategoryOut):
    children: list[CategoryOut] = []


class ShelfLocation(Schema):
    aisle: int
    aisle_name: str | None
    row: int
    label: str  # "Aisle 4 · Row 2"


class Availability(Schema):
    in_stock: bool
    stock: int
    max_qty: int  # most a customer can add (stock capped by the per-order limit)


class ProductOut(Schema):
    id: int
    name: str
    slug: str
    brand: str | None
    unit_label: str
    price: Money
    mrp: Money
    discount_percent: int
    emoji: str
    image_url: str | None
    is_veg: bool
    category_id: int
    # Present when the request names a store.
    availability: Availability | None = None
    location: ShelfLocation | None = None


class ProductDetail(ProductOut):
    description: str | None
    tags: list[str]
    category: CategoryOut
    parent_category: CategoryOut | None
    similar: list[ProductOut] = []


class CategoryPage(Schema):
    category: CategoryOut
    subcategories: list[CategoryOut]
    active_subcategory: str | None
    products: list[ProductOut]


class HomeSection(Schema):
    title: str
    category_slug: str
    products: list[ProductOut]


class HomeFeed(Schema):
    categories: list[CategoryTree]
    sections: list[HomeSection]


class SearchResult(Schema):
    query: str
    products: list[ProductOut]
