const loginBtn = document.getElementById("loginBtn");
const dropdownMenu = document.getElementById("dropdownMenu");

if (loginBtn && dropdownMenu) {
    loginBtn.addEventListener("click", () => {
        dropdownMenu.style.display =
            dropdownMenu.style.display === "block" ? "none" : "block";
    });

    window.addEventListener("click", (e) => {
        if (!e.target.closest("#loginBtn")) {
            dropdownMenu.style.display = "none";
        }
    });
}
