# Corner Shop — online shop for a small coffee and tea roaster

**Mode:** dynamic (web app with its own backend)
**Matches:** `frontend-specs/shop-dynamic.json` + `specs/shop.json`

Corner Shop roasts coffee and blends tea in a small shop on the high street and wants to sell online.

## Who uses it

Customers browsing on their phone or laptop. No accounts for now: anyone can browse, fill a cart and send a
message. (Checkout, payment and customer logins come later.)

## Pages

1. **Home** — a hero with the line "Coffee and tea, roasted down the street", a short subline ("Small batches,
   shipped the same day."), a photo of coffee beans and a "Shop now" button that goes to the catalogue. Below
   it, the product categories as cards.
2. **Products** — the catalogue: product cards with name, price and photo, newest first, 12 per page.
3. **Product detail** — one product: photo, name, description, price and how many are in stock, plus an
   "Add to cart" form with a quantity (1 to 99). After adding, show "Added to cart" and go to the cart.
4. **Cart** — the items in the cart with their quantity; if it is empty, say "Your cart is empty".
5. **Contact** — the shop's e-mail (hello@corner.shop) and address (1 High Street), and a contact form with name,
   e-mail and message. After sending, show "Thanks, we will get back to you".
6. **About** — "Our story: two friends, one roaster", a photo of the shop front, and two customer quotes.

Navigation: Shop, Cart, Contact in the header; About and Contact in the footer ("© Corner Shop").

## Data

- **Categories** — name (unique). Start with "Coffee" and "Tea".
- **Products** — category, name, description, price (never negative), photo URL, stock (default 0), created at.
  Start with: "House blend, 250 g" (coffee, 9.50, 40 in stock), "Single origin Ethiopia, 250 g" (coffee, 13.00,
  12 in stock), "Sencha, 100 g" (tea, 7.25, 25 in stock).
- **Cart items** — a product and a quantity (1–99). They can be listed, added, changed and removed.
- **Contact messages** — name, e-mail, message, received at. Only created from the site.

The catalogue can be filtered by category, sorted by name, price or date, and searched by name or description.

## Look and feel

Clean and minimal, light and dark mode, a strong blue (#1d4ed8) for buttons and links, amber (#f59e0b) as an
accent. Rounded corners, comfortable spacing, the Inter typeface.

## Done when

The shop runs on its own backend: the catalogue shows the three products, a product can be added to the cart
and appears there, and a contact message is stored. Before the backend is ready, the same pages work on example
data.
