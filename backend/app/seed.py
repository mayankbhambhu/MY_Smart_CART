"""Demo data: three stores in Bengaluru, a grocery catalog, stock and shelf locations.

Run `python -m app.seed --reset` to wipe and re-create the database.
"""

import argparse
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .models import Aisle, Category, Inventory, Product, Role, Store, User

STAFF_PHONE = "9999999999"

# slug: (name, emoji, tile colour)
CATEGORIES = {
    "fruits-vegetables": ("Vegetables & Fruits", "🥦", "#e7f6e7"),
    "dairy-bread-eggs": ("Dairy, Bread & Eggs", "🥛", "#e5f1fb"),
    "atta-rice-dal": ("Atta, Rice & Dal", "🌾", "#fdf4dc"),
    "munchies": ("Munchies", "🍿", "#fde7ee"),
    "cold-drinks-juices": ("Cold Drinks & Juices", "🥤", "#dff5f7"),
    "breakfast-instant": ("Breakfast & Instant Food", "🥣", "#f1e8f8"),
    "sweet-tooth": ("Sweet Tooth", "🍫", "#fbe9e4"),
    "tea-coffee": ("Tea, Coffee & Health Drinks", "☕", "#f0ebe6"),
    "masala-oil": ("Masala, Oil & More", "🫙", "#fdf0e1"),
    "cleaning": ("Cleaning Essentials", "🧽", "#e8eaf8"),
    "personal-care": ("Personal Care", "🧴", "#eef6e6"),
}

# (category slug, name, brand, unit, mrp ₹, price ₹, emoji, search keywords)
PRODUCTS = [
    ("fruits-vegetables", "Onion", None, "1 kg", 60, 42, "🧅", "pyaz,pyaaz,kanda,onions"),
    ("fruits-vegetables", "Potato", None, "1 kg", 50, 36, "🥔", "aloo,alu,potatoes"),
    ("fruits-vegetables", "Tomato", None, "500 g", 40, 29, "🍅", "tamatar,tomatoes"),
    ("fruits-vegetables", "Robusta Banana", None, "6 pcs", 60, 48, "🍌", "kela,banana,bananas"),
    ("fruits-vegetables", "Shimla Apple", None, "4 pcs", 180, 149, "🍎", "seb,apple,apples"),
    ("fruits-vegetables", "Coriander Leaves", None, "100 g", 20, 12, "🌿", "dhania,cilantro,kothmir"),
    ("fruits-vegetables", "Green Chilli", None, "100 g", 20, 14, "🌶️", "mirchi,chilli,chili"),
    ("fruits-vegetables", "Lemon", None, "4 pcs", 30, 22, "🍋", "nimbu,lime,lemons"),
    ("dairy-bread-eggs", "Amul Taaza Toned Milk", "Amul", "500 ml", 28, 27, "🥛", "milk,doodh,dudh"),
    ("dairy-bread-eggs", "Amul Gold Full Cream Milk", "Amul", "1 l", 70, 68, "🥛", "milk,doodh,full cream"),
    ("dairy-bread-eggs", "Mother Dairy Classic Curd", "Mother Dairy", "400 g", 50, 45, "🥣", "dahi,yogurt,curd"),
    ("dairy-bread-eggs", "Amul Butter", "Amul", "100 g", 62, 58, "🧈", "makhan,butter"),
    ("dairy-bread-eggs", "Amul Paneer", "Amul", "200 g", 95, 88, "🧀", "cottage cheese,paneer"),
    ("dairy-bread-eggs", "Britannia Brown Bread", "Britannia", "400 g", 55, 50, "🍞", "bread,wheat bread"),
    ("dairy-bread-eggs", "Harvest Gold White Bread", "Harvest Gold", "350 g", 45, 40, "🍞", "bread,sandwich bread"),
    ("dairy-bread-eggs", "Farm Fresh White Eggs", None, "12 pcs", 96, 84, "🥚", "egg,anda,dozen"),
    ("dairy-bread-eggs", "Amul Cheese Slices", "Amul", "200 g", 140, 132, "🧀", "cheese"),
    ("atta-rice-dal", "Aashirvaad Whole Wheat Atta", "Aashirvaad", "5 kg", 290, 245, "🌾", "atta,flour,wheat,aata"),
    ("atta-rice-dal", "India Gate Basmati Rice", "India Gate", "1 kg", 180, 149, "🍚", "rice,chawal,basmati"),
    ("atta-rice-dal", "Sona Masoori Rice", None, "5 kg", 420, 365, "🍚", "rice,chawal"),
    ("atta-rice-dal", "Toor Dal", "Tata Sampann", "1 kg", 210, 179, "🫘", "arhar,toor,tuvar,dal,daal,lentils"),
    ("atta-rice-dal", "Moong Dal", "Tata Sampann", "500 g", 99, 85, "🫘", "moong,dal,daal,lentils"),
    ("atta-rice-dal", "Kabuli Chana", None, "500 g", 90, 72, "🫘", "chickpeas,chole,chana"),
    ("munchies", "Lay's India's Magic Masala Chips", "Lay's", "52 g", 20, 20, "🥔", "chips,crisps,wafers"),
    ("munchies", "Lay's Classic Salted Chips", "Lay's", "52 g", 20, 20, "🥔", "chips,crisps,wafers"),
    ("munchies", "Kurkure Masala Munch", "Kurkure", "90 g", 20, 20, "🌽", "kurkure,namkeen"),
    ("munchies", "Haldiram's Aloo Bhujia", "Haldiram's", "200 g", 60, 54, "🥨", "bhujia,namkeen,sev"),
    ("munchies", "Bingo Mad Angles", "Bingo", "66 g", 20, 20, "🔺", "chips,nachos"),
    ("munchies", "Act II Butter Popcorn", "Act II", "70 g", 35, 30, "🍿", "popcorn"),
    ("cold-drinks-juices", "Coca-Cola", "Coca-Cola", "750 ml", 40, 40, "🥤", "coke,cola,soft drink,cold drink"),
    ("cold-drinks-juices", "Sprite", "Sprite", "750 ml", 40, 38, "🥤", "lemon soda,soft drink,cold drink"),
    ("cold-drinks-juices", "Thums Up", "Thums Up", "750 ml", 40, 40, "🥤", "cola,soft drink,cold drink"),
    ("cold-drinks-juices", "Real Mixed Fruit Juice", "Real", "1 l", 125, 110, "🧃", "juice"),
    ("cold-drinks-juices", "Paper Boat Aamras", "Paper Boat", "200 ml", 30, 28, "🥭", "mango juice,aam,juice"),
    ("cold-drinks-juices", "Bisleri Mineral Water", "Bisleri", "1 l", 20, 20, "💧", "water,pani,paani"),
    ("cold-drinks-juices", "Red Bull Energy Drink", "Red Bull", "250 ml", 125, 120, "⚡", "energy drink,redbull"),
    ("breakfast-instant", "Maggi 2-Minute Masala Noodles", "Maggi", "280 g", 56, 54, "🍜", "maggi,noodles,instant"),
    ("breakfast-instant", "Kellogg's Corn Flakes", "Kellogg's", "475 g", 199, 179, "🥣", "cornflakes,cereal"),
    ("breakfast-instant", "Quaker Oats", "Quaker", "1 kg", 220, 189, "🥣", "oats,oatmeal,dalia"),
    ("breakfast-instant", "MTR Rava Idli Mix", "MTR", "500 g", 140, 126, "🍥", "idli,ready mix"),
    ("breakfast-instant", "Kissan Mixed Fruit Jam", "Kissan", "500 g", 165, 149, "🍓", "jam"),
    ("breakfast-instant", "Sundrop Peanut Butter Crunchy", "Sundrop", "462 g", 199, 169, "🥜", "peanut butter"),
    ("sweet-tooth", "Cadbury Dairy Milk Silk", "Cadbury", "60 g", 90, 85, "🍫", "chocolate,choco"),
    ("sweet-tooth", "KitKat", "Nestle", "37 g", 30, 30, "🍫", "chocolate,wafer"),
    ("sweet-tooth", "Amul Vanilla Ice Cream", "Amul", "1 l", 199, 180, "🍨", "ice cream,icecream"),
    ("sweet-tooth", "Haldiram's Rasgulla", "Haldiram's", "1 kg", 220, 199, "🍡", "rasgulla,sweets,mithai"),
    ("sweet-tooth", "Parle-G Biscuits", "Parle", "800 g", 90, 85, "🍪", "biscuit,biscuits,cookies"),
    ("sweet-tooth", "Britannia Good Day Cashew Cookies", "Britannia", "200 g", 50, 45, "🍪", "biscuit,biscuits,cookies"),
    ("tea-coffee", "Tata Tea Gold", "Tata Tea", "500 g", 340, 299, "🍵", "tea,chai,chai patti"),
    ("tea-coffee", "Red Label Tea", "Brooke Bond", "500 g", 300, 275, "🍵", "tea,chai"),
    ("tea-coffee", "Nescafe Classic Instant Coffee", "Nescafe", "100 g", 380, 345, "☕", "coffee"),
    ("tea-coffee", "Bru Instant Coffee", "Bru", "100 g", 285, 260, "☕", "coffee"),
    ("tea-coffee", "Bournvita Health Drink", "Cadbury", "500 g", 255, 235, "🥤", "bournvita,health drink,malt"),
    ("tea-coffee", "Horlicks Classic Malt", "Horlicks", "500 g", 285, 265, "🥤", "horlicks,health drink,malt"),
    ("masala-oil", "Fortune Sunflower Oil", "Fortune", "1 l", 175, 149, "🛢️", "oil,refined oil,cooking oil,tel"),
    ("masala-oil", "Saffola Gold Oil", "Saffola", "1 l", 210, 185, "🛢️", "oil,cooking oil"),
    ("masala-oil", "Tata Salt", "Tata", "1 kg", 30, 28, "🧂", "namak,salt"),
    ("masala-oil", "Madhur Sugar", "Madhur", "1 kg", 60, 52, "🍬", "cheeni,chini,sugar,shakkar"),
    ("masala-oil", "Everest Turmeric Powder", "Everest", "200 g", 75, 68, "🟡", "haldi,turmeric"),
    ("masala-oil", "MDH Garam Masala", "MDH", "100 g", 92, 86, "🫙", "garam masala,masala,spices"),
    ("masala-oil", "Everest Red Chilli Powder", "Everest", "200 g", 98, 89, "🌶️", "lal mirch,chilli powder"),
    ("cleaning", "Surf Excel Easy Wash Detergent", "Surf Excel", "1 kg", 150, 136, "🧺", "detergent,washing powder,surf"),
    ("cleaning", "Vim Dishwash Liquid Gel", "Vim", "500 ml", 115, 105, "🍽️", "dishwash,vim,utensil"),
    ("cleaning", "Lizol Floor Cleaner", "Lizol", "975 ml", 219, 199, "🧴", "floor cleaner,phenyl"),
    ("cleaning", "Harpic Toilet Cleaner", "Harpic", "500 ml", 106, 98, "🚽", "toilet cleaner"),
    ("cleaning", "Scotch-Brite Scrub Pad", "Scotch-Brite", "3 pcs", 60, 54, "🧽", "scrubber,scrub"),
    ("cleaning", "Garbage Bags Medium", None, "30 pcs", 120, 99, "🗑️", "dustbin bags,trash bags"),
    ("personal-care", "Dove Cream Beauty Bathing Bar", "Dove", "3 x 100 g", 210, 189, "🧼", "soap,bathing soap"),
    ("personal-care", "Colgate Strong Teeth Toothpaste", "Colgate", "200 g", 120, 109, "🪥", "toothpaste,paste"),
    ("personal-care", "Head & Shoulders Shampoo", "Head & Shoulders", "340 ml", 380, 329, "🧴", "shampoo"),
    ("personal-care", "Dettol Original Handwash", "Dettol", "200 ml", 99, 89, "🧴", "handwash,hand wash"),
    ("personal-care", "Nivea Soft Moisturising Cream", "Nivea", "100 ml", 215, 195, "🧴", "cream,moisturiser,moisturizer"),
    ("personal-care", "Gillette Mach3 Razor", "Gillette", "1 pc", 299, 269, "🪒", "razor,shaving"),
]

# (name, address, lat, lng, opens, closes, aisle order as category slugs)
STORES = [
    (
        "SmartCart Koramangala",
        "80 Feet Rd, 4th Block, Koramangala, Bengaluru 560034",
        12.9352, 77.6245, "00:00", "24:00",
        ["fruits-vegetables", "dairy-bread-eggs", "atta-rice-dal", "masala-oil", "breakfast-instant",
         "tea-coffee", "munchies", "sweet-tooth", "cold-drinks-juices", "cleaning", "personal-care"],
    ),
    (
        "SmartCart Indiranagar",
        "100 Feet Rd, HAL 2nd Stage, Indiranagar, Bengaluru 560038",
        12.9719, 77.6412, "06:00", "24:00",
        ["fruits-vegetables", "munchies", "cold-drinks-juices", "sweet-tooth", "dairy-bread-eggs",
         "breakfast-instant", "tea-coffee", "atta-rice-dal", "masala-oil", "personal-care", "cleaning"],
    ),
    (
        "SmartCart HSR Layout",
        "27th Main Rd, Sector 2, HSR Layout, Bengaluru 560102",
        12.9116, 77.6474, "06:00", "24:00",
        ["dairy-bread-eggs", "fruits-vegetables", "breakfast-instant", "atta-rice-dal", "masala-oil",
         "cleaning", "personal-care", "tea-coffee", "cold-drinks-juices", "munchies", "sweet-tooth"],
    ),
]  # fmt: skip

ROWS_PER_AISLE = 4


def seed(db: Session) -> bool:
    """Insert demo data if the database is empty. Returns True if anything was added."""
    if db.scalars(select(Store.id).limit(1)).first() is not None:
        return False

    categories: dict[str, Category] = {}
    for order, (slug, (name, emoji, color)) in enumerate(CATEGORIES.items()):
        categories[slug] = Category(name=name, slug=slug, emoji=emoji, color=color, sort_order=order)
    db.add_all(categories.values())

    products: list[Product] = []
    for slug, name, brand, unit, mrp, price, emoji, keywords in PRODUCTS:
        products.append(
            Product(
                category=categories[slug],
                name=name,
                brand=brand,
                unit=unit,
                description=f"{name} ({unit}). Fresh stock, delivered in minutes.",
                mrp_paise=mrp * 100,
                price_paise=price * 100,
                emoji=emoji,
                keywords=keywords,
            )
        )
    db.add_all(products)

    rng = random.Random(42)  # deterministic demo stock
    for store_index, (name, address, lat, lng, opens, closes, aisle_order) in enumerate(STORES):
        store = Store(name=name, address=address, city="Bengaluru", lat=lat, lng=lng, opens_at=opens, closes_at=closes)
        aisles = {
            slug: Aisle(number=i + 1, name=categories[slug].name, row_count=ROWS_PER_AISLE)
            for i, slug in enumerate(aisle_order)
        }
        store.aisles = list(aisles.values())
        db.add(store)

        for slug in aisle_order:
            in_category = [p for p in products if p.category is categories[slug]]
            for i, product in enumerate(in_category):
                stock = 0 if rng.random() < 0.05 else rng.randint(5, 60)
                db.add(
                    Inventory(
                        store=store,
                        product=product,
                        aisle=aisles[slug],
                        # Spread products over the rows; each store shelves things a little differently.
                        row_number=(i + store_index) % ROWS_PER_AISLE + 1,
                        stock=stock,
                    )
                )

    db.add(User(phone=STAFF_PHONE, name="Store Staff", role=Role.STAFF))
    db.commit()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="drop all tables first")
    args = parser.parse_args()
    if args.reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        print("Seeded demo data" if seed(db) else "Database already has data; use --reset to start over")


if __name__ == "__main__":
    main()
