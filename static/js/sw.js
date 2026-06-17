self.addEventListener('push', function (event) {
  var data = {};
  try { data = event.data.json(); } catch (e) {}
  var title = data.title || 'Nostradamus Cup 2026';
  var options = {
    body: data.body || '',
    icon: '/static/img/icon-192.png',
    badge: '/static/img/icon-192.png',
    data: { url: data.url || '/' }
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  var url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(clients.openWindow(url));
});
