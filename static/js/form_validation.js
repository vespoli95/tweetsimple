document.addEventListener('submit', e => {
    let password_test = document.querySelector('input[name=password]');
    let password_confirm = document.querySelector('input[name=confirm_password]');

    if (password_test.value !== password_confirm.value){
        alert('Passwords do not match!');
        e.preventDefault();
    } else
        document.getElementById('register_form').submit();
});
