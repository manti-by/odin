import { api } from "@/lib/api/client";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

function getBrowser(): string {
  const userAgent = navigator.userAgent;
  if (userAgent.includes("Edg")) return "edge";
  if (userAgent.includes("Firefox")) return "firefox";
  if (userAgent.includes("Chrome")) return "chrome";
  if (userAgent.includes("Safari")) return "safari";
  return "other";
}

async function registerPush(
  serviceWorkerRegistration: ServiceWorkerRegistration,
  applicationServerKey: string,
): Promise<void> {
  if (Notification.permission === "denied") {
    console.log("Notification permission denied, skipping push registration");
    return;
  }

  try {
    const existingSubscription = await serviceWorkerRegistration.pushManager.getSubscription();
    if (existingSubscription) {
      console.log("Existing push subscription found, skipping subscribe");
      return;
    }

    const subscription = await serviceWorkerRegistration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(applicationServerKey) as BufferSource,
    });

    await api.post("core/devices/", {
      subscription: subscription.toJSON(),
      browser: getBrowser(),
    });

    console.log("Push notifications registered successfully");
  } catch (error) {
    console.error("Push registration failed:", error);
  }
}

export async function initPwa(): Promise<void> {
  if (!("serviceWorker" in navigator)) {
    console.error("Service Workers not supported");
    return;
  }

  try {
    const registration = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
    console.log("Service Worker registered:", registration.scope);

    let applicationServerKey = "";
    try {
      const data: { application_server_key: string } = await api.get("core/app-server-key/");
      applicationServerKey = data.application_server_key || "";
    } catch (error) {
      console.error("Failed to fetch application server key:", error);
    }

    if (applicationServerKey) {
      await registerPush(registration, applicationServerKey);
    }
  } catch (error) {
    console.error("Service Worker registration failed:", error);
  }
}
