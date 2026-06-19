self.addEventListener('push', function (event) {
  var data = {};
  try { data = event.data.json(); } catch (e) {}
  var title = data.title || 'Nostradamus Cup 2026';
  var body = data.body || '';
  var url = data.url || '/';
  var tag = url.replace(/\//g, '') || 'general';
  var isChat = tag === 'chat';

  event.waitUntil(
    self.registration.getNotifications({tag: tag}).then(function (existing) {
      var count = existing.length + 1;
      var options = {
        icon: '/static/img/icon-192.png',
        badge: '/static/img/icon-192.png',
        tag: tag,
        renotify: true,
        data: {url: url}
      };
      if (count > 1) {
        options.body = count + ' new notifications';
      } else {
        options.body = body;
      }
      if (isChat) {
        options.actions = [{
          action: 'reply',
          type: 'text',
          title: 'Reply',
          placeholder: 'Type a reply…'
        }];
      }
      return self.registration.showNotification(title, options);
    }));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  var url = (event.notification.data && event.notification.data.url) || '/';

  if (event.action === 'reply' && event.reply) {
    event.waitUntil(
      cookieStore.get('csrftoken').then(function (cookie) {
        return fetch('/chat/', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'X-CSRFToken': cookie ? cookie.value : '',
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: 'text=' + encodeURIComponent(event.reply)
        });
      }).catch(function () {
        return clients.openWindow(url);
      }));
    return;
  }

  event.waitUntil(clients.openWindow(url));
});
