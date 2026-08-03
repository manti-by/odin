/// <reference lib="webworker" />

import { clientsClaim } from "workbox-core";
import type { PrecacheEntry } from "workbox-precaching";
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from "workbox-precaching";
import { NavigationRoute, registerRoute } from "workbox-routing";

declare global {
  interface ServiceWorkerGlobalScope {
    __WB_MANIFEST: (string | PrecacheEntry)[];
  }
}

declare const self: ServiceWorkerGlobalScope;

precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

registerRoute(new NavigationRoute(createHandlerBoundToURL("/static/index.html")));

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event: ExtendableEvent) => {
  event.waitUntil(Promise.resolve(clientsClaim()));
});

interface PwaNotificationAction {
  action: string;
  title: string;
  icon?: string;
}

interface PwaNotificationOptions extends NotificationOptions {
  actions?: PwaNotificationAction[];
  badge?: string;
  requireInteraction?: boolean;
  vibrate?: number[];
}

self.addEventListener("push", (event: PushEvent) => {
  let data: Record<string, unknown> = {};
  try {
    data = event.data?.json() || {};
  } catch {
    console.error("Failed to parse push payload as JSON");
  }

  const options: PwaNotificationOptions = {
    body: (data.body as string) || "",
    icon: (data.icon as string) || "/static/favicon/128.png",
    badge: (data.badge as string) || "/static/favicon/32.png",
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: data.tag || 1,
      url: data.url || "/",
    },
    actions: [
      { action: "open", title: "Open" },
      { action: "close", title: "Close" },
    ],
    tag: (data.tag as string) || "default",
    requireInteraction: true,
  };

  event.waitUntil(self.registration.showNotification((data.title as string) || "ODIN", options));
});

self.addEventListener("notificationclick", (event: NotificationEvent) => {
  event.notification.close();

  if (event.action === "close") {
    return;
  }

  const targetUrl = event.notification.data?.url || "/";
  let resolvedUrl: string;
  try {
    resolvedUrl = new URL(targetUrl, self.location.origin).href;
    if (new URL(resolvedUrl).origin !== self.location.origin) {
      resolvedUrl = "/";
    }
    if (!/^https?:\/\//.test(resolvedUrl)) {
      resolvedUrl = "/";
    }
  } catch {
    resolvedUrl = "/";
  }
  const targetPath = new URL(resolvedUrl, self.location.origin).pathname;

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        const clientPath = new URL(client.url).pathname;
        if (clientPath === targetPath && "focus" in client) {
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(resolvedUrl);
      }
    }),
  );
});

self.addEventListener("notificationclose", (event: NotificationEvent) => {
  console.log("Notification closed:", event.notification.tag);
});
