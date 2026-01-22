document.addEventListener("DOMContentLoaded", async () => {
  if (!("serviceWorker" in navigator)) {
    console.error("Service Workers not supported");
    return;
  }

  let applicationServerKey = "";

  try {
    const response = await fetch("/api/v1/core/vapid/");
    const data = await response.json();
    applicationServerKey = data.server_key || "";
  } catch (error) {
    console.error("Failed to fetch application server key:", error);
    return;
  }

  if (!applicationServerKey) {
    console.error("Application erver key not configured");
    return;
  }

  navigator.serviceWorker.register("/static/js/sw.js").then(
    (registration) => {
      console.log("Service Worker registered:", registration.scope);
      registerPush(registration, applicationServerKey);
    },
    (error) => {
      console.error("Service Worker registration failed:", error);
    },
  );
});

async function registerPush(serviceWorkerRegistration, vapidPublicKey) {
  try {
    const subscription = await serviceWorkerRegistration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
    });

    await fetch("/api/v1/core/devices/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        subscription: subscription.toJSON(),
        browser: getBrowser(),
      }),
    });

    console.log("Push notifications registered successfully");
  } catch (error) {
    console.error("Push registration failed:", error);
  }
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

function getBrowser() {
  const userAgent = navigator.userAgent;
  if (userAgent.includes("Chrome")) return "chrome";
  if (userAgent.includes("Firefox")) return "firefox";
  if (userAgent.includes("Safari") && !userAgent.includes("Chrome"))
    return "safari";
  if (userAgent.includes("Edge")) return "edge";
  return "other";
}
