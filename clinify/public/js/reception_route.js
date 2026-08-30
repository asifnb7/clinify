(() => {
    const fix_reception_link = () => {
        const link = document.querySelector(
            '.sidebar-item-container[item-name="Reception"] a.item-anchor'
        );

        if (link) {
            link.setAttribute("href", "/app/reception-dashboard");
        }
    };

    fix_reception_link();

    new MutationObserver(fix_reception_link).observe(document.body, {
        childList: true,
        subtree: true
    });
})();
