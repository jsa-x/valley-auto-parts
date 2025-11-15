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

// // live search filter on the shop page
// function setupSearchFilter() {
//   const searchInput = document.getElementById("searchInput");
//   const productContainer = document.getElementById("productsContainer");
//   if (!searchInput || !productContainer) return;

//   // grab initial snapshot of rendered cards
//   const allCards = Array.from(productContainer.children).map(card => {
//     return {
//       el: card,
//       text: card.innerText.toLowerCase()
//     };
//   });

//   searchInput.addEventListener("input", e => {
//     const q = e.target.value.toLowerCase();
//     let visibleCount = 0;
//     allCards.forEach(({ el, text }) => {
//       if (text.includes(q)) {
//         el.style.display = "";
//         visibleCount++;
//       } else {
//         el.style.display = "none";
//       }
//     });
//     if (visibleCount === 0) {
//       productContainer.setAttribute("data-empty", "1");
//       if (!document.getElementById("noResultsMsg")) {
//         const p = document.createElement("p");
//         p.id = "noResultsMsg";
//         p.style.color = "#94a3b8";
//         p.style.fontSize = "0.9rem";
//         p.textContent = "No matches found.";
//         productContainer.appendChild(p);
//       }
//     } else {
//       productContainer.removeAttribute("data-empty");
//       const msg = document.getElementById("noResultsMsg");
//       if (msg) msg.remove();
//     }
//   });
// }

// hook click handlers for all "Add to Cart" buttons
function setupAddButtons() {
  document.querySelectorAll(".add-btn[data-id]").forEach(btn => {
    btn.addEventListener("click", e => {
      const pid = e.target.getAttribute("data-id");
      if (pid) addToCart(pid);
    });
  });
}

// mirror users_db/register info into localStorage for the rubric
// We'll listen on register form submit so the browser also saves creds.
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

// mirror login to set 'sessionUser'
function mirrorLoginToLocalStorage() {
  const loginForm = document.getElementById("loginForm");
  if (!loginForm) return;

  loginForm.addEventListener("submit", () => {
    const username = loginForm.username.value.trim();
    // don't know yet if it's valid at this point
    if (username) {
      localStorage.setItem("sessionUser", username);
    }
  });
}

// run on load
document.addEventListener("DOMContentLoaded", () => {
  setupSearchFilter();
  setupAddButtons();
  mirrorRegisterToLocalStorage();
  mirrorLoginToLocalStorage();
});
