// ---------- ADD TO CART ----------
function addToCart(productId) {
  fetch("/api/session")
    .then(res => res.json())
    .then(sess => {
      if (!sess.logged_in) {
        alert("You must be logged in to add items to cart.");
        return;
      }
      const username = sess.username;
      const key = "cart_" + username;
      const cart = JSON.parse(localStorage.getItem(key) || "[]");
      cart.push(productId);
      localStorage.setItem(key, JSON.stringify(cart));
      alert("Added to cart!");
    });
}

// hook click handlers for all "Add to Cart" buttons
function setupAddButtons() {
  document.querySelectorAll(".add-btn[data-id]").forEach(btn => {
    btn.addEventListener("click", e => {
      const pid = e.target.getAttribute("data-id");
      if (pid) addToCart(pid);
    });
  });
}

// ---------- LIVE PRODUCT SEARCH + VEHICLE FILTER ----------

// format price as $xx.xx
const fmtPrice = price => `$${price.toFixed(2)}`;

// highlight match using <mark>
function highlight(text, q) {
  if (!q) return text;
  const safe = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); // escape regex chars
  return text.replace(new RegExp(safe, "ig"), m => `<mark>${m}</mark>`);
}

// filter products by query AND selected vehicle
function searchProducts(products, q, vehicle) {
  q = q.trim().toLowerCase();
  vehicle = (vehicle || "").trim().toLowerCase();

  return products.filter(p => {
    const name = (p.name || "").toLowerCase();
    const category = (p.category || "").toLowerCase();
    const fitment = (p.fitment || "").toLowerCase();

    const matchesText =
      !q ||
      name.includes(q) ||
      category.includes(q) ||
      fitment.includes(q);

    const matchesVehicle =
      !vehicle || fitment.includes(vehicle); // vehicle must be in fitment string

    return matchesText && matchesVehicle;
  });
}

// render product cards into #list (used by shop page)
function renderProducts(products, q = "") {
  const listEl = document.getElementById("list");
  const countEl = document.getElementById("count");
  if (!listEl) return;

  listEl.innerHTML = "";
  if (countEl) {
    countEl.textContent = `${products.length} parts found`;
  }

  for (const p of products) {
    const card = document.createElement("div");
    card.className =
      "product-card bg-white border border-slate-200 rounded-xl shadow-sm flex flex-col overflow-hidden";

    const highlightedName = highlight(p.name, q);

    card.innerHTML = `
      <div class="product-img-wrap bg-slate-200">
        <img
          class="product-img w-full h-44 object-cover"
          src="${p.img}"
          alt="${p.name}"
        >
      </div>

      <div class="product-info flex flex-col p-4 flex-1">
        <div class="product-format mb-2">
          <span class="inline-block bg-slate-800 text-white text-[0.7rem] font-medium rounded px-2 py-1">
            ${p.category || "Part"}
          </span>
        </div>

        <div class="product-title text-slate-900 font-semibold text-sm leading-snug">
          ${highlightedName}
        </div>

        <div class="product-fitment text-[0.8rem] text-slate-600 mt-1">
          ${p.fitment || ""}
        </div>

        <div class="product-desc text-[0.8rem] text-slate-500 mt-3 flex-1">
          ${p.description || ""}
        </div>

        <div class="product-bottom flex items-center justify-between border-t border-slate-200 mt-4 pt-3">
          <div class="product-price text-slate-900 font-semibold text-sm">
            ${fmtPrice(p.price)}
          </div>

          ${
            p.logged_in
              ? `
            <button
              class="add-btn bg-blue-600 hover:bg-blue-700 text-white text-[0.75rem] font-semibold rounded-md px-3 py-1.5 transition"
              data-id="${p.id}"
            >
              Add to Cart
            </button>
          `
              : `
            <button
              class="add-btn bg-slate-400 text-white text-[0.75rem] font-semibold rounded-md px-3 py-1.5 cursor-not-allowed"
              disabled
            >
              Login to buy
            </button>
          `
          }
        </div>
      </div>
    `;

    listEl.appendChild(card);
  }

  // after rendering, wire up add-to-cart buttons
  setupAddButtons();
}

// set up live search (+ vehicle filter) using #search, #vehicleSelect, #list
function setupLiveSearch() {
  const searchInput = document.getElementById("search");
  const listEl = document.getElementById("list");
  const vehicleSelect = document.getElementById("vehicleSelect");
  if (!searchInput || !listEl) return;   // not on shop page
  if (!window.PRODUCTS) return;          // no products exposed

  fetch("/api/session")
    .then(res => res.json())
    .then(sess => {
      const loggedIn = !!sess.logged_in;

      // copy PRODUCTS and attach logged_in flag
      const baseProducts = window.PRODUCTS.map(p => ({
        ...p,
        logged_in: loggedIn
      }));

      // initial render of all products
      renderProducts(baseProducts, "");

      let timeout = null;
      function applyFilters() {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
          const q = searchInput.value;
          const vehicle = vehicleSelect ? vehicleSelect.value : "";
          const results = searchProducts(baseProducts, q, vehicle);
          renderProducts(results, q);
        }, 250);
      }

      searchInput.addEventListener("input", applyFilters);
      if (vehicleSelect) {
        vehicleSelect.addEventListener("change", applyFilters);
      }
    });
}

// ---------- CART PAGE RENDERING ----------
function renderCartPage() {
  const root = document.getElementById("cartRoot");
  if (!root) return; // not on cart page

  fetch("/api/session")
    .then(res => res.json())
    .then(sess => {
      if (!sess.logged_in) {
        root.innerHTML = `
          <p class="text-sm text-slate-600">
            You must be logged in to view your cart.
          </p>
        `;
        return;
      }

      const username = sess.username;
      const key = "cart_" + username;
      const cartIds = JSON.parse(localStorage.getItem(key) || "[]");

      if (cartIds.length === 0) {
        root.innerHTML = `
          <p class="text-sm text-slate-600">
            Your cart is currently empty.
          </p>
        `;
        return;
      }

      // Fetch product info
      fetch("/api/products")
        .then(res => res.json())
        .then(products => {
          const counts = {};
          cartIds.forEach(id => {
            counts[id] = (counts[id] || 0) + 1;
          });

          let total = 0;
          const rows = [];

          Object.keys(counts).forEach(id => {
            const prod = products.find(p => p.id === id);
            if (!prod) return;
            const qty = counts[id];
            const lineTotal = prod.price * qty;
            total += lineTotal;

            rows.push(`
              <tr class="border-b border-slate-200">
                <td class="py-2 pr-4">
                  <div class="font-medium text-slate-800 text-sm">${prod.name}</div>
                  <div class="text-xs text-slate-500">${prod.fitment || ""}</div>
                </td>
                <td class="py-2 text-center text-sm">${qty}</td>
                <td class="py-2 text-right text-sm">$${prod.price.toFixed(2)}</td>
                <td class="py-2 text-right text-sm">$${lineTotal.toFixed(2)}</td>
              </tr>
            `);
          });

          root.innerHTML = `
            <div class="overflow-x-auto">
              <table class="w-full text-left text-sm">
                <thead>
                  <tr class="border-b border-slate-300 text-xs uppercase text-slate-500">
                    <th class="py-2 pr-4">Item</th>
                    <th class="py-2 text-center">Qty</th>
                    <th class="py-2 text-right">Price</th>
                    <th class="py-2 text-right">Subtotal</th>
                  </tr>
                </thead>
                <tbody>
                  ${rows.join("")}
                </tbody>
              </table>
            </div>

            <div class="flex justify-between items-center mt-4">
              <div class="text-sm text-slate-500">
                Items in cart: ${cartIds.length}
              </div>
              <div class="text-right">
                <div class="text-xs text-slate-500">Total</div>
                <div class="text-lg font-semibold text-slate-900">
                  $${total.toFixed(2)}
                </div>
              </div>
            </div>

            <div class="mt-4 flex justify-end">
              <button
                id="checkoutBtn"
                class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-md px-4 py-2 transition"
              >
                Proceed to Payment
              </button>
            </div>
          `;

          const checkoutBtn = document.getElementById("checkoutBtn");
          if (checkoutBtn) {
            checkoutBtn.addEventListener("click", () => {
              // Save the current cart as a "pending order" for this user
              const pendingKey = "pending_order_" + username;
              localStorage.setItem(pendingKey, JSON.stringify(cartIds));

              // Go to the mock payment page
              window.location.href = "/payment";
            });
          }
        });
    });
}

// ---------- PAYMENT PAGE RENDERING ----------
function renderPaymentPage() {
  const root = document.getElementById("paymentRoot");
  if (!root) return; // not on payment page

  fetch("/api/session")
    .then(res => res.json())
    .then(sess => {
      if (!sess.logged_in) {
        root.innerHTML = `
          <p class="text-sm text-slate-600">
            You must be logged in to complete payment.
          </p>
        `;
        return;
      }

      const username = sess.username;
      const pendingKey = "pending_order_" + username;
      const cartKey = "cart_" + username;
      const pendingIds = JSON.parse(localStorage.getItem(pendingKey) || "[]");

      if (pendingIds.length === 0) {
        root.innerHTML = `
          <p class="text-sm text-slate-600">
            There is no pending order to pay for. Go back to your cart and add items.
          </p>
        `;
        return;
      }

      // Fetch product info to show summary
      fetch("/api/products")
        .then(res => res.json())
        .then(products => {
          const counts = {};
          pendingIds.forEach(id => {
            counts[id] = (counts[id] || 0) + 1;
          });

          let total = 0;
          const rows = [];

          Object.keys(counts).forEach(id => {
            const prod = products.find(p => p.id === id);
            if (!prod) return;
            const qty = counts[id];
            const lineTotal = prod.price * qty;
            total += lineTotal;

            rows.push(`
              <tr class="border-b border-slate-200">
                <td class="py-2 pr-4">
                  <div class="font-medium text-slate-800 text-sm">${prod.name}</div>
                  <div class="text-xs text-slate-500">${prod.fitment || ""}</div>
                </td>
                <td class="py-2 text-center text-sm">${qty}</td>
                <td class="py-2 text-right text-sm">$${prod.price.toFixed(2)}</td>
                <td class="py-2 text-right text-sm">$${lineTotal.toFixed(2)}</td>
              </tr>
            `);
          });

          root.innerHTML = `
            <div class="grid gap-4 md:grid-cols-2">
              <!-- Order summary -->
              <div>
                <h2 class="font-semibold text-slate-800 mb-2 text-sm">
                  Order Summary
                </h2>
                <div class="overflow-x-auto border border-slate-200 rounded-lg">
                  <table class="w-full text-left text-sm">
                    <thead>
                      <tr class="border-b border-slate-300 text-xs uppercase text-slate-500">
                        <th class="py-2 pr-4">Item</th>
                        <th class="py-2 text-center">Qty</th>
                        <th class="py-2 text-right">Price</th>
                        <th class="py-2 text-right">Subtotal</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${rows.join("")}
                    </tbody>
                  </table>
                </div>
                <div class="flex justify-between items-center mt-3">
                  <span class="text-xs text-slate-500">Total</span>
                  <span class="text-lg font-semibold text-slate-900">
                    $${total.toFixed(2)}
                  </span>
                </div>
              </div>

              <!-- Mock Stripe payment form -->
              <div>
                <h2 class="font-semibold text-slate-800 mb-2 text-sm">
                  Payment Details (Mock Stripe)
                </h2>
                <p class="text-xs text-slate-500 mb-3">
                  This simulates where Stripe would be called. No real card data is sent.
                </p>

                <div class="space-y-2 text-sm">
                  <div>
                    <label class="block text-xs text-slate-600 mb-1">
                      Card Number
                    </label>
                    <input
                      type="text"
                      class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                      placeholder="4242 4242 4242 4242"
                    >
                  </div>

                  <div class="flex gap-2">
                    <div class="flex-1">
                      <label class="block text-xs text-slate-600 mb-1">
                        Expiration
                      </label>
                      <input
                        type="text"
                        class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                        placeholder="12/34"
                      >
                    </div>
                    <div class="w-24">
                      <label class="block text-xs text-slate-600 mb-1">
                        CVC
                      </label>
                      <input
                        type="text"
                        class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                        placeholder="123"
                      >
                    </div>
                  </div>

                  <button
                    id="payBtn"
                    class="mt-4 w-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-md px-4 py-2 transition"
                  >
                    Pay Now
                  </button>
                </div>
              </div>
            </div>
          `;

          const payBtn = document.getElementById("payBtn");
          if (payBtn) {
            payBtn.addEventListener("click", () => {
              // In a real app, Stripe would be called here.
              // For this assignment, we just create the order and redirect.
              fetch("/api/orders", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ items: pendingIds })
              })
                .then(res => res.json())
                .then(data => {
                  if (!data.ok) {
                    alert("There was a problem placing your order.");
                    return;
                  }
                  // Clear pending + cart
                  localStorage.removeItem(pendingKey);
                  localStorage.removeItem(cartKey);
                  // Go to orders page (order success banner will show)
                  window.location.href = "/orders";
                })
                .catch(() => {
                  alert("There was a problem placing your order.");
                });
            });
          }
        });
    });
}

// ---------- LOCALSTORAGE MIRRORS FOR RUBRIC ----------
function mirrorRegisterToLocalStorage() {
  const regForm = document.getElementById("registerForm");
  if (!regForm) return;

  regForm.addEventListener("submit", () => {
    const username = regForm.username.value.trim();
    const email = regForm.email.value.trim();
    const password = regForm.password.value;

    if (!username || !email || !password) return;

    const usersLS = JSON.parse(localStorage.getItem("users") || "[]");
    if (!usersLS.find(u => u.username === username)) {
      usersLS.push({ username, email, password });
      localStorage.setItem("users", JSON.stringify(usersLS));
    }
  });
}

function mirrorLoginToLocalStorage() {
  const loginForm = document.getElementById("loginForm");
  if (!loginForm) return;

  loginForm.addEventListener("submit", () => {
    const username = loginForm.username.value.trim();
    if (username) {
      localStorage.setItem("sessionUser", username);
    }
  });
}

// ---------- BOOTSTRAP ON PAGE LOAD ----------
document.addEventListener("DOMContentLoaded", () => {
  setupLiveSearch();       // shop page (search + vehicle filter)
  renderCartPage();        // cart page
  renderPaymentPage();     // payment page
  mirrorRegisterToLocalStorage();
  mirrorLoginToLocalStorage();
});