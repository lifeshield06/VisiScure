document.addEventListener('DOMContentLoaded', function() {
    const loginBtn = document.getElementById('loginBtn');
    const dropdownContent = document.getElementById('dropdownContent');

    loginBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdownContent.classList.toggle('show');
    });

    document.addEventListener('click', function() {
        dropdownContent.classList.remove('show');
    });

    dropdownContent.addEventListener('click', function(e) {
        e.stopPropagation();
    });
});