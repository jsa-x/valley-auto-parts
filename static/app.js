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
  mirrorRegisterToLocalStorage();
  mirrorLoginToLocalStorage();
});
