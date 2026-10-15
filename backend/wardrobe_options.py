"""Allowed values for wardrobe item details.

The frontend loads these from GET /api/options, so dropdowns and
backend validation always agree. The recommendation engine (Phase 3)
will rely on the same lists.
"""

CATEGORIES = ["Clothing", "Jewellery", "Footwear", "Bags", "Accessories"]

STYLES = ["Traditional", "Western", "Indo-Western"]

OCCASIONS = [
    "Casual",
    "College",
    "Office",
    "Formal",
    "Party",
    "Festive",
    "Wedding",
    "Traditional function",
    "Date",
    "Travel",
]

# Suggestions only: users may type any garment type.
ITEM_TYPE_SUGGESTIONS = {
    "Clothing": [
        "Kurta", "Kurti", "Saree", "Blouse", "Dupatta", "Lehenga", "Salwar",
        "Churidar", "Palazzo", "Leggings", "Gown", "Dress", "Top", "Shirt",
        "T-shirt", "Jeans", "Trousers", "Skirt", "Jacket", "Shrug",
    ],
    "Jewellery": [
        "Earrings", "Jhumkas", "Necklace", "Bangles", "Bracelet", "Ring",
        "Maang tikka", "Nose pin", "Anklet",
    ],
    "Footwear": ["Juttis", "Kolhapuris", "Sandals", "Heels", "Flats", "Sneakers", "Boots"],
    "Bags": ["Clutch", "Potli", "Handbag", "Tote", "Sling bag", "Backpack"],
    "Accessories": ["Watch", "Belt", "Scarf", "Sunglasses", "Hair accessory"],
}
