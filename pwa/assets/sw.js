self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open('herecrm-v1').then(function(cache) {
            return cache.addAll([
                'icon-192.png',
                'icon-512.png'
            ]);
        })
    );
});

self.addEventListener('fetch', function(event) {
    event.respondWith(
        fetch(event.request).catch(function() {
            return caches.match(event.request);
        })
    );
});
