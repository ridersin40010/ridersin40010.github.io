// スクロールでヘッダーに影をつける
const header = document.querySelector('.site-header');

const updateHeader = () => {
  header.classList.toggle('scrolled', window.scrollY > 20);
};

window.addEventListener('scroll', updateHeader, { passive: true });
updateHeader();
