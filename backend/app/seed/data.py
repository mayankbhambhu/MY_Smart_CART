"""Demo catalog and stores. Prices are illustrative (₹, late 2026).

Product rows: (name, brand, unit, mrp, price, emoji, tags, popularity[, is_veg])
Tags are extra search words: synonyms, Hindi names and common misspellings.
"""

from datetime import time

CATEGORIES = [
    {
        "name": "Fruits & Vegetables",
        "slug": "fruits-vegetables",
        "emoji": "🥦",
        "color": "#E7F6E1",
        "about": "Fresh {name}, hand-picked every morning and kept cool until it reaches you.",
        "children": [
            {
                "name": "Fresh Vegetables",
                "slug": "fresh-vegetables",
                "emoji": "🥕",
                "products": [
                    ("Onion", None, "1 kg", 60, 45, "🧅", "onion, pyaz, pyaaz, kanda, onions", 98),
                    ("Tomato (Hybrid)", None, "500 g", 40, 32, "🍅", "tomato, tamatar, tomatoes", 97),
                    ("Potato", None, "1 kg", 50, 39, "🥔", "potato, aloo, alu, batata", 96),
                    ("Green Capsicum", None, "250 g", 40, 29, "🫑", "capsicum, shimla mirch, bell pepper", 70),
                    ("Cauliflower", None, "1 pc (400-600 g)", 50, 38, "🥦", "cauliflower, gobhi, gobi, phool gobhi", 65),
                    ("Carrot", None, "500 g", 45, 34, "🥕", "carrot, gajar", 72),
                    ("Cucumber", None, "500 g", 40, 30, "🥒", "cucumber, kheera, kakdi", 68),
                    ("Spinach", None, "250 g", 30, 22, "🥬", "spinach, palak, saag", 60),
                    ("Lady Finger", None, "250 g", 35, 27, "🫛", "lady finger, bhindi, okra", 62),
                    ("Bottle Gourd", None, "1 pc", 45, 35, "🥒", "bottle gourd, lauki, ghiya, dudhi", 50),
                ],
            },
            {
                "name": "Fresh Fruits",
                "slug": "fresh-fruits",
                "emoji": "🍎",
                "products": [
                    ("Banana (Robusta)", None, "6 pcs", 60, 48, "🍌", "banana, kela, bananas", 95),
                    ("Shimla Apple", None, "4 pcs (500-600 g)", 180, 149, "🍎", "apple, seb, apples", 85),
                    ("Nagpur Orange", None, "1 kg", 140, 109, "🍊", "orange, santra, narangi", 78),
                    ("Green Grapes", None, "500 g", 99, 79, "🍇", "grapes, angoor", 72),
                    ("Pineapple", None, "1 pc", 120, 89, "🍍", "pineapple, ananas", 55),
                    ("Kiwi", None, "3 pcs", 120, 99, "🥝", "kiwi", 50),
                    ("Watermelon", None, "1 pc (2-3 kg)", 120, 89, "🍉", "watermelon, tarbooz, tarbuj", 60),
                ],
            },
            {
                "name": "Herbs & Seasonings",
                "slug": "herbs-seasonings",
                "emoji": "🌿",
                "products": [
                    ("Coriander Leaves", None, "100 g", 20, 15, "🌿", "coriander, dhaniya, dhania, cilantro", 88),
                    ("Mint Leaves", None, "100 g", 20, 15, "🌿", "mint, pudina", 60),
                    ("Green Chilli", None, "100 g", 20, 14, "🌶️", "green chilli, hari mirch, mirchi, chilli, chili", 85),
                    ("Ginger", None, "200 g", 40, 30, "🫚", "ginger, adrak", 80),
                    ("Garlic", None, "200 g", 60, 45, "🧄", "garlic, lehsun, lahsun", 78),
                    ("Lemon", None, "4 pcs", 30, 22, "🍋", "lemon, nimbu, lime, lemons", 82),
                ],
            },
        ],
    },
    {
        "name": "Dairy, Bread & Eggs",
        "slug": "dairy-bread-eggs",
        "emoji": "🥛",
        "color": "#E5F0FB",
        "about": "{name} from {brand}, stored in the cold chain from the dairy to your door.",
        "children": [
            {
                "name": "Milk",
                "slug": "milk",
                "emoji": "🥛",
                "products": [
                    ("Amul Taaza Toned Milk", "Amul", "500 ml", 28, 28, "🥛", "milk, doodh, dudh, toned milk, amul milk", 99),
                    ("Amul Gold Full Cream Milk", "Amul", "500 ml", 35, 35, "🥛", "milk, doodh, full cream milk", 90),
                    ("Mother Dairy Toned Milk", "Mother Dairy", "500 ml", 28, 28, "🥛", "milk, doodh, toned milk", 88),
                    ("Amul Taaza Toned Milk", "Amul", "1 L", 56, 56, "🥛", "milk, doodh, toned milk, amul milk", 84),
                    ("Amul Kool Kesar Flavoured Milk", "Amul", "180 ml", 30, 28, "🥛", "flavoured milk, kool, kesar milk", 55),
                ],
            },
            {
                "name": "Curd & Yogurt",
                "slug": "curd-yogurt",
                "emoji": "🥣",
                "products": [
                    ("Amul Masti Dahi", "Amul", "400 g", 35, 35, "🥣", "curd, dahi, yogurt, yoghurt", 90),
                    ("Mother Dairy Classic Curd", "Mother Dairy", "400 g", 45, 40, "🥣", "curd, dahi, yogurt", 80),
                    ("Epigamia Greek Yogurt Strawberry", "Epigamia", "85 g", 50, 45, "🍓", "greek yogurt, yogurt, yoghurt", 50),
                    ("Amul Masti Spiced Buttermilk", "Amul", "500 ml", 30, 28, "🥛", "buttermilk, chaas, chhach, chaach", 60),
                ],
            },
            {
                "name": "Butter & Cheese",
                "slug": "butter-cheese",
                "emoji": "🧈",
                "products": [
                    ("Amul Butter", "Amul", "100 g", 60, 58, "🧈", "butter, makhan, makkhan, amul butter", 92),
                    ("Amul Butter", "Amul", "500 g", 285, 275, "🧈", "butter, makhan, amul butter", 70),
                    ("Amul Cheese Slices", "Amul", "200 g (10 slices)", 160, 150, "🧀", "cheese, cheese slice, cheese slices", 75),
                    ("Amul Mozzarella Cheese", "Amul", "200 g", 125, 119, "🧀", "mozzarella, pizza cheese, cheese", 55),
                ],
            },
            {
                "name": "Paneer & Cream",
                "slug": "paneer-cream",
                "emoji": "🧀",
                "products": [
                    ("Amul Malai Paneer", "Amul", "200 g", 95, 90, "🧀", "paneer, panir, cottage cheese", 88),
                    ("Mother Dairy Fresh Paneer", "Mother Dairy", "200 g", 90, 85, "🧀", "paneer, panir, cottage cheese", 78),
                    ("Amul Fresh Cream", "Amul", "250 ml", 72, 70, "🥛", "cream, fresh cream, malai", 50),
                ],
            },
            {
                "name": "Bread & Pav",
                "slug": "bread-pav",
                "emoji": "🍞",
                "products": [
                    ("Harvest Gold White Bread", "Harvest Gold", "400 g", 45, 43, "🍞", "bread, white bread, sandwich bread, double roti", 90),
                    ("Britannia Milk Bread", "Britannia", "400 g", 50, 48, "🍞", "bread, milk bread, double roti", 85),
                    ("Britannia 100% Whole Wheat Bread", "Britannia", "400 g", 60, 57, "🍞", "brown bread, wheat bread, atta bread, bread", 80),
                    ("English Oven Pav", "English Oven", "6 pcs", 30, 28, "🥖", "pav, pao, ladi pav, buns", 70),
                ],
            },
            {
                "name": "Eggs",
                "slug": "eggs",
                "emoji": "🥚",
                "products": [
                    ("Farm Fresh White Eggs", "Farm Fresh", "6 pcs", 54, 48, "🥚", "eggs, egg, anda, ande", 92, False),
                    ("Farm Fresh White Eggs", "Farm Fresh", "30 pcs", 250, 219, "🥚", "eggs, egg, anda, egg tray", 60, False),
                    ("Eggoz Brown Eggs", "Eggoz", "6 pcs", 90, 80, "🥚", "brown eggs, eggs, anda, desi eggs", 55, False),
                ],
            },
        ],
    },
    {
        "name": "Atta, Rice & Dal",
        "slug": "atta-rice-dal",
        "emoji": "🌾",
        "color": "#FFF3DA",
        "about": "{brand} {name} ({unit}). Pantry staple, sealed for freshness.",
        "children": [
            {
                "name": "Atta & Flours",
                "slug": "atta-flours",
                "emoji": "🌾",
                "products": [
                    ("Aashirvaad Shudh Chakki Atta", "Aashirvaad", "5 kg", 290, 255, "🌾", "atta, aata, wheat flour, gehu, chakki atta, whole wheat atta", 95),
                    ("Aashirvaad Shudh Chakki Atta", "Aashirvaad", "10 kg", 540, 489, "🌾", "atta, aata, wheat flour, gehu", 70),
                    ("Fortune Chakki Fresh Atta", "Fortune", "5 kg", 270, 239, "🌾", "atta, aata, wheat flour", 75),
                    ("Rajdhani Besan", "Rajdhani", "500 g", 75, 65, "🌾", "besan, gram flour, chickpea flour", 65),
                    ("Rajdhani Maida", "Rajdhani", "500 g", 35, 30, "🌾", "maida, all purpose flour, refined flour", 50),
                    ("Rajdhani Suji", "Rajdhani", "500 g", 40, 35, "🌾", "suji, sooji, rava, semolina", 55),
                ],
            },
            {
                "name": "Rice & Poha",
                "slug": "rice-poha",
                "emoji": "🍚",
                "products": [
                    ("India Gate Basmati Rice Classic", "India Gate", "1 kg", 220, 185, "🍚", "rice, chawal, basmati, basmati rice", 85),
                    ("Daawat Rozana Super Basmati Rice", "Daawat", "5 kg", 520, 439, "🍚", "rice, chawal, basmati", 75),
                    ("Fortune Sona Masoori Rice", "Fortune", "5 kg", 450, 389, "🍚", "rice, chawal, sona masoori", 60),
                    ("Rajdhani Poha (Thick)", "Rajdhani", "500 g", 45, 39, "🍚", "poha, flattened rice, chivda", 60),
                ],
            },
            {
                "name": "Dals & Pulses",
                "slug": "dals-pulses",
                "emoji": "🫘",
                "products": [
                    ("Tata Sampann Toor Dal", "Tata Sampann", "1 kg", 210, 179, "🫘", "toor dal, arhar dal, tuvar dal, dal, daal", 88),
                    ("Tata Sampann Moong Dal", "Tata Sampann", "1 kg", 190, 165, "🫘", "moong dal, mung dal, dal, daal", 75),
                    ("Tata Sampann Chana Dal", "Tata Sampann", "1 kg", 130, 112, "🫘", "chana dal, dal, daal", 70),
                    ("Rajdhani Masoor Dal", "Rajdhani", "1 kg", 140, 119, "🫘", "masoor dal, red lentil, dal, daal", 65),
                    ("Tata Sampann Rajma Chitra", "Tata Sampann", "500 g", 110, 95, "🫘", "rajma, kidney beans", 70),
                    ("Rajdhani Kabuli Chana", "Rajdhani", "500 g", 95, 82, "🫘", "kabuli chana, chole, chickpeas, chana", 68),
                ],
            },
        ],
    },
    {
        "name": "Oil, Ghee & Masala",
        "slug": "oil-ghee-masala",
        "emoji": "🫙",
        "color": "#FFEEE3",
        "about": "{brand} {name} ({unit}) for everyday Indian cooking.",
        "children": [
            {
                "name": "Cooking Oil",
                "slug": "cooking-oil",
                "emoji": "🌻",
                "products": [
                    ("Fortune Sunlite Refined Sunflower Oil", "Fortune", "1 L", 185, 155, "🌻", "oil, sunflower oil, refined oil, tel", 90),
                    ("Fortune Kachi Ghani Mustard Oil", "Fortune", "1 L", 210, 179, "🫗", "mustard oil, sarson tel, sarson ka tel, kachi ghani, oil", 85),
                    ("Saffola Gold Refined Oil", "Saffola", "1 L", 220, 189, "🌻", "oil, saffola, refined oil", 70),
                    ("Figaro Extra Virgin Olive Oil", "Figaro", "500 ml", 750, 649, "🫒", "olive oil, oil", 40),
                ],
            },
            {
                "name": "Ghee",
                "slug": "ghee",
                "emoji": "🧈",
                "products": [
                    ("Amul Pure Ghee", "Amul", "1 L", 650, 615, "🧈", "ghee, desi ghee, amul ghee", 85),
                    ("Patanjali Cow's Ghee", "Patanjali", "500 ml", 340, 319, "🧈", "ghee, cow ghee, desi ghee", 60),
                ],
            },
            {
                "name": "Masala & Spices",
                "slug": "masala-spices",
                "emoji": "🌶️",
                "products": [
                    ("Everest Turmeric Powder", "Everest", "100 g", 42, 38, "🫙", "turmeric, haldi, turmeric powder", 80),
                    ("MDH Deggi Mirch", "MDH", "100 g", 95, 86, "🌶️", "red chilli powder, lal mirch, mirch, deggi mirch, chilli powder", 75),
                    ("Everest Garam Masala", "Everest", "100 g", 98, 88, "🫙", "garam masala, masala", 72),
                    ("Catch Coriander Powder", "Catch", "100 g", 40, 36, "🫙", "coriander powder, dhania powder, dhaniya powder", 60),
                    ("MDH Chana Masala", "MDH", "100 g", 85, 78, "🫙", "chana masala, chole masala", 55),
                    ("Catch Jeera Whole", "Catch", "100 g", 95, 85, "🫙", "jeera, cumin, zeera, cumin seeds", 65),
                ],
            },
            {
                "name": "Salt & Sugar",
                "slug": "salt-sugar",
                "emoji": "🧂",
                "products": [
                    ("Tata Salt", "Tata", "1 kg", 30, 28, "🧂", "salt, namak, iodised salt", 95),
                    ("Madhur Pure Sugar", "Madhur", "1 kg", 60, 52, "🍬", "sugar, cheeni, chini, shakkar", 92),
                    ("Madhur Pure Sugar", "Madhur", "5 kg", 290, 249, "🍬", "sugar, cheeni, chini", 60),
                    ("Tata Rock Salt", "Tata", "1 kg", 99, 85, "🧂", "rock salt, sendha namak, salt", 40),
                    ("Organic Tattva Jaggery Powder", "Organic Tattva", "500 g", 90, 79, "🍯", "jaggery, gur, gud", 45),
                ],
            },
        ],
    },
    {
        "name": "Snacks & Munchies",
        "slug": "snacks-munchies",
        "emoji": "🍿",
        "color": "#FFF5D1",
        "about": "{brand} {name} ({unit}). Perfect for tea time and movie nights.",
        "children": [
            {
                "name": "Chips & Crisps",
                "slug": "chips-crisps",
                "emoji": "🍟",
                "products": [
                    ("Lay's India's Magic Masala Chips", "Lay's", "52 g", 20, 20, "🍟", "chips, lays, wafers, magic masala", 95),
                    ("Lay's Classic Salted Chips", "Lay's", "52 g", 20, 20, "🍟", "chips, lays, salted chips, wafers", 90),
                    ("Kurkure Masala Munch", "Kurkure", "75 g", 20, 20, "🌽", "kurkure, masala munch, namkeen", 88),
                    ("Bingo! Mad Angles Achaari Masti", "Bingo!", "66 g", 20, 20, "🍟", "mad angles, bingo, chips", 70),
                    ("Pringles Original", "Pringles", "107 g", 110, 99, "🍟", "pringles, chips", 55),
                    ("Doritos Nacho Cheese", "Doritos", "44 g", 30, 30, "🔺", "doritos, nachos, chips", 50),
                ],
            },
            {
                "name": "Namkeen",
                "slug": "namkeen",
                "emoji": "🥨",
                "products": [
                    ("Haldiram's Aloo Bhujia", "Haldiram's", "400 g", 115, 105, "🥨", "bhujia, aloo bhujia, namkeen, haldiram", 85),
                    ("Haldiram's Khatta Meetha", "Haldiram's", "400 g", 115, 105, "🥨", "khatta meetha, namkeen, mixture", 70),
                    ("Haldiram's Navrattan", "Haldiram's", "400 g", 115, 105, "🥨", "navrattan, navratan, namkeen, mixture", 65),
                    ("Haldiram's Moong Dal", "Haldiram's", "200 g", 60, 55, "🥨", "moong dal namkeen, namkeen", 60),
                ],
            },
            {
                "name": "Biscuits & Cookies",
                "slug": "biscuits-cookies",
                "emoji": "🍪",
                "products": [
                    ("Parle-G Original Glucose Biscuits", "Parle", "250 g", 25, 25, "🍪", "biscuit, parle g, parleg, glucose biscuit", 92),
                    ("Britannia Good Day Cashew Cookies", "Britannia", "200 g", 40, 38, "🍪", "cookies, good day, biscuit", 80),
                    ("Oreo Chocolate Cream Biscuits", "Oreo", "120 g", 35, 33, "🍪", "oreo, biscuit, cream biscuit", 78),
                    ("Sunfeast Dark Fantasy Choco Fills", "Sunfeast", "75 g", 40, 38, "🍪", "dark fantasy, choco fills, cookies", 75),
                    ("Britannia Marie Gold", "Britannia", "250 g", 40, 38, "🍪", "marie, marie gold, tea biscuit, biscuit", 70),
                    ("Britannia Toastea Rusk", "Britannia", "300 g", 60, 55, "🍞", "rusk, toast, toastea", 65),
                ],
            },
        ],
    },
    {
        "name": "Sweets & Chocolates",
        "slug": "sweets-chocolates",
        "emoji": "🍫",
        "color": "#F6E9F3",
        "about": "{brand} {name} ({unit}). A little treat, delivered in minutes.",
        "children": [
            {
                "name": "Chocolates",
                "slug": "chocolates",
                "emoji": "🍫",
                "products": [
                    ("Cadbury Dairy Milk Chocolate", "Cadbury", "52 g", 50, 50, "🍫", "chocolate, dairy milk, cadbury, choco", 90),
                    ("Cadbury Dairy Milk Silk", "Cadbury", "60 g", 90, 85, "🍫", "silk, dairy milk silk, chocolate", 80),
                    ("Nestlé KitKat", "Nestlé", "37.3 g", 30, 30, "🍫", "kitkat, kit kat, chocolate, wafer", 82),
                    ("Cadbury 5 Star", "Cadbury", "40 g", 20, 20, "🍫", "5 star, five star, chocolate", 70),
                    ("Amul Dark Chocolate 55%", "Amul", "150 g", 200, 190, "🍫", "dark chocolate, chocolate", 50),
                    ("Ferrero Rocher", "Ferrero", "4 pcs (50 g)", 199, 180, "🍫", "ferrero, ferrero rocher, chocolate, gift", 45),
                ],
            },
            {
                "name": "Indian Sweets",
                "slug": "indian-sweets",
                "emoji": "🍡",
                "products": [
                    ("Haldiram's Gulab Jamun", "Haldiram's", "1 kg", 250, 225, "🍡", "gulab jamun, sweets, mithai", 70),
                    ("Haldiram's Rasgulla", "Haldiram's", "1 kg", 250, 225, "🍡", "rasgulla, rosogolla, sweets, mithai", 65),
                    ("Haldiram's Soan Papdi", "Haldiram's", "500 g", 175, 155, "🍬", "soan papdi, son papdi, sweets, mithai", 55),
                    ("Bikano Kaju Katli", "Bikano", "250 g", 400, 360, "🍬", "kaju katli, kaju barfi, sweets, mithai", 50),
                ],
            },
        ],
    },
    {
        "name": "Cold Drinks & Juices",
        "slug": "cold-drinks-juices",
        "emoji": "🥤",
        "color": "#E6F3FF",
        "about": "{brand} {name} ({unit}), served chilled where available.",
        "children": [
            {
                "name": "Soft Drinks",
                "slug": "soft-drinks",
                "emoji": "🥤",
                "products": [
                    ("Coca-Cola", "Coca-Cola", "750 ml", 45, 42, "🥤", "coke, cola, coca cola, cold drink, soft drink", 92),
                    ("Thums Up", "Thums Up", "750 ml", 45, 42, "🥤", "thums up, thumbs up, cola, cold drink, soft drink", 90),
                    ("Sprite", "Sprite", "750 ml", 45, 42, "🥤", "sprite, lemon soda, cold drink, soft drink", 85),
                    ("Maaza Mango Drink", "Maaza", "600 ml", 42, 40, "🥭", "maaza, mango drink, mango juice", 80),
                    ("Pepsi", "Pepsi", "750 ml", 40, 40, "🥤", "pepsi, cola, cold drink, soft drink", 70),
                    ("Coca-Cola Zero Sugar Can", "Coca-Cola", "300 ml", 40, 38, "🥤", "coke zero, diet coke, cola", 50),
                ],
            },
            {
                "name": "Juices",
                "slug": "juices",
                "emoji": "🧃",
                "products": [
                    ("Real Fruit Power Mixed Fruit Juice", "Real", "1 L", 130, 115, "🧃", "juice, mixed fruit juice, real juice", 70),
                    ("Tropicana 100% Orange Juice", "Tropicana", "1 L", 150, 135, "🧃", "orange juice, juice, tropicana", 65),
                    ("Real Fruit Power Apple Juice", "Real", "1 L", 130, 115, "🧃", "apple juice, juice", 55),
                    ("Paper Boat Aamras", "Paper Boat", "250 ml", 40, 38, "🥭", "aamras, aam ras, mango, paper boat", 50),
                ],
            },
            {
                "name": "Water & Soda",
                "slug": "water-soda",
                "emoji": "💧",
                "products": [
                    ("Bisleri Mineral Water", "Bisleri", "1 L", 20, 20, "💧", "water, pani, paani, mineral water, bisleri", 90),
                    ("Bisleri Mineral Water", "Bisleri", "5 L", 75, 70, "💧", "water, pani, paani, water can", 60),
                    ("Kinley Club Soda", "Kinley", "750 ml", 20, 20, "🫧", "soda, club soda", 55),
                ],
            },
            {
                "name": "Energy Drinks",
                "slug": "energy-drinks",
                "emoji": "⚡",
                "products": [
                    ("Red Bull Energy Drink", "Red Bull", "250 ml", 125, 120, "⚡", "red bull, redbull, energy drink", 60),
                    ("Sting Energy Drink", "Sting", "250 ml", 20, 20, "⚡", "sting, energy drink", 55),
                    ("Monster Energy", "Monster", "350 ml", 125, 120, "⚡", "monster, energy drink", 45),
                ],
            },
        ],
    },
    {
        "name": "Tea, Coffee & Health Drinks",
        "slug": "tea-coffee",
        "emoji": "☕",
        "color": "#F3EBE4",
        "about": "{brand} {name} ({unit}) for your morning cup.",
        "children": [
            {
                "name": "Tea",
                "slug": "tea",
                "emoji": "🍵",
                "products": [
                    ("Tata Tea Gold", "Tata Tea", "500 g", 330, 289, "🍵", "tea, chai, chai patti, chaipatti, tata tea", 88),
                    ("Brooke Bond Red Label Tea", "Brooke Bond", "500 g", 310, 275, "🍵", "tea, chai, chai patti, red label", 82),
                    ("Tetley Green Tea Lemon & Honey", "Tetley", "25 bags", 175, 155, "🍵", "green tea, tea bags, tea", 55),
                ],
            },
            {
                "name": "Coffee",
                "slug": "coffee",
                "emoji": "☕",
                "products": [
                    ("Nescafé Classic Instant Coffee", "Nescafé", "50 g", 190, 175, "☕", "coffee, nescafe, instant coffee", 85),
                    ("Bru Instant Coffee", "Bru", "50 g", 140, 128, "☕", "coffee, bru, instant coffee", 75),
                ],
            },
            {
                "name": "Health Drinks",
                "slug": "health-drinks",
                "emoji": "🥤",
                "products": [
                    ("Cadbury Bournvita", "Cadbury", "500 g", 255, 235, "🍫", "bournvita, health drink, chocolate drink", 70),
                    ("Horlicks Classic Malt", "Horlicks", "500 g", 285, 265, "🥛", "horlicks, health drink, malt", 65),
                ],
            },
        ],
    },
    {
        "name": "Instant & Frozen Food",
        "slug": "instant-frozen",
        "emoji": "🍜",
        "color": "#FFEBE5",
        "about": "{brand} {name} ({unit}). Ready in minutes.",
        "children": [
            {
                "name": "Noodles & Pasta",
                "slug": "noodles-pasta",
                "emoji": "🍜",
                "products": [
                    ("Maggi 2-Minute Masala Noodles", "Maggi", "280 g (4 pack)", 60, 56, "🍜", "maggi, maggie, noodles, instant noodles", 97),
                    ("Maggi 2-Minute Masala Noodles", "Maggi", "70 g", 15, 15, "🍜", "maggi, maggie, noodles", 70),
                    ("Yippee! Magic Masala Noodles", "Sunfeast", "240 g (4 pack)", 60, 56, "🍜", "yippee, noodles, instant noodles", 70),
                    ("Ching's Secret Hakka Noodles", "Ching's Secret", "150 g", 45, 42, "🍜", "hakka noodles, chings, noodles, chinese", 55),
                    ("Del Monte Penne Pasta", "Del Monte", "500 g", 135, 115, "🍝", "pasta, penne, macaroni", 50),
                ],
            },
            {
                "name": "Ready to Eat",
                "slug": "ready-to-eat",
                "emoji": "🍲",
                "products": [
                    ("MTR Ready to Eat Dal Makhani", "MTR", "300 g", 140, 125, "🍲", "dal makhani, ready to eat, mtr", 50),
                    ("MTR Ready to Eat Paneer Butter Masala", "MTR", "300 g", 165, 150, "🍲", "paneer butter masala, ready to eat, mtr", 45),
                    ("Knorr Classic Tomato Soup", "Knorr", "53 g", 65, 60, "🍲", "soup, tomato soup, knorr", 45),
                ],
            },
            {
                "name": "Frozen Snacks",
                "slug": "frozen-snacks",
                "emoji": "🧊",
                "products": [
                    ("McCain French Fries", "McCain", "420 g", 145, 129, "🍟", "french fries, fries, mccain, frozen fries", 70),
                    ("McCain Aloo Tikki", "McCain", "400 g", 130, 115, "🥔", "aloo tikki, tikki, frozen", 55),
                    ("Sumeru Frozen Green Peas", "Sumeru", "500 g", 110, 95, "🫛", "frozen peas, matar, green peas, peas", 60),
                    ("Prasuma Veg Momos", "Prasuma", "10 pcs", 199, 179, "🥟", "momos, veg momos, frozen", 55),
                    ("Prasuma Chicken Momos", "Prasuma", "10 pcs", 250, 219, "🥟", "momos, chicken momos, frozen", 50, False),
                ],
            },
            {
                "name": "Ice Creams",
                "slug": "ice-creams",
                "emoji": "🍦",
                "products": [
                    ("Kwality Wall's Cornetto Double Chocolate", "Kwality Wall's", "105 ml", 50, 50, "🍦", "cornetto, ice cream, icecream, cone", 75),
                    ("Amul Vanilla Magic Ice Cream", "Amul", "1 L", 210, 199, "🍦", "ice cream, icecream, vanilla", 70),
                    ("Magnum Almond", "Magnum", "80 ml", 90, 90, "🍦", "magnum, ice cream, icecream, chocobar", 60),
                    ("Havmor Butterscotch Ice Cream", "Havmor", "700 ml", 250, 225, "🍨", "ice cream, icecream, butterscotch", 55),
                ],
            },
        ],
    },
    {
        "name": "Breakfast & Spreads",
        "slug": "breakfast-spreads",
        "emoji": "🥣",
        "color": "#FCF0E2",
        "about": "{brand} {name} ({unit}) for a quick, tasty breakfast.",
        "children": [
            {
                "name": "Cereals & Oats",
                "slug": "cereals-oats",
                "emoji": "🥣",
                "products": [
                    ("Kellogg's Corn Flakes Original", "Kellogg's", "475 g", 210, 190, "🥣", "cornflakes, corn flakes, cereal, kelloggs", 75),
                    ("Quaker Oats", "Quaker", "1 kg", 220, 199, "🥣", "oats, quaker, oatmeal", 70),
                    ("Kellogg's Chocos", "Kellogg's", "375 g", 199, 185, "🥣", "chocos, cereal, chocolate cereal", 60),
                    ("Saffola Masala Oats Classic", "Saffola", "500 g", 210, 189, "🥣", "masala oats, oats, saffola", 55),
                ],
            },
            {
                "name": "Sauces & Ketchup",
                "slug": "sauces-ketchup",
                "emoji": "🍅",
                "products": [
                    ("Kissan Fresh Tomato Ketchup", "Kissan", "950 g", 160, 145, "🍅", "ketchup, tomato ketchup, sauce, kissan", 80),
                    ("Maggi Hot & Sweet Tomato Chilli Sauce", "Maggi", "500 g", 120, 110, "🌶️", "hot and sweet, chilli sauce, maggi sauce, sauce", 60),
                    ("Ching's Secret Schezwan Chutney", "Ching's Secret", "250 g", 99, 89, "🌶️", "schezwan, schezwan chutney, chings", 55),
                    ("Dr. Oetker FunFoods Veg Mayonnaise", "FunFoods", "275 g", 99, 89, "🫙", "mayonnaise, mayo, mayonaise", 65),
                ],
            },
            {
                "name": "Jams & Spreads",
                "slug": "jams-spreads",
                "emoji": "🍯",
                "products": [
                    ("Dabur Honey", "Dabur", "500 g", 245, 215, "🍯", "honey, shahad, dabur honey", 70),
                    ("Kissan Mixed Fruit Jam", "Kissan", "500 g", 175, 160, "🍓", "jam, mixed fruit jam, kissan", 65),
                    ("Nutella Hazelnut Spread", "Nutella", "350 g", 399, 369, "🍫", "nutella, chocolate spread, hazelnut", 55),
                    ("Pintola Crunchy Peanut Butter", "Pintola", "350 g", 240, 215, "🥜", "peanut butter, pintola", 55),
                ],
            },
        ],
    },
    {
        "name": "Personal Care",
        "slug": "personal-care",
        "emoji": "🧴",
        "color": "#EDEFFF",
        "about": "{brand} {name} ({unit}). 100% genuine products.",
        "children": [
            {
                "name": "Soaps & Body Wash",
                "slug": "soaps-body-wash",
                "emoji": "🧼",
                "products": [
                    ("Dove Cream Beauty Bathing Bar", "Dove", "3 x 100 g", 165, 149, "🧼", "soap, dove, bathing bar", 75),
                    ("Dettol Original Soap", "Dettol", "4 x 125 g", 200, 179, "🧼", "soap, dettol, antibacterial soap", 72),
                    ("Lifebuoy Total 10 Soap", "Lifebuoy", "4 x 125 g", 140, 125, "🧼", "soap, lifebuoy", 70),
                    ("Pears Pure & Gentle Soap", "Pears", "3 x 125 g", 195, 175, "🧼", "soap, pears, glycerine soap", 60),
                    ("Dettol Liquid Handwash", "Dettol", "200 ml", 99, 89, "🧴", "handwash, hand wash, dettol", 65),
                ],
            },
            {
                "name": "Hair Care",
                "slug": "hair-care",
                "emoji": "💇",
                "products": [
                    ("Head & Shoulders Anti-Dandruff Shampoo", "Head & Shoulders", "340 ml", 399, 359, "🧴", "shampoo, anti dandruff shampoo", 65),
                    ("Clinic Plus Strong & Long Shampoo", "Clinic Plus", "355 ml", 220, 199, "🧴", "shampoo, clinic plus", 60),
                    ("Parachute Coconut Oil", "Parachute", "300 ml", 150, 139, "🥥", "coconut oil, hair oil, parachute, nariyal tel", 75),
                    ("Dove Hair Fall Rescue Conditioner", "Dove", "180 ml", 260, 235, "🧴", "conditioner, hair conditioner", 45),
                ],
            },
            {
                "name": "Oral Care",
                "slug": "oral-care",
                "emoji": "🪥",
                "products": [
                    ("Colgate Strong Teeth Toothpaste", "Colgate", "200 g", 125, 115, "🪥", "toothpaste, colgate, paste, manjan", 85),
                    ("Closeup Red Hot Gel Toothpaste", "Closeup", "150 g", 120, 109, "🪥", "toothpaste, closeup, gel toothpaste", 60),
                    ("Oral-B Pro-Health Toothbrush (Medium)", "Oral-B", "2 pcs", 100, 89, "🪥", "toothbrush, brush, oral b", 65),
                    ("Listerine Cool Mint Mouthwash", "Listerine", "250 ml", 175, 155, "🫧", "mouthwash, mouth wash, listerine", 45),
                ],
            },
            {
                "name": "Skin Care",
                "slug": "skin-care",
                "emoji": "🧴",
                "products": [
                    ("Himalaya Purifying Neem Face Wash", "Himalaya", "150 ml", 199, 179, "🧴", "face wash, facewash, himalaya, neem", 65),
                    ("Nivea Soft Light Moisturising Cream", "Nivea", "100 ml", 225, 199, "🧴", "moisturiser, moisturizer, cream, nivea", 55),
                    ("Vaseline Intensive Care Body Lotion", "Vaseline", "400 ml", 425, 375, "🧴", "body lotion, lotion, vaseline", 50),
                    ("Lakmé Sun Expert SPF 50 Sunscreen", "Lakmé", "50 ml", 299, 269, "🧴", "sunscreen, sunblock, lakme", 45),
                ],
            },
        ],
    },
    {
        "name": "Cleaning Essentials",
        "slug": "cleaning-essentials",
        "emoji": "🧽",
        "color": "#E3F6F2",
        "about": "{brand} {name} ({unit}) to keep your home sparkling clean.",
        "children": [
            {
                "name": "Detergents",
                "slug": "detergents",
                "emoji": "🧺",
                "products": [
                    ("Surf Excel Easy Wash Detergent Powder", "Surf Excel", "1 kg", 140, 128, "🧺", "detergent, surf, surf excel, washing powder", 80),
                    ("Tide Plus Double Power Detergent Powder", "Tide", "1 kg", 125, 112, "🧺", "detergent, tide, washing powder", 70),
                    ("Ariel Matic Liquid Detergent Front Load", "Ariel", "1 L", 260, 229, "🧴", "liquid detergent, ariel, matic", 60),
                    ("Comfort Fabric Conditioner", "Comfort", "860 ml", 240, 215, "🧴", "fabric conditioner, softener, comfort", 45),
                ],
            },
            {
                "name": "Dishwash",
                "slug": "dishwash",
                "emoji": "🍽️",
                "products": [
                    ("Vim Dishwash Bar", "Vim", "3 x 200 g", 60, 55, "🍋", "vim, dishwash bar, bartan soap", 75),
                    ("Vim Lemon Dishwash Gel", "Vim", "500 ml", 115, 105, "🍋", "dishwash liquid, vim gel, dish wash, bartan", 70),
                    ("Scotch-Brite Scrub Pad", "Scotch-Brite", "3 pcs", 60, 54, "🧽", "scrub, scrubber, scotch brite", 55),
                ],
            },
            {
                "name": "Floor & Toilet Cleaners",
                "slug": "floor-toilet-cleaners",
                "emoji": "🧹",
                "products": [
                    ("Lizol Disinfectant Floor Cleaner Citrus", "Lizol", "975 ml", 229, 205, "🧴", "floor cleaner, lizol, phenyl, pocha", 70),
                    ("Harpic Power Plus Toilet Cleaner", "Harpic", "500 ml", 99, 92, "🚽", "toilet cleaner, harpic", 72),
                    ("Colin Glass & Surface Cleaner", "Colin", "500 ml", 115, 103, "🪟", "glass cleaner, colin", 50),
                ],
            },
            {
                "name": "Repellents",
                "slug": "repellents",
                "emoji": "🦟",
                "products": [
                    ("Good Knight Gold Flash Refill", "Good Knight", "45 ml", 90, 85, "🦟", "mosquito, good knight, goodknight, repellent, liquid vaporizer", 60),
                    ("All Out Ultra Refill", "All Out", "45 ml", 85, 79, "🦟", "mosquito, all out, allout, refill", 50),
                    ("Odomos Mosquito Repellent Cream", "Odomos", "100 g", 120, 110, "🦟", "odomos, mosquito cream", 45),
                    ("Hit Cockroach Killer Spray", "Hit", "400 ml", 245, 220, "🪳", "hit, cockroach, insect spray, kitchen spray", 45),
                ],
            },
        ],
    },
]

# Aisle sections: (aisle name, top-level category slugs shelved there).
SECTIONS = {
    "fv": ("Fruits & Vegetables", ["fruits-vegetables"]),
    "dairy": ("Dairy, Bread & Eggs", ["dairy-bread-eggs"]),
    "staples": ("Atta, Rice & Dal", ["atta-rice-dal"]),
    "cooking": ("Oil, Ghee & Masala", ["oil-ghee-masala"]),
    "snacks": ("Snacks & Biscuits", ["snacks-munchies"]),
    "sweets": ("Sweets & Breakfast", ["sweets-chocolates", "breakfast-spreads"]),
    "drinks": ("Beverages", ["cold-drinks-juices", "tea-coffee"]),
    "frozen": ("Instant & Frozen", ["instant-frozen"]),
    "care": ("Personal Care", ["personal-care"]),
    "home": ("Cleaning & Home", ["cleaning-essentials"]),
}

STORES = [
    {
        "name": "Smart Cart · Sector 29",
        "slug": "sector-29",
        "address": "SCO 42, Sector 29 Market, Gurugram, Haryana",
        "city": "Gurugram",
        "pincode": "122001",
        "lat": 28.4682,
        "lng": 77.0632,
        "phone": "01244001029",
        "opens_at": time(0, 0),  # open 24 hours
        "closes_at": time(0, 0),
        "pickup_start": time(8, 0),
        "pickup_end": time(22, 0),
        "layout_rows": 6,
        "aisle_order": ["fv", "dairy", "staples", "cooking", "snacks", "sweets", "drinks", "frozen", "care", "home"],
        "skip_ratio": 0.0,
    },
    {
        "name": "Smart Cart · DLF Phase 3",
        "slug": "dlf-phase-3",
        "address": "Shop 7, U Block Market, DLF Phase 3, Gurugram, Haryana",
        "city": "Gurugram",
        "pincode": "122010",
        "lat": 28.4925,
        "lng": 77.0947,
        "phone": "01244001003",
        "opens_at": time(6, 0),
        "closes_at": time(2, 0),  # closes after midnight
        "pickup_start": time(9, 0),
        "pickup_end": time(21, 0),
        "layout_rows": 5,
        "aisle_order": ["drinks", "snacks", "sweets", "frozen", "dairy", "fv", "staples", "cooking", "home", "care"],
        "skip_ratio": 0.0,
    },
    {
        "name": "Smart Cart · Sohna Road",
        "slug": "sohna-road",
        "address": "Ground Floor, Omaxe City Centre, Sohna Road, Gurugram, Haryana",
        "city": "Gurugram",
        "pincode": "122018",
        "lat": 28.4156,
        "lng": 77.0453,
        "phone": "01244001018",
        "opens_at": time(7, 0),
        "closes_at": time(23, 0),
        "pickup_start": time(8, 0),
        "pickup_end": time(21, 0),
        "layout_rows": 7,
        "aisle_order": ["dairy", "fv", "frozen", "drinks", "snacks", "sweets", "staples", "cooking", "care", "home"],
        "skip_ratio": 0.08,  # a smaller store that doesn't carry some slower-moving items
    },
]

# Demo accounts (log in with the OTP shown on screen in dev mode).
STAFF_USERS = [
    {"phone": "9000000001", "name": "Ravi (Sector 29 store)", "role": "staff", "store_slug": "sector-29"},
    {"phone": "9000000002", "name": "Neha (DLF Phase 3 store)", "role": "staff", "store_slug": "dlf-phase-3"},
    {"phone": "9000000003", "name": "Aman (Sohna Road store)", "role": "staff", "store_slug": "sohna-road"},
    {"phone": "9999999999", "name": "Admin", "role": "admin", "store_slug": None},
]

DEMO_CUSTOMER = {
    "phone": "9876543210",
    "name": "Demo Customer",
    "address": {
        "label": "Home",
        "receiver_name": "Demo Customer",
        "receiver_phone": "9876543210",
        "house": "House 1204, Block C",
        "area": "Sector 29",
        "landmark": "Near Leisure Valley Park",
        "city": "Gurugram",
        "pincode": "122001",
        "lat": 28.4655,
        "lng": 77.0661,
    },
}
