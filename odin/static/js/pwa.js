document.addEventListener("DOMContentLoaded", (event) => {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/static/js/sw.js").then(
        (registration) => {
          console.log("SW registered:", registration.scope);
        },
        (error) => {
          console.log("SW registration failed:", error);
        },
      );
    });
  }
});
