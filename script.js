const menuButton = document.querySelector('.menu-button');
const siteNav = document.querySelector('.site-nav');

if (menuButton && siteNav) {
  menuButton.addEventListener('click', () => {
    const isOpen = siteNav.classList.toggle('open');
    menuButton.setAttribute('aria-expanded', String(isOpen));
    menuButton.textContent = isOpen ? '关闭' : '菜单';
  });

  siteNav.addEventListener('click', () => {
    siteNav.classList.remove('open');
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.textContent = '菜单';
  });
}

document.querySelectorAll('[data-current-year]').forEach((element) => {
  element.textContent = new Date().getFullYear();
});
