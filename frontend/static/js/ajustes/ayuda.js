function toggleFaq(btn){btn.closest('.faq-item').classList.toggle('open')}

delegar('click', '[data-faq-alternar]', toggleFaq);
