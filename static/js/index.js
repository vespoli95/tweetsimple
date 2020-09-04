  document.addEventListener('click', e => {
    if (e.target.className.indexOf('card-body') > -1){
      let action = '/categories/' + e.target.innerText
      console.log(action)
      e.target.className += ' light_blue'
      document.getElementById("categories").action = action;
      document.getElementById("categories").submit();
    }
});